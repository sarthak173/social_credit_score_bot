CREATE TABLE IF NOT EXISTS social_credit_scores(
    user_id INTEGER,
    username TEXT,
    guild_id TEXT,
    credit_score INTEGER,
    is_admin BOOLEAN
)