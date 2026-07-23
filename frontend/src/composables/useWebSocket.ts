import { ref } from "vue";

export interface WSEvent {
  event: string;
  data: Record<string, unknown>;
}

type EventHandler = (data: Record<string, unknown>) => void;

const ws = ref<WebSocket | null>(null);
const connected = ref(false);
const handlers = new Map<string, Set<EventHandler>>();
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

function getWsUrl(): string {
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  const base = import.meta.env.BASE_URL.replace(/\/$/, "");
  return `${proto}//${location.host}${base}/ws`;
}

function connect() {
  if (ws.value?.readyState === WebSocket.OPEN) return;

  const socket = new WebSocket(getWsUrl());

  socket.onopen = () => {
    connected.value = true;
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
  };

  socket.onmessage = (e) => {
    try {
      const msg: WSEvent = JSON.parse(e.data);
      const cbs = handlers.get(msg.event);
      if (cbs) {
        for (const cb of cbs) cb(msg.data);
      }
    } catch {
      /* ignore malformed messages */
    }
  };

  socket.onclose = () => {
    connected.value = false;
    ws.value = null;
    reconnectTimer = setTimeout(connect, 3000);
  };

  socket.onerror = () => {
    socket.close();
  };

  ws.value = socket;

  // 心跳
  const heartbeat = setInterval(() => {
    if (socket.readyState === WebSocket.OPEN) {
      socket.send("ping");
    } else {
      clearInterval(heartbeat);
    }
  }, 30_000);
}

export function useWebSocket() {
  if (!ws.value || ws.value.readyState === WebSocket.CLOSED) {
    connect();
  }

  function on(event: string, handler: EventHandler) {
    if (!handlers.has(event)) handlers.set(event, new Set());
    handlers.get(event)!.add(handler);
  }

  return { connected, on };
}
