SCHEMA_DESCRIPTION = """
=== CẤU TRÚC DATABASE ===

TABLE tournaments
  id_tournament (int PK), name (varchar), year (int), 
  region (varchar: 'KR' hoặc 'INT'), ist1winner (varchar: 'YES'/'NO'), 
  winner (varchar - tên đội vô địch)

TABLE teams  
  id_team (int PK), name (varchar), region (varchar), logo_url (varchar)
  NOTE: T1 luôn có id_team = 1

TABLE players
  id_player (int PK), ingame_name (varchar - nickname), 
  full_name (varchar), position (varchar: 'TOP','JUNGLER','MID','ADC','SUPPORT'),
  team_id (int FK → teams, NULL nếu là player đối thủ)

TABLE champions
  id_champion (int PK), name (varchar), image_url (varchar)

TABLE series
  id_series (int PK), tournament_id (int FK), 
  team_t1_id (int FK → teams), team_opponent_id (int FK → teams),
  match_date (date), best_of (int: 1/3/5)

TABLE games
  id_game (int PK), series_id (int FK → series), game_number (int),
  patch (varchar: vd '14.5'), date_played (date), link (varchar)

TABLE game_teams
  id_game_team (int PK), game_id (int FK → games), team_id (int FK → teams),
  side (varchar: 'Blue' hoặc 'Red'),
  result (varchar: 'WIN' hoặc 'LOSS')

TABLE game_players
  id_game_player (int PK), game_team_id (int FK → game_teams),
  player_id (int FK → players), champion_id (int FK → champions), pick_order (int 1-5)

TABLE bans
  id_ban (int PK), game_id (int FK → games), team_id (int FK → teams),
  champion_id (int FK → champions), ban_order (int 1-5)

=== RELATIONSHIPS & QUY TẮC JOIN ===
1. Để lấy thông tin game -> game_teams: 
   FROM games g JOIN game_teams gt ON g.id_game = gt.game_id
2. Để lấy thông tin tướng được pick từ game_teams -> game_players -> champions:
   FROM game_teams gt 
   JOIN game_players gp ON gt.id_game_team = gp.game_team_id
   JOIN champions c ON gp.champion_id = c.id_champion
3. Mối quan hệ giữa games và series:
   FROM series s JOIN games g ON s.id_series = g.series_id

=== LƯU Ý QUAN TRỌNG ===
1. T1 luôn có team_id = 1 (hoặc id_team = 1). Không cần JOIN bảng teams để tìm T1, dùng trực tiếp `team_id = 1`.
2. Để lấy các ván đấu và tướng được pick của T1: 
   FILTER `gt.team_id = 1` ở bảng game_teams.
3. Để lấy picks của đối thủ T1: 
   FILTER `gt.team_id != 1` ở bảng game_teams.
4. Sử dụng `EXTRACT(YEAR FROM g.date_played) = 2023` để lọc theo năm của trận đấu.
5. ingame_name trong bảng players là nickname (Faker, Keria, Oner...)
"""

def build_sql_prompt(user_question: str) -> str:
    """Build prompt for SQL generation from user question"""
    return f"""
{SCHEMA_DESCRIPTION}

=== CÂU HỎI ===
{user_question}

=== YÊU CẦU ===
Viết một PostgreSQL query duy nhất để trả lời câu hỏi trên dựa vào các QUY TẮC JOIN và LƯU Ý QUAN TRỌNG.
Chỉ trả về câu lệnh SQL đặt trong khối code ```sql ... ```, tuyệt đối không giải thích hoặc thêm văn bản nào khác.
Sử dụng ALIAS ngắn gọn cho các bảng khi JOIN (ví dụ: gt, gp, g, s, c, etc.)
Luôn thêm LIMIT 10 nếu không có điều kiện giới hạn cụ thể.
"""