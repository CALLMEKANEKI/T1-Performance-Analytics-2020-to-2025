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

  if (error) return <div className="text-xs text-loss py-3">{error}</div>;
  if (!data) return <div className="text-xs text-textMuted py-3">Đang tải...</div>;

  const t1Team = data.teams.find((t) => t.team_id === 1);
  const oppTeam = data.teams.find((t) => t.team_id !== 1);

  return (
    <div className="grid grid-cols-2 gap-4 py-4 px-1">
      {[t1Team, oppTeam].map((team) => (
        <div key={team.id_game_team} className="space-y-2">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-display font-semibold text-text">
              {team.team_name}
            </span>
            <span
              className={clsx(
                "text-[10px] font-mono uppercase px-1.5 py-0.5 rounded",
                team.result === "WIN"
                  ? "bg-win/10 text-win"
                  : "bg-loss/10 text-loss"
              )}
            >
              {team.side} · {team.result}
            </span>
          </div>

          <div className="bg-bg rounded-md border border-border px-3 py-2 divide-y divide-border/50">
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
