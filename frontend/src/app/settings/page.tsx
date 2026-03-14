"use client";

import { useEffect, useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Check } from "lucide-react";

interface Settings {
  theme: "dark" | "light";
  refreshInterval: number;
  pageSize: number;
}

const DEFAULTS: Settings = {
  theme: "dark",
  refreshInterval: 60,
  pageSize: 20,
};

const STORAGE_KEY = "rssfeed2_settings";

function loadSettings(): Settings {
  if (typeof window === "undefined") return DEFAULTS;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULTS;
    return { ...DEFAULTS, ...JSON.parse(raw) };
  } catch {
    return DEFAULTS;
  }
}

function saveSettings(s: Settings) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(s));
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings>(DEFAULTS);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setSettings(loadSettings());
  }, []);

  const handleSave = () => {
    saveSettings(settings);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const set = <K extends keyof Settings>(key: K, value: Settings[K]) =>
    setSettings((prev) => ({ ...prev, [key]: value }));

  return (
    <div className="max-w-xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-semibold text-zinc-100 mb-8">Settings</h1>

      <div className="bg-zinc-900 border border-zinc-800 rounded-lg divide-y divide-zinc-800">
        {/* Theme */}
        <div className="flex items-center justify-between px-5 py-4">
          <div>
            <p className="text-zinc-200 text-sm font-medium">Theme</p>
            <p className="text-zinc-500 text-xs mt-0.5">
              Select your preferred color scheme
            </p>
          </div>
          <Select
            value={settings.theme}
            onValueChange={(v) => v && set("theme", v as Settings["theme"])}
          >
            <SelectTrigger className="w-32 bg-zinc-800 border-zinc-700 text-zinc-300">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-zinc-900 border-zinc-800">
              <SelectItem value="dark" className="text-zinc-300 focus:bg-zinc-800">
                Dark
              </SelectItem>
              <SelectItem value="light" className="text-zinc-300 focus:bg-zinc-800">
                Light
              </SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Refresh interval */}
        <div className="flex items-center justify-between px-5 py-4">
          <div>
            <p className="text-zinc-200 text-sm font-medium">Refresh interval</p>
            <p className="text-zinc-500 text-xs mt-0.5">
              Auto-refresh feed every N seconds (0 = off)
            </p>
          </div>
          <Input
            type="number"
            min={0}
            max={3600}
            step={10}
            value={settings.refreshInterval}
            onChange={(e) =>
              set("refreshInterval", Math.max(0, Number(e.target.value)))
            }
            className="w-24 text-right bg-zinc-800 border-zinc-700 text-zinc-200"
          />
        </div>

        {/* Page size */}
        <div className="flex items-center justify-between px-5 py-4">
          <div>
            <p className="text-zinc-200 text-sm font-medium">Page size</p>
            <p className="text-zinc-500 text-xs mt-0.5">
              Number of headlines to load per page
            </p>
          </div>
          <Input
            type="number"
            min={5}
            max={100}
            step={5}
            value={settings.pageSize}
            onChange={(e) =>
              set("pageSize", Math.max(5, Number(e.target.value)))
            }
            className="w-24 text-right bg-zinc-800 border-zinc-700 text-zinc-200"
          />
        </div>
      </div>

      <div className="flex justify-end mt-6">
        <Button
          onClick={handleSave}
          className={
            saved
              ? "bg-emerald-700 text-white hover:bg-emerald-600"
              : "bg-zinc-700 text-zinc-100 hover:bg-zinc-600"
          }
        >
          {saved ? (
            <>
              <Check className="w-4 h-4 mr-1.5" />
              Saved
            </>
          ) : (
            "Save settings"
          )}
        </Button>
      </div>

      <Separator className="bg-zinc-800 my-8" />

      <div className="space-y-2">
        <p className="text-zinc-500 text-xs uppercase tracking-wider">About</p>
        <p className="text-zinc-400 text-sm">RSSFeed2 — NLP-powered RSS aggregator</p>
        <p className="text-zinc-600 text-xs">
          Settings are stored in browser localStorage.
        </p>
      </div>
    </div>
  );
}
