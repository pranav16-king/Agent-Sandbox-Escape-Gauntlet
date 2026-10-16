import { WebSocketServer, WebSocket } from 'ws';
import { LiveEvent } from '../src/api/types';

const PORT = 8765;
let globalSeq = 1;

console.log(`Starting sandboxX Mock Replay Server on port ${PORT}...`);
const wss = new WebSocketServer({ port: PORT });

wss.on('connection', (ws: WebSocket) => {
  console.log('Client connected to mock WebSocket stream.');

  const interval = setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) {
      const resEvent: LiveEvent = {
        v: 1,
        seq: ++globalSeq,
        ts: new Date().toISOString(),
        type: 'resources',
        data: {
          cpu_pct: +(10 + Math.random() * 8).toFixed(1),
          mem_mb: Math.floor(180 + Math.random() * 20),
          mem_limit_mb: 512,
          disk_mb: 32,
          disk_limit_mb: 256,
          pids: Math.floor(6 + Math.random() * 4),
          pids_limit: 64,
        },
      };
      ws.send(JSON.stringify(resEvent));
    }
  }, 4000);

  ws.on('close', () => clearInterval(interval));
});

console.log(`WebSocket server live at ws://127.0.0.1:${PORT}`);
