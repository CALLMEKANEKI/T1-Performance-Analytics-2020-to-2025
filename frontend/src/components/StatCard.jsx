import clsx from "clsx";

export default function StatCard({ label, value, sublabel, accent = false }) {
  return (
    <div className="bg-surface border border-border rounded-lg px-5 py-4">
      <div className="text-xs text-textMuted uppercase tracking-wider font-medium mb-2">
        {label}
      </div>
      <div
        className={clsx(
          "font-display font-bold text-3xl tabular-nums",
          accent ? "text-accent" : "text-text"
        )}
      >
        {value}
      </div>
      {sublabel && <div className="text-xs text-textMuted mt-1">{sublabel}</div>}
    </div>
  );
}
