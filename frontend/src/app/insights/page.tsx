"use client";

import { useEffect, useState } from "react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Loading } from "@/components/loading";
import { api, type InsightsSummary } from "@/lib/api";

type Period = "24h" | "7d" | "30d";

const TOPIC_COLORS: Record<string, string> = {
  markets: "#00ff88",
  economy: "#ffd700",
  earnings: "#ff8800",
  crypto: "#aa77ff",
  commodities: "#ff3333",
  real_estate: "#00dddd",
  regulation: "#4488ff",
  fintech: "#33ff99",
  prediction_markets: "#ff69b4",
  mergers: "#ff44aa",
  general: "#666666",
};

function topicColor(topic: string): string {
  return TOPIC_COLORS[topic?.toLowerCase()] ?? "#555";
}

/* ── Feed Health Bar ─────────────────────────────────────────────────────── */
function FeedHealthBar({ health }: { health: InsightsSummary["feed_health"] }) {
  const total = health.healthy + health.erroring + health.inactive;
  if (total === 0) return null;
  const pct = (n: number) => `${((n / total) * 100).toFixed(1)}%`;

  return (
    <div>
      <h2 className="font-mono text-[10px] uppercase tracking-widest text-[#555] mb-3">
        Feed Health
      </h2>
      <div className="flex h-6 w-full overflow-hidden border-2 border-[#333]">
        {health.healthy > 0 && (
          <div
            className="h-full bg-[#00ff88] transition-all"
            style={{ width: pct(health.healthy) }}
            title={`Healthy: ${health.healthy}`}
          />
        )}
        {health.erroring > 0 && (
          <div
            className="h-full bg-[#ffd700] transition-all"
            style={{ width: pct(health.erroring) }}
            title={`Erroring: ${health.erroring}`}
          />
        )}
        {health.inactive > 0 && (
          <div
            className="h-full bg-[#444] transition-all"
            style={{ width: pct(health.inactive) }}
            title={`Inactive: ${health.inactive}`}
          />
        )}
      </div>
      <div className="flex gap-5 mt-2 font-mono text-[10px]">
        <span className="flex items-center gap-1.5">
          <span className="w-2 h-2 bg-[#00ff88] inline-block" />
          <span className="text-[#777]">Healthy</span>
          <span className="text-[#00ff88] font-bold ml-1">{health.healthy}</span>
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2 h-2 bg-[#ffd700] inline-block" />
          <span className="text-[#777]">Erroring</span>
          <span className="text-[#ffd700] font-bold ml-1">{health.erroring}</span>
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2 h-2 bg-[#444] inline-block" />
          <span className="text-[#777]">Inactive</span>
          <span className="text-[#aaa] font-bold ml-1">{health.inactive}</span>
        </span>
      </div>
    </div>
  );
}

/* ── Top Clusters ────────────────────────────────────────────────────────── */
function TopClusters({ clusters }: { clusters: InsightsSummary["top_clusters"] }) {
  return (
    <div>
      <h2 className="font-mono text-[10px] uppercase tracking-widest text-[#555] mb-3">
        Top Clusters
      </h2>
      {clusters.length === 0 ? (
        <p className="font-mono text-[11px] text-[#444]">No clusters yet.</p>
      ) : (
        <ol className="space-y-2">
          {clusters.slice(0, 10).map((c, i) => (
            <li key={i} className="flex items-start gap-3">
              <span className="font-mono text-[10px] text-[#333] w-5 shrink-0 pt-0.5 text-right">
                {i + 1}.
              </span>
              <div className="flex-1 min-w-0">
                <p className="font-mono text-[12px] text-[#e8e8e0] leading-snug truncate">
                  {c.label}
                </p>
              </div>
              <span
                className="font-mono text-[9px] uppercase tracking-wider px-1.5 py-0.5 shrink-0"
                style={{
                  color: topicColor(c.event_type),
                  border: `1px solid ${topicColor(c.event_type)}44`,
                  background: `${topicColor(c.event_type)}11`,
                }}
              >
                {c.event_type ?? "—"}
              </span>
              <span className="font-mono text-[10px] text-[#555] shrink-0 w-12 text-right">
                {c.headline_count} art.
              </span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

/* ── Category Volume ─────────────────────────────────────────────────────── */
function CategoryVolume({ data }: { data: InsightsSummary["category_volume"] }) {
  const max = Math.max(...data.map((d) => d.count), 1);
  return (
    <div>
      <h2 className="font-mono text-[10px] uppercase tracking-widest text-[#555] mb-3">
        Category Volume
      </h2>
      {data.length === 0 ? (
        <p className="font-mono text-[11px] text-[#444]">No data.</p>
      ) : (
        <div className="space-y-2.5">
          {data.map((d) => (
            <div key={d.category} className="flex items-center gap-3">
              <span
                className="w-2 h-2 shrink-0"
                style={{ background: topicColor(d.category) }}
              />
              <span className="font-mono text-[10px] uppercase tracking-wider text-[#777] w-28 shrink-0">
                {d.category.replace(/_/g, " ")}
              </span>
              <div className="flex-1 h-1.5 bg-[#1a1a1a]">
                <div
                  className="h-full transition-all"
                  style={{
                    width: `${(d.count / max) * 100}%`,
                    background: topicColor(d.category),
                  }}
                />
              </div>
              <span className="font-mono text-[10px] text-[#555] w-8 text-right shrink-0">
                {d.count}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ── Top Headlines by Category ───────────────────────────────────────────── */
type CategoryHeadlines = InsightsSummary["top_headlines_by_category"];

function HeadlinesByCategory({ data }: { data: CategoryHeadlines }) {
  const categories = Object.keys(data);
  const [open, setOpen] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(categories.map((c) => [c, true]))
  );

  if (categories.length === 0) {
    return <p className="font-mono text-[11px] text-[#444]">No headlines.</p>;
  }

  return (
    <div>
      <h2 className="font-mono text-[10px] uppercase tracking-widest text-[#555] mb-3">
        Top Headlines by Category
      </h2>
      <div className="space-y-3">
        {categories.map((cat) => {
          const headlines = data[cat] ?? [];
          const isOpen = open[cat] ?? true;
          return (
            <div key={cat} className="border border-[#222]">
              <button
                onClick={() => setOpen((prev) => ({ ...prev, [cat]: !isOpen }))}
                className="w-full flex items-center justify-between px-3 py-2 bg-[#0d0d0d] hover:bg-[#111] transition-colors"
              >
                <div className="flex items-center gap-2">
                  <span
                    className="w-2 h-2 shrink-0"
                    style={{ background: topicColor(cat) }}
                  />
                  <span className="font-mono text-[10px] uppercase tracking-widest text-[#aaa]">
                    {cat.replace(/_/g, " ")}
                  </span>
                  <span className="font-mono text-[9px] text-[#444]">
                    ({headlines.length})
                  </span>
                </div>
                <span className="font-mono text-[10px] text-[#444]">
                  {isOpen ? "▲" : "▼"}
                </span>
              </button>

              {isOpen && (
                <ul className="divide-y divide-[#1a1a1a]">
                  {headlines.slice(0, 5).map((h, i) => (
                    <li key={i} className="px-3 py-2.5 flex items-start gap-3">
                      <div className="flex-1 min-w-0">
                        <a
                          href={h.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="font-mono text-[12px] text-[#e8e8e0] hover:text-[#00ff88] leading-snug block transition-colors"
                        >
                          {h.title}
                        </a>
                        <span className="font-mono text-[10px] text-[#555] mt-0.5 block">
                          {h.source_name}
                        </span>
                      </div>
                      <span
                        className="font-mono text-[9px] uppercase tracking-wider px-1.5 py-0.5 shrink-0 mt-0.5"
                        style={{
                          color: topicColor(h.topic),
                          border: `1px solid ${topicColor(h.topic)}44`,
                          background: `${topicColor(h.topic)}11`,
                        }}
                      >
                        {h.topic}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ── Main Page ───────────────────────────────────────────────────────────── */
export default function InsightsPage() {
  const [period, setPeriod] = useState<Period>("24h");
  const [data, setData] = useState<InsightsSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    setLoading(true);
    api.insights
      .summary(period)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [period]);

  async function handleCopy() {
    if (!data) return;
    await navigator.clipboard.writeText(JSON.stringify(data, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      <div className="flex items-baseline justify-between gap-4 mb-6">
        <div className="flex items-baseline gap-4">
          <h1 className="font-mono text-2xl font-bold uppercase tracking-tight text-[#e8e8e0]">
            Insights
          </h1>
          <span className="font-mono text-[10px] text-[#00ff88] tracking-widest uppercase">
            AI Summary
          </span>
        </div>
        <button
          onClick={handleCopy}
          disabled={!data}
          className="font-mono text-[10px] uppercase tracking-widest px-3 py-1.5 border border-[#333] text-[#555] hover:text-[#00ff88] hover:border-[#00ff88] transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
        >
          {copied ? "Copied!" : "Copy as JSON"}
        </button>
      </div>

      <Tabs value={period} onValueChange={(v) => setPeriod(v as Period)}>
        <TabsList className="bg-[#111] border-2 border-[#333] mb-6 rounded-none p-0">
          <TabsTrigger
            value="24h"
            className="data-[state=active]:bg-[#00ff88] data-[state=active]:text-black text-[#777] font-mono text-xs rounded-none px-4 font-bold uppercase tracking-wider"
          >
            24H
          </TabsTrigger>
          <TabsTrigger
            value="7d"
            className="data-[state=active]:bg-[#00ff88] data-[state=active]:text-black text-[#777] font-mono text-xs rounded-none px-4 font-bold uppercase tracking-wider"
          >
            7D
          </TabsTrigger>
          <TabsTrigger
            value="30d"
            className="data-[state=active]:bg-[#00ff88] data-[state=active]:text-black text-[#777] font-mono text-xs rounded-none px-4 font-bold uppercase tracking-wider"
          >
            30D
          </TabsTrigger>
        </TabsList>

        {(["24h", "7d", "30d"] as Period[]).map((p) => (
          <TabsContent key={p} value={p}>
            {loading ? (
              <Loading message="Loading insights..." />
            ) : !data ? (
              <p className="text-[#555] font-mono text-sm text-center py-12">
                No insights data available.
              </p>
            ) : (
              <div className="space-y-6">
                {/* Feed Health */}
                <div
                  className="border-2 border-[#333] bg-[#111] p-5 animate-fade-in-up"
                  style={{ animationDelay: "0ms" }}
                >
                  <FeedHealthBar health={data.feed_health} />
                </div>

                {/* Top Clusters */}
                <div
                  className="border-2 border-[#333] bg-[#111] p-5 animate-fade-in-up"
                  style={{ animationDelay: "60ms" }}
                >
                  <TopClusters clusters={data.top_clusters} />
                </div>

                {/* Category Volume */}
                <div
                  className="border-2 border-[#333] bg-[#111] p-5 animate-fade-in-up"
                  style={{ animationDelay: "120ms" }}
                >
                  <CategoryVolume data={data.category_volume} />
                </div>

                {/* Top Headlines by Category */}
                <div
                  className="border-2 border-[#333] bg-[#111] p-5 animate-fade-in-up"
                  style={{ animationDelay: "180ms" }}
                >
                  <HeadlinesByCategory data={data.top_headlines_by_category} />
                </div>
              </div>
            )}
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
}
