"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { io, Socket } from "socket.io-client";
import type { PipelineStatus } from "@/lib/api";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "http://localhost:8000";
const MAX_LOGS = 100;

export interface LogMessage {
  id: string;
  timestamp: string;
  level: "info" | "warn" | "error" | "debug";
  message: string;
}

interface UseSocketOptions {
  onHeadlinesUpdate?: () => void;
  onPipelineComplete?: () => void;
}

interface UseSocketReturn {
  connected: boolean;
  status: PipelineStatus;
  logs: LogMessage[];
}

const defaultStatus: PipelineStatus = {
  stage: "idle",
  status: "idle",
  progress: 0,
  total: 0,
  message: "Waiting…",
};

export function useSocket(options: UseSocketOptions = {}): UseSocketReturn {
  const { onHeadlinesUpdate, onPipelineComplete } = options;
  const [connected, setConnected] = useState(false);
  const [status, setStatus] = useState<PipelineStatus>(defaultStatus);
  const [logs, setLogs] = useState<LogMessage[]>([]);

  const socketRef = useRef<Socket | null>(null);
  const onHeadlinesRef = useRef(onHeadlinesUpdate);
  const onCompleteRef = useRef(onPipelineComplete);

  useEffect(() => {
    onHeadlinesRef.current = onHeadlinesUpdate;
  }, [onHeadlinesUpdate]);

  useEffect(() => {
    onCompleteRef.current = onPipelineComplete;
  }, [onPipelineComplete]);

  const addLog = useCallback((entry: Omit<LogMessage, "id">) => {
    setLogs((prev) => {
      const next = [
        { ...entry, id: `${Date.now()}-${Math.random()}` },
        ...prev,
      ].slice(0, MAX_LOGS);
      return next;
    });
  }, []);

  useEffect(() => {
    const socket = io(WS_URL, {
      transports: ["websocket"],
      reconnectionAttempts: 10,
      reconnectionDelay: 2000,
    });

    socketRef.current = socket;

    socket.on("connect", () => {
      setConnected(true);
      socket.emit("subscribe_status");
      addLog({
        timestamp: new Date().toISOString(),
        level: "info",
        message: "Connected to pipeline server",
      });
    });

    socket.on("disconnect", () => {
      setConnected(false);
      addLog({
        timestamp: new Date().toISOString(),
        level: "warn",
        message: "Disconnected from pipeline server",
      });
    });

    socket.on("pipeline_status", (data: PipelineStatus) => {
      setStatus(data);
    });

    socket.on("pipeline_log", (entry: Omit<LogMessage, "id">) => {
      addLog(entry);
    });

    socket.on("pipeline_complete", () => {
      addLog({
        timestamp: new Date().toISOString(),
        level: "info",
        message: "Pipeline run complete",
      });
      onCompleteRef.current?.();
    });

    socket.on("headlines_update", () => {
      onHeadlinesRef.current?.();
    });

    return () => {
      socket.disconnect();
      socketRef.current = null;
    };
  }, [addLog]);

  return { connected, status, logs };
}
