import { useEffect } from 'react';
import { useLiveStore } from '@/store/liveStore';
import { LiveEvent } from './types';
import { api } from './rest';

let socket: WebSocket | null = null;
let reconnectTimer: any = null;
let pingInterval: any = null;
let retryCount = 0;
const MAX_RETRY_DELAY = 10000;
let eventBuffer: LiveEvent[] = [];
let animFrameId: number | null = null;

function flushEvents() {
  if (eventBuffer.length > 0) {
    const events = [...eventBuffer];
    eventBuffer = [];
    const store = useLiveStore.getState();
    events.forEach((evt) => store.ingestEvent(evt));
  }
  animFrameId = null;
}

function queueEvent(event: LiveEvent) {
  eventBuffer.push(event);
  if (animFrameId === null) {
    animFrameId = requestAnimationFrame(flushEvents);
  }
}

export function getWsUrl(targetUrl?: string): string {
  if (targetUrl) return targetUrl;
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  // In dev mode (port != 8000), target direct backend on current hostname:8000
  // which works seamlessly for localhost, 127.0.0.1, or network IPs
  const isDev = window.location.port && window.location.port !== '8000';
  const host = isDev ? `${window.location.hostname}:8000` : window.location.host;
  return `${protocol}//${host}/ws`;
}

export function initWebSocket(targetUrl?: string, force = false) {
  if (force && socket) {
    try {
      socket.close();
    } catch {}
    socket = null;
  }

  if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
    return;
  }

  const store = useLiveStore.getState();
  const lastSeq = store.lastSeq;
  const baseUrl = getWsUrl(targetUrl);
  const urlWithSeq = `${baseUrl}${baseUrl.includes('?') ? '&' : '?'}since=${lastSeq}`;

  store.setConnectionStatus('reconnecting', retryCount);

  try {
    socket = new WebSocket(urlWithSeq);

    socket.onopen = () => {
      retryCount = 0;
      store.setConnectionStatus('connected', 0);

      // Start keep-alive ping heartbeat every 10s to keep connection persistently open
      if (pingInterval) clearInterval(pingInterval);
      pingInterval = setInterval(() => {
        if (socket && socket.readyState === WebSocket.OPEN) {
          try {
            socket.send(JSON.stringify({ type: 'ping' }));
          } catch {
            // Socket closing
          }
        }
      }, 10000);

      // Immediately re-sync telemetry snapshot upon connection/reconnection
      api.getSnapshot().then((snapshot) => {
        if (snapshot && snapshot.counts) {
          store.setSnapshot(snapshot);
        }
      }).catch(() => {
        // Background sync catch
      });
    };

    socket.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data) as LiveEvent | { type: string };
        if (parsed && typeof parsed === 'object' && parsed.type === 'pong') {
          return;
        }
        queueEvent(parsed as LiveEvent);
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err, event.data);
      }
    };

    socket.onerror = (err) => {
      console.warn('WebSocket connection error:', err);
    };

    socket.onclose = () => {
      if (pingInterval) {
        clearInterval(pingInterval);
        pingInterval = null;
      }
      socket = null;
      store.setConnectionStatus('offline', retryCount);
      scheduleReconnect(targetUrl);
    };
  } catch (err) {
    console.error('Failed to initialize WebSocket:', err);
    if (pingInterval) {
      clearInterval(pingInterval);
      pingInterval = null;
    }
    scheduleReconnect(targetUrl);
  }
}

function scheduleReconnect(targetUrl?: string) {
  if (reconnectTimer) clearTimeout(reconnectTimer);

  retryCount++;
  const delay = Math.min(1000 * Math.pow(1.5, retryCount), MAX_RETRY_DELAY) + Math.random() * 500;
  useLiveStore.getState().setConnectionStatus('reconnecting', retryCount);

  reconnectTimer = setTimeout(() => {
    initWebSocket(targetUrl);
  }, delay);
}

export function reconnectWebSocket(targetUrl?: string) {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
  initWebSocket(targetUrl, true);
}

export function disconnectWebSocket() {
  if (pingInterval) {
    clearInterval(pingInterval);
    pingInterval = null;
  }
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
  if (socket) {
    socket.close();
    socket = null;
  }
  if (animFrameId !== null) {
    cancelAnimationFrame(animFrameId);
    animFrameId = null;
  }
  useLiveStore.getState().setConnectionStatus('offline', 0);
}

// Auto-reconnect on visibility and online events
if (typeof window !== 'undefined') {
  window.addEventListener('online', () => {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      initWebSocket(undefined, true);
    }
  });

  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
      if (!socket || socket.readyState !== WebSocket.OPEN) {
        initWebSocket(undefined, false);
      }
    }
  });
}

export function useLiveConnection() {
  const connectionStatus = useLiveStore((s) => s.connectionStatus);
  const retryCount = useLiveStore((s) => s.retryCount);

  useEffect(() => {
    initWebSocket();
    return () => {
      // Keep socket alive across component remounts in dev mode
    };
  }, []);

  return { connectionStatus, retryCount, reconnect: () => reconnectWebSocket() };
}
