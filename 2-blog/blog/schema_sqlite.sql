CREATE TABLE IF NOT EXISTS articles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  slug TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  excerpt TEXT,
  content TEXT NOT NULL,
  category TEXT NOT NULL DEFAULT 'technology',
  status TEXT NOT NULL DEFAULT 'draft',
  meta_description TEXT,
  image_url TEXT,
  image_alt TEXT,
  image_credit TEXT,
  image_credit_url TEXT,
  image_license TEXT,
  sources_json TEXT,
  views INTEGER NOT NULL DEFAULT 0,
  published_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS idempotency_keys (
  k TEXT PRIMARY KEY,
  slug TEXT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sync_state (
  id INTEGER PRIMARY KEY,
  last_run INTEGER NOT NULL DEFAULT 0,
  last_status TEXT
);

INSERT OR IGNORE INTO sync_state (id, last_run) VALUES (1, 0);
