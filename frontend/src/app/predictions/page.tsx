"use client";

import { useEffect, useState } from "react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Loading } from "@/components/loading";
import { api, type PredictionSignals } from "@/lib/api";
import { TrendingUp, TrendingDown, Minus, AlertTriangle } from "lucide-react";

type Period = "24h" | "7d" | "30d";

function sentimentIcon(s?: string) {
  if (s === "bullish") return <TrendingUp className="w-3.5 h-3.5 text-[#30d158]" />;
  if (s === "bearish") return <TrendingDown className="w-3.5 h-3.5 text-[#ff453a]" />;
  return <Minus className="w-3.5 h-3.5 text-[#98989d]" />;
}

/* -- Stats Bar ----------------------------------------------------------- */
function StatsBar({ stats }: { stats: PredictionSignals["stats"] }) {
  return (
    <div className="flex flex-wrap items-center gap-3 sm:gap-6 text-[11px] text-[#636366] border border-[#3a3a3c] bg-[#2c2c2e] rounded-[10px] px-4 py-2.5 mb-6">
      <span>
        <span className="text-[#e5e5e7] font-semibold">{stats.pm_headline_count}</span>{" "}
        headlines
      </span>
      <span className="text-[#3a3a3c] hidden sm:inline">|</span>
      <span>
        <span className="text-[#e5e5e7] font-semibold">{stats.cross_references_found}</span>{" "}
        cross-references
      </span>
      <span className="text-[#3a3a3c] hidden sm:inline">|</span>
      <span>
        <span
          className="font-semibold"
          style={{ color: stats.divergences_found > 0 ? "#ff453a" : "#e5e5e7" }}
        >
          {stats.divergences_found}
        </span>{" "}
        divergences
      </span>
    </div>
  );
}

/* -- Divergence Alerts --------------------------------------------------- */
function DivergenceAlerts({
  divergences,
}: {
  divergences: PredictionSignals["divergences"];
}) {
  return (
    <div className="border border-[#3a3a3c] bg-[#2c2c2e] rounded-[10px] p-5 shadow-sm animate-fade-in-up" style={{ animationDelay: "0ms" }}>
      <div className="flex items-center gap-3 mb-4">
        <AlertTriangle className="w-4 h-4 text-[#ff453a]" />
        <h2 className="text-xs text-[#636366] uppercase tracking-wide">
          Divergence Alerts
        </h2>
        <span className="text-[9px] px-1.5 py-0.5 rounded border border-[#ff453a44] bg-[#ff453a11] text-[#ff453a]">
          {divergences.length}
        </span>
      </div>

      {divergences.length === 0 ? (
        <p className="text-[13px] text-[#48484a]">
          No sentiment divergences detected in this period
        </p>
      ) : (
        <div className="space-y-3">
          {divergences.map((div, i) => {
            const topRelated = div.related_headlines[0];
            const pmColor = div.pm_sentiment === "bearish" ? "#ff453a" : "#30d158";
            const mktColor = div.market_sentiment === "bearish" ? "#ff453a" : "#30d158";
            const pmLabel = `PM ${div.pm_sentiment?.toUpperCase()}`;
            const mktLabel = `MARKET ${div.market_sentiment?.toUpperCase()}`;

            return (
              <div
                key={i}
                className="border border-[#3a3a3c] rounded-lg flex flex-col sm:flex-row sm:items-stretch overflow-hidden"
                style={{
                  animationDelay: `${i * 40}ms`,
                  borderLeftWidth: 3,
                  borderLeftColor: pmColor,
                }}
              >
                {/* Left: PM headline */}
                <div className="flex-1 p-3 min-w-0 border-b sm:border-b-0 sm:border-r border-[#3a3a3c]">
                  <div className="flex items-start gap-2 mb-1.5">
                    {sentimentIcon(div.pm_sentiment)}
                    <a
                      href={div.pm_headline.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[13px] text-[#e5e5e7] hover:text-[#0a84ff] leading-snug transition-colors line-clamp-2"
                    >
                      {div.pm_headline.title}
                    </a>
                  </div>
                  <span className="text-[10px] text-[#636366]">
                    {div.pm_headline.source_name}
                  </span>
                </div>

                {/* VS divider */}
                <div className="flex flex-row sm:flex-col items-center justify-center px-3 py-2 sm:py-0 gap-1.5 shrink-0 border-b sm:border-b-0 border-[#3a3a3c]">
                  <span
                    className="text-[9px] font-semibold px-1.5 py-0.5 rounded"
                    style={{
                      color: pmColor,
                      border: `1px solid ${pmColor}44`,
                      background: `${pmColor}11`,
                    }}
                  >
                    {pmLabel}
                  </span>
                  <span className="text-[9px] text-[#48484a] font-semibold">VS</span>
                  <span
                    className="text-[9px] font-semibold px-1.5 py-0.5 rounded"
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
                          className="text-[13px] text-[#e5e5e7] hover:text-[#0a84ff] leading-snug transition-colors line-clamp-2"
                        >
                          {topRelated.title}
                        </a>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] text-[#636366]">
                          {topRelated.source_name}
                        </span>
                        {topRelated.category && (
                          <span className="text-[9px] uppercase tracking-wide px-1.5 py-0.5 rounded border border-[#48484a] text-[#98989d] bg-[#48484a22]">
                            {topRelated.category}
                          </span>
                        )}
                      </div>
                    </>
                  ) : (
                    <span className="text-[11px] text-[#48484a]">—</span>
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

/* -- Cross References ---------------------------------------------------- */
function CrossReferences({
  crossRefs,
}: {
  crossRefs: PredictionSignals["cross_references"];
}) {
  return (
    <div className="border border-[#3a3a3c] bg-[#2c2c2e] rounded-[10px] p-5 shadow-sm animate-fade-in-up" style={{ animationDelay: "60ms" }}>
      <div className="flex items-center gap-3 mb-4">
        <h2 className="text-xs text-[#636366] uppercase tracking-wide">
          Cross-References
        </h2>
        <span className="text-[9px] px-1.5 py-0.5 rounded border border-[#0a84ff44] bg-[#0a84ff11] text-[#0a84ff]">
          {crossRefs.length}
        </span>
      </div>

      {crossRefs.length === 0 ? (
        <p className="text-[13px] text-[#48484a]">No cross-references found</p>
      ) : (
        <div className="space-y-4">
          {crossRefs.map((xref, i) => (
            <div key={i} className="border border-[#3a3a3c] rounded-lg overflow-hidden">
              {/* PM headline */}
              <div className="border-l-[3px] border-[#0a84ff] pl-3 py-2.5 pr-3 bg-[#2c2c2e]">
                <div className="flex items-start gap-2">
                  {sentimentIcon(xref.pm_headline.sentiment)}
                  <a
                    href={xref.pm_headline.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[13px] text-[#e5e5e7] hover:text-[#0a84ff] leading-snug transition-colors"
                  >
                    {xref.pm_headline.title}
                  </a>
                </div>
                <span className="text-[10px] text-[#636366] mt-1 block">
                  {xref.pm_headline.source_name}
                </span>
              </div>

              {/* Related headlines */}
              <ul className="divide-y divide-[#3a3a3c]">
                {xref.related.map((rel, j) => (
                  <li key={j} className="px-3 py-2 flex items-start gap-2.5">
                    <div className="pt-0.5 shrink-0">{sentimentIcon(rel.sentiment)}</div>
                    <div className="flex-1 min-w-0">
                      <a
                        href={rel.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[12px] text-[#98989d] hover:text-[#0a84ff] leading-snug block transition-colors"
                      >
                        {rel.title}
                      </a>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-[10px] text-[#636366]">
                          {rel.source_name}
                        </span>
                        {rel.category && (
                          <span className="text-[9px] uppercase tracking-wide px-1.5 py-0.5 rounded border border-[#48484a] text-[#98989d] bg-[#48484a22]">
                            {rel.category}
                          </span>
                        )}
                        <span className="text-[9px] text-[#48484a]">
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

/* -- Prediction Market Headlines ----------------------------------------- */
function PredictionHeadlines({
  headlines,
}: {
  headlines: PredictionSignals["prediction_headlines"];
}) {
  return (
    <div className="border border-[#3a3a3c] bg-[#2c2c2e] rounded-[10px] p-5 shadow-sm animate-fade-in-up" style={{ animationDelay: "120ms" }}>
      <div className="flex items-center gap-3 mb-4">
        <h2 className="text-xs text-[#636366] uppercase tracking-wide">
          Prediction Market Headlines
        </h2>
        <span className="text-[9px] px-1.5 py-0.5 rounded border border-[#48484a] text-[#98989d]">
          {headlines.length}
        </span>
      </div>

      {headlines.length === 0 ? (
        <p className="text-[13px] text-[#48484a]">No prediction market headlines found</p>
      ) : (
        <ul className="divide-y divide-[#3a3a3c]">
          {headlines.map((h, i) => (
            <li key={i} className="py-2.5 flex items-start gap-2.5">
              <div className="pt-0.5 shrink-0">{sentimentIcon(h.sentiment)}</div>
              <div className="flex-1 min-w-0">
                <a
                  href={h.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[13px] text-[#e5e5e7] hover:text-[#0a84ff] leading-snug block transition-colors"
                >
                  {h.title}
                </a>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-[10px] text-[#636366]">{h.source_name}</span>
                  {h.topic && (
                    <span className="text-[9px] uppercase tracking-wide px-1.5 py-0.5 rounded border border-[#48484a] text-[#98989d] bg-[#48484a22]">
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

/* -- Main Page ----------------------------------------------------------- */
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
    <div className="max-w-5xl mx-auto px-3 sm:px-6 py-6 sm:py-8">
      <div className="flex items-baseline gap-4 mb-6">
        <h1 className="text-2xl font-semibold text-[#e5e5e7]">
          Predictions
        </h1>
        <span className="text-xs text-[#636366] uppercase tracking-wide">
          Market Intelligence
        </span>
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
              <Loading message="Loading predictions..." />
            ) : !data ? (
              <p className="text-[#636366] text-sm text-center py-12">
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
