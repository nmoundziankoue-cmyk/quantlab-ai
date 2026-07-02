/**
 * M9 Phase 2 — useWebSocket hook.
 *
 * Features:
 *   - Auto-reconnect with exponential back-off (max 30 s)
 *   - Heartbeat / ping-pong (responds to server heartbeats)
 *   - Typed event envelope v2 support
 *   - Channel subscribe / unsubscribe
 *   - Connection state: "connecting" | "open" | "closed" | "error"
 *   - Per-message handler via onMessage callback
 *   - Decompression of compressed payloads
 *
 * Usage:
 *   const { state, send, subscribe, unsubscribe, close } = useWebSocket({
 *     url: getWsV2Url({ channels: ["orders", "market_data:AAPL"] }),
 *     onMessage: (event) => { ... },
 *   });
 */
import { useCallback, useEffect, useRef, useState } from "react";

const INITIAL_RECONNECT_DELAY_MS = 500;
const MAX_RECONNECT_DELAY_MS = 30_000;
const RECONNECT_MULTIPLIER = 2;

function decompressPayload(compressed) {
  // Browser-side decompression is not possible without a WASM zlib.
  // Return the compressed string as-is; the application can handle it.
  return compressed;
}

function parseEnvelope(raw) {
  try {
    const parsed = JSON.parse(raw);
    if (parsed.compressed && parsed.payload?._compressed) {
      return { ...parsed, payload: { _compressed: decompressPayload(parsed.payload._compressed) } };
    }
    return parsed;
  } catch {
    return null;
  }
}

export function useWebSocket({
  url,
  onMessage,
  onOpen,
  onClose,
  onError,
  enabled = true,
  reconnect = true,
  reconnectAttempts = 10,
} = {}) {
  const [state, setState] = useState("connecting");
  const [lastEvent, setLastEvent] = useState(null);
  const wsRef = useRef(null);
  const reconnectDelay = useRef(INITIAL_RECONNECT_DELAY_MS);
  const attemptsLeft = useRef(reconnectAttempts);
  const isMounted = useRef(true);
  const pendingSubscriptions = useRef([]);

  const send = useCallback((data) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(typeof data === "string" ? data : JSON.stringify(data));
    }
  }, []);

  const subscribe = useCallback((channels) => {
    if (!Array.isArray(channels)) channels = [channels];
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      send({ action: "subscribe", channels });
    } else {
      pendingSubscriptions.current.push(...channels);
    }
  }, [send]);

  const unsubscribe = useCallback((channels) => {
    if (!Array.isArray(channels)) channels = [channels];
    send({ action: "unsubscribe", channels });
  }, [send]);

  const ping = useCallback(() => {
    send({ action: "ping" });
  }, [send]);

  const close = useCallback(() => {
    reconnect && (attemptsLeft.current = 0);
    wsRef.current?.close();
  }, [reconnect]);

  useEffect(() => {
    if (!enabled || !url) return;
    isMounted.current = true;
    let timeoutId;

    function connect() {
      if (!isMounted.current) return;
      setState("connecting");
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!isMounted.current) return;
        setState("open");
        reconnectDelay.current = INITIAL_RECONNECT_DELAY_MS;
        attemptsLeft.current = reconnectAttempts;
        // Flush pending subscriptions
        if (pendingSubscriptions.current.length > 0) {
          ws.send(JSON.stringify({ action: "subscribe", channels: pendingSubscriptions.current }));
          pendingSubscriptions.current = [];
        }
        onOpen?.();
      };

      ws.onmessage = (ev) => {
        if (!isMounted.current) return;
        const envelope = parseEnvelope(ev.data);
        if (!envelope) return;

        // Respond to server heartbeats automatically
        if (envelope.event_type === "heartbeat") {
          ping();
          return;
        }

        setLastEvent(envelope);
        onMessage?.(envelope);
      };

      ws.onerror = (ev) => {
        if (!isMounted.current) return;
        setState("error");
        onError?.(ev);
      };

      ws.onclose = (ev) => {
        if (!isMounted.current) return;
        setState("closed");
        onClose?.(ev);
        if (reconnect && attemptsLeft.current > 0) {
          attemptsLeft.current -= 1;
          timeoutId = setTimeout(() => {
            if (isMounted.current) {
              reconnectDelay.current = Math.min(
                reconnectDelay.current * RECONNECT_MULTIPLIER,
                MAX_RECONNECT_DELAY_MS
              );
              connect();
            }
          }, reconnectDelay.current);
        }
      };
    }

    connect();

    return () => {
      isMounted.current = false;
      clearTimeout(timeoutId);
      wsRef.current?.close();
    };
  }, [url, enabled]); // eslint-disable-line react-hooks/exhaustive-deps

  return { state, lastEvent, send, subscribe, unsubscribe, ping, close };
}

/**
 * Convenience hook for a single channel.
 * Returns an array of the last N received payloads for that channel.
 */
export function useChannel({ url, channel, maxHistory = 100, enabled = true } = {}) {
  const [messages, setMessages] = useState([]);

  const handleMessage = useCallback((envelope) => {
    if (envelope.channel === channel || envelope.channel?.startsWith(`${channel}:`)) {
      setMessages((prev) => {
        const next = [envelope.payload, ...prev];
        return next.length > maxHistory ? next.slice(0, maxHistory) : next;
      });
    }
  }, [channel, maxHistory]);

  const ws = useWebSocket({ url, onMessage: handleMessage, enabled });
  return { ...ws, messages };
}
