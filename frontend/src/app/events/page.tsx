"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { FeedSkeleton, CardSkeleton } from "@/components/loading";
import { api, type Event, type Headline } from "@/lib/api";
import { ArrowLeft, Layers, TrendingUp, TrendingDown, Minus } from "lucide-react";

const PAGE_SIZE = 20;

const EVENT_TYPE_COLORS: Record<string, { bg: string; text: string }> = {
  earnings_report:   { bg: "rgba(255,159,10,0.15)",  text: "#ff9f0a" },
  policy_decision:   { bg: "rgba(255,214,10,0.15)",  text: "#ffd60a" },
  market_move:       { bg: "rgba(48,209,88,0.15)",   text: "#30d158" },
  deal:              { bg: "rgba(191,90,242,0.15)",   text: "#bf5af2" },
  regulatory_action: { bg: "rgba(10,132,255,0.15)",  text: "#0a84ff" },
  crypto_event:      { bg: "rgba(191,90,242,0.15)",   text: "#bf5af2" },
  other:             { bg: "rgba(99,99,102,0.15)",    text: "#636366" },
};

function eventTypeColors(type: string) {
  return EVENT_TYPE_COLORS[type.toLowerCase()] ?? EVENT_TYPE_COLORS.other;
}

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

function EventCard({
  event,
  onClick,
  index,
}: {
  event: Event;
  onClick: () => void;
  index: number;
}) {
  const etc = event.event_type ? eventTypeColors(event.event_type) : null;

  return (
    <button
      onClick={onClick}
      className="animate-fade-in-up w-full text-left border border-[#3a3a3c] bg-[#2c2c2e] rounded-[10px] px-4 py-3 hover:bg-[#3a3a3c] transition-colors group"
      style={{
        animationDelay: `${index * 30}ms`,
        boxShadow: "0 1px 3px rgba(0,0,0,0.2)",
      }}
    >
      <div className="flex items-start justify-between gap-3 mb-2">
        <span className="text-[15px] font-medium leading-snug text-[#e5e5e7] group-hover:text-[#0a84ff] transition-colors">
          {event.label.replace(/['".,;:!?]+$/, '').trim()}
        </span>
        {event.event_type && etc && (
          <span
            className="inline-block px-2 py-0.5 text-[11px] font-medium rounded-md shrink-0"
            style={{
              backgroundColor: etc.bg,
              color: etc.text,
            }}
          >
            {event.event_type.replace(/_/g, " ")}
          </span>
        )}
      </div>
      <div className="flex items-center gap-4 text-xs">
        <span className="flex items-center gap-1.5 text-[#0a84ff]">
          <Layers className="w-3 h-3" />
          <span className="font-semibold text-sm">{event.headline_count}</span>
          <span className="text-[#98989d]">headlines</span>
        </span>
        {event.created_at && (
          <span className="text-[#636366]">
            {new Date(event.created_at).toLocaleDateString()}
          </span>
        )}
      </div>
    </button>
  );
}

function SentimentBar({ headlines }: { headlines: Headline[] }) {
  const bullish = headlines.filter((h) => h.sentiment === "bullish").length;
  const bearish = headlines.filter((h) => h.sentiment === "bearish").length;
  const neutral = headlines.length - bullish - bearish;
  const total = headlines.length;
  if (total === 0) return null;

  return (
    <div>
      <div className="flex h-2.5 w-full overflow-hidden rounded-lg border border-[#3a3a3c]">
        {bullish > 0 && (
          <div
            style={{ width: `${(bullish / total) * 100}%`, backgroundColor: "#30d158" }}
          />
        )}
        {neutral > 0 && (
          <div
            style={{ width: `${(neutral / total) * 100}%`, backgroundColor: "#636366" }}
          />
        )}
        {bearish > 0 && (
          <div
            style={{ width: `${(bearish / total) * 100}%`, backgroundColor: "#ff453a" }}
          />
        )}
      </div>
      <div className="flex gap-4 mt-2 text-[11px]">
        <span className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-[#30d158]" />
          <span className="text-[#98989d]">Bullish</span>
          <span className="text-[#30d158] font-semibold">{bullish}</span>
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-[#636366]" />
          <span className="text-[#98989d]">Neutral</span>
          <span className="text-[#636366] font-semibold">{neutral}</span>
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-[#ff453a]" />
          <span className="text-[#98989d]">Bearish</span>
          <span className="text-[#ff453a] font-semibold">{bearish}</span>
        </span>
      </div>
    </div>
  );
}

function EventDetail({
  event,
  onBack,
}: {
  event: Event;
  onBack: () => void;
}) {
  const [headlines, setHeadlines] = useState<Headline[]>(event.members ?? event.headlines ?? []);
  const [loading, setLoading] = useState(!event.members && !event.headlines);
  const etc = event.event_type ? eventTypeColors(event.event_type) : null;

  useEffect(() => {
    if (event.members || event.headlines) return;
    setLoading(true);
    api.events
      .get(event.id)
      .then((full) => setHeadlines(full.members ?? full.headlines ?? []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [event]);

  // Compute date range from headlines
  const dates = headlines
    .map((h) => h.published_at)
    .filter(Boolean)
    .map((d) => new Date(d!).getTime());
  const earliest = dates.length > 0 ? new Date(Math.min(...dates)) : null;
  const latest = dates.length > 0 ? new Date(Math.max(...dates)) : null;

  // Unique topics from headlines
  const uniqueTopics = [...new Set(headlines.map((h) => h.topic).filter(Boolean))] as string[];

  return (
    <div>
      <button
        onClick={onBack}
        className="flex items-center gap-1.5 text-[#0a84ff] hover:underline text-sm mb-6 transition-colors"
      >
        <ArrowLeft className="w-3.5 h-3.5" />
        Back to events
      </button>

      <div className="border border-[#3a3a3c] bg-[#2c2c2e] rounded-[10px] p-5 mb-6" style={{ boxShadow: "0 1px 3px rgba(0,0,0,0.2)" }}>
        <div className="flex items-start justify-between gap-4 mb-2">
          <h2 className="text-2xl font-bold text-[#e5e5e7]">
            {event.label.replace(/['".,;:!?]+$/, '').trim()}
          </h2>
          {event.event_type && etc && (
            <span
              className="inline-block px-2 py-0.5 text-[11px] font-medium rounded-md shrink-0"
              style={{
                backgroundColor: etc.bg,
                color: etc.text,
              }}
            >
              {event.event_type.replace(/_/g, " ")}
            </span>
          )}
        </div>
        <p className="text-sm text-[#98989d] mb-4">
          <span className="text-[#0a84ff] font-semibold">{event.headline_count}</span>
          {" "}headlines
          {earliest && latest && (
            <>
              {" · "}
              <span className="text-[#e5e5e7]">
                {earliest.toLocaleDateString()}
                {earliest.getTime() !== latest.getTime() && ` — ${latest.toLocaleDateString()}`}
              </span>
            </>
          )}
          {!earliest && (
            <>
              {" · "}
              {new Date(event.created_at).toLocaleDateString()}
            </>
          )}
        </p>

        {/* Sentiment summary bar */}
        {headlines.length > 0 && (
          <div className="mb-4">
            <SentimentBar headlines={headlines} />
          </div>
        )}

        {/* Topic tags */}
        {uniqueTopics.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {uniqueTopics.map((t) => {
              const tc = topicColors(t);
              return (
                <span
                  key={t}
                  className="inline-block px-2 py-0.5 text-[11px] font-medium rounded-md"
                  style={{ backgroundColor: tc.bg, color: tc.text }}
                >
                  {t.replace(/_/g, " ")}
                </span>
              );
            })}
          </div>
        )}
      </div>

      {loading ? (
        <FeedSkeleton />
      ) : headlines.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-[#98989d] text-sm">No headlines in this cluster</p>
          <p className="text-[#636366] text-xs mt-2">Headlines may not have been loaded yet</p>
        </div>
      ) : (
        <div className="space-y-2">
          {headlines.map((h, i) => {
            const tc = h.topic ? topicColors(h.topic) : null;
            return (
              <div
                key={h.id}
                className="animate-fade-in-up border border-[#3a3a3c] bg-[#2c2c2e] rounded-[10px] px-4 py-3 hover:bg-[#3a3a3c] transition-colors"
                style={{
                  animationDelay: `${i * 30}ms`,
                  boxShadow: "0 1px 3px rgba(0,0,0,0.2)",
                }}
              >
                <div className="flex items-start gap-2.5">
                  <div className="pt-0.5 shrink-0">{sentimentIcon(h.sentiment)}</div>
                  <div className="flex-1 min-w-0">
                    <a
                      href={h.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[15px] font-medium text-[#e5e5e7] hover:text-[#0a84ff] transition-colors leading-snug"
                    >
                      {h.title}
                    </a>
                    {h.description && (
                      <p className="text-[#98989d] text-sm mt-1 line-clamp-2">
                        {h.description}
                      </p>
                    )}
                    <div className="flex items-center gap-2 mt-2 flex-wrap">
                      {h.topic && tc && (
                        <span
                          className="inline-block px-2 py-0.5 text-[10px] font-medium rounded-md"
                          style={{ backgroundColor: tc.bg, color: tc.text }}
                        >
                          {h.topic.replace(/_/g, " ")}
                        </span>
                      )}
                      <span className="text-[12px] text-[#636366]">
                        {h.source_name}
                        {h.published_at &&
                          ` · ${new Date(h.published_at).toLocaleDateString()}`}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default function EventsPage() {
  const [events, setEvents] = useState<Event[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [selected, setSelected] = useState<Event | null>(null);

  const fetchEvents = async (nextPage: number, replace: boolean) => {
    if (nextPage === 1) setLoading(true);
    else setLoadingMore(true);
    try {
      const res = await api.events.list({ page: nextPage, limit: PAGE_SIZE });
      setEvents((prev) => (replace ? res.data : [...prev, ...res.data]));
      setTotalPages(res.pagination.total_pages);
      setPage(nextPage);
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  };

  useEffect(() => {
    fetchEvents(1, true);
  }, []);

  if (selected) {
    return (
      <div className="max-w-4xl mx-auto px-3 sm:px-6 py-6 sm:py-8">
        <EventDetail event={selected} onBack={() => setSelected(null)} />
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-3 sm:px-6 py-6 sm:py-8">
      <div className="flex items-baseline gap-4 mb-6">
        <h1 className="text-[28px] font-bold text-[#e5e5e7]">
          Events
        </h1>
        <span className="text-[12px] text-[#98989d]">
          Clusters
        </span>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
      ) : events.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-[#98989d] text-sm">No event clusters found</p>
          <p className="text-[#636366] text-xs mt-2">Events will appear after the pipeline groups headlines into clusters</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {events.map((e, i) => (
            <EventCard key={e.id} event={e} onClick={() => setSelected(e)} index={i} />
          ))}
        </div>
      )}

      {!loading && page < totalPages && (
        <div className="flex justify-center mt-8">
          <Button
            onClick={() => fetchEvents(page + 1, false)}
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
