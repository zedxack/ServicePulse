/**
 * ServicePulse - Real-Time WebSocket Monitoring Hook
 * Author: Muhammadyusuf Usmonov
 *  */
import { useCallback, useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { getWebSocketUrl, getWSTicket } from '../../shared/api/ws';
import { getAuthToken } from '../../shared/api/client';
import {
  DeviceTelemetryPayload,
  WSConnectionStatus,
  WSMessage,
} from '../../shared/types/ws';

const MAX_EVENTS_IN_FEED = 100;
const INITIAL_RECONNECT_DELAY_MS = 1000;
const MAX_RECONNECT_DELAY_MS = 15000;
const PING_INTERVAL_MS = 25000;

export function useRealtimeMonitoring(enabled: boolean = true) {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<WSConnectionStatus>('disconnected');
  const [events, setEvents] = useState<WSMessage[]>([]);
  const [lastMessage, setLastMessage] = useState<WSMessage | null>(null);
  const [telemetryMap, setTelemetryMap] = useState<Record<string | number, DeviceTelemetryPayload>>({});

  const socketRef = useRef<WebSocket | null>(null);
  const pingTimerRef = useRef<number | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);
  const backoffRef = useRef<number>(INITIAL_RECONNECT_DELAY_MS);
  const isMountedRef = useRef<boolean>(true);

  const clearTimers = useCallback(() => {
    if (pingTimerRef.current !== null) {
      window.clearInterval(pingTimerRef.current);
      pingTimerRef.current = null;
    }
    if (reconnectTimerRef.current !== null) {
      window.clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  const clearEvents = useCallback(() => {
    setEvents([]);
  }, []);

  const connect = useCallback(async () => {
    clearTimers();
    if (!enabled || !getAuthToken()) {
      setStatus('disconnected');
      return;
    }

    try {
      setStatus('connecting');
      const ticketData = await getWSTicket();
      if (!isMountedRef.current) return;

      const wsUrl = getWebSocketUrl(ticketData.ticket);
      const ws = new WebSocket(wsUrl);
      socketRef.current = ws;

      ws.onopen = () => {
        if (!isMountedRef.current) return;
        setStatus('connected');
        backoffRef.current = INITIAL_RECONNECT_DELAY_MS;

        // Periodic ping heartbeat
        pingTimerRef.current = window.setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
          }
        }, PING_INTERVAL_MS);
      };

      ws.onmessage = (event: MessageEvent) => {
        if (!isMountedRef.current) return;
        try {
          const parsed: WSMessage = JSON.parse(event.data);
          if (parsed.type === 'pong') return;

          setLastMessage(parsed);
          setEvents((prev) => [parsed, ...prev.slice(0, MAX_EVENTS_IN_FEED - 1)]);

          // Handle specific event actions
          if (parsed.type === 'device:telemetry') {
            const tel = parsed.payload as DeviceTelemetryPayload;
            if (tel) {
              const key = tel.device_id ?? tel.agent_id;
              setTelemetryMap((prev) => ({ ...prev, [key]: tel }));
            }
          }

          // Cache invalidations based on event types
          if (parsed.type === 'device:status_change' || parsed.type === 'device:telemetry') {
            queryClient.invalidateQueries({ queryKey: ['devices'] });
            queryClient.invalidateQueries({ queryKey: ['dashboard'] });
          } else if (
            parsed.type === 'incident:created' ||
            parsed.type === 'incident:acknowledged' ||
            parsed.type === 'incident:assigned' ||
            parsed.type === 'incident:resolved'
          ) {
            queryClient.invalidateQueries({ queryKey: ['incidents'] });
            queryClient.invalidateQueries({ queryKey: ['dashboard'] });
          } else if (parsed.type === 'alert:created') {
            queryClient.invalidateQueries({ queryKey: ['alerts'] });
            queryClient.invalidateQueries({ queryKey: ['unread-alerts-count'] });
          } else if (parsed.type === 'remediation:status') {
            queryClient.invalidateQueries({ queryKey: ['incidents'] });
            queryClient.invalidateQueries({ queryKey: ['remediations'] });
          }
        } catch {
          // ignore unparseable frame
        }
      };

      ws.onerror = () => {
        if (!isMountedRef.current) return;
        setStatus('error');
      };

      ws.onclose = () => {
        if (!isMountedRef.current) return;
        setStatus('disconnected');
        clearTimers();

        // Schedule reconnect with bounded backoff
        const delay = backoffRef.current;
        backoffRef.current = Math.min(backoffRef.current * 1.5, MAX_RECONNECT_DELAY_MS);
        reconnectTimerRef.current = window.setTimeout(() => {
          if (isMountedRef.current && enabled) {
            connect();
          }
        }, delay);
      };
    } catch {
      if (!isMountedRef.current) return;
      setStatus('error');
      const delay = backoffRef.current;
      backoffRef.current = Math.min(backoffRef.current * 1.5, MAX_RECONNECT_DELAY_MS);
      reconnectTimerRef.current = window.setTimeout(() => {
        if (isMountedRef.current && enabled) {
          connect();
        }
      }, delay);
    }
  }, [clearTimers, enabled, queryClient]);

  useEffect(() => {
    isMountedRef.current = true;
    connect();

    return () => {
      isMountedRef.current = false;
      clearTimers();
      if (socketRef.current) {
        socketRef.current.close();
        socketRef.current = null;
      }
    };
  }, [clearTimers, connect]);

  return {
    status,
    events,
    lastMessage,
    telemetryMap,
    clearEvents,
    reconnect: connect,
  };
}
