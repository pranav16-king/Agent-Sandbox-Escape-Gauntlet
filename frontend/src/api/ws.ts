import { useEffect } from 'react';
import { useLiveStore } from '@/store/liveStore';
import { LiveEvent } from './types';

let socket: WebSocket | null = null;
let reconnectTimer: NodeJS.Timeout | null = null;
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

export function initWebSocket(targetUrl?: string) {
  if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
    return;
  }

  const store = useLiveStore.getState();
  const lastSeq = store.lastSeq;

  let wsUrl = targetUrl;
  if (!wsUrl) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    // If running in Vite dev server (port 5173), default to port 8000
    const host = window.location.port === '5173' ? '127.0.0.1:8000' : window.location.host;
    wsUrl = `${protocol}//${host}/ws`;
  }

  const urlWithSeq = `${wsUrl}${wsUrl.includes('?') ? '&' : '?'}since=${lastSeq}`;

  store.setConnectionStatus(retryCount === 0 ? 'reconnecting' : 'reconnecting', retryCount);

  try {
    socket = new WebSocket(urlWithSeq);

    socket.onopen = () => {
      retryCount = 0;
      store.setConnectionStatus('connected', 0);
    };

    socket.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data) as LiveEvent;
        queueEvent(parsed);
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err, event.data);
      }
    };

    socket.onerror = (err) => {
      console.warn('WebSocket error:', err);
    };

    socket.onclose = () => {
      socket = null;
      store.setConnectionStatus('offline', retryCount);
      scheduleReconnect(targetUrl);
    };
  } catch (err) {
    console.error('Failed to initialize WebSocket:', err);
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

export function disconnectWebSocket() {
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

export function useLiveConnection() {
  const connectionStatus = useLiveStore((s) => s.connectionStatus);
  const retryCount = useLiveStore((s) => s.retryCount);

  useEffect(() => {
    initWebSocket();
    return () => {
      // Keep socket alive across component remounts in dev mode
    };
  }, []);

  return { connectionStatus, retryCount, reconnect: () => initWebSocket() };
}
