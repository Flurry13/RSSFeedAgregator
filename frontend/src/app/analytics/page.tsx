"use client";

import React, { useEffect, useState } from "react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { AnalyticsSkeleton } from "@/components/loading";
import { ErrorBoundary } from "@/components/error-boundary";
import { api, type AnalyticsData } from "@/lib/api";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
} from "recharts";

type Period = "24h" | "7d" | "30d";

/* Apple system topic colors */
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

/* Fallback palette for pie chart / unknown topics */
const COLORS = [
  "#30d158",
  "#0a84ff",
  "#bf5af2",
  "#ff453a",
  "#ffd60a",
  "#ff375f",
  "#ff9f0a",
  "#64d2ff",
];

const tooltipStyle = {
  backgroundColor: "#3a3a3c",
  border: "1px solid #48484a",
  color: "#e5e5e7",
  fontSize: 12,
  borderRadius: 8,
};

const labelStyle = { color: "#636366", fontSize: 11 };

const SENTIMENT_COLORS: Record<string, string> = {
  bullish: "#30d158",
  bearish: "#ff453a",
  neutral: "#636366",
};

function TopicsChart({ data }: { data: AnalyticsData["topic_distribution"] }) {
  return (
    <div>
      <h2 className="text-xs text-[#636366] uppercase tracking-wide mb-4">
        Topic Distribution
      </h2>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} margin={{ left: -20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#3a3a3c" />
          <XAxis
            dataKey="topic"
            tick={{ fontSize: 11, fill: "#636366" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 11, fill: "#636366" }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip contentStyle={tooltipStyle} labelStyle={labelStyle} cursor={{ fill: "#2c2c2e" }} />
          <Bar dataKey="count" radius={[4, 4, 0, 0]}>
            {data.map((entry, i) => (
              <Cell
                key={i}
                fill={TOPIC_COLORS[entry.topic?.toLowerCase()] ?? COLORS[i % COLORS.length]}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function CategoryChart({ data }: { data: { category: string; count: number }[] }) {
  return (
    <div>
      <h2 className="text-xs text-[#636366] uppercase tracking-wide mb-4">
        Category Breakdown
      </h2>
      <div className="flex flex-col sm:flex-row items-center gap-4 sm:gap-6">
        <ResponsiveContainer width="100%" height={200} className="sm:!w-[60%]">
          <PieChart>
            <Pie
              data={data}
              dataKey="count"
              nameKey="category"
              cx="50%"
              cy="50%"
              outerRadius={80}
              labelLine={false}
              strokeWidth={2}
              stroke="#1c1c1e"
            >
              {data.map((entry) => (
                <Cell
                  key={entry.category}
                  fill={TOPIC_COLORS[entry.category] ?? COLORS[0]}
                />
              ))}
            </Pie>
            <Tooltip contentStyle={tooltipStyle} />
          </PieChart>
        </ResponsiveContainer>
        <div className="flex flex-wrap sm:flex-col gap-2 text-[11px]">
          {data.map((d) => (
            <div key={d.category} className="flex items-center gap-2">
              <span
                className="w-2 h-2 rounded-full shrink-0"
                style={{ background: TOPIC_COLORS[d.category] ?? "#636366" }}
              />
              <span className="text-[#98989d]">{d.category.replace('_', ' ')}</span>
              <span className="text-[#e5e5e7] ml-1 font-semibold">{d.count}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function VolumeChart({ data }: { data: AnalyticsData["daily_volume"] }) {
  return (
    <div>
      <h2 className="text-xs text-[#636366] uppercase tracking-wide mb-4">
        Daily Volume
      </h2>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={data} margin={{ left: -20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#3a3a3c" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 11, fill: "#636366" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 11, fill: "#636366" }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip contentStyle={tooltipStyle} labelStyle={labelStyle} />
          <Line
            type="monotone"
            dataKey="count"
            stroke="#0a84ff"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, fill: "#0a84ff", stroke: "#1c1c1e", strokeWidth: 2 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function SentimentChart({ data }: { data: { sentiment: string; count: number }[] }) {
  const total = data.reduce((sum, d) => sum + d.count, 0);
  return (
    <div>
      <h2 className="text-xs text-[#636366] uppercase tracking-wide mb-4">
        Sentiment Distribution
      </h2>
      {total === 0 ? (
        <p className="text-[#636366] text-xs">No sentiment data yet.</p>
      ) : (
        <div>
          <div className="flex h-8 w-full overflow-hidden rounded-lg border border-[#3a3a3c]">
            {data.map((d) => (
              <div
                key={d.sentiment}
                style={{
                  width: `${(d.count / total) * 100}%`,
                  backgroundColor: SENTIMENT_COLORS[d.sentiment] ?? "#48484a",
                }}
              />
            ))}
          </div>
          <div className="flex gap-6 mt-3 text-[11px]">
            {data.map((d) => (
              <div key={d.sentiment} className="flex items-center gap-2">
                <span
                  className="w-2 h-2 rounded-full shrink-0"
                  style={{ background: SENTIMENT_COLORS[d.sentiment] ?? "#48484a" }}
                />
                <span className="text-[#98989d]">{d.sentiment}</span>
                <span className="font-semibold" style={{ color: SENTIMENT_COLORS[d.sentiment] ?? "#98989d" }}>
                  {d.count}
                </span>
                <span className="text-[#636366]">({Math.round((d.count / total) * 100)}%)</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function HeatmapChart({ data }: { data: { topic: string; category: string; count: number }[] }) {
  if (!data.length) return <p className="text-[#636366] text-xs">No data yet.</p>;

  const topics = [...new Set(data.map((d) => d.topic))];
  const categories = [...new Set(data.map((d) => d.category))];
  const maxCount = Math.max(...data.map((d) => d.count));
  const lookup = new Map(data.map((d) => [`${d.topic}-${d.category}`, d.count]));

  return (
    <div>
      <h2 className="text-xs text-[#636366] uppercase tracking-wide mb-4">
        Topic x Category
      </h2>
      <div className="overflow-x-auto">
        <div
          className="grid gap-[2px]"
          style={{
            gridTemplateColumns: `100px repeat(${categories.length}, 1fr)`,
            gridTemplateRows: `24px repeat(${topics.length}, 28px)`,
          }}
        >
          <div />
          {categories.map((cat) => (
            <div key={cat} className="text-[9px] text-[#636366] uppercase text-center truncate px-1">
              {cat.replace(/_/g, " ")}
            </div>
          ))}
          {topics.map((topic) => (
            <React.Fragment key={topic}>
              <div className="text-[10px] text-[#98989d] flex items-center truncate">
                {topic.replace(/_/g, " ")}
              </div>
              {categories.map((cat) => {
                const count = lookup.get(`${topic}-${cat}`) ?? 0;
                const intensity = maxCount > 0 ? count / maxCount : 0;
                return (
                  <div
                    key={`${topic}-${cat}`}
                    className="flex items-center justify-center text-[9px] rounded border border-[#3a3a3c]"
                    style={{
                      backgroundColor: count > 0
                        ? `rgba(48, 209, 88, ${0.1 + intensity * 0.8})`
                        : "transparent",
                      color: intensity > 0.5 ? "#000" : "#636366",
                    }}
                    title={`${topic} × ${cat}: ${count}`}
                  >
                    {count > 0 ? count : ""}
                  </div>
                );
              })}
            </React.Fragment>
          ))}
        </div>
      </div>
    </div>
  );
}

function SourcesChart({ data }: { data: AnalyticsData["source_breakdown"] }) {
  return (
    <div>
      <h2 className="text-xs text-[#636366] uppercase tracking-wide mb-4">
        Top Sources
      </h2>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} layout="vertical" margin={{ left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#3a3a3c" />
          <XAxis
            type="number"
            tick={{ fontSize: 11, fill: "#636366" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey="name"
            tick={{ fontSize: 11, fill: "#98989d" }}
            axisLine={false}
            tickLine={false}
            width={110}
          />
          <Tooltip contentStyle={tooltipStyle} labelStyle={labelStyle} cursor={{ fill: "#2c2c2e" }} />
          <Bar dataKey="count" fill="#0a84ff" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export default function AnalyticsPage() {
  const [period, setPeriod] = useState<Period>("24h");
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.analytics
      .get(period)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [period]);

  return (
    <div className="max-w-5xl mx-auto px-3 sm:px-6 py-6 sm:py-8">
      <div className="flex items-baseline gap-4 mb-6">
        <h1 className="text-2xl font-semibold text-[#e5e5e7]">
          Analytics
        </h1>
        <span className="text-xs text-[#636366] uppercase tracking-wide">
          Dashboard
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
              <AnalyticsSkeleton />
            ) : !data ? (
              <p className="text-[#636366] text-sm text-center py-12">
                No analytics data available.
              </p>
            ) : (
              <div className="space-y-6">
                <ErrorBoundary>
                  <div className="border border-[#3a3a3c] bg-[#2c2c2e] rounded-[10px] p-5 shadow-sm animate-fade-in-up" style={{ animationDelay: "0ms" }}>
                    <TopicsChart data={data.topic_distribution} />
                  </div>
                </ErrorBoundary>
                <ErrorBoundary>
                  <div className="border border-[#3a3a3c] bg-[#2c2c2e] rounded-[10px] p-5 shadow-sm animate-fade-in-up" style={{ animationDelay: "30ms" }}>
                    <SentimentChart data={data.sentiment_distribution ?? []} />
                  </div>
                </ErrorBoundary>
                <ErrorBoundary>
                  <div className="border border-[#3a3a3c] bg-[#2c2c2e] rounded-[10px] p-5 shadow-sm animate-fade-in-up" style={{ animationDelay: "60ms" }}>
                    <HeatmapChart data={data.topic_category_heatmap ?? []} />
                  </div>
                </ErrorBoundary>
                <ErrorBoundary>
                  <div className="border border-[#3a3a3c] bg-[#2c2c2e] rounded-[10px] p-5 shadow-sm animate-fade-in-up" style={{ animationDelay: "90ms" }}>
                    <CategoryChart data={data.category_breakdown ?? []} />
                  </div>
                </ErrorBoundary>
                <ErrorBoundary>
                  <div className="border border-[#3a3a3c] bg-[#2c2c2e] rounded-[10px] p-5 shadow-sm animate-fade-in-up" style={{ animationDelay: "120ms" }}>
                    <VolumeChart data={data.daily_volume} />
                  </div>
                </ErrorBoundary>
                <ErrorBoundary>
                  <div className="border border-[#3a3a3c] bg-[#2c2c2e] rounded-[10px] p-5 shadow-sm animate-fade-in-up" style={{ animationDelay: "150ms" }}>
                    <SourcesChart data={data.source_breakdown} />
                  </div>
                </ErrorBoundary>
              </div>
            )}
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
}
