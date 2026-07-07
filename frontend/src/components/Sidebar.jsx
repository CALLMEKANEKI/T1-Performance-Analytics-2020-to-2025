import { NavLink } from "react-router-dom";
import { LayoutDashboard, TrendingUp, Brain, History, Users, Settings, Network } from "lucide-react";
import clsx from "clsx";

const NAV_ITEMS = [
  { to: "/", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/players", label: "Players", icon: Users },
  { to: "/matches", label: "Match History", icon: History },
  { to: "/meta-shifts", label: "Meta Shifts", icon: TrendingUp },
  { to: "/win-prediction", label: "Win Prediction", icon: Brain },
  { to: "/synergy", label: "Synergy Network", icon: Network },
];

const ADMIN_ITEMS = [
  { to: "/admin", label: "Admin", icon: Settings },
];

export default function Sidebar() {
  return (
    <aside className="w-60 shrink-0 border-r border-border bg-surface flex flex-col">
      <div className="px-5 py-6 border-b border-border">
        <div className="font-display font-bold text-lg tracking-wide text-text">
          T1<span className="text-accent">.</span>ANALYTICS
        </div>
        <div className="text-xs text-textMuted mt-1 font-mono">2020 — 2025</div>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              clsx(
                "flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors",
                isActive
                  ? "bg-accent/10 text-accent border-l-2 border-accent -ml-px pl-[11px]"
                  : "text-textMuted hover:text-text hover:bg-surfaceHover"
              )
            }
          >
            <Icon size={16} strokeWidth={2} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="px-3 pb-4 border-t border-border pt-3 space-y-1">
        {ADMIN_ITEMS.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              clsx(
                "flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors",
                isActive
                  ? "bg-accent/10 text-accent border-l-2 border-accent -ml-px pl-[11px]"
                  : "text-textMuted hover:text-text hover:bg-surfaceHover"
              )
            }
          >
            <Icon size={16} strokeWidth={2} />
            {label}
          </NavLink>
        ))}
        <div className="text-[11px] text-textMuted px-3 pt-2 leading-relaxed">
          ML-powered match analytics.
          <br />
          903 games · 5 seasons.
        </div>
      </div>
    </aside>
  );
}