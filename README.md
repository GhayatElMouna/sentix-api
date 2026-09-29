# SentixAPI

REST API and web interface for multilingual sentiment analysis of social-media comments, grouped by post URL.

## Overview

Sentix classifies a comment as **positive**, **neutral**, or **negative** using a pretrained BERT model (`nlptown/bert-base-multilingual-uncased-sentiment`). The web UI associates each analysis with a post link, increments per-post counters, and avoids counting the same comment twice.

The application does **not** fetch comments from Instagram, TikTok, or Facebook. The user pastes a post URL and a comment; the URL is used as a storage key.

## Features

- Single-comment classification (`POST /predict`)
- Batch classification with counts and percentages (`POST /predict/batch`)
- Per-post persistence: positive / negative / neutral / total counters and comment history
- Duplicate detection (normalized comment text) so the same comment is not counted twice for the same URL
- Static frontend served at `/`: post URL, one comment, analysis result, counters, history
- Health check (`GET /health`)
- CLI demo script (`predict.py`) independent of the HTTP server

## Project Structure

```
sentix-api/
├── main.py              # FastAPI app, model loading, HTTP routes, static files
├── posts_store.py       # JSON persistence, URL/comment normalization, counters
├── predict.py           # Standalone CLI demo of the same Hugging Face model
├── requirements.txt     # Python dependencies with pinned versions
├── .gitignore           # venv, caches, .env, models, data/
└── static/
    ├── index.html       # Sentix UI
    ├── styles.css       # Layout and theme
    └── app.js           # Calls GET /posts and POST /posts/analyze
```

`data/posts.json` is created at runtime (directory `data/` is gitignored).

## Technologies Used

| Area | From the repository |
| --- | --- |
| API | FastAPI, Starlette, Uvicorn, Pydantic |
| ML | PyTorch, Hugging Face Transformers, Tokenizers, Hugging Face Hub |
| Model | `nlptown/bert-base-multilingual-uncased-sentiment` |
| Frontend | HTML, CSS, vanilla JavaScript |
| Storage | JSON file (`data/posts.json`), `threading.Lock` |

## Architecture / How It Works

1. The BERT tokenizer and sequence-classification model are loaded **on first prediction** (`get_model()` in `main.py`), not at process start.
2. Model class indices `0–4` (1–5 stars) are mapped to `negative` (0–1), `neutral` (2), `positive` (3–4).
3. Inference uses `torch.no_grad()`, truncation/padding, `max_length=512`. Texts longer than 2000 characters are rejected (or skipped in batch).
4. **Web flow:** the browser sends `{ url, text }` to `POST /posts/analyze`. The server normalizes the URL, looks up a matching comment key, classifies if new, then updates `data/posts.json`.
5. **Reload:** changing or leaving the post URL field calls `GET /posts?url=…` and redraws counters and history if that post already exists.

`predict.py` loads the same model and prints a class index and probabilities for a hardcoded English sentence. It is not used by FastAPI.

## Installation

Requires Python with `pip`. A specific Python version is not declared in the repository.

```bash
python -m venv venv
```

Activate the virtual environment (`venv\Scripts\activate` on Windows, `source venv/bin/activate` on Unix).

```bash
pip install -r requirements.txt
```

The first inference downloads the Hugging Face model (on the order of hundreds of megabytes). Network access to the Hugging Face Hub is required for that download.

## Configuration

No environment variables are read in the application code.

`.gitignore` lists `.env`, but nothing in the project loads it. A Hugging Face token is **not** required in code; unauthenticated Hub downloads may be rate-limited.

Constants in `main.py`:

- `MODEL_NAME`: `nlptown/bert-base-multilingual-uncased-sentiment`
- `MAX_TEXT_LEN`: 2000
- `MAX_BATCH`: 200

Storage path in `posts_store.py`: `data/posts.json` (relative to the project root).

CORS is enabled for all origins (`allow_origins=["*"]`).

## Usage

Start the API and UI:

```bash
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/).

1. Enter a post URL.
2. Enter one comment.
3. Click **Lancer l’analyse**.
4. The sentiment badge appears only after the response. Counters (Positive, Negative, Total) and the history list appear once the post has at least one stored comment.

FastAPI also serves interactive OpenAPI docs at `/docs` (framework default).

CLI demo (loads the model immediately):

```bash
python predict.py
```

## API

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/` | Serves `static/index.html`, or `{"message": "SentixAPI is running"}` if the file is missing |
| `GET` | `/health` | `{"message": "SentixAPI is running"}` |
| `POST` | `/predict` | Body: `{ "text": "..." }`. Returns `text`, `sentiment`, `confidence`, `star_rating` (1–5) |
| `POST` | `/predict/batch` | Body: `{ "texts": ["..."], "platform": null }`. `platform` is optional and only echoed. Returns `total`, `skipped`, `counts`, `percentages`, `results`. Over-long items are `skipped` |
| `GET` | `/posts` | Query: `url`. Returns post record (`positiveCount`, `negativeCount`, `neutralCount`, `total`, `comments`, `exists`) |
| `POST` | `/posts/analyze` | Body: `{ "url": "...", "text": "..." }`. Returns `duplicate`, `result`, `post` |

Static assets: `GET /static/...` (CSS and JS). `index.html` is served at `/`.

The UI uses `/posts` and `/posts/analyze` only. `/predict` and `/predict/batch` are available for direct API use.

## Data / Storage

Posts are stored in `data/posts.json`, keyed by a normalized URL (scheme/host lowercased, optional `https://` if missing, trailing slash stripped from the path).

Each post keeps:

- `positiveCount`, `negativeCount`, `neutralCount`, `total`
- `comments`: `key`, `text`, `sentiment`, `confidence`, `star_rating`

The comment `key` is the text trimmed, case-folded, and collapsed whitespace. Writes use a process lock and a temporary file then replace.

This is local file storage, not a database. There is no authentication.

## Frontend

`static/index.html` + `static/styles.css` + `static/app.js`. No frontend build step or npm package.

- `GET /posts?url=…` on URL `change` / `blur`
- `POST /posts/analyze` with JSON `{ url, text }`
- Result, counters, and history are injected into empty containers (`#latest`, `#counters`, `#history`) so unused UI is not shown at load

## Screenshots

Add screenshots of the form, a completed analysis (badge + counters), and the comment history if you publish the project.

## Future Improvements

These are **not** implemented:

- Fetching comments from social-network APIs
- Authentication or multi-user access
- A database instead of a JSON file
- Tests and CI
- Hugging Face token configuration in the app
- Using the unused `platform` field on batch requests in the UI
