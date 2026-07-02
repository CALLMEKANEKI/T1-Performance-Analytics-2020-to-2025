import { STATIC_BASE } from "../lib/api";

export default function BansStrip({ bans, label }) {
  return (
    <div>
      <div className="text-[10px] text-textMuted uppercase tracking-wider font-medium mb-1.5">
        {label}
      </div>
      <div className="flex gap-1.5">
        {bans.map((b) => (
          <div key={b.ban_order} className="relative">
            <img
              src={`${STATIC_BASE}/static/champions/${encodeURIComponent(b.champion_name)}.png`}
              alt={b.champion_name}
              title={b.champion_name}
              className="w-7 h-7 rounded border border-border object-cover bg-bg opacity-50"
              onError={(e) => {
                e.currentTarget.style.visibility = "hidden";
              }}
            />
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-full h-px bg-loss rotate-45 absolute" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
