SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    remote_id INTEGER UNIQUE,
    title TEXT NOT NULL,
    normalized_title TEXT NOT NULL,
    options_json TEXT NOT NULL,
    answer_indices_json TEXT NOT NULL,
    answer_text_json TEXT NOT NULL,
    is_right INTEGER,
    source TEXT NOT NULL DEFAULT 'jx3box',
    hit_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_questions_normalized_title
    ON questions(normalized_title);

CREATE UNIQUE INDEX IF NOT EXISTS idx_questions_user_normalized_title
    ON questions(normalized_title)
    WHERE source = 'user';

CREATE TABLE IF NOT EXISTS sync_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""
