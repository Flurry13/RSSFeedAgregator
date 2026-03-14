"use client";

import { useEffect, useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Loading } from "@/components/loading";
import { api, type Source } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Trash2, AlertCircle, Plus, X } from "lucide-react";

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
    <div className="max-w-3xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold text-zinc-100">Sources</h1>
        <Button
          size="sm"
          onClick={() => setShowForm((v) => !v)}
          className="bg-zinc-800 text-zinc-200 hover:bg-zinc-700 border border-zinc-700"
        >
          {showForm ? (
            <>
              <X className="w-3.5 h-3.5 mr-1.5" />
              Cancel
            </>
          ) : (
            <>
              <Plus className="w-3.5 h-3.5 mr-1.5" />
              Add source
            </>
          )}
        </Button>
      </div>

      {/* Add form */}
      {showForm && (
        <form
          onSubmit={handleAdd}
          className="bg-zinc-900 border border-zinc-800 rounded-lg p-5 mb-6 space-y-3"
        >
          <p className="text-zinc-400 text-sm font-medium mb-2">New source</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Input
              placeholder="Name *"
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
              className="bg-zinc-800 border-zinc-700 text-zinc-100 placeholder:text-zinc-600"
            />
            <Input
              placeholder="Feed URL *"
              value={formUrl}
              onChange={(e) => setFormUrl(e.target.value)}
              className="bg-zinc-800 border-zinc-700 text-zinc-100 placeholder:text-zinc-600"
            />
            <Input
              placeholder="Language (e.g. en)"
              value={formLanguage}
              onChange={(e) => setFormLanguage(e.target.value)}
              className="bg-zinc-800 border-zinc-700 text-zinc-100 placeholder:text-zinc-600"
            />
            <Input
              placeholder="Country (e.g. US)"
              value={formCountry}
              onChange={(e) => setFormCountry(e.target.value)}
              className="bg-zinc-800 border-zinc-700 text-zinc-100 placeholder:text-zinc-600"
            />
          </div>
          {formError && (
            <p className="text-red-400 text-xs">{formError}</p>
          )}
          <Button
            type="submit"
            disabled={submitting}
            className="bg-zinc-700 text-zinc-100 hover:bg-zinc-600"
          >
            {submitting ? "Adding…" : "Add source"}
          </Button>
        </form>
      )}

      {loading ? (
        <Loading message="Loading sources…" />
      ) : sources.length === 0 ? (
        <p className="text-zinc-500 text-sm text-center py-12">
          No sources yet. Add one above.
        </p>
      ) : (
        <div className="space-y-3">
          {sources.map((source) => (
            <div
              key={source.id}
              className={cn(
                "bg-zinc-900 border rounded-lg p-4 flex items-start gap-4",
                source.error
                  ? "border-red-900/50"
                  : "border-zinc-800"
              )}
            >
              {/* Active toggle */}
              <button
                onClick={() => handleToggle(source)}
                disabled={toggling === source.id}
                className={cn(
                  "mt-0.5 w-8 h-5 rounded-full shrink-0 transition-colors relative",
                  source.active ? "bg-emerald-600" : "bg-zinc-700"
                )}
                aria-label={source.active ? "Deactivate" : "Activate"}
              >
                <span
                  className={cn(
                    "absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform",
                    source.active ? "translate-x-3.5" : "translate-x-0.5"
                  )}
                />
              </button>

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-zinc-100 font-medium text-sm">
                    {source.name}
                  </span>
                  {source.language && (
                    <Badge
                      variant="outline"
                      className="border-zinc-700 text-zinc-500 text-xs uppercase py-0"
                    >
                      {source.language}
                    </Badge>
                  )}
                  {source.country && (
                    <Badge
                      variant="outline"
                      className="border-zinc-700 text-zinc-500 text-xs uppercase py-0"
                    >
                      {source.country}
                    </Badge>
                  )}
                  {source.error && (
                    <span className="flex items-center gap-1 text-red-400 text-xs">
                      <AlertCircle className="w-3 h-3" />
                      Error
                    </span>
                  )}
                </div>
                <a
                  href={source.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-zinc-600 text-xs hover:text-zinc-400 transition-colors truncate block mt-0.5"
                >
                  {source.url}
                </a>
                {source.error && (
                  <p className="text-red-400/70 text-xs mt-1 truncate">
                    {source.error}
                  </p>
                )}
              </div>

              <button
                onClick={() => handleDelete(source.id)}
                disabled={deleting === source.id}
                className="text-zinc-700 hover:text-red-400 transition-colors shrink-0"
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
