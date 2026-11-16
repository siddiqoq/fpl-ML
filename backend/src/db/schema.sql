-- Season-aware schema. FPL reassigns player and team IDs every season, so every table is keyed by
-- season. Stats a season did not record (e.g. xG before 2022/23) are NULL, never 0.

CREATE TABLE IF NOT EXISTS positions (
    element_type INT PRIMARY KEY,
    singular_name TEXT NOT NULL,
    plural_name TEXT NOT NULL
);

INSERT INTO positions VALUES
    (1, 'Goalkeeper', 'Goalkeepers'),
    (2, 'Defender', 'Defenders'),
    (3, 'Midfielder', 'Midfielders'),
    (4, 'Forward', 'Forwards'),
    (5, 'Manager', 'Managers')  -- assistant-manager chip, 2024/25 only
ON CONFLICT (element_type) DO NOTHING;

CREATE TABLE IF NOT EXISTS teams (
    season TEXT NOT NULL,          -- e.g. '2025/26'
    team_id INT NOT NULL,          -- FPL id, only unique within a season
    code INT,                      -- stable across seasons (NULL before 2019/20)
    name TEXT NOT NULL,
    short_name TEXT,
    strength_overall_home INT,
    strength_overall_away INT,
    strength_attack_home INT,
    strength_attack_away INT,
    strength_defence_home INT,
    strength_defence_away INT,
    PRIMARY KEY (season, team_id)
);

CREATE TABLE IF NOT EXISTS players (
    season TEXT NOT NULL,
    player_id INT NOT NULL,        -- FPL element id, only unique within a season
    code INT NOT NULL,             -- stable across seasons: use it to follow a player between seasons
    first_name TEXT,
    second_name TEXT,
    web_name TEXT NOT NULL,
    element_type INT,
    team_id INT,                   -- team at end of season (or now); per-match team is in player_fixture_stats
    PRIMARY KEY (season, player_id)
);
CREATE INDEX IF NOT EXISTS players_code_idx ON players (code);

CREATE TABLE IF NOT EXISTS gameweeks (
    season TEXT NOT NULL,
    gameweek INT NOT NULL,
    deadline_time TIMESTAMPTZ,     -- NULL for seasons loaded from vaastav
    finished BOOLEAN,
    data_checked BOOLEAN,          -- stats are only final once this is true
    PRIMARY KEY (season, gameweek)
);

CREATE TABLE IF NOT EXISTS fixtures (
    season TEXT NOT NULL,
    fixture_id INT NOT NULL,
    gameweek INT,                  -- NULL while a postponed fixture is unscheduled
    kickoff_time TIMESTAMPTZ,
    team_h INT,
    team_a INT,
    team_h_score INT,
    team_a_score INT,
    team_h_difficulty INT,
    team_a_difficulty INT,
    finished BOOLEAN,
    PRIMARY KEY (season, fixture_id)
);

-- One row per player per fixture, so double gameweeks keep both matches and blank gameweeks have no rows.
-- value/selected/transfers are as they were at that gameweek, not today's.
CREATE TABLE IF NOT EXISTS player_fixture_stats (
    season TEXT NOT NULL,
    player_id INT NOT NULL,
    fixture_id INT NOT NULL,
    gameweek INT NOT NULL,
    kickoff_time TIMESTAMPTZ,
    team_id INT,                   -- player's team in this match (handles mid-season transfers)
    opponent_team INT,
    was_home BOOLEAN,
    minutes INT,
    starts INT,
    total_points INT,
    goals_scored INT,
    assists INT,
    clean_sheets INT,
    goals_conceded INT,
    own_goals INT,
    penalties_saved INT,
    penalties_missed INT,
    yellow_cards INT,
    red_cards INT,
    saves INT,
    bonus INT,
    bps INT,
    influence NUMERIC,
    creativity NUMERIC,
    threat NUMERIC,
    ict_index NUMERIC,
    expected_goals NUMERIC,
    expected_assists NUMERIC,
    expected_goal_involvements NUMERIC,
    expected_goals_conceded NUMERIC,
    defensive_contribution INT,
    clearances_blocks_interceptions INT,
    recoveries INT,
    tackles INT,
    value INT,                     -- price x10 at the time
    selected INT,
    transfers_in INT,
    transfers_out INT,
    transfers_balance INT,
    xp NUMERIC,                    -- FPL expected points from vaastav; live season uses ep_snapshots
    PRIMARY KEY (season, player_id, fixture_id)
);
CREATE INDEX IF NOT EXISTS player_fixture_stats_gw_idx ON player_fixture_stats (season, gameweek);

-- FPL's own expected points, captured before each deadline (the API overwrites them afterwards).
CREATE TABLE IF NOT EXISTS ep_snapshots (
    season TEXT NOT NULL,
    gameweek INT NOT NULL,         -- the upcoming gameweek ep_next refers to
    player_id INT NOT NULL,
    taken_at TIMESTAMPTZ NOT NULL,
    ep_next NUMERIC,
    ep_this NUMERIC,
    chance_of_playing_next_round INT,
    status TEXT,
    now_cost INT,
    selected_by_percent NUMERIC,
    PRIMARY KEY (season, gameweek, player_id)
);

-- Audit log of every load, used to tell pipeline faults apart from real drift.
CREATE TABLE IF NOT EXISTS ingest_runs (
    run_id SERIAL PRIMARY KEY,
    source TEXT NOT NULL,          -- 'vaastav', 'fpl_api' or 'ep_snapshot'
    season TEXT,
    gameweeks INT[],
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    rows_written INT,
    status TEXT NOT NULL,          -- 'running', 'ok' or 'failed'
    message TEXT
);
