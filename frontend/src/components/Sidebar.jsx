import { useState } from "react";
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard, TrendingUp, Brain, History,
  Users, Settings, Share2, MessageSquare,
} from "lucide-react";
import clsx from "clsx";

const NAV_ITEMS = [
  { to: "/", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/players", label: "Players", icon: Users },
  { to: "/matches", label: "Match History", icon: History },
  { to: "/meta-shifts", label: "Meta Shifts", icon: TrendingUp },
  { to: "/win-prediction", label: "Win Prediction", icon: Brain },
  { to: "/synergy", label: "Synergy Network", icon: Share2 },
  { to: "/agent", label: "Analytics Agent", icon: MessageSquare },
];

const ADMIN_ITEMS = [
  { to: "/admin", label: "Admin", icon: Settings },
];

function NavItem({ to, label, icon: Icon, end }) {
  const [showTooltip, setShowTooltip] = useState(false);

  return (
    <div
      className="relative"
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <NavLink
        to={to}
        end={end}
        className={({ isActive }) =>
          clsx(
            "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium",
            "transition-all duration-200",
            isActive
              ? "bg-accent/10 text-accent border-l-2 border-accent -ml-px pl-[11px]"
              : "text-textMuted hover:text-text hover:bg-surfaceHover"
          )
        }
      >
        <Icon size={16} strokeWidth={2} />
        {label}
      </NavLink>

      {/* Tooltip */}
      {showTooltip && (
        <div className="absolute left-full top-1/2 -translate-y-1/2 ml-2 z-50 pointer-events-none">
          <div className="bg-bg border border-border rounded-lg px-3 py-1.5 text-xs text-text whitespace-nowrap shadow-lg">
            {label}
          </div>
        </div>
      )}
    </div>
  );
}

export default function Sidebar() {
  return (
    <aside className="w-60 shrink-0 border-r border-border bg-surface flex flex-col">
      {/* Accent bar ở top */}
      <div className="h-1 bg-accent w-full" />

      {/* Logo */}
      <div className="px-5 py-6 border-b border-border">
        <div className="font-display font-bold text-lg tracking-wide text-text">
          T1
          <span className="text-accent relative">
            .
            {/* Pulse animation trên dấu chấm */}
            <span className="absolute inset-0 text-accent animate-pulse">.</span>
          </span>
          ANALYTICS
        </div>
        <div className="text-xs text-textMuted mt-1 font-mono">2020 — 2025</div>
      </div>

      {/* Main nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        {NAV_ITEMS.map((item) => (
          <NavItem key={item.to} {...item} />
        ))}
      </nav>

      {/* Divider + Admin */}
      <div className="px-3 pb-4 pt-3 space-y-0.5 border-t border-border">
        {/* Section label */}
        <div className="px-3 pb-1.5 text-[10px] uppercase tracking-widest text-textMuted/60">
          System
        </div>

        {ADMIN_ITEMS.map((item) => (
          <NavItem key={item.to} {...item} />
        ))}

        <div className="text-[11px] text-textMuted px-3 pt-3 leading-relaxed border-t border-border/50 mt-2">
          ML-powered match analytics.
          <br />
          903 games · 5 seasons.
        </div>
      </div>
    </aside>
  );
}