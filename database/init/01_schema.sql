-- T1 Analytics Database Schema
-- Mirrors existing PostgreSQL schema exactly

CREATE TABLE IF NOT EXISTS tournaments (
    id_tournament   SERIAL PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    year            INTEGER,
    region          VARCHAR(100),
    ist1winner      VARCHAR(10),
    winner          VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS teams (
    id_team         SERIAL PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    region          VARCHAR(100),
    logo_url        VARCHAR(500)
);

CREATE TABLE IF NOT EXISTS players (
    id_player       SERIAL PRIMARY KEY,
    ingame_name     VARCHAR(100) NOT NULL,
    full_name       VARCHAR(255),
    position        VARCHAR(50),
    photo_url       VARCHAR(500),
    birth_date      DATE,
    country         VARCHAR(100),
    team_id         INTEGER REFERENCES teams(id_team)
);

CREATE TABLE IF NOT EXISTS champions (
    id_champion     SERIAL PRIMARY KEY,
    name            VARCHAR(100) NOT NULL UNIQUE,
    image_url       VARCHAR(500)
);

CREATE TABLE IF NOT EXISTS series (
    id_series       SERIAL PRIMARY KEY,
    tournament_id   INTEGER REFERENCES tournaments(id_tournament),
    team_t1_id      INTEGER REFERENCES teams(id_team),
    team_opponent_id INTEGER REFERENCES teams(id_team),
    match_date      DATE,
    best_of         INTEGER
);

CREATE TABLE IF NOT EXISTS games (
    id_game         SERIAL PRIMARY KEY,
    series_id       INTEGER REFERENCES series(id_series),
    game_number     INTEGER,
    patch           VARCHAR(20),
    link            VARCHAR(500),
    date_played     DATE
);

CREATE TABLE IF NOT EXISTS game_teams (
    id_game_team    SERIAL PRIMARY KEY,
    game_id         INTEGER REFERENCES games(id_game),
    team_id         INTEGER REFERENCES teams(id_team),
    side            VARCHAR(10),    -- 'Blue' or 'Red'
    result          VARCHAR(10)     -- 'WIN' or 'LOSS'
);

CREATE TABLE IF NOT EXISTS game_players (
    id_game_player  SERIAL PRIMARY KEY,
    game_team_id    INTEGER REFERENCES game_teams(id_game_team),
    player_id       INTEGER REFERENCES players(id_player),
    champion_id     INTEGER REFERENCES champions(id_champion),
    pick_order      INTEGER
);

CREATE TABLE IF NOT EXISTS bans (
    id_ban          SERIAL PRIMARY KEY,
    game_id         INTEGER REFERENCES games(id_game),
    team_id         INTEGER REFERENCES teams(id_team),
    champion_id     INTEGER REFERENCES champions(id_champion),
    ban_order       INTEGER
);

-- Indexes cho các JOIN thường dùng
CREATE INDEX IF NOT EXISTS idx_games_date ON games(date_played);
CREATE INDEX IF NOT EXISTS idx_games_patch ON games(patch);
CREATE INDEX IF NOT EXISTS idx_game_teams_game ON game_teams(game_id);
CREATE INDEX IF NOT EXISTS idx_game_players_team ON game_players(game_team_id);
CREATE INDEX IF NOT EXISTS idx_game_players_champion ON game_players(champion_id);
CREATE INDEX IF NOT EXISTS idx_game_players_player ON game_players(player_id);
CREATE INDEX IF NOT EXISTS idx_bans_game ON bans(game_id);
CREATE INDEX IF NOT EXISTS idx_bans_champion ON bans(champion_id);
