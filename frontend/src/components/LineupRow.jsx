import { useState } from "react";
import { getChampionImageUrl, STATIC_BASE } from "../lib/api";

export default function LineupRow({ pick }) {
  const [playerImgError, setPlayerImgError] = useState(false);

  return (
    <div className="flex items-center gap-3 py-1.5">
      {/* Champion icon */}
      <img
        src={getChampionImageUrl(pick.champion_name)}
        alt={pick.champion_name}
        title={pick.champion_name}
        className="w-9 h-9 rounded-lg border border-border object-cover bg-bg shrink-0"
        onError={(e) => { e.currentTarget.style.opacity = "0.2"; }}
      />

      {/* Player avatar */}
      {playerImgError ? (
        <div className="w-7 h-7 rounded-full border border-border bg-bg flex items-center justify-center shrink-0">
          <span className="text-[10px] font-display font-bold text-textMuted">
            {pick.ingame_name?.charAt(0)?.toUpperCase()}
          </span>
        </div>
      ) : (
        <img
          src={`${STATIC_BASE}/static/players/${encodeURIComponent(pick.ingame_name)}.png`}
          alt={pick.ingame_name}
          className="w-7 h-7 rounded-full border border-border object-cover bg-bg shrink-0"
          onError={() => setPlayerImgError(true)}
        />
      )}

      <div className="min-w-0 flex-1">
        <div className="text-sm text-text font-medium truncate">{pick.ingame_name}</div>
        <div className="text-xs text-textMuted truncate">{pick.champion_name}</div>
      </div>

      <span className="text-[10px] text-textMuted font-mono uppercase shrink-0 bg-bg border border-border px-1.5 py-0.5 rounded">
        {pick.position}
      </span>
    </div>
  );
}