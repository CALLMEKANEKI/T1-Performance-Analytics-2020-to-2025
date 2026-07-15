import { getChampionImageUrl, STATIC_BASE } from "../lib/api";

export default function LineupRow({ pick }) {
  return (
    <div className="flex items-center gap-3 py-1.5">
      <div className="relative shrink-0">
        <img
          src={getChampionImageUrl(pick.champion_name)}
          alt={pick.champion_name}
          className="w-9 h-9 rounded-md border border-border object-cover bg-bg"
          onError={(e) => {
            e.currentTarget.style.visibility = "hidden";
          }}
        />
      </div>
      <img
        src={`${STATIC_BASE}/static/players/${encodeURIComponent(pick.ingame_name)}.png`}
        alt={pick.ingame_name}
        className="w-7 h-7 rounded-full border border-border object-cover bg-bg shrink-0"
        onError={(e) => {
          e.currentTarget.style.visibility = "hidden";
        }}
      />
      <div className="min-w-0 flex-1">
        <div className="text-sm text-text font-medium truncate">{pick.ingame_name}</div>
        <div className="text-xs text-textMuted truncate">{pick.champion_name}</div>
      </div>
      <span className="text-[10px] text-textMuted font-mono uppercase shrink-0">
        {pick.position}
      </span>
    </div>
  );
}
