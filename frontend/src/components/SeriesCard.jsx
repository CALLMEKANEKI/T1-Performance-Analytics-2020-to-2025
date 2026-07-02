import { useState } from "react";
import { ChevronDown, Youtube } from "lucide-react";
import clsx from "clsx";
import { api } from "../lib/api";
import GameDetail from "./GameDetail";

export default function SeriesCard({ series }) {
  const [expanded, setExpanded] = useState(false);
  const [games, setGames] = useState(null);
  const [activeGameId, setActiveGameId] = useState(null);

  const handleToggle = async () => {
    const next = !expanded;
    setExpanded(next);
    if (next && !games) {
      const detail = await api.seriesDetail(series.id_series);
      setGames(detail.games);
      if (detail.games.length > 0) setActiveGameId(detail.games[0].id_game);
    }
  };

  const score = `${series.t1_wins}–${series.t1_losses}`;
  const won = series.t1_wins > series.t1_losses;

  return (
    <div className="bg-surface border border-border rounded-lg overflow-hidden">
      <button
        onClick={handleToggle}
        className="w-full flex items-center gap-4 px-5 py-4 text-left hover:bg-surfaceHover transition-colors"
      >
        <div
          className={clsx(
            "font-mono text-sm font-semibold w-12 text-center py-1 rounded",
            won ? "bg-win/10 text-win" : "bg-loss/10 text-loss"
          )}
        >
          {score}
        </div>

        <div className="flex-1 min-w-0">
          <div className="text-sm text-text font-medium truncate">
            T1 vs {series.opponent_name}
          </div>
          <div className="text-xs text-textMuted mt-0.5 truncate">
            {series.tournament_name}
          </div>
        </div>

        <div className="text-xs text-textMuted font-mono shrink-0">{series.match_date}</div>

        <ChevronDown
          size={16}
          className={clsx(
            "text-textMuted transition-transform shrink-0",
            expanded && "rotate-180"
          )}
        />
      </button>

      {expanded && (
        <div className="border-t border-border px-5 pb-4">
          {!games ? (
            <div className="text-xs text-textMuted py-4">Đang tải...</div>
          ) : (
            <>
              <div className="flex gap-2 pt-3 pb-1 flex-wrap">
                {games.map((g) => (
                  <button
                    key={g.id_game}
                    onClick={() => setActiveGameId(g.id_game)}
                    className={clsx(
                      "px-3 py-1.5 rounded-md text-xs font-mono transition-colors flex items-center gap-1.5",
                      activeGameId === g.id_game
                        ? "bg-accent text-white"
                        : "bg-bg text-textMuted hover:text-text"
                    )}
                  >
                    Game {g.game_number}
                    <span
                      className={clsx(
                        "w-1.5 h-1.5 rounded-full",
                        g.t1_result === "WIN" ? "bg-win" : "bg-loss"
                      )}
                    />
                  </button>
                ))}
                {games.find((g) => g.id_game === activeGameId)?.link && (
                  <a
                    href={games.find((g) => g.id_game === activeGameId).link}
                    target="_blank"
                    rel="noreferrer"
                    className="px-3 py-1.5 rounded-md text-xs text-textMuted hover:text-accent transition-colors flex items-center gap-1.5 ml-auto"
                  >
                    <Youtube size={14} /> VOD
                  </a>
                )}
              </div>

              {activeGameId && <GameDetail gameId={activeGameId} />}
            </>
          )}
        </div>
      )}
    </div>
  );
}
