"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Loading } from "@/components/loading";
import { api, type Event, type Headline } from "@/lib/api";
import { ArrowLeft, Layers } from "lucide-react";

const PAGE_SIZE = 20;

const EVENT_TYPE_COLORS: Record<string, string> = {
  earnings_report: "#ff8800",
  policy_decision: "#ffd700",
  market_move: "#00ff88",
  deal: "#ff44aa",
  regulatory_action: "#4488ff",
  crypto_event: "#aa77ff",
  other: "#666",
};

function eventTypeBg(type: string): string {
  return EVENT_TYPE_COLORS[type.toLowerCase()] ?? "#00ff88";
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
  return (
    <button
      onClick={onClick}
      className="animate-fade-in-up w-full text-left border-2 border-[#333] bg-[#111] px-4 py-3 hover:border-[#00ff88] transition-colors group"
      style={{ animationDelay: `${index * 30}ms` }}
    >
      <div className="flex items-start justify-between gap-3 mb-2">
        <span className="font-mono text-sm font-bold leading-snug text-[#e8e8e0] group-hover:text-[#00ff88] transition-colors">
          {event.label}
        </span>
        {event.event_type && (
          <span
            className="inline-block px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider border-2 shrink-0 text-black"
            style={{
              backgroundColor: eventTypeBg(event.event_type),
              borderColor: eventTypeBg(event.event_type),
            }}
          >
            {event.event_type}
          </span>
        )}
      </div>
      <div className="flex items-center gap-4 font-mono text-xs">
        <span className="flex items-center gap-1.5 text-[#00ff88]">
          <Layers className="w-3 h-3" />
          <span className="font-bold text-sm">{event.headline_count}</span>
          <span className="text-[#555]">headlines</span>
        </span>
        {event.created_at && (
          <span className="text-[#444]">
            {new Date(event.created_at).toLocaleDateString()}
          </span>
        )}
      </div>
    </button>
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

  useEffect(() => {
    if (event.members || event.headlines) return;
    setLoading(true);
    api.events
      .get(event.id)
      .then((full) => setHeadlines(full.members ?? full.headlines ?? []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [event]);

  return (
    <div>
      <button
        onClick={onBack}
        className="flex items-center gap-1.5 text-[#555] hover:text-[#00ff88] font-mono text-xs mb-6 transition-colors tracking-widest uppercase"
      >
        <ArrowLeft className="w-3.5 h-3.5" />
        Back to events
      </button>

      <div className="border-2 border-[#333] bg-[#111] p-5 mb-6">
        <div className="flex items-start justify-between gap-4 mb-2">
          <h2 className="font-mono text-2xl font-bold uppercase tracking-tight text-[#e8e8e0]">
            {event.label}
          </h2>
          {event.event_type && (
            <span
              className="inline-block px-2.5 py-1 text-[9px] font-bold uppercase tracking-wider border-2 text-black shrink-0"
              style={{
                backgroundColor: eventTypeBg(event.event_type),
                borderColor: eventTypeBg(event.event_type),
              }}
            >
              {event.event_type}
            </span>
          )}
        </div>
        <p className="font-mono text-xs text-[#777]">
          <span className="text-[#00ff88] font-bold">{event.headline_count}</span>
          {" "}headlines
          {" "}<span className="text-[#333]">|</span>{" "}
          {new Date(event.created_at).toLocaleDateString()}
        </p>
      </div>

      {loading ? (
        <Loading message="Loading headlines..." />
      ) : headlines.length === 0 ? (
        <p className="text-[#555] font-mono text-sm">No headlines in this cluster.</p>
      ) : (
        <div className="border-2 border-[#333]">
          {headlines.map((h, i) => (
            <div
              key={h.id}
              className="animate-fade-in-up border-b-2 border-[#222] last:border-b-0 px-4 py-3 hover:bg-[#111] transition-colors"
              style={{ animationDelay: `${i * 30}ms` }}
            >
              <a
                href={h.url}
                target="_blank"
                rel="noopener noreferrer"
                className="font-mono text-sm font-bold text-[#e8e8e0] hover:text-[#00ff88] transition-colors"
              >
                {h.title}
              </a>
              {h.description && (
                <p className="text-[#777] text-xs mt-1 line-clamp-2 font-mono">
                  {h.description}
                </p>
              )}
              <p className="font-mono text-[11px] text-[#444] mt-2">
                {h.source_name}
                {h.published_at &&
                  ` // ${new Date(h.published_at).toLocaleDateString()}`}
              </p>
            </div>
          ))}
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
      <div className="max-w-4xl mx-auto px-6 py-8">
        <EventDetail event={selected} onBack={() => setSelected(null)} />
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      <div className="flex items-baseline gap-4 mb-6">
        <h1 className="font-mono text-2xl font-bold uppercase tracking-tight text-[#e8e8e0]">
          Events
        </h1>
        <span className="font-mono text-[10px] text-[#00ff88] tracking-widest uppercase">
          Clusters
        </span>
      </div>

      {loading ? (
        <Loading message="Loading events..." />
      ) : events.length === 0 ? (
        <p className="text-[#555] font-mono text-sm text-center py-12">
          No event clusters found.
        </p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {events.map((e, i) => (
            <EventCard key={e.id} event={e} onClick={() => setSelected(e)} index={i} />
          ))}
        </div>
      )}

      {!loading && page < totalPages && (
        <div className="flex justify-center mt-8">
          <button
            onClick={() => fetchEvents(page + 1, false)}
            disabled={loadingMore}
            className="border-2 border-[#333] bg-[#111] text-[#e8e8e0] hover:border-[#00ff88] hover:text-[#00ff88] font-mono text-[10px] font-bold uppercase tracking-wider px-6 py-2.5 transition-colors disabled:opacity-50"
          >
            {loadingMore ? "Loading..." : "Load more"}
          </button>
        </div>
      )}
    </div>
  );
}
