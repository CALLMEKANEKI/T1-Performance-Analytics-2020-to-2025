import { useEffect, useRef, useState } from "react";
import clsx from "clsx";

// Animated counter hook
function useCountUp(target, duration = 1000) {
  const [current, setCurrent] = useState(0);
  const rafRef = useRef(null);

  useEffect(() => {
    const num = parseFloat(String(target).replace(/[^0-9.]/g, ""));
    if (isNaN(num)) return;

    // Detect số thập phân
    const decimals = String(target).includes(".") 
      ? (String(target).split(".")[1]?.length ?? 0) 
      : 0;

    const start = performance.now();
    const animate = (now) => {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const val = eased * num;
      // Giữ decimal places thay vì floor
      setCurrent(parseFloat(val.toFixed(decimals)));
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
  // Giữ nguyên decimal places của original
  const decimals = str.includes(".") ? str.split(".")[1]?.length ?? 0 : 0;
  return current.toFixed(decimals);
}

export default function StatCard({
  label,
  value,
  sublabel,
  accent = false,
  trend = null, // { value: number, label: string } — dương = xanh, âm = đỏ
}) {
  const animated = useCountUp(value);
  const isNumeric = !isNaN(parseFloat(String(value).replace(/[^0-9.]/g, "")));
  const displayValue = isNumeric ? formatValue(value, animated) : value;

  return (
    <div
      className={clsx(
        "bg-surface border border-border rounded-xl px-5 py-4",
        "transition-all duration-200 hover:border-border/80",
        "group relative overflow-hidden",
      )}
    >
      {/* Shimmer on hover */}
      <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 animate-shimmer pointer-events-none" />

      <div className="text-xs uppercase tracking-widest text-textMuted font-medium mb-2">
        {label}
      </div>

      <div className="flex items-end gap-2">
        <div
          className={clsx(
            "font-display font-bold text-3xl tabular-nums",
            accent ? "text-accent" : "text-text"
          )}
        >
          {displayValue}
        </div>

        {/* Trend badge */}
        {trend && (
          <span
            className={clsx(
              "text-xs font-mono px-1.5 py-0.5 rounded-full mb-1",
              trend.value >= 0
                ? "bg-win/10 text-win"
                : "bg-loss/10 text-loss"
            )}
          >
            {trend.value >= 0 ? "▲" : "▼"} {Math.abs(trend.value)}
            {trend.label && ` ${trend.label}`}
          </span>
        )}
      </div>

      {sublabel && <div className="text-xs text-textMuted mt-1">{sublabel}</div>}
    </div>
  );
}
