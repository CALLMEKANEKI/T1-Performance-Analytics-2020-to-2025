"""
ETL Script: Parse Excel → PostgreSQL
Run locally trước khi Dockerize

Usage:
    python etl.py --file data/csv/lck_data.xlsx --db-url postgresql://t1_user:password@localhost:5433/t1_analytics
"""

import ast
import re
import argparse
import logging
from datetime import datetime

import pandas as pd
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


# ── Helpers ──────────────────────────────────────────────────────────────────

def parse_list_str(value: str) -> list[str]:
    """Parse "['Faker', 'Oner', ...]" → ['Faker', 'Oner', ...]"""
    if not value or pd.isna(value):
        return []
    try:
        result = ast.literal_eval(str(value).strip())
        return [s.strip() for s in result] if isinstance(result, list) else []
    except Exception:
        # Fallback: strip brackets và split
        cleaned = re.sub(r"[\[\]']", "", str(value))
        return [s.strip() for s in cleaned.split(",") if s.strip()]


def normalize_patch(patch: str) -> str:
    """'10,2' → '10.2'"""
    return str(patch).replace(",", ".").strip()


def normalize_result(result: str) -> str:
    """'Win'/'Loss' → 'WIN'/'LOSS'"""
    return result.strip().upper()


def normalize_side(side: str) -> str:
    """'Blue'/'Red' → consistent"""
    return side.strip().capitalize()


# ── DB Helpers ────────────────────────────────────────────────────────────────

def get_or_create(conn, table: str, pk: str, lookup_col: str, value: str, extra: dict = None) -> int:
    """Lookup by value, insert if not exists, return id."""
    row = conn.execute(
        text(f"SELECT {pk} FROM {table} WHERE {lookup_col} = :val"),
        {"val": value}
    ).fetchone()
    if row:
        return row[0]

    cols = {lookup_col: value, **(extra or {})}
    col_names = ", ".join(cols.keys())
    placeholders = ", ".join(f":{k}" for k in cols.keys())
    result = conn.execute(
        text(f"INSERT INTO {table} ({col_names}) VALUES ({placeholders}) RETURNING {pk}"),
        cols
    )
    return result.fetchone()[0]


# ── Main ETL ──────────────────────────────────────────────────────────────────

def run_etl(excel_path: str, db_url: str):
    engine = create_engine(db_url)

    log.info(f"Reading Excel: {excel_path}")
    df_main = pd.read_excel(excel_path, sheet_name="LolMatchHistory_2020-2025")
    df_champions = pd.read_excel(excel_path, sheet_name="Champion")
    df_players = pd.read_excel(excel_path, sheet_name="Player")
    df_teams = pd.read_excel(excel_path, sheet_name="Team")
    df_tournaments = pd.read_excel(excel_path, sheet_name="Tournament")

    log.info(f"Loaded {len(df_main)} games from main sheet")

    with engine.begin() as conn:

        # ── 1. Seed lookup tables từ mapping sheets ───────────────────────────

        log.info("Seeding champions...")
        for _, row in df_champions.iterrows():
            get_or_create(conn, "champions", "id_champion", "name", str(row["Name"]).strip())

        log.info("Seeding teams...")
        t1_id = get_or_create(conn, "teams", "id_team", "name", "T1")
        for _, row in df_teams.iterrows():
            name = str(row["Name"]).strip()
            get_or_create(conn, "teams", "id_team", "name", name)

        log.info("Seeding players...")
        for _, row in df_players.iterrows():
            ingame = str(row["Nickname"]).strip()
            get_or_create(conn, "players", "id_player", "ingame_name", ingame, {
                "full_name": str(row["Name"]).strip(),
                "position": str(row["Role"]).strip() if pd.notna(row["Role"]) else None,
                "team_id": t1_id
            })

        # ── 2. Process main sheet row by row ──────────────────────────────────

        # Group by series: cùng (Match Date, Opponent Team) = 1 series
        processed_series = {}   # key: (date_str, opponent_name) → id_series
        game_number_tracker = {}  # key: same → count

        positions = ["Top", "Jungle", "Mid", "Bot", "Support"]

        for idx, row in df_main.iterrows():
            date_val = pd.to_datetime(row["Match Date"]).date()
            opponent_name = str(row["Opponent Team"]).strip()
            event_name = str(row["Event Name"]).strip()
            patch = normalize_patch(row["Patch"])
            result = normalize_result(row["Result"])
            side = normalize_side(row["Side"])
            link = str(row.get("Link", "")) or None

            t1_players = parse_list_str(row["T1 Players"])
            opp_players = parse_list_str(row["Opponent Players"])
            bans_t1 = parse_list_str(row["Bans Team 1"])
            bans_opp = parse_list_str(row["Bans Team 2"])
            picks_t1 = parse_list_str(row["Team 1 Champs"])
            picks_opp = parse_list_str(row["Team 2 Champs"])

            # Tournament
            year = int(row.get("Year", date_val.year))
            tournament_id = get_or_create(
                conn, "tournaments", "id_tournament", "name", event_name,
                {"year": year, "region": "KR"}
            )

            # Opponent team
            opp_team_id = get_or_create(conn, "teams", "id_team", "name", opponent_name)

            # Series (group games trong cùng 1 match)
            series_key = (str(date_val), opponent_name)
            if series_key not in processed_series:
                res = conn.execute(
                    text("""
                        INSERT INTO series (tournament_id, team_t1_id, team_opponent_id, match_date)
                        VALUES (:tid, :t1, :opp, :date) RETURNING id_series
                    """),
                    {"tid": tournament_id, "t1": t1_id, "opp": opp_team_id, "date": date_val}
                )
                processed_series[series_key] = res.fetchone()[0]
                game_number_tracker[series_key] = 0

            series_id = processed_series[series_key]
            game_number_tracker[series_key] += 1
            game_num = game_number_tracker[series_key]

            # Game
            res = conn.execute(
                text("""
                    INSERT INTO games (series_id, game_number, patch, link, date_played)
                    VALUES (:sid, :gnum, :patch, :link, :date) RETURNING id_game
                """),
                {"sid": series_id, "gnum": game_num, "patch": patch, "link": link, "date": date_val}
            )
            game_id = res.fetchone()[0]

            # T1 game_team
            t1_result = result          # 'WIN' or 'LOSS'
            opp_result = "LOSS" if result == "WIN" else "WIN"

            res = conn.execute(
                text("""
                    INSERT INTO game_teams (game_id, team_id, side, result)
                    VALUES (:gid, :tid, :side, :result) RETURNING id_game_team
                """),
                {"gid": game_id, "tid": t1_id, "side": side, "result": t1_result}
            )
            t1_game_team_id = res.fetchone()[0]

            opp_side = "Red" if side == "Blue" else "Blue"
            res = conn.execute(
                text("""
                    INSERT INTO game_teams (game_id, team_id, side, result)
                    VALUES (:gid, :tid, :side, :result) RETURNING id_game_team
                """),
                {"gid": game_id, "tid": opp_team_id, "side": opp_side, "result": opp_result}
            )
            opp_game_team_id = res.fetchone()[0]

            # T1 players + picks
            for pick_order, (player_name, champ_name) in enumerate(zip(t1_players, picks_t1), 1):
                player_id = get_or_create(
                    conn, "players", "id_player", "ingame_name", player_name,
                    {"position": positions[pick_order - 1], "team_id": t1_id}
                )
                champ_id = get_or_create(conn, "champions", "id_champion", "name", champ_name)
                conn.execute(
                    text("""
                        INSERT INTO game_players (game_team_id, player_id, champion_id, pick_order)
                        VALUES (:gtid, :pid, :cid, :order)
                    """),
                    {"gtid": t1_game_team_id, "pid": player_id, "cid": champ_id, "order": pick_order}
                )

            # Opponent players + picks
            for pick_order, (player_name, champ_name) in enumerate(zip(opp_players, picks_opp), 1):
                player_id = get_or_create(
                    conn, "players", "id_player", "ingame_name", player_name,
                    {"team_id": opp_team_id}
                )
                champ_id = get_or_create(conn, "champions", "id_champion", "name", champ_name)
                conn.execute(
                    text("""
                        INSERT INTO game_players (game_team_id, player_id, champion_id, pick_order)
                        VALUES (:gtid, :pid, :cid, :order)
                    """),
                    {"gtid": opp_game_team_id, "pid": player_id, "cid": champ_id, "order": pick_order}
                )

            # Bans
            for ban_order, champ_name in enumerate(bans_t1, 1):
                champ_id = get_or_create(conn, "champions", "id_champion", "name", champ_name)
                conn.execute(
                    text("""
                        INSERT INTO bans (game_id, team_id, champion_id, ban_order)
                        VALUES (:gid, :tid, :cid, :order)
                    """),
                    {"gid": game_id, "tid": t1_id, "cid": champ_id, "order": ban_order}
                )

            for ban_order, champ_name in enumerate(bans_opp, 1):
                champ_id = get_or_create(conn, "champions", "id_champion", "name", champ_name)
                conn.execute(
                    text("""
                        INSERT INTO bans (game_id, team_id, champion_id, ban_order)
                        VALUES (:gid, :tid, :cid, :order)
                    """),
                    {"gid": game_id, "tid": opp_team_id, "cid": champ_id, "order": ban_order}
                )

            if (idx + 1) % 100 == 0:
                log.info(f"  Processed {idx + 1}/{len(df_main)} rows...")

    log.info("ETL complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Path to Excel file")
    parser.add_argument("--db-url", required=True, help="PostgreSQL connection URL")
    args = parser.parse_args()
    run_etl(args.file, args.db_url)
