import { useEffect, useState } from "react";
import clsx from "clsx";
import { api } from "../lib/api";
import LineupRow from "./LineupRow";
import BansStrip from "./BansStrip";

export default function GameDetail({ gameId }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    setData(null);
    api.gameDetail(gameId).then(setData).catch((e) => setError(e.message));
  }, [gameId]);

  if (error) return (
    <div className="text-xs text-loss bg-loss/10 border border-loss/30 rounded-xl px-3 py-2">
      {error}
    </div>
  );
  if (!data) return (
    <div className="space-y-2 animate-pulse">
      <div className="skeleton h-4 w-24" />
      <div className="skeleton h-32 rounded-xl" />
    </div>
  );

  const t1Team = data.teams.find((t) => t.team_id === 1);
  const oppTeam = data.teams.find((t) => t.team_id !== 1);

  return (
    <div className="grid grid-cols-2 gap-4 py-3 px-1 animate-fade-in">
      {[t1Team, oppTeam].map((team) => (
        <div key={team.id_game_team} className="space-y-2.5">
          <div className="flex items-center justify-between">
            <span className="text-sm font-display font-semibold text-text">
              {team.team_name}
            </span>
            <span className={clsx(
              "text-[10px] font-mono uppercase px-2 py-0.5 rounded-full border",
              team.result === "WIN"
                ? "bg-win/10 text-win border-win/20"
                : "bg-loss/10 text-loss border-loss/20"
            )}>
              {team.side} · {team.result}
            </span>
          </div>

          <div className="bg-bg rounded-xl border border-border px-3 py-1.5 divide-y divide-border/40">
            {team.lineup.map((pick) => (
              <LineupRow key={pick.pick_order} pick={pick} />
            ))}
          </div>

          {team.bans.length > 0 && (
            <BansStrip bans={team.bans} label={`${team.team_name} bans`} />
          )}
        </div>
      ))}
    </div>
  );
}