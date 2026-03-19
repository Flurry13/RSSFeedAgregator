"use client";

import { useEffect, useState, useCallback } from "react";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { PanelRight } from "lucide-react";
import { useSocket } from "@/hooks/use-socket";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

interface Stats {
  headlineCount: number;
  sourceCount: number;
  topics: { topic: string; count: number }[];
}

const TOPIC_COLORS: Record<string, string> = {
  politics: "#ff453a",
  economy: "#ffd60a",
  technology: "#0a84ff",
  science: "#bf5af2",
  environment: "#30d158",
  entertainment: "#ff375f",
  world: "#64d2ff",
  business: "#ff9f0a",
  education: "#5ac8fa",
  art: "#ff2d55",
  health: "#30d158",
  sports: "#0a84ff",
};

function topicBarColorHex(topic: string): string {
  return TOPIC_COLORS[topic.toLowerCase()] ?? "#636366";
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
          topics: (analytics.topic_distribution || []).slice(0, 5),
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

  const maxTopicCount = Math.max(...stats.topics.map((t) => t.count), 1);

  return (
    <div className="flex flex-col gap-0 text-sm">
      {/* Connection status header */}
      <div className="px-4 py-3 border-b border-[#3a3a3c] flex items-center gap-2">
        <span
          className={cn(
            "w-1.5 h-1.5 rounded-full shrink-0",
            connected ? "bg-[#30d158]" : "bg-[#636366]"
          )}
        />
        <span className="text-[11px] uppercase tracking-wide text-[#636366]">
          {connected ? (
            <span className="text-[#30d158]">Live</span>
          ) : (
            <span className="text-[#ff453a]">Offline</span>
          )}
        </span>
      </div>

      {/* Pipeline status */}
      <div className="px-4 py-3 border-b border-[#3a3a3c] space-y-2">
        <p className="text-[11px] uppercase tracking-wide text-[#636366]">
          Pipeline
        </p>
        <div className="flex items-center gap-2">
          <span
            className={cn(
              "w-1.5 h-1.5 rounded-full shrink-0",
              status.status === "running"
                ? "bg-[#30d158]"
                : status.status === "error"
                ? "bg-[#ff453a]"
                : "bg-[#636366]"
            )}
          />
          <span className="text-[13px] text-[#e5e5e7] capitalize">
            {status.stage}
          </span>
        </div>
        {status.message && (
          <p className="text-[11px] text-[#98989d] truncate">
            {status.message}
          </p>
        )}
        {/* Progress bar */}
        <div className="w-full h-1 bg-[#3a3a3c] rounded-full overflow-hidden">
          <div
            className="h-full bg-[#0a84ff] rounded-full transition-all duration-300"
            style={{ width: `${progressPct}%` }}
          />
        </div>
        {status.last_run && (
          <p className="text-[11px] text-[#636366]">
            Last: {new Date(status.last_run).toLocaleTimeString()}
          </p>
        )}
      </div>

      {/* Stats */}
      <div className="px-4 py-3 border-b border-[#3a3a3c] space-y-2">
        <p className="text-[11px] uppercase tracking-wide text-[#636366]">
          Stats
        </p>
        <div className="flex justify-between text-[13px]">
          <span className="text-[#98989d]">Headlines</span>
          <span className="text-[#e5e5e7] font-semibold tabular-nums">
            {stats.headlineCount.toLocaleString()}
          </span>
        </div>
        <div className="flex justify-between text-[13px]">
          <span className="text-[#98989d]">Sources</span>
          <span className="text-[#e5e5e7] font-semibold tabular-nums">
            {stats.sourceCount}
          </span>
        </div>
      </div>

      {/* Top topics with color-coded bars */}
      {stats.topics.length > 0 && (
        <div className="px-4 py-3 space-y-2">
          <p className="text-[11px] uppercase tracking-wide text-[#636366]">
            Topics (24h)
          </p>
          <div className="space-y-2">
            {stats.topics.map(({ topic, count }) => (
              <div key={topic} className="space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-[12px] text-[#98989d] capitalize truncate max-w-[120px]">
                    {topic}
                  </span>
                  <span className="text-[11px] text-[#636366] tabular-nums shrink-0">
                    {count}
                  </span>
                </div>
                <div className="w-full h-1 bg-[#3a3a3c] rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{
                      width: `${(count / maxTopicCount) * 100}%`,
                      backgroundColor: topicBarColorHex(topic),
                    }}
                  />
                </div>
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
    <aside className="hidden lg:flex flex-col w-56 shrink-0 h-screen sticky top-0 bg-[#1c1c1e] border-l border-[#3a3a3c] overflow-y-auto">
      <DataSidebarContent />
    </aside>
  );
}

export function MobileDataSidebar() {
  return (
    <Sheet>
      <SheetTrigger
        className="lg:hidden fixed bottom-4 right-4 z-50 inline-flex items-center justify-center w-10 h-10 rounded-lg bg-[#2c2c2e] border border-[#3a3a3c] text-[#98989d] hover:text-[#e5e5e7] hover:bg-[#3a3a3c] transition-colors"
        aria-label="Open data sidebar"
      >
        <PanelRight className="w-4 h-4" />
      </SheetTrigger>
      <SheetContent
        side="right"
        className="w-64 bg-[#1c1c1e] border-l border-[#3a3a3c] p-0"
      >
        <DataSidebarContent />
      </SheetContent>
    </Sheet>
  );
}
