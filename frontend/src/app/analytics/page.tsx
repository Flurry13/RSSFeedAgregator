"use client";

import React, { useEffect, useState } from "react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Loading } from "@/components/loading";
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

/* Full saturation topic colors */
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

/* Fallback palette for pie chart / unknown topics */
const COLORS = [
  "#00ff88",
  "#00ffaa",
  "#4488ff",
  "#aa77ff",
  "#ff3333",
  "#ffd700",
  "#ff69b4",
  "#ff8800",
];

const tooltipStyle = {
  backgroundColor: "#111",
  border: "2px solid #333",
  color: "#e8e8e0",
  fontSize: 10,
  fontFamily: "'Space Mono', monospace",
};

const labelStyle = { color: "#777", fontSize: 10, fontFamily: "'Space Mono', monospace" };

const SENTIMENT_COLORS: Record<string, string> = {
  bullish: "#00ff88",
  bearish: "#ff3333",
  neutral: "#666",
};

function TopicsChart({ data }: { data: AnalyticsData["topic_distribution"] }) {
  return (
    <div>
      <h2 className="font-mono text-[10px] uppercase tracking-widest text-[#555] mb-4">
        Topic Distribution
      </h2>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} margin={{ left: -20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#222" />
          <XAxis
            dataKey="topic"
            tick={{ fontSize: 10, fill: "#555", fontFamily: "'Space Mono', monospace" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 10, fill: "#555", fontFamily: "'Space Mono', monospace" }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip contentStyle={tooltipStyle} labelStyle={labelStyle} cursor={{ fill: "#1a1a1a" }} />
          <Bar dataKey="count" radius={[0, 0, 0, 0]}>
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
      <h2 className="font-mono text-[10px] uppercase tracking-widest text-[#555] mb-4">
        Category Breakdown
      </h2>
      <div className="flex items-center gap-6">
        <ResponsiveContainer width="60%" height={200}>
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
              stroke="#050505"
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
        <div className="flex flex-col gap-2 font-mono text-[11px]">
          {data.map((d) => (
            <div key={d.category} className="flex items-center gap-2">
              <span
                className="w-2 h-2 shrink-0"
                style={{ background: TOPIC_COLORS[d.category] ?? "#555" }}
              />
              <span className="text-[#777] uppercase">{d.category.replace('_', ' ')}</span>
              <span className="text-[#00ff88] ml-1 font-bold">{d.count}</span>
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
      <h2 className="font-mono text-[10px] uppercase tracking-widest text-[#555] mb-4">
        Daily Volume
      </h2>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={data} margin={{ left: -20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#222" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 10, fill: "#555", fontFamily: "'Space Mono', monospace" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 10, fill: "#555", fontFamily: "'Space Mono', monospace" }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip contentStyle={tooltipStyle} labelStyle={labelStyle} />
          <Line
            type="monotone"
            dataKey="count"
            stroke="#00ff88"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, fill: "#00ff88", stroke: "#050505", strokeWidth: 2 }}
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
      <h2 className="font-mono text-[10px] uppercase tracking-widest text-[#555] mb-4">
        Sentiment Distribution
      </h2>
      {total === 0 ? (
        <p className="text-[#555] font-mono text-xs">No sentiment data yet.</p>
      ) : (
        <div>
          <div className="flex h-8 w-full overflow-hidden border-2 border-[#333]">
            {data.map((d) => (
              <div
                key={d.sentiment}
                style={{
                  width: `${(d.count / total) * 100}%`,
                  backgroundColor: SENTIMENT_COLORS[d.sentiment] ?? "#444",
                }}
              />
            ))}
          </div>
          <div className="flex gap-6 mt-3 font-mono text-[11px]">
            {data.map((d) => (
              <div key={d.sentiment} className="flex items-center gap-2">
                <span
                  className="w-2 h-2 shrink-0"
                  style={{ background: SENTIMENT_COLORS[d.sentiment] ?? "#444" }}
                />
                <span className="text-[#777] uppercase">{d.sentiment}</span>
                <span className="font-bold" style={{ color: SENTIMENT_COLORS[d.sentiment] ?? "#777" }}>
                  {d.count}
                </span>
                <span className="text-[#555]">({Math.round((d.count / total) * 100)}%)</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function HeatmapChart({ data }: { data: { topic: string; category: string; count: number }[] }) {
  if (!data.length) return <p className="text-[#555] font-mono text-xs">No data yet.</p>;

  const topics = [...new Set(data.map((d) => d.topic))];
  const categories = [...new Set(data.map((d) => d.category))];
  const maxCount = Math.max(...data.map((d) => d.count));
  const lookup = new Map(data.map((d) => [`${d.topic}-${d.category}`, d.count]));

  return (
    <div>
      <h2 className="font-mono text-[10px] uppercase tracking-widest text-[#555] mb-4">
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
            <div key={cat} className="font-mono text-[8px] text-[#555] uppercase text-center truncate px-1">
              {cat.replace(/_/g, " ")}
            </div>
          ))}
          {topics.map((topic) => (
            <React.Fragment key={topic}>
              <div className="font-mono text-[9px] text-[#777] uppercase flex items-center truncate">
                {topic.replace(/_/g, " ")}
              </div>
              {categories.map((cat) => {
                const count = lookup.get(`${topic}-${cat}`) ?? 0;
                const intensity = maxCount > 0 ? count / maxCount : 0;
                return (
                  <div
                    key={`${topic}-${cat}`}
                    className="flex items-center justify-center font-mono text-[8px] border border-[#222]"
                    style={{
                      backgroundColor: count > 0
                        ? `rgba(0, 255, 136, ${0.1 + intensity * 0.8})`
                        : "transparent",
                      color: intensity > 0.5 ? "#000" : "#555",
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
      <h2 className="font-mono text-[10px] uppercase tracking-widest text-[#555] mb-4">
        Top Sources
      </h2>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} layout="vertical" margin={{ left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#222" />
          <XAxis
            type="number"
            tick={{ fontSize: 10, fill: "#555", fontFamily: "'Space Mono', monospace" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey="name"
            tick={{ fontSize: 10, fill: "#777", fontFamily: "'Space Mono', monospace" }}
            axisLine={false}
            tickLine={false}
            width={110}
          />
          <Tooltip contentStyle={tooltipStyle} labelStyle={labelStyle} cursor={{ fill: "#1a1a1a" }} />
          <Bar dataKey="count" fill="#00ff88" radius={[0, 0, 0, 0]} />
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
    <div className="max-w-5xl mx-auto px-6 py-8">
      <div className="flex items-baseline gap-4 mb-6">
        <h1 className="font-mono text-2xl font-bold uppercase tracking-tight text-[#e8e8e0]">
          Analytics
        </h1>
        <span className="font-mono text-[10px] text-[#00ff88] tracking-widest uppercase">
          Dashboard
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
              <Loading message="Loading analytics..." />
            ) : !data ? (
              <p className="text-[#555] font-mono text-sm text-center py-12">
                No analytics data available.
              </p>
            ) : (
              <div className="space-y-6">
                <div className="border-2 border-[#333] bg-[#111] p-5 animate-fade-in-up" style={{ animationDelay: "0ms" }}>
                  <TopicsChart data={data.topic_distribution} />
                </div>
                <div className="border-2 border-[#333] bg-[#111] p-5 animate-fade-in-up" style={{ animationDelay: "30ms" }}>
                  <SentimentChart data={data.sentiment_distribution ?? []} />
                </div>
                <div className="border-2 border-[#333] bg-[#111] p-5 animate-fade-in-up" style={{ animationDelay: "60ms" }}>
                  <HeatmapChart data={data.topic_category_heatmap ?? []} />
                </div>
                <div className="border-2 border-[#333] bg-[#111] p-5 animate-fade-in-up" style={{ animationDelay: "90ms" }}>
                  <CategoryChart data={data.category_breakdown ?? []} />
                </div>
                <div className="border-2 border-[#333] bg-[#111] p-5 animate-fade-in-up" style={{ animationDelay: "120ms" }}>
                  <VolumeChart data={data.daily_volume} />
                </div>
                <div className="border-2 border-[#333] bg-[#111] p-5 animate-fade-in-up" style={{ animationDelay: "150ms" }}>
                  <SourcesChart data={data.source_breakdown} />
                </div>
              </div>
            )}
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
}
