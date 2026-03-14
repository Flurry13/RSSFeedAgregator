"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Loading } from "@/components/loading";
import { api, type Event, type Headline } from "@/lib/api";
import { ArrowLeft, Layers } from "lucide-react";

const PAGE_SIZE = 20;

function EventCard({
  event,
  onClick,
}: {
  event: Event;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left bg-zinc-900 border border-zinc-800 rounded-lg p-4 hover:border-zinc-600 transition-colors"
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <span className="text-zinc-100 font-medium text-sm leading-snug">
          {event.label}
        </span>
        {event.event_type && (
          <Badge className="bg-zinc-800 text-zinc-400 border-zinc-700 text-xs shrink-0 capitalize">
            {event.event_type}
          </Badge>
        )}
      </div>
      <div className="flex items-center gap-3 text-xs text-zinc-600">
        <span className="flex items-center gap-1">
          <Layers className="w-3 h-3" />
          {event.headline_count} headlines
        </span>
        {event.created_at && (
          <span>{new Date(event.created_at).toLocaleDateString()}</span>
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
  const [headlines, setHeadlines] = useState<Headline[]>(event.headlines ?? []);
  const [loading, setLoading] = useState(!event.headlines);

  useEffect(() => {
    if (event.headlines) return;
    setLoading(true);
    api.events
      .get(event.id)
      .then((full) => setHeadlines(full.headlines ?? []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [event]);

  return (
    <div>
      <button
        onClick={onBack}
        className="flex items-center gap-1 text-zinc-500 hover:text-zinc-300 text-sm mb-4 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to events
      </button>

      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5 mb-6">
        <div className="flex items-center justify-between gap-3 mb-1">
          <h2 className="text-zinc-100 font-semibold text-lg">{event.label}</h2>
          {event.event_type && (
            <Badge className="bg-zinc-800 text-zinc-400 border-zinc-700 capitalize">
              {event.event_type}
            </Badge>
          )}
        </div>
        <p className="text-zinc-500 text-xs">
          {event.headline_count} headlines ·{" "}
          {new Date(event.created_at).toLocaleDateString()}
        </p>
      </div>

      {loading ? (
        <Loading message="Loading headlines…" />
      ) : headlines.length === 0 ? (
        <p className="text-zinc-500 text-sm">No headlines in this cluster.</p>
      ) : (
        <div className="space-y-3">
          {headlines.map((h) => (
            <div
              key={h.id}
              className="bg-zinc-900 border border-zinc-800 rounded-lg p-4"
            >
              <a
                href={h.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-zinc-100 text-sm font-medium hover:text-zinc-300 transition-colors"
              >
                {h.title}
              </a>
              {h.description && (
                <p className="text-zinc-400 text-xs mt-1 line-clamp-2">
                  {h.description}
                </p>
              )}
              <p className="text-zinc-600 text-xs mt-2">
                {h.source_name}
                {h.published_at &&
                  ` · ${new Date(h.published_at).toLocaleDateString()}`}
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
      <div className="max-w-3xl mx-auto px-4 py-8">
        <EventDetail event={selected} onBack={() => setSelected(null)} />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-semibold text-zinc-100 mb-6">Events</h1>

      {loading ? (
        <Loading message="Loading events…" />
      ) : events.length === 0 ? (
        <p className="text-zinc-500 text-sm text-center py-12">
          No event clusters found.
        </p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {events.map((e) => (
            <EventCard key={e.id} event={e} onClick={() => setSelected(e)} />
          ))}
        </div>
      )}

      {!loading && page < totalPages && (
        <div className="flex justify-center mt-8">
          <Button
            variant="outline"
            onClick={() => fetchEvents(page + 1, false)}
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
