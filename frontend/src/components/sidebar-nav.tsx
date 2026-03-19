"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import {
  Rss,
  Layers,
  BarChart2,
  Lightbulb,
  GitBranch,
  Database,
  Settings,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { label: "Feed", href: "/", icon: Rss },
  { label: "Events", href: "/events", icon: Layers },
  { label: "Analytics", href: "/analytics", icon: BarChart2 },
  { label: "Insights", href: "/insights", icon: Lightbulb },
  { label: "Pipeline", href: "/pipeline", icon: GitBranch },
  { label: "Sources", href: "/sources", icon: Database },
  { label: "Settings", href: "/settings", icon: Settings },
];

export function SidebarNav() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className={cn(
        "hidden md:flex flex-col h-screen sticky top-0 bg-[#0a0a0a] border-r-2 border-[#333] transition-all duration-200 shrink-0",
        collapsed ? "w-14" : "w-52"
      )}
    >
      {/* Logo */}
      <div
        className={cn(
          "flex items-center gap-2.5 px-4 py-5 border-b-2 border-[#333]",
          collapsed && "justify-center px-0"
        )}
      >
        <Rss className="w-5 h-5 text-[#00ff88] shrink-0" />
        {!collapsed && (
          <span className="text-sm font-bold uppercase tracking-wider text-[#e8e8e0] font-mono">
            RSSFeed2
          </span>
        )}
      </div>

      {/* Nav links */}
      <nav className="flex-1 px-2 py-4 space-y-0.5">
        {NAV_ITEMS.map(({ label, href, icon: Icon }) => {
          const active =
            href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 px-3 py-2 font-mono transition-colors relative",
                active
                  ? "text-[#00ff88] bg-[#00ff8810]"
                  : "text-[#555] hover:text-[#e8e8e0] hover:bg-[#111]",
                collapsed && "justify-center px-0"
              )}
              title={collapsed ? label : undefined}
            >
              {/* Active indicator bar */}
              {active && (
                <span className="absolute left-0 top-0 bottom-0 w-[3px] bg-[#00ff88]" />
              )}
              <Icon className="w-4 h-4 shrink-0" />
              {!collapsed && (
                <span className="text-[10px] uppercase tracking-widest">{label}</span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Collapse toggle */}
      <button
        onClick={() => setCollapsed((c) => !c)}
        className="flex items-center justify-center h-10 border-t-2 border-[#333] text-[#444] hover:text-[#00ff88] transition-colors"
        aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
      >
        {collapsed ? (
          <ChevronRight className="w-4 h-4" />
        ) : (
          <ChevronLeft className="w-4 h-4" />
        )}
      </button>
    </aside>
  );
}
