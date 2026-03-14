"use client";

import { useEffect, useState } from "react";
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

const COLORS = [
  "#6366f1",
  "#22d3ee",
  "#f59e0b",
  "#10b981",
  "#f43f5e",
  "#a78bfa",
  "#fb923c",
  "#34d399",
];

const tooltipStyle = {
  backgroundColor: "#18181b",
  border: "1px solid #3f3f46",
  borderRadius: "6px",
  color: "#e4e4e7",
  fontSize: 12,
};

const labelStyle = { color: "#a1a1aa", fontSize: 11 };

function TopicsChart({ data }: { data: AnalyticsData["topics"] }) {
  return (
    <div>
      <h2 className="text-zinc-400 text-sm font-medium mb-4">Topics</h2>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} margin={{ left: -20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
          <XAxis
            dataKey="topic"
            tick={{ fontSize: 11, fill: "#71717a" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 11, fill: "#71717a" }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip contentStyle={tooltipStyle} labelStyle={labelStyle} />
          <Bar dataKey="count" fill="#6366f1" radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function LanguagesChart({ data }: { data: AnalyticsData["languages"] }) {
  return (
    <div>
      <h2 className="text-zinc-400 text-sm font-medium mb-4">Languages</h2>
      <div className="flex items-center gap-6">
        <ResponsiveContainer width="60%" height={200}>
          <PieChart>
            <Pie
              data={data}
              dataKey="count"
              nameKey="language"
              cx="50%"
              cy="50%"
              outerRadius={80}
              labelLine={false}
            >
              {data.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip contentStyle={tooltipStyle} />
          </PieChart>
        </ResponsiveContainer>
        <div className="flex flex-col gap-2 text-xs">
          {data.map((d, i) => (
            <div key={d.language} className="flex items-center gap-2">
              <span
                className="w-2.5 h-2.5 rounded-sm shrink-0"
                style={{ background: COLORS[i % COLORS.length] }}
              />
              <span className="text-zinc-400 uppercase">{d.language}</span>
              <span className="text-zinc-500 ml-1">{d.count}</span>
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
      <h2 className="text-zinc-400 text-sm font-medium mb-4">Daily Volume</h2>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={data} margin={{ left: -20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 10, fill: "#71717a" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 11, fill: "#71717a" }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip contentStyle={tooltipStyle} labelStyle={labelStyle} />
          <Line
            type="monotone"
            dataKey="count"
            stroke="#22d3ee"
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function SourcesChart({ data }: { data: AnalyticsData["top_sources"] }) {
  const mapped = data.map((d) => ({ ...d, name: d.source }));
  return (
    <div>
      <h2 className="text-zinc-400 text-sm font-medium mb-4">Top Sources</h2>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={mapped} layout="vertical" margin={{ left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
          <XAxis
            type="number"
            tick={{ fontSize: 11, fill: "#71717a" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey="name"
            tick={{ fontSize: 10, fill: "#71717a" }}
            axisLine={false}
            tickLine={false}
            width={110}
          />
          <Tooltip contentStyle={tooltipStyle} labelStyle={labelStyle} />
          <Bar dataKey="count" fill="#10b981" radius={[0, 3, 3, 0]} />
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
    <div className="max-w-4xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-semibold text-zinc-100 mb-6">Analytics</h1>

      <Tabs value={period} onValueChange={(v) => setPeriod(v as Period)}>
        <TabsList className="bg-zinc-900 border border-zinc-800 mb-6">
          <TabsTrigger value="24h" className="data-[state=active]:bg-zinc-800 text-zinc-400">
            24h
          </TabsTrigger>
          <TabsTrigger value="7d" className="data-[state=active]:bg-zinc-800 text-zinc-400">
            7d
          </TabsTrigger>
          <TabsTrigger value="30d" className="data-[state=active]:bg-zinc-800 text-zinc-400">
            30d
          </TabsTrigger>
        </TabsList>

        {(["24h", "7d", "30d"] as Period[]).map((p) => (
          <TabsContent key={p} value={p}>
            {loading ? (
              <Loading message="Loading analytics…" />
            ) : !data ? (
              <p className="text-zinc-500 text-sm text-center py-12">
                No analytics data available.
              </p>
            ) : (
              <div className="space-y-8">
                <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5">
                  <TopicsChart data={data.topics} />
                </div>
                <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5">
                  <LanguagesChart data={data.languages} />
                </div>
                <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5">
                  <VolumeChart data={data.daily_volume} />
                </div>
                <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5">
                  <SourcesChart data={data.top_sources} />
                </div>
              </div>
            )}
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
}
