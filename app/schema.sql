CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('employee','admin','finance'))
);
CREATE TABLE IF NOT EXISTS policies (
    id INTEGER PRIMARY KEY,
    series_key TEXT NOT NULL,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    keywords TEXT NOT NULL,
    version TEXT NOT NULL,
    scope TEXT NOT NULL,
    content TEXT NOT NULL,
    effective_date TEXT NOT NULL,
    expiry_date TEXT,
    enabled INTEGER NOT NULL CHECK(enabled IN (0,1)),
    updated_by INTEGER NOT NULL REFERENCES users(id),
    updated_at TEXT NOT NULL,
    CHECK(expiry_date IS NULL OR expiry_date > effective_date)
);
CREATE TABLE IF NOT EXISTS consents (
    user_id INTEGER PRIMARY KEY REFERENCES users(id),
    granted INTEGER NOT NULL CHECK(granted IN (0,1)),
    version TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS claims (
    id INTEGER PRIMARY KEY,
    number TEXT NOT NULL UNIQUE,
    user_id INTEGER NOT NULL REFERENCES users(id),
    purpose TEXT NOT NULL,
    amount_cents INTEGER NOT NULL CHECK(amount_cents >= 0),
    submitted_date TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('待核对','审批中','待付款','已付款','已退回')),
    verified INTEGER NOT NULL DEFAULT 0 CHECK(verified IN (0,1)),
    note TEXT NOT NULL DEFAULT '',
    verified_by INTEGER REFERENCES users(id),
    verified_at TEXT
);
CREATE TABLE IF NOT EXISTS claim_history (
    id INTEGER PRIMARY KEY,
    claim_id INTEGER NOT NULL REFERENCES claims(id),
    status TEXT NOT NULL,
    note TEXT NOT NULL,
    actor_id INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL
);
