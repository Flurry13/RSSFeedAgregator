"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useSocket } from "@/hooks/use-socket";
import { api, PipelineRun } from "@/lib/api";
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
  info: "text-[#00ff88]",
  warn: "text-[#ffd700]",
  error: "text-[#ff3333]",
  debug: "text-[#555]",
};

const LOG_LEVEL_LABEL_CLASSES: Record<string, string> = {
  info: "text-[#00ff88]",
  warn: "text-[#ffd700]",
  error: "text-[#ff3333]",
  debug: "text-[#444]",
};

const RUN_STATUS_CLASSES: Record<string, string> = {
  completed: "text-[#00ff88] border-[#00ff88]",
  error: "text-[#ff3333] border-[#ff3333]",
  running: "text-[#ffd700] border-[#ffd700]",
};

export default function PipelinePage() {
  const { connected, status, logs } = useSocket();
  const [running, setRunning] = useState<ActionKey | null>(null);
  const [runs, setRuns] = useState<PipelineRun[]>([]);
  const [runsLoading, setRunsLoading] = useState(true);

  useEffect(() => {
    api.pipeline
      .history(10)
      .then(setRuns)
      .catch(console.error)
      .finally(() => setRunsLoading(false));
  }, []);

  const progressPct =
    status.total > 0
      ? Math.round((status.progress / status.total) * 100)
      : status.status === "running"
      ? 50
      : 0;

  const refreshHistory = () => {
    api.pipeline.history(10).then(setRuns).catch(console.error);
  };

  const handleAction = async (key: ActionKey) => {
    if (running) return;
    setRunning(key);
    try {
      await api.pipeline[key]();
    } catch (err) {
      console.error(err);
    } finally {
      setRunning(null);
      // Refresh after a short delay to let the run record appear
      setTimeout(refreshHistory, 2000);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-6 py-8 space-y-6">
      <div className="flex items-baseline gap-4">
        <h1 className="font-mono text-2xl font-bold uppercase tracking-tight text-[#e8e8e0]">
          Pipeline
        </h1>
        <span className="font-mono text-[10px] text-[#00ff88] tracking-widest uppercase">
          Control
        </span>
      </div>

      {/* Status card */}
      <div className="border-2 border-[#333] bg-[#111]">
        <div className="px-4 py-2.5 border-b-2 border-[#222] flex items-center gap-2">
          <span className="font-mono text-[10px] uppercase tracking-widest text-[#444]">
            Status
          </span>
          <span className="flex-1" />
          <span className="font-mono text-[10px]">
            {connected ? (
              <span className="text-[#00ff88]">CONNECTED</span>
            ) : (
              <span className="text-[#ff3333]">DISCONNECTED</span>
            )}
          </span>
        </div>
        <div className="px-4 py-3 space-y-3">
          <div className="flex items-center gap-3">
            <span
              className={cn(
                "w-2.5 h-2.5 shrink-0",
                !connected
                  ? "bg-[#333]"
                  : status.status === "running"
                  ? "bg-[#00ff88] shadow-[0_0_8px_#00ff88] animate-pulse"
                  : status.status === "error"
                  ? "bg-[#ff3333]"
                  : "bg-[#00ff88]"
              )}
            />
            <div>
              <p className="font-mono text-sm font-bold text-[#e8e8e0] uppercase tracking-wide">
                {status.stage === "idle" ? "Idle" : status.stage}
              </p>
              {status.message && (
                <p className="font-mono text-[11px] text-[#555] mt-0.5">
                  {status.message}
                </p>
              )}
            </div>
            <div className="ml-auto text-right font-mono text-[11px]">
              {status.last_run && (
                <p className="text-[#555]">
                  Last: {new Date(status.last_run).toLocaleTimeString()}
                </p>
              )}
              {status.last_duration_ms && (
                <p className="text-[#444]">
                  {(status.last_duration_ms / 1000).toFixed(1)}s
                </p>
              )}
            </div>
          </div>

          {/* Progress bar */}
          <div className="w-full h-1.5 bg-[#1a1a1a] overflow-hidden">
            <div
              className="h-full bg-[#00ff88] transition-all duration-500"
              style={{ width: `${progressPct}%` }}
            />
          </div>
          {status.total > 0 && (
            <p className="font-mono text-[11px] text-[#555]">
              {status.progress} / {status.total}{" "}
              <span className="text-[#00ff88]">({progressPct}%)</span>
            </p>
          )}
        </div>
      </div>

      {/* Action buttons */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {ACTIONS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => handleAction(key)}
            disabled={!!running || status.status === "running"}
            className={cn(
              "flex flex-col items-center h-auto py-5 gap-2.5 border-2 border-[#333] bg-[#111] text-[#e8e8e0] hover:bg-[#1a1a1a] hover:text-[#00ff88] hover:border-[#00ff88] font-mono transition-colors disabled:opacity-40",
              running === key && "opacity-60"
            )}
          >
            <Icon className="w-5 h-5" />
            <span className="text-[10px] uppercase tracking-widest font-bold">{label}</span>
          </button>
        ))}
      </div>

      {/* Log viewer */}
      <div className="border-2 border-[#333] bg-[#0a0a0a]">
        <div className="px-4 py-2.5 border-b-2 border-[#222] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="font-mono text-[10px] uppercase tracking-widest text-[#444]">
              Logs
            </span>
            <span className="w-1.5 h-3 bg-[#00ff88] animate-pulse" />
          </div>
          <span className="font-mono text-[10px] text-[#444]">
            {logs.length} entries
          </span>
        </div>
        <ScrollArea className="h-80">
          <div className="p-4 font-mono text-xs space-y-0.5">
            {logs.length === 0 ? (
              <p className="text-[#444]">
                {">"} Waiting for pipeline output...
              </p>
            ) : (
              logs.map((log) => (
                <div key={log.id} className="flex gap-3 py-0.5 hover:bg-[#111]">
                  <span className="text-[#444] shrink-0 tabular-nums">
                    {new Date(log.timestamp).toLocaleTimeString()}
                  </span>
                  <span
                    className={cn(
                      "uppercase w-12 shrink-0 font-bold text-right",
                      LOG_LEVEL_LABEL_CLASSES[log.level] ?? "text-[#555]"
                    )}
                  >
                    {log.level}
                  </span>
                  <span className={LOG_LEVEL_CLASSES[log.level] ?? "text-[#777]"}>
                    {log.message}
                  </span>
                </div>
              ))
            )}
          </div>
        </ScrollArea>
      </div>

      {/* Recent Runs */}
      <div className="border-2 border-[#333] bg-[#0a0a0a]">
        <div className="px-4 py-2.5 border-b-2 border-[#222] flex items-center justify-between">
          <span className="font-mono text-[10px] uppercase tracking-widest text-[#444]">
            Recent Runs
          </span>
          <span className="font-mono text-[10px] text-[#444]">
            {runs.length} recorded
          </span>
        </div>
        <div className="divide-y divide-[#1a1a1a]">
          {runsLoading ? (
            <p className="p-4 font-mono text-xs text-[#444]">Loading...</p>
          ) : runs.length === 0 ? (
            <p className="p-4 font-mono text-xs text-[#444]">
              No runs recorded yet. Run the full pipeline to start tracking.
            </p>
          ) : (
            runs.map((run) => (
              <div
                key={run.id}
                className="px-4 py-3 flex items-center gap-4 hover:bg-[#111]"
              >
                {/* Status badge */}
                <span
                  className={cn(
                    "font-mono text-[9px] uppercase tracking-widest border px-1.5 py-0.5 shrink-0",
                    RUN_STATUS_CLASSES[run.status] ?? "text-[#555] border-[#333]"
                  )}
                >
                  {run.status}
                </span>

                {/* Started time */}
                <span className="font-mono text-[11px] text-[#777] shrink-0 tabular-nums">
                  {new Date(run.started_at).toLocaleString(undefined, {
                    month: "short",
                    day: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                  })}
                </span>

                {/* Duration */}
                <span className="font-mono text-[11px] text-[#555] shrink-0 tabular-nums w-16 text-right">
                  {run.duration_ms != null
                    ? `${(run.duration_ms / 1000).toFixed(1)}s`
                    : run.status === "running"
                    ? "running"
                    : "—"}
                </span>

                {/* Headlines */}
                <span className="font-mono text-[11px] text-[#e8e8e0] shrink-0 tabular-nums">
                  <span className="text-[#00ff88]">{run.headlines_gathered}</span>
                  <span className="text-[#444]"> gathered</span>
                  {run.headlines_inserted > 0 && (
                    <span className="text-[#444]">
                      {" / "}
                      <span className="text-[#00ff88]">{run.headlines_inserted}</span>
                      {" new"}
                    </span>
                  )}
                </span>

                {/* Feeds */}
                {(run.feeds_success > 0 || run.feeds_failed > 0) && (
                  <span className="font-mono text-[11px] text-[#555] shrink-0">
                    <span className="text-[#00ff88]">{run.feeds_success}</span>
                    {" ok / "}
                    <span
                      className={
                        run.feeds_failed > 0 ? "text-[#ff3333]" : "text-[#555]"
                      }
                    >
                      {run.feeds_failed}
                    </span>
                    {" fail"}
                  </span>
                )}

                {/* Error */}
                {run.error && (
                  <span
                    className="font-mono text-[10px] text-[#ff3333] truncate flex-1"
                    title={run.error}
                  >
                    {run.error}
                  </span>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
