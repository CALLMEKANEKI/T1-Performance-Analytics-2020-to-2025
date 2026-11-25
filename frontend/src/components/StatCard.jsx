import { useEffect, useRef, useState } from "react";
import clsx from "clsx";

function useCountUp(target, duration = 1000) {
  const [current, setCurrent] = useState(0);
  const rafRef = useRef(null);

  useEffect(() => {
    const num = parseFloat(String(target).replace(/[^0-9.]/g, ""));
    if (!Number.isFinite(num)) return undefined;

    const decimals = String(target).includes(".")
      ? (String(target).split(".")[1]?.length ?? 0)
      : 0;
    const start = performance.now();

    const animate = (now) => {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setCurrent(Number((eased * num).toFixed(decimals)));
      if (progress < 1) rafRef.current = requestAnimationFrame(animate);
    };

    rafRef.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(rafRef.current);
  }, [target, duration]);

  return current;
}

function formatValue(original, current) {
  const str = String(original);
  if (str.includes("%")) return `${current}%`;
  if (str.includes(",")) return current.toLocaleString();
  const decimals = str.includes(".") ? (str.split(".")[1]?.length ?? 0) : 0;
  return current.toFixed(decimals);
}

export default function StatCard({ label, value, sublabel, accent = false, trend = null }) {
  const animated = useCountUp(value);
  const numericValue = parseFloat(String(value).replace(/[^0-9.]/g, ""));
  const isNumeric = Number.isFinite(numericValue);
  const displayValue = isNumeric ? formatValue(value, animated) : value;

  return (
    <article className="group relative overflow-hidden rounded-xl border border-border bg-surface px-5 py-4 transition-all duration-200 hover:-translate-y-0.5 hover:border-border/90">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-accent/60 to-transparent opacity-0 transition-opacity group-hover:opacity-100" />
      <div className="mb-2 text-xs font-medium uppercase tracking-widest text-textMuted">{label}</div>
      <div className="flex items-end gap-2">
        <div className={clsx("font-display text-3xl font-bold tabular-nums", accent ? "text-accent" : "text-text")}>
          {displayValue}
        </div>
        {trend && (
          <span className={clsx(
            "mb-1 inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-mono font-semibold",
            trend.value >= 0 ? "bg-win/10 text-win" : "bg-loss/10 text-loss"
          )}>
            <span aria-hidden="true">{trend.value >= 0 ? "▲" : "▼"}</span>
            {Math.abs(trend.value)}{trend.label ? ` ${trend.label}` : ""}
          </span>
        )}
      </div>
      {sublabel && <div className="mt-1 text-xs text-textMuted">{sublabel}</div>}
    </article>
  );
}
