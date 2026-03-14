"use client";

import { useEffect, useState, useCallback } from "react";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { PanelRight } from "lucide-react";
import { useSocket } from "@/hooks/use-socket";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

interface Stats {
  headlineCount: number;
  sourceCount: number;
  topics: { topic: string; count: number }[];
}

function useStats(refreshTrigger: number) {
  const [stats, setStats] = useState<Stats>({
    headlineCount: 0,
    sourceCount: 0,
    topics: [],
  });

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      api.headlines.list({ limit: 1 }),
      api.sources.list({ limit: 1 }),
      api.analytics.get("24h"),
    ])
      .then(([headlines, sources, analytics]) => {
        if (cancelled) return;
        setStats({
          headlineCount: headlines.pagination.total,
          sourceCount: sources.pagination.total,
          topics: analytics.topics.slice(0, 5),
        });
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [refreshTrigger]);

  return stats;
}

function DataSidebarContent() {
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const onPipelineComplete = useCallback(() => {
    setRefreshTrigger((n) => n + 1);
  }, []);

  const { connected, status } = useSocket({ onPipelineComplete });
  const stats = useStats(refreshTrigger);

  const progressPct =
    status.total > 0
      ? Math.round((status.progress / status.total) * 100)
      : status.status === "running"
      ? 50
      : 0;

  return (
    <div className="flex flex-col gap-4 p-4 text-sm">
      {/* Connection status */}
      <div className="flex items-center gap-2">
        <span
          className={cn(
            "w-2 h-2 rounded-full shrink-0",
            connected ? "bg-emerald-500" : "bg-zinc-600"
          )}
        />
        <span className="text-zinc-400 text-xs">
          {connected ? "Live" : "Disconnected"}
        </span>
      </div>

      <Separator className="bg-zinc-800" />

      {/* Pipeline status */}
      <div className="space-y-2">
        <p className="text-zinc-500 text-xs uppercase tracking-wider">Pipeline</p>
        <div className="flex items-center gap-2">
          <span
            className={cn(
              "w-2 h-2 rounded-full shrink-0",
              status.status === "running"
                ? "bg-blue-400 animate-pulse"
                : status.status === "error"
                ? "bg-red-500"
                : "bg-zinc-600"
            )}
          />
          <span className="text-zinc-300 text-xs capitalize">{status.stage}</span>
        </div>
        {status.message && (
          <p className="text-zinc-500 text-xs truncate">{status.message}</p>
        )}
        {/* Progress bar */}
        <div className="w-full h-1 bg-zinc-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-blue-500 transition-all duration-300"
            style={{ width: `${progressPct}%` }}
          />
        </div>
        {status.last_run && (
          <p className="text-zinc-600 text-xs">
            Last run: {new Date(status.last_run).toLocaleTimeString()}
          </p>
        )}
      </div>

      <Separator className="bg-zinc-800" />

      {/* Stats */}
      <div className="space-y-2">
        <p className="text-zinc-500 text-xs uppercase tracking-wider">Stats</p>
        <div className="flex justify-between text-xs">
          <span className="text-zinc-400">Headlines</span>
          <span className="text-zinc-200 font-medium">
            {stats.headlineCount.toLocaleString()}
          </span>
        </div>
        <div className="flex justify-between text-xs">
          <span className="text-zinc-400">Sources</span>
          <span className="text-zinc-200 font-medium">{stats.sourceCount}</span>
        </div>
      </div>

      <Separator className="bg-zinc-800" />

      {/* Top topics */}
      {stats.topics.length > 0 && (
        <div className="space-y-2">
          <p className="text-zinc-500 text-xs uppercase tracking-wider">
            Top Topics (24h)
          </p>
          <div className="space-y-1.5">
            {stats.topics.map(({ topic, count }) => (
              <div key={topic} className="flex items-center justify-between gap-2">
                <Badge
                  variant="outline"
                  className="text-zinc-300 border-zinc-700 text-xs px-1.5 py-0 truncate max-w-[140px]"
                >
                  {topic}
                </Badge>
                <span className="text-zinc-500 text-xs shrink-0">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export function DataSidebar() {
  return (
    <aside className="hidden lg:flex flex-col w-56 shrink-0 h-screen sticky top-0 bg-zinc-950 border-l border-zinc-800 overflow-y-auto">
      <DataSidebarContent />
    </aside>
  );
}

export function MobileDataSidebar() {
  return (
    <Sheet>
      <SheetTrigger
        className="lg:hidden fixed bottom-4 right-4 z-50 inline-flex items-center justify-center w-10 h-10 rounded-md bg-zinc-900 border border-zinc-700 text-zinc-300 hover:bg-zinc-800 shadow-lg"
        aria-label="Open data sidebar"
      >
        <PanelRight className="w-4 h-4" />
      </SheetTrigger>
      <SheetContent
        side="right"
        className="w-64 bg-zinc-950 border-l border-zinc-800 p-0"
      >
        <DataSidebarContent />
      </SheetContent>
    </Sheet>
  );
}
