import { useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import {
  Activity, Brain, ChevronDown, History, LayoutDashboard,
  Menu, MessageSquare, Settings, Share2, TrendingUp, Users, X,
} from "lucide-react";
import clsx from "clsx";

const PRIMARY_LINKS = [
  { to: "/", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/players", label: "Players", icon: Users },
  { to: "/matches", label: "Matches", icon: History },
];

const ANALYTICS_LINKS = [
  { to: "/meta-shifts", label: "Meta Shifts", icon: TrendingUp },
  { to: "/win-prediction", label: "Win Prediction", icon: Brain },
  { to: "/synergy", label: "Synergy", icon: Share2 },
  { to: "/agent", label: "Analytics Agent", icon: MessageSquare },
];

function linkClass({ isActive }) {
  return clsx(
    "inline-flex items-center gap-2 whitespace-nowrap rounded-md px-3 py-2 text-sm font-semibold uppercase tracking-wide transition-colors",
    isActive
      ? "bg-accent/10 text-accent"
      : "text-textMuted hover:bg-surfaceHover hover:text-text"
  );
}

export default function Navbar() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [analyticsOpen, setAnalyticsOpen] = useState(false);
  const location = useLocation();
  const analyticsActive = ANALYTICS_LINKS.some((item) => item.to === location.pathname);

  return (
    <header className="sticky top-0 z-40 w-full border-b-2 border-accent bg-bg/95 backdrop-blur">
      <div className="mx-auto flex min-h-16 max-w-[1600px] items-center gap-5 px-4 sm:px-6 lg:px-8">
        <NavLink to="/" className="flex shrink-0 items-center gap-2" aria-label="T1 Analytics Overview">
          <span className="font-display text-xl font-bold tracking-tight text-text">
            T1<span className="text-accent">.</span>
          </span>
          <span className="hidden text-xs font-bold tracking-[0.18em] text-textMuted sm:inline">ANALYTICS</span>
        </NavLink>

        <nav className="hidden min-w-0 flex-1 items-center gap-1 lg:flex" aria-label="Main navigation">
          {PRIMARY_LINKS.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink key={item.to} to={item.to} end={item.end} className={linkClass}>
                <Icon size={15} />
                {item.label}
              </NavLink>
            );
          })}

          <div className="relative">
            <button
              type="button"
              onClick={() => setAnalyticsOpen((open) => !open)}
              onBlur={(event) => {
                if (!event.currentTarget.parentElement?.contains(event.relatedTarget)) {
                  setAnalyticsOpen(false);
                }
              }}
              className={clsx(
                "inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm font-semibold uppercase tracking-wide transition-colors",
                analyticsActive || analyticsOpen
                  ? "bg-accent/10 text-accent"
                  : "text-textMuted hover:bg-surfaceHover hover:text-text"
              )}
              aria-expanded={analyticsOpen}
            >
              <Activity size={15} /> Analytics <ChevronDown size={14} />
            </button>
            {analyticsOpen && (
              <div className="absolute left-0 top-full mt-2 min-w-52 rounded-lg border border-border bg-surface p-1 shadow-xl">
                {ANALYTICS_LINKS.map((item) => {
                  const Icon = item.icon;
                  return (
                    <NavLink key={item.to} to={item.to} onClick={() => setAnalyticsOpen(false)} className={linkClass}>
                      <Icon size={15} /> {item.label}
                    </NavLink>
                  );
                })}
              </div>
            )}
          </div>
        </nav>

        <NavLink to="/admin" className={({ isActive }) => clsx(linkClass({ isActive }), "ml-auto hidden lg:inline-flex")}>
          <Settings size={15} /> Admin
        </NavLink>

        <button
          type="button"
          className="ml-auto rounded-md p-2 text-textMuted hover:bg-surfaceHover hover:text-text lg:hidden"
          onClick={() => setMobileOpen((open) => !open)}
          aria-label={mobileOpen ? "Close navigation" : "Open navigation"}
          aria-expanded={mobileOpen}
        >
          {mobileOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>

      {mobileOpen && (
        <nav className="border-t border-border px-4 py-3 lg:hidden" aria-label="Mobile navigation">
          <div className="flex flex-col gap-1">
            {[...PRIMARY_LINKS, ...ANALYTICS_LINKS, { to: "/admin", label: "Admin", icon: Settings }].map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  onClick={() => setMobileOpen(false)}
                  className={linkClass}
                >
                  <Icon size={15} /> {item.label}
                </NavLink>
              );
            })}
          </div>
        </nav>
      )}
    </header>
  );
}
