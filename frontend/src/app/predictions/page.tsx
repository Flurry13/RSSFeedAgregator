"use client";

import { useEffect, useState } from "react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Loading } from "@/components/loading";
import { api, type PredictionSignals } from "@/lib/api";
import { TrendingUp, TrendingDown, Minus, AlertTriangle } from "lucide-react";

type Period = "24h" | "7d" | "30d";

function sentimentIcon(s?: string) {
  if (s === "bullish") return <TrendingUp className="w-3.5 h-3.5 text-[#00ff88]" />;
  if (s === "bearish") return <TrendingDown className="w-3.5 h-3.5 text-[#ff3333]" />;
  return <Minus className="w-3.5 h-3.5 text-[#555]" />;
}

/* ── Stats Bar ────────────────────────────────────────────────────────────── */
function StatsBar({ stats }: { stats: PredictionSignals["stats"] }) {
  return (
    <div className="flex items-center gap-6 font-mono text-[11px] text-[#555] border-2 border-[#222] bg-[#0d0d0d] px-4 py-2.5 mb-6">
      <span>
        <span className="text-[#e8e8e0] font-bold">{stats.pm_headline_count}</span>{" "}
        headlines
      </span>
      <span className="text-[#222]">|</span>
      <span>
        <span className="text-[#e8e8e0] font-bold">{stats.cross_references_found}</span>{" "}
        cross-references
      </span>
      <span className="text-[#222]">|</span>
      <span>
        <span
          className="font-bold"
          style={{ color: stats.divergences_found > 0 ? "#ff3333" : "#e8e8e0" }}
        >
          {stats.divergences_found}
        </span>{" "}
        divergences
      </span>
    </div>
  );
}

/* ── Divergence Alerts ────────────────────────────────────────────────────── */
function DivergenceAlerts({
  divergences,
}: {
  divergences: PredictionSignals["divergences"];
}) {
  return (
    <div className="border-2 border-[#333] bg-[#111] p-5 animate-fade-in-up" style={{ animationDelay: "0ms" }}>
      <div className="flex items-center gap-3 mb-4">
        <AlertTriangle className="w-4 h-4 text-[#ff3333]" />
        <h2 className="font-mono text-[10px] uppercase tracking-widest text-[#555]">
          Divergence Alerts
        </h2>
        <span className="font-mono text-[9px] px-1.5 py-0.5 border border-[#ff333344] bg-[#ff333311] text-[#ff3333]">
          {divergences.length}
        </span>
      </div>

      {divergences.length === 0 ? (
        <p className="font-mono text-[12px] text-[#444]">
          No sentiment divergences detected in this period
        </p>
      ) : (
        <div className="space-y-3">
          {divergences.map((div, i) => {
            const topRelated = div.related_headlines[0];
            const pmColor = div.pm_sentiment === "bearish" ? "#ff3333" : "#00ff88";
            const mktColor = div.market_sentiment === "bearish" ? "#ff3333" : "#00ff88";
            const pmLabel = `PM ${div.pm_sentiment?.toUpperCase()}`;
            const mktLabel = `MARKET ${div.market_sentiment?.toUpperCase()}`;

            return (
              <div
                key={i}
                className="border border-[#2a2a2a] flex items-stretch"
                style={{ animationDelay: `${i * 40}ms` }}
              >
                {/* Left: PM headline */}
                <div className="flex-1 p-3 min-w-0 border-r border-[#2a2a2a]">
                  <div className="flex items-start gap-2 mb-1.5">
                    {sentimentIcon(div.pm_sentiment)}
                    <a
                      href={div.pm_headline.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="font-mono text-[12px] text-[#e8e8e0] hover:text-[#00ff88] leading-snug transition-colors line-clamp-2"
                    >
                      {div.pm_headline.title}
                    </a>
                  </div>
                  <span className="font-mono text-[10px] text-[#555]">
                    {div.pm_headline.source_name}
                  </span>
                </div>

                {/* VS divider */}
                <div className="flex flex-col items-center justify-center px-3 gap-1.5 shrink-0">
                  <span
                    className="font-mono text-[9px] font-bold px-1.5 py-0.5"
                    style={{
                      color: pmColor,
                      border: `1px solid ${pmColor}44`,
                      background: `${pmColor}11`,
                    }}
                  >
                    {pmLabel}
                  </span>
                  <span className="font-mono text-[9px] text-[#333] font-bold">VS</span>
                  <span
                    className="font-mono text-[9px] font-bold px-1.5 py-0.5"
                    style={{
                      color: mktColor,
                      border: `1px solid ${mktColor}44`,
                      background: `${mktColor}11`,
                    }}
                  >
                    {mktLabel}
                  </span>
                </div>

                {/* Right: top related headline */}
                <div className="flex-1 p-3 min-w-0">
                  {topRelated ? (
                    <>
                      <div className="flex items-start gap-2 mb-1.5">
                        {sentimentIcon(topRelated.sentiment)}
                        <a
                          href={topRelated.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="font-mono text-[12px] text-[#e8e8e0] hover:text-[#00ff88] leading-snug transition-colors line-clamp-2"
                        >
                          {topRelated.title}
                        </a>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-[10px] text-[#555]">
                          {topRelated.source_name}
                        </span>
                        {topRelated.category && (
                          <span className="font-mono text-[9px] uppercase tracking-wider px-1.5 py-0.5 border border-[#33333388] text-[#666]">
                            {topRelated.category}
                          </span>
                        )}
                      </div>
                    </>
                  ) : (
                    <span className="font-mono text-[11px] text-[#444]">—</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

/* ── Cross References ─────────────────────────────────────────────────────── */
function CrossReferences({
  crossRefs,
}: {
  crossRefs: PredictionSignals["cross_references"];
}) {
  return (
    <div className="border-2 border-[#333] bg-[#111] p-5 animate-fade-in-up" style={{ animationDelay: "60ms" }}>
      <div className="flex items-center gap-3 mb-4">
        <h2 className="font-mono text-[10px] uppercase tracking-widest text-[#555]">
          Cross-References
        </h2>
        <span className="font-mono text-[9px] px-1.5 py-0.5 border border-[#00ff8844] bg-[#00ff8811] text-[#00ff88]">
          {crossRefs.length}
        </span>
      </div>

      {crossRefs.length === 0 ? (
        <p className="font-mono text-[12px] text-[#444]">No cross-references found</p>
      ) : (
        <div className="space-y-4">
          {crossRefs.map((xref, i) => (
            <div key={i} className="border border-[#222]">
              {/* PM headline */}
              <div className="border-l-2 border-[#00ff88] pl-3 py-2.5 pr-3 bg-[#0d0d0d]">
                <div className="flex items-start gap-2">
                  {sentimentIcon(xref.pm_headline.sentiment)}
                  <a
                    href={xref.pm_headline.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-mono text-[12px] text-[#e8e8e0] hover:text-[#00ff88] leading-snug transition-colors"
                  >
                    {xref.pm_headline.title}
                  </a>
                </div>
                <span className="font-mono text-[10px] text-[#555] mt-1 block">
                  {xref.pm_headline.source_name}
                </span>
              </div>

              {/* Related headlines */}
              <ul className="divide-y divide-[#1a1a1a]">
                {xref.related.map((rel, j) => (
                  <li key={j} className="px-3 py-2 flex items-start gap-2.5">
                    <div className="pt-0.5 shrink-0">{sentimentIcon(rel.sentiment)}</div>
                    <div className="flex-1 min-w-0">
                      <a
                        href={rel.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-mono text-[11px] text-[#bbb] hover:text-[#00ff88] leading-snug block transition-colors"
                      >
                        {rel.title}
                      </a>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="font-mono text-[10px] text-[#555]">
                          {rel.source_name}
                        </span>
                        {rel.category && (
                          <span className="font-mono text-[9px] uppercase tracking-wider px-1 py-0.5 border border-[#33333388] text-[#555]">
                            {rel.category}
                          </span>
                        )}
                        <span className="font-mono text-[9px] text-[#444]">
                          {rel.shared_words} shared words
                        </span>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ── Prediction Market Headlines ──────────────────────────────────────────── */
function PredictionHeadlines({
  headlines,
}: {
  headlines: PredictionSignals["prediction_headlines"];
}) {
  return (
    <div className="border-2 border-[#333] bg-[#111] p-5 animate-fade-in-up" style={{ animationDelay: "120ms" }}>
      <div className="flex items-center gap-3 mb-4">
        <h2 className="font-mono text-[10px] uppercase tracking-widest text-[#555]">
          Prediction Market Headlines
        </h2>
        <span className="font-mono text-[9px] px-1.5 py-0.5 border border-[#33333388] text-[#666]">
          {headlines.length}
        </span>
      </div>

      {headlines.length === 0 ? (
        <p className="font-mono text-[12px] text-[#444]">No prediction market headlines found</p>
      ) : (
        <ul className="divide-y divide-[#1a1a1a]">
          {headlines.map((h, i) => (
            <li key={i} className="py-2.5 flex items-start gap-2.5">
              <div className="pt-0.5 shrink-0">{sentimentIcon(h.sentiment)}</div>
              <div className="flex-1 min-w-0">
                <a
                  href={h.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-mono text-[12px] text-[#e8e8e0] hover:text-[#00ff88] leading-snug block transition-colors"
                >
                  {h.title}
                </a>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="font-mono text-[10px] text-[#555]">{h.source_name}</span>
                  {h.topic && (
                    <span className="font-mono text-[9px] uppercase tracking-wider px-1 py-0.5 border border-[#33333388] text-[#555]">
                      {h.topic.replace(/_/g, " ")}
                    </span>
                  )}
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/* ── Main Page ────────────────────────────────────────────────────────────── */
export default function PredictionsPage() {
  const [period, setPeriod] = useState<Period>("24h");
  const [data, setData] = useState<PredictionSignals | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.insights
      .predictions(period)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [period]);

  return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      <div className="flex items-baseline gap-4 mb-6">
        <h1 className="font-mono text-2xl font-bold uppercase tracking-tight text-[#e8e8e0]">
          Predictions
        </h1>
        <span className="font-mono text-[10px] text-[#00ff88] tracking-widest uppercase">
          Market Intelligence
        </span>
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
              <Loading message="Loading predictions..." />
            ) : !data ? (
              <p className="text-[#555] font-mono text-sm text-center py-12">
                No predictions data available.
              </p>
            ) : (
              <>
                <StatsBar stats={data.stats} />
                <div className="space-y-6">
                  <DivergenceAlerts divergences={data.divergences ?? []} />
                  <CrossReferences crossRefs={data.cross_references ?? []} />
                  <PredictionHeadlines headlines={data.prediction_headlines ?? []} />
                </div>
              </>
            )}
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
}
