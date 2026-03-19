"use client";

import { useEffect, useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Loading } from "@/components/loading";
import { api, type Source } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Trash2, AlertCircle, Plus, X } from "lucide-react";

function relativeTime(iso: string | null | undefined): string {
  if (!iso) return "Never";
  const diffMs = Date.now() - new Date(iso).getTime();
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
}

function healthDotColor(source: Source): string {
  const count = source.error_count ?? 0;
  if (!source.active) return "bg-[#444]";
  if (count >= 3) return "bg-[#ff3333]";
  if (count >= 1) return "bg-[#ffaa00]";
  return "bg-[#00ff88]";
}

export default function SourcesPage() {
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState<number | null>(null);
  const [toggling, setToggling] = useState<number | null>(null);

  // Add form state
  const [showForm, setShowForm] = useState(false);
  const [formName, setFormName] = useState("");
  const [formUrl, setFormUrl] = useState("");
  const [formLanguage, setFormLanguage] = useState("");
  const [formCountry, setFormCountry] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const res = await api.sources.list({ limit: 100 });
      setSources(res.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this source?")) return;
    setDeleting(id);
    try {
      await api.sources.delete(id);
      setSources((prev) => prev.filter((s) => s.id !== id));
    } finally {
      setDeleting(null);
    }
  };

  const handleToggle = async (source: Source) => {
    setToggling(source.id);
    try {
      const updated = await api.sources.update(source.id, {
        active: !source.active,
      });
      setSources((prev) => prev.map((s) => (s.id === updated.id ? updated : s)));
    } finally {
      setToggling(null);
    }
  };

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError("");
    if (!formName.trim() || !formUrl.trim()) {
      setFormError("Name and URL are required.");
      return;
    }
    setSubmitting(true);
    try {
      const created = await api.sources.create({
        name: formName.trim(),
        url: formUrl.trim(),
        language: formLanguage.trim() || undefined,
        country: formCountry.trim() || undefined,
        active: true,
      });
      setSources((prev) => [created, ...prev]);
      setFormName("");
      setFormUrl("");
      setFormLanguage("");
      setFormCountry("");
      setShowForm(false);
    } catch (err) {
      setFormError("Failed to create source.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-baseline gap-4">
          <h1 className="font-mono text-2xl font-bold uppercase tracking-tight text-[#e8e8e0]">
            Sources
          </h1>
          <span className="font-mono text-[10px] text-[#00ff88] tracking-widest uppercase">
            {sources.length} Feeds
          </span>
        </div>
        <button
          onClick={() => setShowForm((v) => !v)}
          className={cn(
            "font-mono text-[10px] uppercase tracking-wider font-bold px-4 py-2 border-2 transition-colors",
            showForm
              ? "bg-[#111] text-[#e8e8e0] border-[#333] hover:border-[#00ff88]"
              : "bg-[#00ff88] text-black border-[#00ff88] hover:bg-[#00dd77]"
          )}
        >
          {showForm ? (
            <span className="flex items-center gap-1.5">
              <X className="w-3 h-3" />
              Cancel
            </span>
          ) : (
            <span className="flex items-center gap-1.5">
              <Plus className="w-3 h-3" />
              Add
            </span>
          )}
        </button>
      </div>

      {/* Add form */}
      {showForm && (
        <form
          onSubmit={handleAdd}
          className="animate-fade-in-up border-2 border-[#333] bg-[#111] p-5 mb-6 space-y-4"
        >
          <p className="font-mono text-[10px] uppercase tracking-widest text-[#444]">
            New source
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Input
              placeholder="Name *"
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
              className="bg-[#0a0a0a] border-2 border-[#333] text-[#e8e8e0] placeholder:text-[#444] font-mono text-sm rounded-none focus:border-[#00ff88]"
            />
            <Input
              placeholder="Feed URL *"
              value={formUrl}
              onChange={(e) => setFormUrl(e.target.value)}
              className="bg-[#0a0a0a] border-2 border-[#333] text-[#e8e8e0] placeholder:text-[#444] font-mono text-sm rounded-none focus:border-[#00ff88]"
            />
            <Input
              placeholder="Language (e.g. en)"
              value={formLanguage}
              onChange={(e) => setFormLanguage(e.target.value)}
              className="bg-[#0a0a0a] border-2 border-[#333] text-[#e8e8e0] placeholder:text-[#444] font-mono text-sm rounded-none focus:border-[#00ff88]"
            />
            <Input
              placeholder="Country (e.g. US)"
              value={formCountry}
              onChange={(e) => setFormCountry(e.target.value)}
              className="bg-[#0a0a0a] border-2 border-[#333] text-[#e8e8e0] placeholder:text-[#444] font-mono text-sm rounded-none focus:border-[#00ff88]"
            />
          </div>
          {formError && (
            <p className="text-[#ff3333] font-mono text-xs">{formError}</p>
          )}
          <button
            type="submit"
            disabled={submitting}
            className="bg-[#00ff88] text-black border-2 border-[#00ff88] font-mono text-[10px] uppercase tracking-wider font-bold px-4 py-2 hover:bg-[#00dd77] disabled:opacity-50 transition-colors"
          >
            {submitting ? "Adding..." : "Add source"}
          </button>
        </form>
      )}

      {loading ? (
        <Loading message="Loading sources..." />
      ) : sources.length === 0 ? (
        <p className="text-[#555] font-mono text-sm text-center py-12">
          No sources yet. Add one above.
        </p>
      ) : (
        <div className="border-2 border-[#333]">
          {sources.map((source, i) => (
            <div
              key={source.id}
              className={cn(
                "animate-fade-in-up flex items-center gap-4 px-4 py-2.5 border-b-2 border-[#222] last:border-b-0 hover:bg-[#111] transition-colors",
                source.active ? "border-l-2 border-l-[#00ff88]" : "border-l-2 border-l-[#333]",
                source.fetch_error && "bg-[#ff333308]"
              )}
              style={{ animationDelay: `${i * 30}ms` }}
            >
              {/* Active toggle */}
              <button
                onClick={() => handleToggle(source)}
                disabled={toggling === source.id}
                className={cn(
                  "w-7 h-4 shrink-0 transition-colors relative",
                  source.active ? "bg-[#00ff88]" : "bg-[#333]"
                )}
                aria-label={source.active ? "Deactivate" : "Activate"}
              >
                <span
                  className={cn(
                    "absolute top-0.5 w-3 h-3 bg-black transition-transform",
                    source.active ? "translate-x-3.5" : "translate-x-0.5"
                  )}
                />
              </button>

              {/* Source info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  {/* Health dot */}
                  <span
                    className={cn("w-2 h-2 rounded-full shrink-0", healthDotColor(source))}
                    title={
                      (source.error_count ?? 0) === 0
                        ? "Healthy"
                        : `${source.error_count} consecutive error(s)`
                    }
                  />
                  <span className="text-[#e8e8e0] font-mono font-bold text-sm">
                    {source.name}
                  </span>
                  {source.category && (
                    <span className="font-mono text-[9px] uppercase tracking-wider text-[#00ff88] border-2 border-[#00ff8844] px-1.5 py-0">
                      {source.category}
                    </span>
                  )}
                  {source.language && (
                    <span className="font-mono text-[9px] uppercase tracking-wider text-[#777] border-2 border-[#333] px-1.5 py-0">
                      {source.language}
                    </span>
                  )}
                  {source.country && (
                    <span className="font-mono text-[9px] uppercase tracking-wider text-[#777] border-2 border-[#333] px-1.5 py-0">
                      {source.country}
                    </span>
                  )}
                  {source.fetch_error && (
                    <span className="flex items-center gap-1 text-[#ff3333] text-xs">
                      <AlertCircle className="w-3 h-3" />
                      <span className="font-mono text-[10px] font-bold">ERR</span>
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-3 mt-0.5">
                  <a
                    href={source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-mono text-[11px] text-[#555] hover:text-[#00ff88] transition-colors truncate"
                  >
                    {source.url}
                  </a>
                  <span className="font-mono text-[10px] text-[#444] shrink-0">
                    {relativeTime(source.last_fetched_at)}
                  </span>
                </div>
                {source.fetch_error && (
                  <p className="text-[#ff3333] font-mono text-[10px] mt-0.5 truncate opacity-70">
                    {source.fetch_error}
                  </p>
                )}
              </div>

              {/* Delete */}
              <button
                onClick={() => handleDelete(source.id)}
                disabled={deleting === source.id}
                className="text-[#333] hover:text-[#ff3333] transition-colors shrink-0"
                aria-label="Delete source"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
