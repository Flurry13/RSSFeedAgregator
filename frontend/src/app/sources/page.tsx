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
  if (!source.active) return "bg-[#636366]";
  if (count >= 3) return "bg-[#ff453a]";
  if (count >= 1) return "bg-[#ff9f0a]";
  return "bg-[#30d158]";
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
          <h1 className="text-2xl font-bold text-[#e5e5e7]">
            Sources
          </h1>
          <span className="text-[11px] text-[#636366] uppercase tracking-wide">
            {sources.length} Feeds
          </span>
        </div>
        <button
          onClick={() => setShowForm((v) => !v)}
          className={cn(
            "text-sm font-medium px-4 py-2 rounded-lg transition-colors",
            showForm
              ? "bg-transparent text-[#e5e5e7] border border-[#48484a] hover:border-[#636366]"
              : "bg-[#0a84ff] text-white hover:bg-[#0a84ff]/90"
          )}
        >
          {showForm ? (
            <span className="flex items-center gap-1.5">
              <X className="w-3.5 h-3.5" />
              Cancel
            </span>
          ) : (
            <span className="flex items-center gap-1.5">
              <Plus className="w-3.5 h-3.5" />
              Add
            </span>
          )}
        </button>
      </div>

      {/* Add form */}
      {showForm && (
        <form
          onSubmit={handleAdd}
          className="animate-fade-in-up border border-[#3a3a3c] bg-[#2c2c2e] rounded-[10px] p-5 mb-6 space-y-4"
        >
          <p className="text-[11px] uppercase tracking-wide text-[#636366]">
            New source
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Input
              placeholder="Name *"
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
              className="bg-[#1c1c1e] border border-[#48484a] text-[#e5e5e7] placeholder:text-[#636366] text-sm rounded-lg focus:border-[#0a84ff]"
            />
            <Input
              placeholder="Feed URL *"
              value={formUrl}
              onChange={(e) => setFormUrl(e.target.value)}
              className="bg-[#1c1c1e] border border-[#48484a] text-[#e5e5e7] placeholder:text-[#636366] text-sm rounded-lg focus:border-[#0a84ff]"
            />
            <Input
              placeholder="Language (e.g. en)"
              value={formLanguage}
              onChange={(e) => setFormLanguage(e.target.value)}
              className="bg-[#1c1c1e] border border-[#48484a] text-[#e5e5e7] placeholder:text-[#636366] text-sm rounded-lg focus:border-[#0a84ff]"
            />
            <Input
              placeholder="Country (e.g. US)"
              value={formCountry}
              onChange={(e) => setFormCountry(e.target.value)}
              className="bg-[#1c1c1e] border border-[#48484a] text-[#e5e5e7] placeholder:text-[#636366] text-sm rounded-lg focus:border-[#0a84ff]"
            />
          </div>
          {formError && (
            <p className="text-[#ff453a] text-xs">{formError}</p>
          )}
          <button
            type="submit"
            disabled={submitting}
            className="bg-[#0a84ff] text-white text-sm font-medium px-4 py-2 rounded-lg hover:bg-[#0a84ff]/90 disabled:opacity-50 transition-colors"
          >
            {submitting ? "Adding..." : "Add source"}
          </button>
        </form>
      )}

      {loading ? (
        <Loading message="Loading sources..." />
      ) : sources.length === 0 ? (
        <p className="text-[#636366] text-sm text-center py-12">
          No sources yet. Add one above.
        </p>
      ) : (
        <div className="space-y-3">
          {sources.map((source, i) => (
            <div
              key={source.id}
              className={cn(
                "animate-fade-in-up flex items-center gap-4 bg-[#2c2c2e] border border-[#3a3a3c] rounded-[10px] p-4 hover:border-[#48484a] transition-colors",
                source.fetch_error && "border-[#ff453a]/20"
              )}
              style={{ animationDelay: `${i * 30}ms` }}
            >
              {/* Active toggle */}
              <button
                onClick={() => handleToggle(source)}
                disabled={toggling === source.id}
                className={cn(
                  "w-7 h-4 shrink-0 rounded-full transition-colors relative",
                  source.active ? "bg-[#30d158]" : "bg-[#3a3a3c]"
                )}
                aria-label={source.active ? "Deactivate" : "Activate"}
              >
                <span
                  className={cn(
                    "absolute top-0.5 w-3 h-3 rounded-full bg-white transition-transform",
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
                  <span className="text-[15px] font-medium text-[#e5e5e7]">
                    {source.name}
                  </span>
                  {source.category && (
                    <span className="text-[11px] text-[#0a84ff] bg-[#0a84ff]/10 rounded-md px-2 py-0.5">
                      {source.category}
                    </span>
                  )}
                  {source.language && (
                    <span className="text-[11px] text-[#98989d] bg-[#3a3a3c] rounded-md px-2 py-0.5">
                      {source.language}
                    </span>
                  )}
                  {source.country && (
                    <span className="text-[11px] text-[#98989d] bg-[#3a3a3c] rounded-md px-2 py-0.5">
                      {source.country}
                    </span>
                  )}
                  {source.fetch_error && (
                    <span className="flex items-center gap-1 text-[#ff453a] text-xs">
                      <AlertCircle className="w-3 h-3" />
                      <span className="text-[10px] font-medium">ERR</span>
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-3 mt-0.5">
                  <a
                    href={source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[12px] text-[#98989d] hover:text-[#0a84ff] transition-colors truncate"
                  >
                    {source.url}
                  </a>
                  <span className="text-[12px] text-[#636366] shrink-0">
                    {relativeTime(source.last_fetched_at)}
                  </span>
                </div>
                {source.fetch_error && (
                  <p className="text-[#ff453a] text-[10px] mt-0.5 truncate opacity-70">
                    {source.fetch_error}
                  </p>
                )}
              </div>

              {/* Delete */}
              <button
                onClick={() => handleDelete(source.id)}
                disabled={deleting === source.id}
                className="text-[#636366] hover:text-[#ff453a] transition-colors shrink-0"
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
