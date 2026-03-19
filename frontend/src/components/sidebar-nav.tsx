"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import {
  Rss,
  Layers,
  BarChart2,
  Lightbulb,
  TrendingUp,
  GitBranch,
  Settings,
  ChevronLeft,
  ChevronRight,
  Menu,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { label: "Feed", href: "/", icon: Rss },
  { label: "Events", href: "/events", icon: Layers },
  { label: "Analytics", href: "/analytics", icon: BarChart2 },
  { label: "Insights", href: "/insights", icon: Lightbulb },
  { label: "Predictions", href: "/predictions", icon: TrendingUp },
  { label: "Pipeline", href: "/pipeline", icon: GitBranch },
  { label: "Settings", href: "/settings", icon: Settings },
];

export function SidebarNav() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  const navLinks = (onNavClick?: () => void) =>
    NAV_ITEMS.map(({ label, href, icon: Icon }) => {
      const active =
        href === "/" ? pathname === "/" : pathname.startsWith(href);
      return (
        <Link
          key={href}
          href={href}
          onClick={onNavClick}
          className={cn(
            "flex items-center gap-3 px-3 py-[7px] rounded-md text-[13px] transition-colors",
            active
              ? "text-[#0a84ff] bg-[rgba(10,132,255,0.15)]"
              : "text-[#98989d] hover:text-[#e5e5e7] hover:bg-[rgba(255,255,255,0.05)]",
            collapsed && "lg:justify-center lg:px-0"
          )}
          title={collapsed ? label : undefined}
        >
          <Icon className="w-4 h-4 shrink-0" />
          {!collapsed && <span>{label}</span>}
        </Link>
      );
    });

  return (
    <>
      {/* Mobile hamburger button */}
      <button
        onClick={() => setMobileOpen(true)}
        className="lg:hidden fixed top-3 left-3 z-50 inline-flex items-center justify-center w-10 h-10 rounded-lg bg-[#2c2c2e] border border-[#3a3a3c] text-[#98989d] hover:text-[#e5e5e7] hover:bg-[#3a3a3c] transition-colors"
        aria-label="Open navigation"
      >
        <Menu className="w-5 h-5" />
      </button>

      {/* Mobile slide-in sidebar */}
      {mobileOpen && (
        <div className="lg:hidden fixed inset-0 z-50">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/50"
            onClick={() => setMobileOpen(false)}
          />
          {/* Panel */}
          <aside className="absolute inset-y-0 left-0 w-64 bg-[#1c1c1e] border-r border-[#3a3a3c] flex flex-col animate-slide-in-left">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-5 border-b border-[#3a3a3c]">
              <div className="flex items-center gap-2.5">
                <Rss className="w-4 h-4 text-[#0a84ff] shrink-0" />
                <span className="text-[15px] font-semibold text-[#e5e5e7]">
                  RSSFeed2
                </span>
              </div>
              <button
                onClick={() => setMobileOpen(false)}
                className="text-[#636366] hover:text-[#e5e5e7] transition-colors"
                aria-label="Close navigation"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            {/* Nav links */}
            <nav className="flex-1 px-2 py-4 space-y-0.5 overflow-y-auto">
              {navLinks(() => setMobileOpen(false))}
            </nav>
          </aside>
        </div>
      )}

      {/* Desktop sidebar */}
      <aside
        className={cn(
          "hidden lg:flex flex-col h-screen sticky top-0 bg-[#1c1c1e] border-r border-[#3a3a3c] transition-all duration-200 shrink-0",
          collapsed ? "w-14" : "w-52"
        )}
      >
        {/* Logo */}
        <div
          className={cn(
            "flex items-center gap-2.5 px-4 py-5 border-b border-[#3a3a3c]",
            collapsed && "justify-center px-0"
          )}
        >
          <Rss className="w-4 h-4 text-[#0a84ff] shrink-0" />
          {!collapsed && (
            <span className="text-[15px] font-semibold text-[#e5e5e7]">
              RSSFeed2
            </span>
          )}
        </div>

        {/* Nav links */}
        <nav className="flex-1 px-2 py-4 space-y-0.5">
          {navLinks()}
        </nav>

        {/* Collapse toggle */}
        <button
          onClick={() => setCollapsed((c) => !c)}
          className="flex items-center justify-center h-10 border-t border-[#3a3a3c] text-[#636366] hover:text-[#e5e5e7] transition-colors"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? (
            <ChevronRight className="w-4 h-4" />
          ) : (
            <ChevronLeft className="w-4 h-4" />
          )}
        </button>
      </aside>
    </>
  );
}
