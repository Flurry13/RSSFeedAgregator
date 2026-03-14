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
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Loading } from "@/components/loading";
import { api, type Headline } from "@/lib/api";
import { useSocket } from "@/hooks/use-socket";
import { Search } from "lucide-react";

const TOPICS = [
  "all",
  "politics",
  "technology",
  "business",
  "science",
  "health",
  "sports",
  "entertainment",
  "world",
];

const PAGE_SIZE = 20;

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
    <div className="max-w-3xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-semibold text-zinc-100 mb-6">Feed</h1>

      {/* Filters */}
      <div className="flex gap-3 mb-6">
        <form onSubmit={handleSearch} className="flex-1 flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
            <Input
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Search headlines…"
              className="pl-9 bg-zinc-900 border-zinc-800 text-zinc-100 placeholder:text-zinc-600"
            />
          </div>
          <Button type="submit" variant="secondary" className="bg-zinc-800 text-zinc-200 hover:bg-zinc-700">
            Search
          </Button>
        </form>

        <Select value={topic} onValueChange={(v) => setTopic(v ?? "all")}>
          <SelectTrigger className="w-40 bg-zinc-900 border-zinc-800 text-zinc-300">
            <SelectValue placeholder="Topic" />
          </SelectTrigger>
          <SelectContent className="bg-zinc-900 border-zinc-800">
            {TOPICS.map((t) => (
              <SelectItem
                key={t}
                value={t}
                className="text-zinc-300 focus:bg-zinc-800 capitalize"
              >
                {t === "all" ? "All topics" : t}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* List */}
      {loading ? (
        <Loading message="Loading headlines…" />
      ) : headlines.length === 0 ? (
        <p className="text-zinc-500 text-sm text-center py-12">No headlines found.</p>
      ) : (
        <div className="space-y-4">
          {headlines.map((h) => (
            <article
              key={h.id}
              className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 hover:border-zinc-700 transition-colors"
            >
              <div className="flex items-center gap-2 mb-2 flex-wrap">
                {h.topic && (
                  <Badge className="bg-zinc-800 text-zinc-300 border-zinc-700 text-xs capitalize">
                    {h.topic}
                  </Badge>
                )}
                {h.language && (
                  <Badge
                    variant="outline"
                    className="border-zinc-700 text-zinc-500 text-xs uppercase"
                  >
                    {h.language}
                  </Badge>
                )}
              </div>
              <a
                href={h.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-zinc-100 font-medium text-base leading-snug hover:text-zinc-300 transition-colors"
              >
                {h.title}
              </a>
              {h.description && (
                <p className="text-zinc-400 text-sm mt-1 line-clamp-2">{h.description}</p>
              )}
              <div className="flex items-center gap-2 mt-3 text-xs text-zinc-600">
                <span>{h.source_name}</span>
                {h.published_at && (
                  <>
                    <span>·</span>
                    <span>{new Date(h.published_at).toLocaleDateString()}</span>
                  </>
                )}
              </div>
            </article>
          ))}
        </div>
      )}

      {/* Load more */}
      {!loading && page < totalPages && (
        <div className="flex justify-center mt-8">
          <Button
            variant="outline"
            onClick={() => fetchHeadlines(page + 1, false)}
            disabled={loadingMore}
            className="border-zinc-700 text-zinc-300 hover:bg-zinc-800"
          >
            {loadingMore ? "Loading…" : "Load more"}
          </Button>
        </div>
      )}
    </div>
  );
}
