"use client";

import { useEffect, useState } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Check, Download } from "lucide-react";
import { api, AppSettings } from "@/lib/api";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8081";

const TOPICS = [
  "all",
  "markets",
  "economy",
  "earnings",
  "crypto",
  "commodities",
  "real_estate",
  "regulation",
  "fintech",
  "prediction_markets",
  "mergers",
];

const SENTIMENTS = ["all", "bullish", "bearish", "neutral"];

const INTERVALS = [
  { value: "15", label: "15 min" },
  { value: "30", label: "30 min" },
  { value: "60", label: "1 hour" },
  { value: "240", label: "4 hours" },
];

const RETENTION_OPTIONS = [
  { value: "0", label: "Never" },
  { value: "7", label: "7 days" },
  { value: "30", label: "30 days" },
  { value: "90", label: "90 days" },
];

const EXPORT_PERIODS = ["24h", "7d", "30d"] as const;
type ExportPeriod = (typeof EXPORT_PERIODS)[number];

const DEFAULTS: AppSettings = {
  pipeline_schedule_enabled: "false",
  pipeline_schedule_interval: "60",
  retention_days: "0",
  default_topic: "all",
  default_sentiment: "all",
};

function SaveButton({
  onClick,
  saved,
  disabled,
}: {
  onClick: () => void;
  saved: boolean;
  disabled?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={
        saved
          ? "text-sm font-medium px-5 py-2 rounded-lg text-[#30d158] bg-[#30d158]/10 border border-[#30d158]/30 transition-colors"
          : "text-sm font-medium px-5 py-2 rounded-lg bg-[#0a84ff] text-white hover:bg-[#0a84ff]/90 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
      }
    >
      {saved ? (
        <span className="flex items-center gap-1.5">
          <Check className="w-3.5 h-3.5" />
          Saved!
        </span>
      ) : (
        "Save"
      )}
    </button>
  );
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<AppSettings>(DEFAULTS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Per-section draft state
  const [scheduleEnabled, setScheduleEnabled] = useState(false);
  const [scheduleInterval, setScheduleInterval] = useState("60");
  const [defaultTopic, setDefaultTopic] = useState("all");
  const [defaultSentiment, setDefaultSentiment] = useState("all");
  const [retentionDays, setRetentionDays] = useState("0");

  // Per-section saved flash
  const [savedSchedule, setSavedSchedule] = useState(false);
  const [savedFilters, setSavedFilters] = useState(false);
  const [savedRetention, setSavedRetention] = useState(false);

  // Export
  const [exportPeriod, setExportPeriod] = useState<ExportPeriod>("24h");

  useEffect(() => {
    api.settings
      .get()
      .then((s) => {
        setSettings(s);
        setScheduleEnabled(s.pipeline_schedule_enabled === "true");
        setScheduleInterval(s.pipeline_schedule_interval ?? "60");
        setDefaultTopic(s.default_topic ?? "all");
        setDefaultSentiment(s.default_sentiment ?? "all");
        setRetentionDays(s.retention_days ?? "0");
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  function flash(setter: (v: boolean) => void) {
    setter(true);
    setTimeout(() => setter(false), 2000);
  }

  async function saveSchedule() {
    await api.settings.update({
      pipeline_schedule_enabled: String(scheduleEnabled),
      pipeline_schedule_interval: scheduleInterval,
    });
    flash(setSavedSchedule);
  }

  async function saveFilters() {
    await api.settings.update({
      default_topic: defaultTopic,
      default_sentiment: defaultSentiment,
    });
    flash(setSavedFilters);
  }

  async function saveRetention() {
    await api.settings.update({ retention_days: retentionDays });
    flash(setSavedRetention);
  }

  function exportUrl(format: "csv" | "json") {
    return `${BASE_URL}/api/headlines/export?format=${format}&period=${exportPeriod}`;
  }

  const selectCls =
    "bg-[#1c1c1e] border border-[#48484a] text-[#e5e5e7] text-sm rounded-lg";
  const contentCls = "bg-[#2c2c2e] border border-[#3a3a3c] rounded-lg";
  const itemCls =
    "text-[#e5e5e7] focus:bg-[#3a3a3c] text-sm rounded-lg";

  return (
    <div className="max-w-xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="flex items-baseline gap-4 mb-8">
        <h1 className="text-2xl font-bold text-[#e5e5e7]">
          Settings
        </h1>
      </div>

      {loading && (
        <p className="text-xs text-[#636366] mb-6">Loading...</p>
      )}
      {error && (
        <p className="text-xs text-[#ff453a] mb-6">{error}</p>
      )}

      <div className="space-y-6">
        {/* -- Section 1: Pipeline Schedule -- */}
        <section className="border border-[#3a3a3c] bg-[#2c2c2e] rounded-[10px] overflow-hidden">
          <div className="px-4 py-2 bg-[#3a3a3c] rounded-t-[10px]">
            <p className="text-[11px] uppercase tracking-wide text-[#636366]">
              Pipeline Schedule
            </p>
          </div>

          <div className="divide-y divide-[#3a3a3c]">
            {/* Toggle */}
            <div className="flex items-center justify-between px-4 py-3">
              <div>
                <p className="text-[14px] font-medium text-[#e5e5e7]">
                  Auto-run
                </p>
                <p className="text-[12px] text-[#98989d] mt-0.5">
                  Run the pipeline on a schedule
                </p>
              </div>
              <button
                onClick={() => setScheduleEnabled((v) => !v)}
                className={
                  scheduleEnabled
                    ? "text-sm font-medium px-4 py-1.5 rounded-lg bg-[#30d158] text-white transition-colors"
                    : "text-sm font-medium px-4 py-1.5 rounded-lg bg-[#3a3a3c] text-[#98989d] hover:bg-[#48484a] transition-colors"
                }
              >
                {scheduleEnabled ? "Enabled" : "Disabled"}
              </button>
            </div>

            {/* Interval */}
            <div className="flex items-center justify-between px-4 py-3">
              <div>
                <p className="text-[14px] font-medium text-[#e5e5e7]">
                  Interval
                </p>
                <p className="text-[12px] text-[#98989d] mt-0.5">
                  How often to run
                </p>
              </div>
              <Select
                value={scheduleInterval}
                onValueChange={setScheduleInterval}
              >
                <SelectTrigger className={`w-32 ${selectCls}`}>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className={contentCls}>
                  {INTERVALS.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value} className={itemCls}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="flex justify-end px-4 py-3 border-t border-[#3a3a3c]">
            <SaveButton
              onClick={saveSchedule}
              saved={savedSchedule}
              disabled={loading}
            />
          </div>
        </section>

        {/* -- Section 2: Default Filters -- */}
        <section className="border border-[#3a3a3c] bg-[#2c2c2e] rounded-[10px] overflow-hidden">
          <div className="px-4 py-2 bg-[#3a3a3c] rounded-t-[10px]">
            <p className="text-[11px] uppercase tracking-wide text-[#636366]">
              Default Filters
            </p>
          </div>

          <div className="divide-y divide-[#3a3a3c]">
            {/* Topic */}
            <div className="flex items-center justify-between px-4 py-3">
              <p className="text-[14px] font-medium text-[#e5e5e7]">
                Default topic
              </p>
              <Select value={defaultTopic} onValueChange={setDefaultTopic}>
                <SelectTrigger className={`w-44 ${selectCls}`}>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className={contentCls}>
                  {TOPICS.map((t) => (
                    <SelectItem key={t} value={t} className={itemCls}>
                      {t === "all" ? "All" : t.replace("_", " ")}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Sentiment */}
            <div className="flex items-center justify-between px-4 py-3">
              <p className="text-[14px] font-medium text-[#e5e5e7]">
                Default sentiment
              </p>
              <Select
                value={defaultSentiment}
                onValueChange={setDefaultSentiment}
              >
                <SelectTrigger className={`w-44 ${selectCls}`}>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className={contentCls}>
                  {SENTIMENTS.map((s) => (
                    <SelectItem key={s} value={s} className={itemCls}>
                      {s.charAt(0).toUpperCase() + s.slice(1)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="flex items-center justify-between px-4 py-3 border-t border-[#3a3a3c]">
            <p className="text-[12px] text-[#636366]">
              Applied when loading the feed page
            </p>
            <SaveButton
              onClick={saveFilters}
              saved={savedFilters}
              disabled={loading}
            />
          </div>
        </section>

        {/* -- Section 3: Data Retention -- */}
        <section className="border border-[#3a3a3c] bg-[#2c2c2e] rounded-[10px] overflow-hidden">
          <div className="px-4 py-2 bg-[#3a3a3c] rounded-t-[10px]">
            <p className="text-[11px] uppercase tracking-wide text-[#636366]">
              Data Retention
            </p>
          </div>

          <div className="px-4 py-3 flex items-center justify-between">
            <p className="text-[14px] font-medium text-[#e5e5e7]">
              Keep headlines for
            </p>
            <Select value={retentionDays} onValueChange={setRetentionDays}>
              <SelectTrigger className={`w-32 ${selectCls}`}>
                <SelectValue />
              </SelectTrigger>
              <SelectContent className={contentCls}>
                {RETENTION_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value} className={itemCls}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {retentionDays !== "0" && (
            <div className="px-4 pb-3">
              <p className="text-[12px] text-[#ff9f0a]">
                Headlines older than {retentionDays} days will be deleted after
                each pipeline run
              </p>
            </div>
          )}

          <div className="flex justify-end px-4 py-3 border-t border-[#3a3a3c]">
            <SaveButton
              onClick={saveRetention}
              saved={savedRetention}
              disabled={loading}
            />
          </div>
        </section>

        {/* -- Section 4: Export Data -- */}
        <section className="border border-[#3a3a3c] bg-[#2c2c2e] rounded-[10px] overflow-hidden">
          <div className="px-4 py-2 bg-[#3a3a3c] rounded-t-[10px]">
            <p className="text-[11px] uppercase tracking-wide text-[#636366]">
              Export Data
            </p>
          </div>

          <div className="px-4 py-3 space-y-4">
            {/* Period selector */}
            <div className="flex items-center gap-2">
              <p className="text-sm text-[#98989d] mr-2">Period:</p>
              {EXPORT_PERIODS.map((p) => (
                <button
                  key={p}
                  onClick={() => setExportPeriod(p)}
                  className={
                    exportPeriod === p
                      ? "text-sm font-medium px-3 py-1.5 rounded-lg bg-[#0a84ff] text-white transition-colors"
                      : "text-sm font-medium px-3 py-1.5 rounded-lg bg-transparent border border-[#48484a] text-[#98989d] hover:border-[#636366] hover:text-[#e5e5e7] transition-colors"
                  }
                >
                  {p}
                </button>
              ))}
            </div>

            {/* Download buttons */}
            <div className="flex gap-3">
              <a
                href={exportUrl("csv")}
                download
                className="flex items-center gap-1.5 text-sm font-medium px-4 py-2 rounded-lg bg-transparent border border-[#48484a] text-[#e5e5e7] hover:border-[#0a84ff] hover:text-[#0a84ff] transition-colors"
              >
                <Download className="w-3.5 h-3.5" />
                Download CSV
              </a>
              <a
                href={exportUrl("json")}
                download
                className="flex items-center gap-1.5 text-sm font-medium px-4 py-2 rounded-lg bg-transparent border border-[#48484a] text-[#e5e5e7] hover:border-[#0a84ff] hover:text-[#0a84ff] transition-colors"
              >
                <Download className="w-3.5 h-3.5" />
                Download JSON
              </a>
            </div>
          </div>
        </section>

        {/* -- Section 5: About -- */}
        <section className="pt-6">
          <p className="text-[11px] uppercase tracking-wide text-[#636366] mb-2">
            About
          </p>
          <p className="text-[#98989d] text-sm">
            RSSFeed2 -- Financial News Intelligence Platform
          </p>
          <p className="text-[12px] text-[#636366] mt-1">
            Settings stored on server
          </p>
        </section>
      </div>
    </div>
  );
}
