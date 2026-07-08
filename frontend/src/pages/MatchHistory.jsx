import { useEffect, useState, useCallback } from "react";
import { ChevronLeft, ChevronRight, ChevronDown, Trophy, Youtube } from "lucide-react";
import clsx from "clsx";
import { api } from "../lib/api";
import GameDetail from "../components/GameDetail";

const PAGE_SIZE = 10;

// ── Helpers ──────────────────────────────────────────────────────────────────

function fmt(dateStr) {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" });
}

function WinBadge({ wins, total }) {
  const losses = total - wins;
  const pct = total ? ((wins / total) * 100).toFixed(0) : 0;
  const won = wins > losses;
  return (
    <span className={clsx(
      "font-mono text-xs px-2 py-0.5 rounded shrink-0",
      won ? "bg-win/10 text-win" : "bg-loss/10 text-loss"
    )}>
      {wins}W {losses}L · {pct}%
    </span>
  );
}

// ── Game tab row inside a series ──────────────────────────────────────────────

function SeriesExpanded({ seriesId }) {
  const [games, setGames] = useState(null);
  const [activeGameId, setActiveGameId] = useState(null);

  useEffect(() => {
    api.seriesDetail(seriesId).then((d) => {
      setGames(d.games ?? []);
      if (d.games?.length) setActiveGameId(d.games[0].id_game);
    });
  }, [seriesId]);

  if (!games) return <div className="text-xs text-textMuted py-3 px-4">Đang tải...</div>;

  return (
    <div className="px-4 pb-4 pt-2 border-t border-border/50 bg-bg/30">
      <div className="flex gap-2 mb-3 flex-wrap">
        {games.map((g) => (
          <button
            key={g.id_game}
            onClick={() => setActiveGameId(g.id_game)}
            className={clsx(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono transition-colors",
              activeGameId === g.id_game
                ? "bg-accent text-text"
                : "bg-surface text-textMuted hover:text-text border border-border"
            )}
          >
            Game {g.game_number}
            <span className={clsx(
              "w-1.5 h-1.5 rounded-full",
              g.t1_result === "WIN" ? "bg-win" : "bg-loss"
            )} />
          </button>
        ))}
        {(() => {
          const link = games.find((g) => g.id_game === activeGameId)?.link;
          return link ? (
            <a
              href={link}
              target="_blank"
              rel="noreferrer"
              className="ml-auto flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-textMuted hover:text-accent transition-colors"
            >
              <Youtube size={13} /> VOD
            </a>
          ) : null;
        })()}
      </div>
      {activeGameId && <GameDetail gameId={activeGameId} />}
    </div>
  );
}

// ── Series row ────────────────────────────────────────────────────────────────

function SeriesRow({ series }) {
  const [open, setOpen] = useState(false);
  const wins = series.t1_wins ?? 0;
  const total = series.total_games ?? 0;

  return (
    <div className="border border-border rounded-lg overflow-hidden bg-surface">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-surfaceHover transition-colors"
      >
        <WinBadge wins={wins} total={total} />
        <div className="flex-1 min-w-0">
          <span className="text-sm text-text font-medium truncate block">
            T1 vs {series.opponent_name}
          </span>
        </div>
        <span className="text-xs text-textMuted font-mono shrink-0">{fmt(series.match_date)}</span>
        <ChevronDown size={14} className={clsx("text-textMuted transition-transform shrink-0", open && "rotate-180")} />
      </button>
      {open && <SeriesExpanded seriesId={series.id_series} />}
    </div>
  );
}

// ── Tournament card ───────────────────────────────────────────────────────────

function TournamentCard({ tournament }) {
  const [open, setOpen] = useState(false);
  const [series, setSeries] = useState(null);

  const handleToggle = async () => {
    const next = !open;
    setOpen(next);
    if (next && !series) {
      const data = await api.matches({ tournamentId: tournament.id_tournament, pageSize: 100 });
      setSeries(data);
    }
  };

  const wins = tournament.t1_wins ?? 0;
  const total = tournament.total_games ?? 0;

  return (
    <div className="border border-border rounded-xl overflow-hidden">
      {/* Tournament header */}
      <button
        onClick={handleToggle}
        className="w-full flex items-center gap-4 px-5 py-4 bg-surface hover:bg-surfaceHover transition-colors text-left"
      >
        <Trophy size={16} className="text-accent shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="font-display font-semibold text-sm text-text truncate">
            {tournament.tournament_name}
          </div>
          <div className="text-xs text-textMuted mt-0.5">
            {fmt(tournament.start_date)} — {fmt(tournament.end_date)}
            <span className="mx-1.5">·</span>
            {tournament.total_series} series · {total} games
          </div>
        </div>
        <WinBadge wins={wins} total={total} />
        <ChevronDown
          size={16}
          className={clsx("text-textMuted transition-transform shrink-0", open && "rotate-180")}
        />
      </button>

      {/* Series list */}
      {open && (
        <div className="bg-bg/50 border-t border-border px-4 py-3 space-y-2">
          {!series ? (
            <div className="text-xs text-textMuted py-2">Đang tải series...</div>
          ) : series.length === 0 ? (
            <div className="text-xs text-textMuted py-2">Không có series nào.</div>
          ) : (
            series.map((s) => <SeriesRow key={s.id_series} series={s} />)
          )}
        </div>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function MatchHistory() {
  const [tournaments, setTournaments] = useState([]);
  const [page, setPage] = useState(1);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [loading, setLoading] = useState(true);
  const [selectedTournamentId, setSelectedTournamentId] = useState("");
  const [tournamentOptions, setTournamentOptions] = useState([]);

  const load = useCallback(() => {
  setLoading(true);
  api.matchesTournaments({ page, pageSize: PAGE_SIZE, startDate, endDate, tournamentId: selectedTournamentId })
    .then((data) => setTournaments(Array.isArray(data) ? data : []))
    .finally(() => setLoading(false));
}, [page, startDate, endDate, selectedTournamentId]);

  useEffect(() => { load(); }, [load]);

  // Fetch options cho dropdown — re-fetch khi date thay đổi
  useEffect(() => {
    api.matchesTournaments({ page: 1, pageSize: 100, startDate, endDate })
      .then((data) => {
        const list = Array.isArray(data) ? data : [];
        setTournamentOptions(list);
        if (selectedTournamentId && !list.find((t) => String(t.id_tournament) === selectedTournamentId)) {
          setSelectedTournamentId("");
        }
      });
  }, [startDate, endDate]);

  // Reset page khi filter thay đổi
  const handleFilter = () => { setPage(1); load(); };

  return (
    <div className="space-y-6">
      <div>
        <h1>Match History</h1>
        <p className="text-textMuted text-sm mt-1">
          Lịch sử thi đấu T1, 2020–2025. Nhấn vào tournament để xem series, nhấn series để xem chi tiết game.
        </p>
      </div>

      {/* Filter bar */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex items-center gap-2 bg-surface border border-border rounded-lg px-3 py-2">
          <span className="text-xs uppercase tracking-widest text-textMuted">Từ</span>
          <input
            type="date"
            value={startDate}
            onChange={(e) => { setStartDate(e.target.value); setPage(1); }}
            className="bg-transparent text-sm text-text focus:outline-none"
          />
        </div>
        <div className="flex items-center gap-2 bg-surface border border-border rounded-lg px-3 py-2">
          <span className="text-xs uppercase tracking-widest text-textMuted">Đến</span>
          <input
            type="date"
            value={endDate}
            onChange={(e) => { setEndDate(e.target.value); setPage(1); }}
            className="bg-transparent text-sm text-text focus:outline-none"
          />
        </div>
      <div className="flex items-center gap-2 bg-surface border border-border rounded-lg px-3 py-2">
        <span className="text-xs uppercase tracking-widest text-textMuted">Giải đấu</span>
        <select
          value={selectedTournamentId}
          onChange={(e) => { setSelectedTournamentId(e.target.value); setPage(1); }}
          className="bg-transparent text-sm focus:outline-none max-w-[220px] text-text"
        >
          <option value="">Tất cả</option>
          {tournamentOptions.map((t) => (
            <option key={t.id_tournament} value={String(t.id_tournament)}>
              {t.tournament_name}
            </option>
          ))}
        </select>
      </div>
        {(startDate || endDate || selectedTournamentId) && (
          <button
            onClick={() => { setStartDate(""); setEndDate(""); setSelectedTournamentId(""); setPage(1); }}
            className="text-xs uppercase tracking-widest text-textMuted hover:text-accent transition-colors px-2 py-1"
          >
            Xóa filter
          </button>
        )}
        <span className="text-xs uppercase tracking-widest text-textMuted ml-auto">
          {tournaments.length} tournament
        </span>
      </div>

      {/* Tournament list */}
      <div className="space-y-3">
        {loading
          ? [...Array(4)].map((_, i) => (
              <div key={i} className="h-16 bg-surface border border-border rounded-xl animate-pulse" />
            ))
          : tournaments.map((t) => (
              <TournamentCard key={t.id_tournament} tournament={t} />
            ))
        }
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between pt-1">
        <button
          onClick={() => setPage((p) => Math.max(1, p - 1))}
          disabled={page === 1}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm text-textMuted hover:text-text disabled:opacity-30 transition-colors"
        >
          <ChevronLeft size={16} /> Trước
        </button>
        <span className="text-xs text-textMuted font-mono">Trang {page}</span>
        <button
          onClick={() => setPage((p) => p + 1)}
          disabled={tournaments.length < PAGE_SIZE}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm text-textMuted hover:text-text disabled:opacity-30 transition-colors"
        >
          Sau <ChevronRight size={16} />
        </button>
      </div>
    </div>
  );
}