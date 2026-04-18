-- ============================================
-- BOT MIGRATION — Tables pour les vidéos anime
-- Exécuter dans Supabase > SQL Editor
-- ============================================

-- Table des séries (anime/mangas indexés)
CREATE TABLE IF NOT EXISTS bot_series (
  id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  title      TEXT NOT NULL,
  type       TEXT DEFAULT 'anime' CHECK (type IN ('anime', 'manga', 'film')),
  cover_url  TEXT,
  synopsis   TEXT,
  mal_id     INTEGER,
  tmdb_id    INTEGER,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bot_series_title ON bot_series(title);

-- Table des épisodes vidéo (indexés depuis Telegram)
CREATE TABLE IF NOT EXISTS bot_videos (
  id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  series_id  UUID REFERENCES bot_series(id) ON DELETE CASCADE NOT NULL,
  episode    INTEGER NOT NULL,
  season     INTEGER NOT NULL DEFAULT 1,
  language   TEXT NOT NULL DEFAULT 'VF' CHECK (language IN ('VF', 'VOSTFR', 'VO', 'VOSTA')),
  file_id    TEXT NOT NULL,        -- Telegram file_id (pour re-envoyer)
  message_id INTEGER NOT NULL,     -- ID du message Telegram (pour MTProto stream)
  channel_id TEXT NOT NULL,        -- ID ou @username du canal source
  file_size  BIGINT,               -- Taille en bytes (pour byte-range)
  file_name  TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (series_id, episode, season, language)
);

CREATE INDEX IF NOT EXISTS idx_bot_videos_series  ON bot_videos(series_id, season, episode);
CREATE INDEX IF NOT EXISTS idx_bot_videos_episode ON bot_videos(episode);

-- Colonnes manquantes sur la table chapters
ALTER TABLE chapters ADD COLUMN IF NOT EXISTS file_url    TEXT;
ALTER TABLE chapters ADD COLUMN IF NOT EXISTS file_type   TEXT;
ALTER TABLE chapters ADD COLUMN IF NOT EXISTS content_rating TEXT NOT NULL DEFAULT 'all'
  CHECK (content_rating IN ('all', '16+', '18+'));

-- Colonnes Telegram pour stocker les fichiers SUR Telegram (pas sur R2)
-- Le fichier ne quitte jamais Telegram — seul le file_id est stocké
ALTER TABLE chapters ADD COLUMN IF NOT EXISTS telegram_file_id   TEXT;
ALTER TABLE chapters ADD COLUMN IF NOT EXISTS telegram_message_id BIGINT;
ALTER TABLE chapters ADD COLUMN IF NOT EXISTS telegram_chat_id   TEXT;
ALTER TABLE chapters ADD COLUMN IF NOT EXISTS file_size          BIGINT;

-- RLS : lecture publique sur les deux tables
ALTER TABLE bot_series ENABLE ROW LEVEL SECURITY;
ALTER TABLE bot_videos ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "bot_series public read" ON bot_series;
CREATE POLICY "bot_series public read" ON bot_series FOR SELECT USING (true);

DROP POLICY IF EXISTS "bot_videos public read" ON bot_videos;
CREATE POLICY "bot_videos public read" ON bot_videos FOR SELECT USING (true);
