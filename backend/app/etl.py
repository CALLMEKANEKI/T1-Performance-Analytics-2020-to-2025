"""
ETL Script: Parse Excel → PostgreSQL
Run locally trước khi Dockerize

Usage:
    python etl.py --file data/csv/T1MatchHistory_2020-2025.xlsx --db-url postgresql://t1_user:password@localhost:5433/t1_analytics
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
    """Generic get_or_create (không dùng cho players vì cần xử lý team_id)."""
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


def get_or_create_player(conn, nickname: str, full_name: str = None, position: str = None, photo_url: str = None, team_id: int = None) -> int:
    """
    Lấy player theo nickname. Nếu chưa có, insert với team_id = None.
    Nếu đã có và team_id được truyền vào (ví dụ 1) và player hiện có team_id = NULL, cập nhật team_id.
    """
    # Kiểm tra tồn tại
    row = conn.execute(
        text("SELECT id_player, team_id FROM players WHERE ingame_name = :nickname"),
        {"nickname": nickname}
    ).fetchone()
    if row:
        player_id = row[0]
        current_team_id = row[1]
        # Nếu player chưa có team_id và ta muốn gán team_id (ví dụ 1), thì cập nhật
        if team_id is not None and current_team_id is None:
            conn.execute(
                text("UPDATE players SET team_id = :team_id WHERE id_player = :pid"),
                {"team_id": team_id, "pid": player_id}
            )
            log.debug(f"Updated team_id for player {nickname} to {team_id}")
        return player_id

    # Insert mới với team_id = None (hoặc team_id nếu được truyền)
    ins = conn.execute(
        text("""
            INSERT INTO players (ingame_name, full_name, position, photo_url, team_id)
            VALUES (:nickname, :full_name, :position, :photo_url, :team_id)
            RETURNING id_player
        """),
        {
            "nickname": nickname,
            "full_name": full_name,
            "position": position,
            "photo_url": photo_url,
            "team_id": team_id   # Nếu không truyền, mặc định None
        }
    )
    return ins.fetchone()[0]


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

        # ── 1. Seed lookup tables ───────────────────────────────────────────────

        log.info("Seeding champions...")
        for _, row in df_champions.iterrows():
            name = str(row.get("Name", row.iloc[2]))
            if name:
                get_or_create(conn, "champions", "id_champion", "name", name, {"image_url": row.get("Icon")})

        log.info("Seeding teams...")
        t1_id = get_or_create(conn, "teams", "id_team", "name", "T1")
        for _, row in df_teams.iterrows():
            name = str(row.get("Name", row.iloc[2]))
            if name and name != "T1":
                get_or_create(conn, "teams", "id_team", "name", name, {"region": row.get("Region")})

        log.info("Seeding players (initial)...")
        # Seed từ sheet player với team_id = NULL
        for _, row in df_players.iterrows():
            nickname = str(row.get("Nickname", row.iloc[3]))
            if nickname:
                full_name = row.get("Name", row.iloc[2])
                role = row.get("Role", row.iloc[4])
                avatar = row.get("Avatar", row.iloc[1])
                # Dùng get_or_create_player với team_id=None để insert nếu chưa có
                get_or_create_player(conn, nickname, full_name, role, avatar, team_id=None)

        log.info("Seeding tournaments...")
        for _, row in df_tournaments.iterrows():
            name = str(row.get("Name", row.iloc[1]))
            year = int(row.get("Date", row.iloc[2]))
            if name and year:
                region = row.get("Region", row.iloc[5])
                is_t1_winner = row.get("Is T1 winner", row.iloc[3])
                winner = row.get("Winner", row.iloc[4])
                get_or_create(
                    conn, "tournaments", "id_tournament", "name", name,
                    {"year": year, "region": region, "ist1winner": is_t1_winner, "winner": winner}
                )

        # ── 2. Process main sheet ──────────────────────────────────────────────

        df_main = df_main.sort_values('Index')
        grouped = df_main.groupby(['Match Date', 'Opponent Team', 'Event Name'])

        total_games = 0
        processed = 0

        for (date_val, opponent_name, event_name), group in grouped:
            date_obj = pd.to_datetime(date_val).date()
            game_count = len(group)
            best_of = game_count   # 1, 3, 5

            # Tournament lookup
            year = int(group.iloc[0]['Year'])
            tournament_id = get_or_create(
                conn, "tournaments", "id_tournament", "name", event_name,
                {"year": year, "region": "KR"}
            )

            # Opponent team
            opp_team_id = get_or_create(conn, "teams", "id_team", "name", opponent_name)

            # Insert series (không có winner_team_id)
            res = conn.execute(
                text("""
                    INSERT INTO series (tournament_id, team_t1_id, team_opponent_id, match_date, best_of)
                    VALUES (:tid, :t1, :opp, :date, :best)
                    RETURNING id_series
                """),
                {
                    "tid": tournament_id,
                    "t1": t1_id,
                    "opp": opp_team_id,
                    "date": date_obj,
                    "best": best_of
                }
            )
            series_id = res.fetchone()[0]

            game_number = 1
            for _, row in group.iterrows():
                patch = normalize_patch(row['Patch'])
                result = normalize_result(row['Result'])
                side = normalize_side(row['Side'])
                link = str(row.get('Link')) if pd.notna(row.get('Link')) else None
                date_played = date_obj

                # Insert game
                res = conn.execute(
                    text("""
                        INSERT INTO games (series_id, game_number, patch, link, date_played)
                        VALUES (:sid, :gnum, :patch, :link, :date)
                        RETURNING id_game
                    """),
                    {"sid": series_id, "gnum": game_number, "patch": patch, "link": link, "date": date_played}
                )
                game_id = res.fetchone()[0]

                # T1 game_team
                t1_result = result
                opp_result = "LOSS" if result == "WIN" else "WIN"
                t1_side = side
                opp_side = "Red" if side == "Blue" else "Blue"

                res = conn.execute(
                    text("""
                        INSERT INTO game_teams (game_id, team_id, side, result)
                        VALUES (:gid, :tid, :side, :result)
                        RETURNING id_game_team
                    """),
                    {"gid": game_id, "tid": t1_id, "side": t1_side, "result": t1_result}
                )
                t1_game_team_id = res.fetchone()[0]

                res = conn.execute(
                    text("""
                        INSERT INTO game_teams (game_id, team_id, side, result)
                        VALUES (:gid, :tid, :side, :result)
                        RETURNING id_game_team
                    """),
                    {"gid": game_id, "tid": opp_team_id, "side": opp_side, "result": opp_result}
                )
                opp_game_team_id = res.fetchone()[0]

                # T1 picks - gán team_id = 1 cho các player T1
                t1_players = parse_list_str(row['T1 Players'])
                t1_picks = parse_list_str(row['Team 1 Champs'])
                positions = ["Top", "Jungle", "Mid", "Bot", "Support"]
                for pick_order, (player_name, champ_name) in enumerate(zip(t1_players, t1_picks), 1):
                    if not player_name or not champ_name:
                        continue
                    # Gán team_id = t1_id cho player này (nếu chưa có)
                    player_id = get_or_create_player(
                        conn, player_name,
                        position=positions[pick_order - 1],
                        team_id=t1_id   # <-- Quan trọng: gán team_id = 1
                    )
                    champ_id = get_or_create(conn, "champions", "id_champion", "name", champ_name)
                    conn.execute(
                        text("""
                            INSERT INTO game_players (game_team_id, player_id, champion_id, pick_order)
                            VALUES (:gtid, :pid, :cid, :order)
                        """),
                        {"gtid": t1_game_team_id, "pid": player_id, "cid": champ_id, "order": pick_order}
                    )

                # Opponent picks - không gán team_id (để NULL)
                opp_players = parse_list_str(row['Opponent Players'])
                opp_picks = parse_list_str(row['Team 2 Champs'])
                for pick_order, (player_name, champ_name) in enumerate(zip(opp_players, opp_picks), 1):
                    if not player_name or not champ_name:
                        continue
                    player_id = get_or_create_player(
                        conn, player_name,
                        team_id=None   # Không gán team_id cho đối thủ
                    )
                    champ_id = get_or_create(conn, "champions", "id_champion", "name", champ_name)
                    conn.execute(
                        text("""
                            INSERT INTO game_players (game_team_id, player_id, champion_id, pick_order)
                            VALUES (:gtid, :pid, :cid, :order)
                        """),
                        {"gtid": opp_game_team_id, "pid": player_id, "cid": champ_id, "order": pick_order}
                    )

                # Bans – bỏ qua "None"
                for ban_order, champ_name in enumerate(parse_list_str(row['Bans Team 1']), 1):
                    if champ_name and champ_name.strip().lower() != 'none':
                        champ_id = get_or_create(conn, "champions", "id_champion", "name", champ_name)
                        conn.execute(
                            text("""
                                INSERT INTO bans (game_id, team_id, champion_id, ban_order)
                                VALUES (:gid, :tid, :cid, :order)
                            """),
                            {"gid": game_id, "tid": t1_id, "cid": champ_id, "order": ban_order}
                        )

                for ban_order, champ_name in enumerate(parse_list_str(row['Bans Team 2']), 1):
                    if champ_name and champ_name.strip().lower() != 'none':
                        champ_id = get_or_create(conn, "champions", "id_champion", "name", champ_name)
                        conn.execute(
                            text("""
                                INSERT INTO bans (game_id, team_id, champion_id, ban_order)
                                VALUES (:gid, :tid, :cid, :order)
                            """),
                            {"gid": game_id, "tid": opp_team_id, "cid": champ_id, "order": ban_order}
                        )

                game_number += 1
                total_games += 1
                processed += 1

                if processed % 100 == 0:
                    log.info(f"Processed {processed} games...")

        log.info(f"Total games inserted: {total_games}")

    log.info("ETL completed successfully.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Path to Excel file")
    parser.add_argument("--db-url", required=True, help="PostgreSQL connection URL")
    args = parser.parse_args()
    run_etl(args.file, args.db_url)