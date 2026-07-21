import { useEffect, useState, useCallback } from "react";
import { ChevronLeft, ChevronRight, ChevronDown, Trophy, Youtube, Sword } from "lucide-react";
import clsx from "clsx";
import { api } from "../lib/api";
import GameDetail from "../components/GameDetail";

const PAGE_SIZE = 10;

function fmt(dateStr) {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleDateString("vi-VN", {
    day: "2-digit", month: "2-digit", year: "numeric",
  });
}

function WinBadge({ wins, total }) {
  const losses = total - wins;
  const pct = total ? ((wins / total) * 100).toFixed(0) : 0;
  const won = wins > losses;
  return (
    <span className={clsx(
      "font-mono text-xs px-2.5 py-1 rounded-full shrink-0 font-medium",
      won
        ? "bg-win/10 text-win border border-win/20"
        : "bg-loss/10 text-loss border border-loss/20"
    )}>
      {wins}W {losses}L · {pct}%
    </span>
  );
}

function SeriesExpanded({ seriesId }) {
  const [games, setGames] = useState(null);
  const [activeGameId, setActiveGameId] = useState(null);

  useEffect(() => {
    api.seriesDetail(seriesId).then((d) => {
      setGames(d.games ?? []);
      if (d.games?.length) setActiveGameId(d.games[0].id_game);
    });
  }, [seriesId]);

  if (!games) return (
    <div className="px-5 py-4 border-t border-border">
      <div className="skeleton h-4 w-32 mb-2" />
      <div className="skeleton h-4 w-48" />
    </div>
  );

  return (
    <div className="px-5 pb-4 pt-3 border-t border-border/50 bg-bg/20 animate-fade-in">
      <div className="flex gap-2 mb-4 flex-wrap items-center">
        {games.map((g) => (
          <button
            key={g.id_game}
            onClick={() => setActiveGameId(g.id_game)}
            className={clsx(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono transition-all",
              activeGameId === g.id_game
                ? "bg-accent text-white shadow-[0_0_8px_rgba(224,20,76,0.3)]"
                : "bg-surface text-textMuted hover:text-text border border-border hover:border-border/80"
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
              className="ml-auto flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-textMuted hover:text-accent transition-colors border border-border hover:border-accent/30"
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

function SeriesRow({ series }) {
  const [open, setOpen] = useState(false);
  const wins = series.t1_wins ?? 0;
  const total = series.total_games ?? 0;

  return (
    <div className={clsx(
      "border border-border rounded-xl overflow-hidden bg-surface transition-all duration-200",
      open && "border-border/80 shadow-sm"
    )}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-3 px-4 py-3.5 text-left hover:bg-surfaceHover transition-colors"
      >
        <WinBadge wins={wins} total={total} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <Sword size={12} className="text-textMuted shrink-0" />
            <span className="text-sm text-text font-medium truncate">
              T1 vs {series.opponent_name}
            </span>
          </div>
        </div>
        <span className="text-xs text-textMuted font-mono shrink-0">{fmt(series.match_date)}</span>
        <ChevronDown
          size={14}
          className={clsx("text-textMuted transition-transform shrink-0 duration-200", open && "rotate-180")}
        />
      </button>
      {open && <SeriesExpanded seriesId={series.id_series} />}
    </div>
  );
}

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
  const winPct = total ? (wins / total * 100).toFixed(0) : 0;

  return (
    <div className={clsx(
      "border rounded-xl overflow-hidden transition-all duration-200",
      open ? "border-border/80 shadow-md" : "border-border"
    )}>
      <button
        onClick={handleToggle}
        className="w-full flex items-center gap-4 px-5 py-4 bg-surface hover:bg-surfaceHover transition-colors text-left"
      >
        <div className="w-10 h-10 rounded-xl bg-accent/10 border border-accent/20 flex items-center justify-center shrink-0">
          <Trophy size={16} className="text-accent" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-display font-semibold text-sm text-text truncate">
            {tournament.tournament_name}
          </div>
          <div className="text-xs text-textMuted mt-0.5">
            {fmt(tournament.start_date)} — {fmt(tournament.end_date)}
            <span className="mx-1.5 text-border">·</span>
            {tournament.total_series} series · {total} games
          </div>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <WinBadge wins={wins} total={total} />
          <ChevronDown
            size={16}
            className={clsx("text-textMuted transition-transform duration-200", open && "rotate-180")}
          />
        </div>
      </button>

      {open && (
        <div className="bg-bg/30 border-t border-border px-4 py-3 space-y-2 animate-fade-in">
          {!series ? (
            <div className="space-y-2 py-2">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="skeleton h-12 rounded-xl" />
              ))}
            </div>
          ) : series.length === 0 ? (
            <div className="text-xs text-textMuted py-3 text-center">Không có series nào.</div>
          ) : (
            series.map((s) => <SeriesRow key={s.id_series} series={s} />)
          )}
        </div>
      )}
    </div>
  );
}

export default function MatchHistory() {
  const [tournaments, setTournaments] = useState([]);
  const [page, setPage] = useState(1);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [selectedTournamentId, setSelectedTournamentId] = useState("");
  const [tournamentOptions, setTournamentOptions] = useState([]);
  const [loading, setLoading] = useState(true);

  // Fetch dropdown options khi date thay đổi
  useEffect(() => {
    const params = new URLSearchParams({ page: 1, page_size: 100 });
    if (startDate) params.set("start_date", startDate);
    if (endDate) params.set("end_date", endDate);
    fetch(`http://localhost:8000/api/matches/tournaments?${params}`)
      .then((r) => r.json())
      .then((data) => {
        const list = Array.isArray(data) ? data : [];
        setTournamentOptions(list);
        if (selectedTournamentId && !list.find((t) => String(t.id_tournament) === selectedTournamentId)) {
          setSelectedTournamentId("");
        }
      });
  }, [startDate, endDate]);

  const load = useCallback(() => {
    setLoading(true);
    const params = new URLSearchParams({ page, page_size: PAGE_SIZE });
    if (startDate) params.set("start_date", startDate);
    if (endDate) params.set("end_date", endDate);
    if (selectedTournamentId) params.set("tournament_id", selectedTournamentId);
    fetch(`http://localhost:8000/api/matches/tournaments?${params}`)
      .then((r) => r.json())
      .then((data) => setTournaments(Array.isArray(data) ? data : []))
      .finally(() => setLoading(false));
  }, [page, startDate, endDate, selectedTournamentId]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="space-y-6">
      <div className="animate-fade-in">
        <h1 className="font-display font-bold text-2xl text-text tracking-tight">Match History</h1>
        <p className="text-textMuted text-sm mt-1">
          Lịch sử thi đấu T1, 2020–2025. Nhấn vào tournament để xem series.
        </p>
      </div>

      {/* Filter bar */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex items-center gap-2 bg-surface border border-border rounded-xl px-3 py-2 hover:border-border/80 transition-colors">
          <span className="text-xs text-textMuted">Từ</span>
          <input
            type="date"
            value={startDate}
            onChange={(e) => { setStartDate(e.target.value); setPage(1); }}
            className="bg-transparent text-sm text-text focus:outline-none"
          />
        </div>
        <div className="flex items-center gap-2 bg-surface border border-border rounded-xl px-3 py-2 hover:border-border/80 transition-colors">
          <span className="text-xs text-textMuted">Đến</span>
          <input
            type="date"
            value={endDate}
            onChange={(e) => { setEndDate(e.target.value); setPage(1); }}
            className="bg-transparent text-sm text-text focus:outline-none"
          />
        </div>
        <div className="flex items-center gap-2 bg-surface border border-border rounded-xl px-3 py-2 hover:border-border/80 transition-colors">
          <span className="text-xs text-textMuted">Giải đấu</span>
          <select
            value={selectedTournamentId}
            onChange={(e) => { setSelectedTournamentId(e.target.value); setPage(1); }}
            className="bg-transparent text-sm text-text focus:outline-none max-w-[200px]"
            style={{ color: "black" }}
          >
            <option value="" style={{ color: "black" }}>Tất cả</option>
            {tournamentOptions.map((t) => (
              <option key={t.id_tournament} value={String(t.id_tournament)} style={{ color: "black" }}>
                {t.tournament_name}
              </option>
            ))}
          </select>
        </div>
        {(startDate || endDate || selectedTournamentId) && (
          <button
            onClick={() => { setStartDate(""); setEndDate(""); setSelectedTournamentId(""); setPage(1); }}
            className="text-xs text-textMuted hover:text-accent transition-colors px-2 py-1 rounded-lg hover:bg-surfaceHover"
          >
            Xóa filter
          </button>
        )}
        <span className="text-xs text-textMuted ml-auto">{tournaments.length} tournament</span>
      </div>

      {/* Tournament list */}
      <div className="space-y-3">
        {loading
          ? [...Array(4)].map((_, i) => (
              <div key={i} className="skeleton h-16 rounded-xl" />
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
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm text-textMuted hover:text-text disabled:opacity-30 transition-colors hover:bg-surfaceHover"
        >
          <ChevronLeft size={16} /> Trước
        </button>
        <span className="text-xs text-textMuted font-mono">Trang {page}</span>
        <button
          onClick={() => setPage((p) => p + 1)}
          disabled={tournaments.length < PAGE_SIZE}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm text-textMuted hover:text-text disabled:opacity-30 transition-colors hover:bg-surfaceHover"
        >
          Sau <ChevronRight size={16} />
        </button>
      </div>
    </div>
  );
}