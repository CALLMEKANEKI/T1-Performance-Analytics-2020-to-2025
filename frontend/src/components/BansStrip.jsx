import { getChampionImageUrl } from "../lib/api";

export default function BansStrip({ bans, label }) {
  return (
    <div>
      <div className="text-[10px] text-textMuted uppercase tracking-wider font-medium mb-1.5">
        {label}
      </div>
      <div className="flex gap-1.5 flex-wrap">
        {bans.map((b) => (
          <div key={b.ban_order} className="relative group" title={b.champion_name}>
            <img
              src={getChampionImageUrl(b.champion_name)}
              alt={b.champion_name}
              className="w-7 h-7 rounded-lg border border-border object-cover bg-bg opacity-40 grayscale"
              onError={(e) => { e.currentTarget.style.visibility = "hidden"; }}
            />
            {/* X overlay */}
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <div className="w-[90%] h-px bg-loss rotate-45 absolute" />
              <div className="w-[90%] h-px bg-loss -rotate-45 absolute" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}