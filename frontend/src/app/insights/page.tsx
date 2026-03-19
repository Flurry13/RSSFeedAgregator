"use client";

import { useEffect, useState } from "react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Loading } from "@/components/loading";
import { api, type InsightsSummary, type PredictionSignals } from "@/lib/api";

type Period = "24h" | "7d" | "30d";

const TOPIC_COLORS: Record<string, string> = {
  markets: "#30d158",
  economy: "#ffd60a",
  earnings: "#ff9f0a",
  crypto: "#bf5af2",
  commodities: "#ff453a",
  real_estate: "#64d2ff",
  regulation: "#0a84ff",
  fintech: "#30d158",
  prediction_markets: "#ff375f",
  mergers: "#bf5af2",
  general: "#636366",
};

function topicColor(topic: string): string {
  return TOPIC_COLORS[topic?.toLowerCase()] ?? "#636366";
}

/* -- Market Sentiment ---------------------------------------------------- */
function MarketSentiment({
  breakdown,
  byCategory,
}: {
  breakdown: Record<string, number>;
  byCategory: Record<string, { bullish: number; bearish: number; neutral: number }>;
}) {
  const total = (breakdown.bullish ?? 0) + (breakdown.bearish ?? 0) + (breakdown.neutral ?? 0);

  return (
    <div className="border border-[#3a3a3c] bg-[#2c2c2e] rounded-[10px] p-5 shadow-sm animate-fade-in-up">
      <h2 className="text-xs text-[#636366] uppercase tracking-wide mb-4">
        Market Sentiment
      </h2>
      {total === 0 ? (
        <p className="text-[#636366] text-xs">No sentiment data yet.</p>
      ) : (
        <>
          <div className="flex h-6 w-full overflow-hidden rounded-lg border border-[#3a3a3c] mb-2">
            <div style={{ width: `${((breakdown.bullish ?? 0) / total) * 100}%`, backgroundColor: "#30d158" }} />
            <div style={{ width: `${((breakdown.bearish ?? 0) / total) * 100}%`, backgroundColor: "#ff453a" }} />
            <div style={{ width: `${((breakdown.neutral ?? 0) / total) * 100}%`, backgroundColor: "#3a3a3c" }} />
          </div>
          <div className="flex gap-4 text-[11px] mb-6">
            <span className="text-[#30d158] font-semibold">Bullish {breakdown.bullish ?? 0}</span>
            <span className="text-[#ff453a] font-semibold">Bearish {breakdown.bearish ?? 0}</span>
            <span className="text-[#636366] font-semibold">Neutral {breakdown.neutral ?? 0}</span>
          </div>

          <h3 className="text-xs text-[#636366] uppercase tracking-wide mb-3">
            By Category
          </h3>
          <div className="space-y-2">
            {Object.entries(byCategory)
              .sort(([, a], [, b]) => (b.bullish + b.bearish + b.neutral) - (a.bullish + a.bearish + a.neutral))
              .map(([cat, counts]) => {
                const catTotal = counts.bullish + counts.bearish + counts.neutral;
                return (
                  <div key={cat} className="flex items-center gap-2 sm:gap-3 text-[11px]">
                    <span className="text-[#98989d] w-20 sm:w-28 shrink-0 truncate">{cat.replace(/_/g, ' ')}</span>
                    <div className="flex h-3 flex-1 overflow-hidden rounded border border-[#3a3a3c]">
                      <div style={{ width: `${(counts.bullish / catTotal) * 100}%`, backgroundColor: "#30d158" }} />
                      <div style={{ width: `${(counts.bearish / catTotal) * 100}%`, backgroundColor: "#ff453a" }} />
                      <div style={{ width: `${(counts.neutral / catTotal) * 100}%`, backgroundColor: "#3a3a3c" }} />
                    </div>
                    <span className="text-[#636366] w-10 text-right">{catTotal}</span>
                  </div>
                );
              })}
          </div>
        </>
      )}
    </div>
  );
}

/* -- Feed Health Bar ----------------------------------------------------- */
function FeedHealthBar({ health }: { health: InsightsSummary["feed_health"] }) {
  const total = health.healthy + health.erroring + health.inactive;
  if (total === 0) return null;
  const pct = (n: number) => `${((n / total) * 100).toFixed(1)}%`;

  return (
    <div>
      <h2 className="text-xs text-[#636366] uppercase tracking-wide mb-3">
        Feed Health
      </h2>
      <div className="flex h-6 w-full overflow-hidden rounded-lg border border-[#3a3a3c]">
        {health.healthy > 0 && (
          <div
            className="h-full bg-[#30d158] transition-all"
            style={{ width: pct(health.healthy) }}
            title={`Healthy: ${health.healthy}`}
          />
        )}
        {health.erroring > 0 && (
          <div
            className="h-full bg-[#ff9f0a] transition-all"
            style={{ width: pct(health.erroring) }}
            title={`Erroring: ${health.erroring}`}
          />
        )}
        {health.inactive > 0 && (
          <div
            className="h-full bg-[#636366] transition-all"
            style={{ width: pct(health.inactive) }}
            title={`Inactive: ${health.inactive}`}
          />
        )}
      </div>
      <div className="flex gap-5 mt-2 text-[11px]">
        <span className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-[#30d158] inline-block" />
          <span className="text-[#98989d]">Healthy</span>
          <span className="text-[#30d158] font-semibold ml-1">{health.healthy}</span>
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-[#ff9f0a] inline-block" />
          <span className="text-[#98989d]">Erroring</span>
          <span className="text-[#ff9f0a] font-semibold ml-1">{health.erroring}</span>
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-[#636366] inline-block" />
          <span className="text-[#98989d]">Inactive</span>
          <span className="text-[#98989d] font-semibold ml-1">{health.inactive}</span>
        </span>
      </div>
    </div>
  );
}

/* -- Top Clusters -------------------------------------------------------- */
function TopClusters({ clusters }: { clusters: InsightsSummary["top_clusters"] }) {
  return (
    <div>
      <h2 className="text-xs text-[#636366] uppercase tracking-wide mb-3">
        Top Clusters
      </h2>
      {clusters.length === 0 ? (
        <p className="text-[11px] text-[#48484a]">No clusters yet.</p>
      ) : (
        <ol className="space-y-2">
          {clusters.slice(0, 10).map((c, i) => (
            <li key={i} className="flex items-start gap-3">
              <span className="text-[10px] text-[#48484a] w-5 shrink-0 pt-0.5 text-right">
                {i + 1}.
              </span>
              <div className="flex-1 min-w-0">
                <p className="text-[13px] text-[#e5e5e7] leading-snug truncate">
                  {c.label}
                </p>
              </div>
              <span
                className="text-[9px] uppercase tracking-wide px-1.5 py-0.5 rounded shrink-0"
                style={{
                  color: topicColor(c.event_type),
                  border: `1px solid ${topicColor(c.event_type)}44`,
                  background: `${topicColor(c.event_type)}11`,
                }}
              >
                {c.event_type ?? "—"}
              </span>
              <span className="text-[10px] text-[#636366] shrink-0 w-12 text-right">
                {c.headline_count} art.
              </span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

/* -- Category Volume ----------------------------------------------------- */
function CategoryVolume({ data }: { data: InsightsSummary["category_volume"] }) {
  const max = Math.max(...data.map((d) => d.count), 1);
  return (
    <div>
      <h2 className="text-xs text-[#636366] uppercase tracking-wide mb-3">
        Category Volume
      </h2>
      {data.length === 0 ? (
        <p className="text-[11px] text-[#48484a]">No data.</p>
      ) : (
        <div className="space-y-2.5">
          {data.map((d) => (
            <div key={d.category} className="flex items-center gap-2 sm:gap-3">
              <span
                className="w-2 h-2 rounded-full shrink-0"
                style={{ background: topicColor(d.category) }}
              />
              <span className="text-[11px] text-[#98989d] w-20 sm:w-28 shrink-0 truncate">
                {d.category.replace(/_/g, " ")}
              </span>
              <div className="flex-1 h-1.5 bg-[#1c1c1e] rounded-full">
                <div
                  className="h-full rounded-full transition-all"
                  style={{
                    width: `${(d.count / max) * 100}%`,
                    background: topicColor(d.category),
                  }}
                />
              </div>
              <span className="text-[11px] text-[#636366] w-8 text-right shrink-0">
                {d.count}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* -- Top Headlines by Category ------------------------------------------- */
type CategoryHeadlines = InsightsSummary["top_headlines_by_category"];

function HeadlinesByCategory({ data }: { data: CategoryHeadlines }) {
  const categories = Object.keys(data);
  const [open, setOpen] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(categories.map((c) => [c, true]))
  );

  if (categories.length === 0) {
    return <p className="text-[11px] text-[#48484a]">No headlines.</p>;
  }

  return (
    <div>
      <h2 className="text-xs text-[#636366] uppercase tracking-wide mb-3">
        Top Headlines by Category
      </h2>
      <div className="space-y-3">
        {categories.map((cat) => {
          const headlines = data[cat] ?? [];
          const isOpen = open[cat] ?? true;
          return (
            <div key={cat} className="border border-[#3a3a3c] rounded-lg overflow-hidden">
              <button
                onClick={() => setOpen((prev) => ({ ...prev, [cat]: !isOpen }))}
                className="w-full flex items-center justify-between px-3 py-2 bg-[#2c2c2e] hover:bg-[#3a3a3c] transition-colors"
              >
                <div className="flex items-center gap-2">
                  <span
                    className="w-2 h-2 rounded-full shrink-0"
                    style={{ background: topicColor(cat) }}
                  />
                  <span className="text-[11px] text-[#e5e5e7]">
                    {cat.replace(/_/g, " ")}
                  </span>
                  <span className="text-[10px] text-[#48484a]">
                    ({headlines.length})
                  </span>
                </div>
                <span className="text-[10px] text-[#48484a]">
                  {isOpen ? "▲" : "▼"}
                </span>
              </button>

              {isOpen && (
                <ul className="divide-y divide-[#3a3a3c]">
                  {headlines.slice(0, 5).map((h, i) => (
                    <li key={i} className="px-3 py-2.5 flex items-start gap-3">
                      <div className="flex-1 min-w-0">
                        <a
                          href={h.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-[13px] text-[#e5e5e7] hover:text-[#0a84ff] leading-snug block transition-colors"
                        >
                          {h.title}
                        </a>
                        <span className="text-[10px] text-[#636366] mt-0.5 block">
                          {h.source_name}
                        </span>
                      </div>
                      <span
                        className="text-[9px] uppercase tracking-wide px-1.5 py-0.5 rounded shrink-0 mt-0.5"
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

/* -- Prediction Markets -------------------------------------------------- */
function PredictionMarketsSection({ data }: { data: PredictionSignals | null }) {
  if (!data) return null;
  const { stats, divergences } = data;

  return (
    <div className="border border-[#3a3a3c] bg-[#2c2c2e] rounded-[10px] p-5 shadow-sm animate-fade-in-up">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xs text-[#636366] uppercase tracking-wide">
          Prediction Markets
        </h2>
        <a
          href="/predictions"
          className="text-[11px] text-[#0a84ff] hover:underline"
        >
          View all →
        </a>
      </div>

      <div className="flex gap-4 text-[11px] mb-4">
        <span className="text-[#98989d]">{stats.pm_headline_count} headlines</span>
        <span className="text-[#98989d]">{stats.cross_references_found} cross-refs</span>
        <span className={stats.divergences_found > 0 ? "text-[#ff453a] font-semibold" : "text-[#98989d]"}>
          {stats.divergences_found} divergences
        </span>
      </div>

      {divergences.length > 0 ? (
        <div className="space-y-2">
          {divergences.slice(0, 3).map((d, i) => (
            <div key={i} className="flex items-center gap-3 text-[11px] border border-[#3a3a3c] rounded-lg px-3 py-2">
              <span className={d.pm_sentiment === "bearish" ? "text-[#ff453a]" : "text-[#30d158]"}>
                PM: {d.pm_sentiment.toUpperCase()}
              </span>
              <span className="text-[#636366] truncate flex-1">{d.pm_headline.title.slice(0, 60)}...</span>
              <span className="text-[#636366]">vs</span>
              <span className={d.market_sentiment === "bearish" ? "text-[#ff453a]" : "text-[#30d158]"}>
                MKT: {d.market_sentiment.toUpperCase()}
              </span>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-[#636366] text-xs">No divergences detected</p>
      )}
    </div>
  );
}

/* -- Main Page ----------------------------------------------------------- */
export default function InsightsPage() {
  const [period, setPeriod] = useState<Period>("24h");
  const [data, setData] = useState<InsightsSummary | null>(null);
  const [pmData, setPmData] = useState<PredictionSignals | null>(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    setLoading(true);
    api.insights
      .summary(period)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
    api.insights.predictions(period).then(setPmData).catch(() => setPmData(null));
  }, [period]);

  async function handleCopy() {
    if (!data) return;
    await navigator.clipboard.writeText(JSON.stringify(data, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="max-w-5xl mx-auto px-3 sm:px-6 py-6 sm:py-8">
      <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-3 sm:gap-4 mb-6">
        <div className="flex items-baseline gap-4">
          <h1 className="text-2xl font-semibold text-[#e5e5e7]">
            Insights
          </h1>
          <span className="text-xs text-[#636366] uppercase tracking-wide">
            AI Summary
          </span>
        </div>
        <button
          onClick={handleCopy}
          disabled={!data}
          className="text-[11px] px-3 py-1.5 rounded-lg bg-transparent border border-[#48484a] text-[#e5e5e7] hover:border-[#0a84ff] hover:text-[#0a84ff] transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
        >
          {copied ? "Copied!" : "Copy as JSON"}
        </button>
      </div>

      <Tabs value={period} onValueChange={(v) => setPeriod(v as Period)}>
        <TabsList className="bg-[#2c2c2e] border border-[#3a3a3c] mb-6 rounded-lg p-0.5">
          <TabsTrigger
            value="24h"
            className="data-[state=active]:bg-[#0a84ff] data-[state=active]:text-white text-[#98989d] text-xs rounded-md px-4 py-1.5 font-medium"
          >
            24H
          </TabsTrigger>
          <TabsTrigger
            value="7d"
            className="data-[state=active]:bg-[#0a84ff] data-[state=active]:text-white text-[#98989d] text-xs rounded-md px-4 py-1.5 font-medium"
          >
            7D
          </TabsTrigger>
          <TabsTrigger
            value="30d"
            className="data-[state=active]:bg-[#0a84ff] data-[state=active]:text-white text-[#98989d] text-xs rounded-md px-4 py-1.5 font-medium"
          >
            30D
          </TabsTrigger>
        </TabsList>

        {(["24h", "7d", "30d"] as Period[]).map((p) => (
          <TabsContent key={p} value={p}>
            {loading ? (
              <Loading message="Loading insights..." />
            ) : !data ? (
              <p className="text-[#636366] text-sm text-center py-12">
                No insights data available.
              </p>
            ) : (
              <div className="space-y-6">
                {/* Market Sentiment */}
                <MarketSentiment
                  breakdown={data.sentiment_breakdown ?? {}}
                  byCategory={data.sentiment_by_category ?? {}}
                />

                {/* Feed Health */}
                <div
                  className="border border-[#3a3a3c] bg-[#2c2c2e] rounded-[10px] p-5 shadow-sm animate-fade-in-up"
                  style={{ animationDelay: "0ms" }}
                >
                  <FeedHealthBar health={data.feed_health} />
                </div>

                {/* Top Clusters */}
                <div
                  className="border border-[#3a3a3c] bg-[#2c2c2e] rounded-[10px] p-5 shadow-sm animate-fade-in-up"
                  style={{ animationDelay: "60ms" }}
                >
                  <TopClusters clusters={data.top_clusters} />
                </div>

                {/* Prediction Markets */}
                <PredictionMarketsSection data={pmData} />

                {/* Category Volume */}
                <div
                  className="border border-[#3a3a3c] bg-[#2c2c2e] rounded-[10px] p-5 shadow-sm animate-fade-in-up"
                  style={{ animationDelay: "120ms" }}
                >
                  <CategoryVolume data={data.category_volume} />
                </div>

                {/* Top Headlines by Category */}
                <div
                  className="border border-[#3a3a3c] bg-[#2c2c2e] rounded-[10px] p-5 shadow-sm animate-fade-in-up"
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
