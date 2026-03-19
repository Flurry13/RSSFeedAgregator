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
import { Search } from "lucide-react";

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

function topicStyle(topic: string): { bg: string; fg: string; border: string } {
  const m: Record<string, { bg: string; fg: string; border: string }> = {
    markets:            { bg: "bg-[#00ff88]", fg: "text-black", border: "border-[#00ff88]" },
    economy:            { bg: "bg-[#ffd700]", fg: "text-black", border: "border-[#ffd700]" },
    earnings:           { bg: "bg-[#ff8800]", fg: "text-black", border: "border-[#ff8800]" },
    crypto:             { bg: "bg-[#aa77ff]", fg: "text-black", border: "border-[#aa77ff]" },
    commodities:        { bg: "bg-[#ff3333]", fg: "text-black", border: "border-[#ff3333]" },
    real_estate:        { bg: "bg-[#00dddd]", fg: "text-black", border: "border-[#00dddd]" },
    regulation:         { bg: "bg-[#4488ff]", fg: "text-black", border: "border-[#4488ff]" },
    fintech:            { bg: "bg-[#33ff99]", fg: "text-black", border: "border-[#33ff99]" },
    prediction_markets: { bg: "bg-[#ff69b4]", fg: "text-black", border: "border-[#ff69b4]" },
    mergers:            { bg: "bg-[#ff44aa]", fg: "text-black", border: "border-[#ff44aa]" },
    general:            { bg: "bg-[#666]",    fg: "text-black", border: "border-[#666]" },
  };
  return m[topic.toLowerCase()] ?? m.general;
}

function topicBorderColor(topic: string): string {
  const m: Record<string, string> = {
    markets: "#00ff88", economy: "#ffd700", earnings: "#ff8800",
    crypto: "#aa77ff", commodities: "#ff3333", real_estate: "#00dddd",
    regulation: "#4488ff", fintech: "#33ff99", prediction_markets: "#ff69b4",
    mergers: "#ff44aa",
  };
  return m[topic.toLowerCase()] ?? "#333";
}

export default function FeedPage() {
  const [headlines, setHeadlines] = useState<Headline[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [search, setSearch] = useState("");
  const [topic, setTopic] = useState("all");
  const [searchInput, setSearchInput] = useState("");

  const fetchHeadlines = useCallback(
    async (nextPage: number, replace: boolean) => {
      if (nextPage === 1) setLoading(true);
      else setLoadingMore(true);
      try {
        const res = await api.headlines.list({
          page: nextPage,
          limit: PAGE_SIZE,
          q: search || undefined,
          topic: topic !== "all" ? topic : undefined,
        });
        setHeadlines((prev) => (replace ? res.data : [...prev, ...res.data]));
        setTotalPages(res.pagination.total_pages);
        setPage(nextPage);
      } finally {
        setLoading(false);
        setLoadingMore(false);
      }
    },
    [search, topic]
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
        <h1 className="text-2xl font-bold uppercase tracking-tight text-[#e8e8e0]">
          Feed
        </h1>
        <span className="text-[10px] text-[#00ff88] tracking-widest">
          LIVE
        </span>
      </div>

      {/* Filters */}
      <div className="flex gap-2 mb-4">
        <form onSubmit={handleSearch} className="flex-1 flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[#555]" />
            <Input
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="grep headlines..."
              className="pl-8 bg-[#111] border-2 border-[#333] text-[#e8e8e0] placeholder:text-[#444] text-xs h-8 focus:border-[#00ff88] focus:ring-0"
            />
          </div>
          <Button
            type="submit"
            className="bg-[#00ff88] text-black hover:bg-[#00dd77] text-[10px] font-bold uppercase tracking-wider h-8 px-4 border-2 border-[#00ff88] hover:border-[#00dd77]"
          >
            Search
          </Button>
        </form>

        <Select value={topic} onValueChange={(v) => setTopic(v ?? "all")}>
          <SelectTrigger className="w-36 bg-[#111] border-2 border-[#333] text-[#e8e8e0] text-[10px] uppercase tracking-wider h-8">
            <SelectValue placeholder="Topic" />
          </SelectTrigger>
          <SelectContent className="bg-[#111] border-2 border-[#333]">
            {TOPICS.map((t) => (
              <SelectItem
                key={t}
                value={t}
                className="text-[#e8e8e0] focus:bg-[#1a1a1a] uppercase text-[10px] tracking-wider"
              >
                {t === "all" ? "ALL TOPICS" : t}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Headlines */}
      {loading ? (
        <Loading message="Loading..." />
      ) : headlines.length === 0 ? (
        <p className="text-[#555] text-xs text-center py-12">
          No headlines found.
        </p>
      ) : (
        <div className="border-2 border-[#333]">
          {headlines.map((h, i) => {
            const tc = h.topic ? topicStyle(h.topic) : null;
            return (
              <article
                key={h.id}
                className="animate-fade-in-up border-b-2 border-[#222] last:border-b-0 px-3 py-2.5 hover:bg-[#111] transition-colors"
                style={{
                  animationDelay: `${i * 30}ms`,
                  borderLeftWidth: "4px",
                  borderLeftColor: h.topic ? topicBorderColor(h.topic) : "#222",
                }}
              >
                <div className="flex items-start gap-3">
                  {/* Topic badge */}
                  <div className="shrink-0 w-20 pt-0.5">
                    {h.topic && tc && (
                      <span
                        className={`inline-block px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider border-2 ${tc.bg} ${tc.fg} ${tc.border}`}
                      >
                        {h.topic}
                      </span>
                    )}
                  </div>

                  {/* Title */}
                  <div className="flex-1 min-w-0">
                    <a
                      href={h.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm font-bold text-[#e8e8e0] hover:text-[#00ff88] transition-colors leading-snug"
                    >
                      {h.title}
                    </a>
                  </div>

                  {/* Meta */}
                  <div className="shrink-0 text-right">
                    <span className="text-[10px] text-[#666] block">
                      {h.source_name}
                    </span>
                    {h.published_at && (
                      <span className="text-[9px] text-[#444] block">
                        {new Date(h.published_at).toLocaleDateString()}
                      </span>
                    )}
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
            variant="outline"
            onClick={() => fetchHeadlines(page + 1, false)}
            disabled={loadingMore}
            className="border-2 border-[#333] text-[#00ff88] hover:bg-[#111] hover:border-[#00ff88] text-[10px] uppercase tracking-wider font-bold"
          >
            {loadingMore ? "Loading..." : "[ Load More ]"}
          </Button>
        </div>
      )}
    </div>
  );
}
