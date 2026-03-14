"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useSocket } from "@/hooks/use-socket";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Play, Download, Languages, Tag } from "lucide-react";

type ActionKey = "run" | "gather" | "translate" | "classify";

const ACTIONS: { key: ActionKey; label: string; icon: React.ElementType }[] = [
  { key: "run", label: "Run Full", icon: Play },
  { key: "gather", label: "Gather", icon: Download },
  { key: "translate", label: "Translate", icon: Languages },
  { key: "classify", label: "Classify", icon: Tag },
];

const LOG_LEVEL_CLASSES: Record<string, string> = {
  info: "text-zinc-400",
  warn: "text-yellow-400",
  error: "text-red-400",
  debug: "text-zinc-600",
};

export default function PipelinePage() {
  const { connected, status, logs } = useSocket();
  const [running, setRunning] = useState<ActionKey | null>(null);

  const progressPct =
    status.total > 0
      ? Math.round((status.progress / status.total) * 100)
      : status.status === "running"
      ? 50
      : 0;

  const handleAction = async (key: ActionKey) => {
    if (running) return;
    setRunning(key);
    try {
      await api.pipeline[key]();
    } catch (err) {
      console.error(err);
    } finally {
      setRunning(null);
    }
  };

  return (
    <div className="max-w-3xl mx-auto px-4 py-8 space-y-6">
      <h1 className="text-2xl font-semibold text-zinc-100">Pipeline</h1>

      {/* Status card */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5 space-y-4">
        <div className="flex items-center gap-3">
          <span
            className={cn(
              "w-3 h-3 rounded-full shrink-0",
              !connected
                ? "bg-zinc-700"
                : status.status === "running"
                ? "bg-blue-400 animate-pulse"
                : status.status === "error"
                ? "bg-red-500"
                : "bg-emerald-500"
            )}
          />
          <div>
            <p className="text-zinc-100 font-medium capitalize">
              {status.stage === "idle" ? "Idle" : status.stage}
            </p>
            {status.message && (
              <p className="text-zinc-500 text-xs mt-0.5">{status.message}</p>
            )}
          </div>
          <div className="ml-auto text-right text-xs text-zinc-600">
            {connected ? (
              <span className="text-emerald-500">Live</span>
            ) : (
              <span>Disconnected</span>
            )}
            {status.last_run && (
              <p>Last: {new Date(status.last_run).toLocaleTimeString()}</p>
            )}
            {status.last_duration_ms && (
              <p>{(status.last_duration_ms / 1000).toFixed(1)}s</p>
            )}
          </div>
        </div>

        {/* Progress bar */}
        <div className="w-full h-2 bg-zinc-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-blue-500 transition-all duration-500"
            style={{ width: `${progressPct}%` }}
          />
        </div>
        {status.total > 0 && (
          <p className="text-zinc-600 text-xs">
            {status.progress} / {status.total} ({progressPct}%)
          </p>
        )}
      </div>

      {/* Action buttons */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {ACTIONS.map(({ key, label, icon: Icon }) => (
          <Button
            key={key}
            onClick={() => handleAction(key)}
            disabled={!!running || status.status === "running"}
            variant="outline"
            className={cn(
              "flex flex-col h-auto py-4 gap-2 border-zinc-700 text-zinc-300 hover:bg-zinc-800 hover:text-zinc-100",
              running === key && "opacity-60"
            )}
          >
            <Icon className="w-5 h-5" />
            <span className="text-xs">{label}</span>
          </Button>
        ))}
      </div>

      {/* Log viewer */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b border-zinc-800 flex items-center justify-between">
          <p className="text-zinc-400 text-xs font-medium uppercase tracking-wider">
            Logs
          </p>
          <span className="text-zinc-600 text-xs">{logs.length} entries</span>
        </div>
        <ScrollArea className="h-80">
          <div className="p-4 font-mono text-xs space-y-1">
            {logs.length === 0 ? (
              <p className="text-zinc-600">No logs yet. Run a pipeline stage to see output.</p>
            ) : (
              logs.map((log) => (
                <div key={log.id} className="flex gap-3">
                  <span className="text-zinc-700 shrink-0">
                    {new Date(log.timestamp).toLocaleTimeString()}
                  </span>
                  <span
                    className={cn(
                      "uppercase w-10 shrink-0 font-semibold",
                      LOG_LEVEL_CLASSES[log.level] ?? "text-zinc-400"
                    )}
                  >
                    {log.level}
                  </span>
                  <span className={LOG_LEVEL_CLASSES[log.level] ?? "text-zinc-400"}>
                    {log.message}
                  </span>
                </div>
              ))
            )}
          </div>
        </ScrollArea>
      </div>
    </div>
  );
}
