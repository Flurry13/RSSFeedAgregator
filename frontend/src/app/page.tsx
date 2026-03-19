"use client";

import { useCallback, useEffect, useState } from "react";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Loading } from "@/components/loading";
import { api, type Headline } from "@/lib/api";
import { useSocket } from "@/hooks/use-socket";
import { Search, TrendingUp, TrendingDown, Minus } from "lucide-react";

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

const PAGE_SIZE = 20;

const TOPIC_COLORS: Record<string, { bg: string; text: string }> = {
  markets:            { bg: "rgba(48,209,88,0.15)",  text: "#30d158" },
  economy:            { bg: "rgba(255,214,10,0.15)", text: "#ffd60a" },
  earnings:           { bg: "rgba(255,159,10,0.15)", text: "#ff9f0a" },
  crypto:             { bg: "rgba(191,90,242,0.15)", text: "#bf5af2" },
  commodities:        { bg: "rgba(255,69,58,0.15)",  text: "#ff453a" },
  real_estate:        { bg: "rgba(100,210,255,0.15)", text: "#64d2ff" },
  regulation:         { bg: "rgba(10,132,255,0.15)", text: "#0a84ff" },
  fintech:            { bg: "rgba(48,209,88,0.15)",  text: "#30d158" },
  prediction_markets: { bg: "rgba(255,55,95,0.15)",  text: "#ff375f" },
  mergers:            { bg: "rgba(191,90,242,0.15)", text: "#bf5af2" },
  general:            { bg: "rgba(152,152,157,0.15)", text: "#98989d" },
};

function topicColors(topic: string) {
  return TOPIC_COLORS[topic.toLowerCase()] ?? TOPIC_COLORS.general;
}

function sentimentIcon(sentiment?: string) {
  if (sentiment === "bullish")
    return <TrendingUp className="w-3.5 h-3.5 text-[#30d158]" />;
  if (sentiment === "bearish")
    return <TrendingDown className="w-3.5 h-3.5 text-[#ff453a]" />;
  if (sentiment === "neutral")
    return <Minus className="w-3.5 h-3.5 text-[#636366]" />;
  return null;
}

export default function FeedPage() {
  const [headlines, setHeadlines] = useState<Headline[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [search, setSearch] = useState("");
  const [topic, setTopic] = useState<string | null>(null);
  const [searchInput, setSearchInput] = useState("");
  const [sentiment, setSentiment] = useState<string | null>(null);

  useEffect(() => {
    api.settings.get().then((s) => {
      setTopic(s.default_topic || "all");
      setSentiment(s.default_sentiment || "all");
    }).catch(() => {
      setTopic("all");
      setSentiment("all");
    });
  }, []);

  const fetchHeadlines = useCallback(
    async (nextPage: number, replace: boolean) => {
      if (topic === null || sentiment === null) return;
      if (nextPage === 1) setLoading(true);
      else setLoadingMore(true);
      try {
        const res = await api.headlines.list({
          page: nextPage,
          limit: PAGE_SIZE,
          q: search || undefined,
          topic: topic !== "all" ? topic : undefined,
          sentiment: sentiment !== "all" ? sentiment : undefined,
        });
        setHeadlines((prev) => (replace ? res.data : [...prev, ...res.data]));
        setTotalPages(res.pagination.total_pages);
        setPage(nextPage);
      } finally {
        setLoading(false);
        setLoadingMore(false);
      }
    },
    [search, topic, sentiment]
  );

  useEffect(() => {
    fetchHeadlines(1, true);
  }, [fetchHeadlines]);

  const onHeadlinesUpdate = useCallback(() => {
    fetchHeadlines(1, true);
  }, [fetchHeadlines]);

  useSocket({ onHeadlinesUpdate });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSearch(searchInput);
  };

  return (
    <div className="px-4 py-6">
      {/* Header */}
      <div className="flex items-baseline gap-3 mb-4">
        <h1 className="text-[28px] font-bold text-[#e5e5e7]">
          Feed
        </h1>
        <span className="text-[10px] text-[#30d158] tracking-widest uppercase">
          LIVE
        </span>
      </div>

      {/* Filters */}
      <div className="flex gap-2 mb-4">
        <form onSubmit={handleSearch} className="flex-1 flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[#636366]" />
            <Input
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Search headlines..."
              className="pl-8 bg-[#1c1c1e] border border-[#48484a] text-[#e5e5e7] placeholder:text-[#636366] text-sm h-8 rounded-lg focus:border-[#0a84ff] focus:ring-0"
            />
          </div>
          <Button
            type="submit"
            className="bg-[#0a84ff] text-white hover:bg-[#0a84ff]/90 text-xs font-medium h-8 px-4 rounded-lg"
          >
            Search
          </Button>
        </form>

        <Select value={topic ?? "all"} onValueChange={(v) => setTopic(v ?? "all")}>
          <SelectTrigger className="w-36 bg-[#1c1c1e] border border-[#48484a] text-[#e5e5e7] text-xs h-8 rounded-lg">
            <SelectValue placeholder="Topic" />
          </SelectTrigger>
          <SelectContent className="bg-[#2c2c2e] border border-[#3a3a3c] rounded-[10px]">
            {TOPICS.map((t) => (
              <SelectItem
                key={t}
                value={t}
                className="text-[#e5e5e7] focus:bg-[#3a3a3c] text-xs"
              >
                {t === "all" ? "All Topics" : t.replace(/_/g, " ")}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={sentiment ?? "all"} onValueChange={(v) => { setSentiment(v); }}>
          <SelectTrigger className="w-[130px] bg-[#1c1c1e] border border-[#48484a] text-[#e5e5e7] text-xs h-8 rounded-lg">
            <SelectValue placeholder="Sentiment" />
          </SelectTrigger>
          <SelectContent className="bg-[#2c2c2e] border border-[#3a3a3c] rounded-[10px]">
            {["all", "bullish", "bearish", "neutral"].map((s) => (
              <SelectItem key={s} value={s} className="text-xs text-[#e5e5e7] focus:bg-[#3a3a3c]">
                {s.charAt(0).toUpperCase() + s.slice(1)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Headlines */}
      {loading ? (
        <Loading message="Loading..." />
      ) : headlines.length === 0 ? (
        <p className="text-[#636366] text-sm text-center py-12">
          No headlines found.
        </p>
      ) : (
        <div className="space-y-2">
          {headlines.map((h, i) => {
            const tc = h.topic ? topicColors(h.topic) : null;
            return (
              <article
                key={h.id}
                className="animate-fade-in-up bg-[#2c2c2e] border border-[#3a3a3c] rounded-[10px] p-4 hover:bg-[#3a3a3c] transition-colors"
                style={{
                  animationDelay: `${i * 30}ms`,
                  boxShadow: "0 1px 3px rgba(0,0,0,0.2)",
                }}
              >
                <div className="flex items-start gap-3">
                  {/* Topic badge + sentiment */}
                  <div className="shrink-0 w-24 pt-0.5 flex flex-col gap-1.5">
                    {h.topic && tc && (
                      <span
                        className="inline-block px-2 py-0.5 text-[11px] font-medium rounded-md w-fit"
                        style={{
                          backgroundColor: tc.bg,
                          color: tc.text,
                        }}
                      >
                        {h.topic.replace(/_/g, " ")}
                      </span>
                    )}
                    {sentimentIcon(h.sentiment)}
                  </div>

                  {/* Title */}
                  <div className="flex-1 min-w-0">
                    <a
                      href={h.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[15px] font-medium text-[#e5e5e7] hover:text-[#0a84ff] transition-colors leading-snug"
                    >
                      {h.title}
                    </a>
                  </div>

                  {/* Meta */}
                  <div className="shrink-0 text-right">
                    <span className="text-[12px] text-[#98989d]">
                      {h.source_name}
                      {(h.published_at || h.created_at) &&
                        ` · ${new Date(h.published_at || h.created_at).toLocaleDateString()}`}
                    </span>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      )}

      {/* Load more */}
      {!loading && page < totalPages && (
        <div className="flex justify-center mt-6">
          <Button
            onClick={() => fetchHeadlines(page + 1, false)}
            disabled={loadingMore}
            className="bg-[#0a84ff] text-white hover:bg-[#0a84ff]/90 text-sm font-medium px-6 py-2 rounded-lg"
          >
            {loadingMore ? "Loading..." : "Load More"}
          </Button>
        </div>
      )}
    </div>
  );
}
