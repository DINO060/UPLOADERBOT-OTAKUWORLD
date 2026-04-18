# Manga/Anime Uploader Bot — Structure complète

## Démarrage rapide

```bash
# 1. Installer les dépendances
pip install -r requirements.txt

# 2. Configurer l'environnement
copy .env.example .env
# Remplir .env avec vos valeurs

# 3. Configurer la whitelist
# Éditer whitelist.json avec vos Telegram ID → Supabase UUID

# 4. Exécuter la migration SQL
# Coller bot_migration.sql dans Supabase > SQL Editor

# 5. Lancer le bot
cd src
python main.py
```

---

## Structure des fichiers

```
manga-uploader-bot/
│
├── .env                    ← Variables d'environnement (NE PAS COMMIT)
├── .env.example            ← Template de configuration
├── .gitignore
├── requirements.txt        ← Dépendances Python
├── whitelist.json          ← { "telegram_id": "supabase_uuid" }
├── bot_migration.sql       ← Migration Supabase (bot_series + bot_videos)
├── BOT_STRUCTURE.md        ← Ce fichier
│
└── src/
    ├── main.py             ← Point d'entrée — lance bot + serveur API
    ├── bot.py              ← Enregistrement de tous les handlers
    │
    ├── commands/           ── Commandes Telegram
    │   ├── start.py        ← /start, /help
    │   ├── upload.py       ← /upload, /cancel, /skip + handlers texte/photo/document
    │   ├── addchapter.py   ← /addchapter <titre>
    │   ├── status.py       ← /status
    │   └── video.py        ← /addvideo, /listvids + handlers vidéo
    │
    ├── handlers/           ── Routage des messages entrants
    │   └── message.py      ← Route texte/photo/document/vidéo vers le bon handler
    │
    ├── services/           ── Logique métier
    │   ├── r2_storage.py       ← Upload vers Cloudflare R2 (boto3)
    │   ├── supabase_client.py  ← CRUD sur tables Comment Live + bot_series/bot_videos
    │   ├── whitelist.py        ← Lecture whitelist.json, vérification accès
    │   ├── channel.py          ← Annonces sur canaux Telegram
    │   ├── telethon_client.py  ← Client MTProto (streaming vidéo byte-range)
    │   ├── metadata.py         ← Jikan (anime) + TMDB (films/séries)
    │   └── filename_parser.py  ← Parse "EP10 VF @user.mp4" → titre, ep, langue
    │
    ├── api/                ── Serveur FastAPI (streaming vidéo web)
    │   ├── server.py       ← App FastAPI + CORS
    │   └── stream.py       ← GET /stream/{id}, GET /videos, GET /videos/{id}/episodes
    │
    └── models/
        └── types.py        ← UploadSession, VideoSession, ParsedFilename
```

---

## Commandes disponibles

### Manga (PDF / CBZ)

| Commande | Description |
|----------|-------------|
| `/upload` | Nouvel upload (nouveau titre) |
| `/addchapter <titre>` | Ajouter un chapitre à une oeuvre existante |
| `/status` | Voir ses 10 derniers chapitres publiés |
| `/cancel` | Annuler l'upload en cours |
| `/skip` | Passer description ou cover |

**Flow `/upload` :**
```
titre → description (skip ok) → cover (skip ok) → fichier PDF/CBZ → confirm oui/non
```

**Flow `/addchapter` :**
```
/addchapter One Piece → envoyer le fichier directement → confirm
```

### Vidéo / Anime

| Commande | Description |
|----------|-------------|
| `/addvideo` | Indexer un épisode manuellement |
| `/listvids <titre>` | Lister les épisodes d'une série |

**Flow `/addvideo` :**
```
titre → numéro d'épisode → langue (VF/VOSTFR) → envoyer la vidéo → confirm
```

---

## Architecture technique

### Upload manga
```
Utilisateur → PDF/CBZ
    ↓
Téléchargement depuis Telegram
    ↓
Upload vers Cloudflare R2  (r2_storage.py)
    ↓ URL publique
Insert dans table chapters  (supabase_client.py)
    ↓
Annonce sur canaux Telegram  (channel.py)
```

### Indexation vidéo
```
Vidéo dans canal Telegram
    ↓ (file_id + message_id stockés)
Recherche metadata Jikan/TMDB  (metadata.py)
    ↓
Upsert bot_series + Insert bot_videos  (supabase_client.py)
    ↓
Annonce sur canaux  (channel.py)
```

### Streaming vidéo (FastAPI)
```
Browser  →  GET /stream/{video_id}  Range: bytes=X-Y
    ↓
Lecture file_id + channel_id depuis bot_videos
    ↓
Telethon MTProto  →  iter_download(offset=X, limit=Y)
    ↓  (chunks alignés sur 4096 bytes)
StreamingResponse 206 Partial Content
    ↓
Player HTML5  (seeking natif)
```

---

## Base de données

### Tables utilisées depuis Comment Live
- `chapters` — chapitres manga (file_url, file_type, content_type = 'pdf'/'cbz')
- `chapter_tags` — tags des chapitres
- `profiles` — profils utilisateurs (UUID = clé dans whitelist.json)

### Tables ajoutées par bot_migration.sql
- `bot_series` — séries anime/manga indexées (title, cover, synopsis, mal_id)
- `bot_videos` — épisodes vidéo (file_id, message_id, channel_id, file_size)

---

## Whitelist (`whitelist.json`)

Chaque entrée = un uploader autorisé.

```json
{
  "123456789": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "987654321": "yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy"
}
```

- Clé : Telegram user ID (récupérer via @userinfobot)
- Valeur : UUID Supabase du profil (table `profiles`, colonne `id`)

---

## Variables d'environnement

| Variable | Requis | Description |
|----------|--------|-------------|
| `TELEGRAM_BOT_TOKEN` | Oui | Token du bot (@BotFather) |
| `TELEGRAM_CHANNELS` | Non | Canaux pour annonces |
| `TELEGRAM_API_ID` | Pour vidéo | my.telegram.org/apps |
| `TELEGRAM_API_HASH` | Pour vidéo | my.telegram.org/apps |
| `TELETHON_SESSION` | Pour vidéo | Généré à la 1ère connexion |
| `SUPABASE_URL` | Oui | URL du projet Supabase |
| `SUPABASE_SERVICE_KEY` | Oui | Clé service_role |
| `R2_ACCOUNT_ID` | Oui | Cloudflare account ID |
| `R2_ACCESS_KEY_ID` | Oui | R2 access key |
| `R2_SECRET_ACCESS_KEY` | Oui | R2 secret key |
| `R2_BUCKET_NAME` | Oui | Nom du bucket (live-chapter) |
| `R2_PUBLIC_URL` | Oui | URL publique du bucket |
| `API_PORT` | Non | Port FastAPI (défaut 8000) |
| `TMDB_API_KEY` | Non | Pour metadata films/séries |

---

## Endpoints API streaming

| Endpoint | Description |
|----------|-------------|
| `GET /stream/{video_id}` | Stream vidéo avec byte-range |
| `GET /videos` | Liste toutes les séries |
| `GET /videos/{series_id}/episodes` | Épisodes d'une série |
| `GET /health` | Statut du serveur |
