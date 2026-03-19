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
  info: "text-[#0a84ff]",
  warn: "text-[#ff9f0a]",
  error: "text-[#ff453a]",
  debug: "text-[#636366]",
};

const LOG_LEVEL_LABEL_CLASSES: Record<string, string> = {
  info: "text-[#0a84ff]",
  warn: "text-[#ff9f0a]",
  error: "text-[#ff453a]",
  debug: "text-[#636366]",
};

const RUN_STATUS_CLASSES: Record<string, string> = {
  completed: "text-[#30d158] border-[#30d158]",
  error: "text-[#ff453a] border-[#ff453a]",
  running: "text-[#ff9f0a] border-[#ff9f0a]",
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
        <h1 className="text-2xl font-bold text-[#e5e5e7]">
          Pipeline
        </h1>
        <span className="text-[11px] text-[#636366] uppercase tracking-wide">
          Control
        </span>
      </div>

      {/* Status card */}
      <div className="border border-[#3a3a3c] bg-[#2c2c2e] rounded-[10px] overflow-hidden">
        <div className="px-4 py-2.5 border-b border-[#3a3a3c] flex items-center gap-2">
          <span className="text-[11px] uppercase tracking-wide text-[#636366]">
            Status
          </span>
          <span className="flex-1" />
          <span className="text-[11px]">
            {connected ? (
              <span className="text-[#30d158]">Connected</span>
            ) : (
              <span className="text-[#ff453a]">Disconnected</span>
            )}
          </span>
        </div>
        <div className="px-4 py-3 space-y-3">
          <div className="flex items-center gap-3">
            <span
              className={cn(
                "w-2.5 h-2.5 rounded-full shrink-0",
                !connected
                  ? "bg-[#3a3a3c]"
                  : status.status === "running"
                  ? "bg-[#30d158] shadow-[0_0_8px_#30d158] animate-pulse"
                  : status.status === "error"
                  ? "bg-[#ff453a]"
                  : "bg-[#30d158]"
              )}
            />
            <div>
              <p className="text-sm font-medium text-[#e5e5e7]">
                {status.stage === "idle" ? "Idle" : status.stage}
              </p>
              {status.message && (
                <p className="text-[11px] text-[#636366] mt-0.5">
                  {status.message}
                </p>
              )}
            </div>
            <div className="ml-auto text-right text-[11px]">
              {status.last_run && (
                <p className="text-[#636366]">
                  Last: {new Date(status.last_run).toLocaleTimeString()}
                </p>
              )}
              {status.last_duration_ms && (
                <p className="text-[#636366]">
                  {(status.last_duration_ms / 1000).toFixed(1)}s
                </p>
              )}
            </div>
          </div>

          {/* Progress bar */}
          <div className="w-full h-1.5 bg-[#3a3a3c] rounded-full overflow-hidden">
            <div
              className="h-full bg-[#0a84ff] rounded-full transition-all duration-500"
              style={{ width: `${progressPct}%` }}
            />
          </div>
          {status.total > 0 && (
            <p className="text-[11px] text-[#636366]">
              {status.progress} / {status.total}{" "}
              <span className="text-[#0a84ff]">({progressPct}%)</span>
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
              "flex flex-col items-center h-auto py-5 gap-2.5 border border-[#3a3a3c] bg-[#2c2c2e] text-[#e5e5e7] hover:bg-[#3a3a3c] hover:border-[#0a84ff] rounded-[10px] transition-colors disabled:opacity-40",
              running === key && "opacity-60"
            )}
          >
            <Icon className="w-5 h-5" />
            <span className="text-[12px] font-medium">{label}</span>
          </button>
        ))}
      </div>

      {/* Log viewer */}
      <div className="border border-[#3a3a3c] bg-[#1c1c1e] rounded-[10px] overflow-hidden">
        <div className="px-4 py-2.5 border-b border-[#3a3a3c] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-[11px] uppercase tracking-wide text-[#636366]">
              Logs
            </span>
            <span className="w-1.5 h-3 bg-[#0a84ff] rounded-sm animate-pulse" />
          </div>
          <span className="text-[11px] text-[#636366]">
            {logs.length} entries
          </span>
        </div>
        <ScrollArea className="h-80">
          <div className="p-4 font-mono text-xs space-y-0.5">
            {logs.length === 0 ? (
              <p className="text-[#636366]">
                {">"} Waiting for pipeline output...
              </p>
            ) : (
              logs.map((log) => (
                <div key={log.id} className="flex gap-3 py-0.5 hover:bg-[#2c2c2e] rounded">
                  <span className="text-[#636366] shrink-0 tabular-nums">
                    {new Date(log.timestamp).toLocaleTimeString()}
                  </span>
                  <span
                    className={cn(
                      "uppercase w-12 shrink-0 font-bold text-right",
                      LOG_LEVEL_LABEL_CLASSES[log.level] ?? "text-[#636366]"
                    )}
                  >
                    {log.level}
                  </span>
                  <span className={LOG_LEVEL_CLASSES[log.level] ?? "text-[#98989d]"}>
                    {log.message}
                  </span>
                </div>
              ))
            )}
          </div>
        </ScrollArea>
      </div>

      {/* Recent Runs */}
      <div className="border border-[#3a3a3c] bg-[#2c2c2e] rounded-[10px] overflow-hidden">
        <div className="px-4 py-2.5 border-b border-[#3a3a3c] flex items-center justify-between">
          <span className="text-[11px] uppercase tracking-wide text-[#636366]">
            Recent Runs
          </span>
          <span className="text-[11px] text-[#636366]">
            {runs.length} recorded
          </span>
        </div>
        <div className="divide-y divide-[#3a3a3c]">
          {runsLoading ? (
            <p className="p-4 text-xs text-[#636366]">Loading...</p>
          ) : runs.length === 0 ? (
            <p className="p-4 text-xs text-[#636366]">
              No runs recorded yet. Run the full pipeline to start tracking.
            </p>
          ) : (
            runs.map((run) => (
              <div
                key={run.id}
                className="px-4 py-3 flex items-center gap-4 hover:bg-[#3a3a3c]/40 transition-colors"
              >
                {/* Status badge */}
                <span
                  className={cn(
                    "text-[10px] font-medium border px-2 py-0.5 rounded-md shrink-0",
                    RUN_STATUS_CLASSES[run.status] ?? "text-[#636366] border-[#3a3a3c]"
                  )}
                >
                  {run.status}
                </span>

                {/* Started time */}
                <span className="text-[11px] text-[#98989d] shrink-0 tabular-nums">
                  {new Date(run.started_at).toLocaleString(undefined, {
                    month: "short",
                    day: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                  })}
                </span>

                {/* Duration */}
                <span className="text-[11px] text-[#636366] shrink-0 tabular-nums w-16 text-right">
                  {run.duration_ms != null
                    ? `${(run.duration_ms / 1000).toFixed(1)}s`
                    : run.status === "running"
                    ? "running"
                    : "\u2014"}
                </span>

                {/* Headlines */}
                <span className="text-[11px] text-[#e5e5e7] shrink-0 tabular-nums">
                  <span className="text-[#30d158]">{run.headlines_gathered}</span>
                  <span className="text-[#636366]"> gathered</span>
                  {run.headlines_inserted > 0 && (
                    <span className="text-[#636366]">
                      {" / "}
                      <span className="text-[#30d158]">{run.headlines_inserted}</span>
                      {" new"}
                    </span>
                  )}
                </span>

                {/* Feeds */}
                {(run.feeds_success > 0 || run.feeds_failed > 0) && (
                  <span className="text-[11px] text-[#636366] shrink-0">
                    <span className="text-[#30d158]">{run.feeds_success}</span>
                    {" ok / "}
                    <span
                      className={
                        run.feeds_failed > 0 ? "text-[#ff453a]" : "text-[#636366]"
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
                    className="text-[10px] text-[#ff453a] truncate flex-1"
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
