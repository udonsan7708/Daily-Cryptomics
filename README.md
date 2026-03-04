# Daily Cryptomics – OpenClaw Agent

> Automated daily crypto news digest: tweets in, comics image + tweet out.

## Overview

The **Daily Cryptomics** agent is a five-step automated pipeline that runs on a
cron schedule and produces an eye-catching daily crypto briefing on Twitter.

```
┌──────────────────────────────────────────────────────────────┐
│                  Daily Cryptomics Pipeline                    │
│                                                              │
│  [1] Tweet Acquisition                                       │
│      tweepy v2 API  →  List[Tweet]                           │
│           │                                                  │
│  [2] AI Summarization                                        │
│      Claude (Anthropic)  →  5-bullet briefing               │
│           │                                                  │
│  [3] Image Creation                                          │
│      Gemini (nano-banana-pro)  →  PNG file                   │
│           │                                                  │
│  [4] Content Packaging                                       │
│      text + image  →  TweetPackage (≤280 chars)              │
│           │                                                  │
│  [5] Twitter Publishing                                      │
│      v1.1 media upload + v2 create_tweet  →  live URL       │
└──────────────────────────────────────────────────────────────┘
```

## Project Structure

```
Daily-Cryptomics/
├── main.py                        # Entry point (cron target)
├── requirements.txt
├── pytest.ini
├── .env.example                   # All required env variables
├── config/
│   └── sources.yaml               # Twitter handles, hashtags, style
├── src/
│   ├── agents/
│   │   └── daily_cryptomics.py    # Pipeline orchestrator
│   ├── steps/
│   │   ├── tweet_acquisition.py   # Step 1 – fetch tweets
│   │   ├── ai_summarization.py    # Step 2 – Claude summary
│   │   ├── image_creation.py      # Step 3 – Gemini image
│   │   ├── content_packaging.py   # Step 4 – assemble payload
│   │   └── twitter_publishing.py  # Step 5 – post to Twitter
│   └── utils/
│       ├── config.py              # Typed config from env + YAML
│       ├── logger.py              # Structured stdout logger
│       └── file_manager.py        # Dated output dir helpers
└── tests/
    ├── test_tweet_acquisition.py
    ├── test_ai_summarization.py
    ├── test_image_creation.py
    ├── test_content_packaging.py
    ├── test_twitter_publishing.py
    ├── test_daily_cryptomics_agent.py
    └── test_utils.py
```

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
# Fill in all values in .env
```

| Variable | Description |
|---|---|
| `TWITTER_BEARER_TOKEN` | Read-only bearer token (tweet search) |
| `TWITTER_API_KEY` | OAuth 1.0a consumer key (publishing) |
| `TWITTER_API_SECRET` | OAuth 1.0a consumer secret |
| `TWITTER_ACCESS_TOKEN` | OAuth 1.0a access token |
| `TWITTER_ACCESS_TOKEN_SECRET` | OAuth 1.0a access token secret |
| `ANTHROPIC_API_KEY` | Claude API key |
| `GEMINI_API_KEY` | Google Gemini API key |
| `LOOKBACK_HOURS` | Hours of tweets to pull (default: `24`) |
| `MAX_TWEETS_PER_SOURCE` | Max tweets per handle (default: `10`) |
| `OUTPUT_DIR` | Where generated images are saved (default: `output/`) |
| `LOG_LEVEL` | `DEBUG` / `INFO` / `WARNING` (default: `INFO`) |

> **Twitter API note**: your app needs **Read and Write** permissions and a
> user-level OAuth 1.0a token to publish tweets with media.

### 3. Customise sources

Edit `config/sources.yaml` to add/remove Twitter handles and hashtags.

## Running

```bash
# Single run
python main.py

# Cron (every day at 09:00 UTC)
0 9 * * * /path/to/venv/bin/python /path/to/Daily-Cryptomics/main.py
```

Exit codes: `0` = success, `1` = pipeline failure, `2` = config error.

## Running tests

```bash
pytest
```

## Pipeline Steps

### Step 1 – Tweet Acquisition (`TweetAcquisition`)

Queries the Twitter v2 API using a bearer token.  Iterates over handles from
`sources.yaml`, fetches up to `MAX_TWEETS_PER_SOURCE` original tweets (no
retweets, no replies) within the `LOOKBACK_HOURS` window.  Each handle failure
is logged and counted but does not abort the run.

### Step 2 – AI Summarization (`AISummarization`)

Passes all collected tweets to Claude with a strict prompt that produces
exactly **5 emoji bullet points** + a **Degen Take** closing sentence.
Token usage is tracked in `SummarizationResult`.

### Step 3 – Image Creation (`ImageCreation`)

Sends a rich comics-style prompt (built from the summary) to the Gemini image
generation API (`nano-banana-pro`).  The PNG is saved to a dated sub-directory
under `OUTPUT_DIR` (e.g. `output/2026-03-04/daily_cryptomics_20260304_090015.png`).

### Step 4 – Content Packaging (`ContentPackaging`)

Assembles the final tweet text:
```
📰 Daily Cryptomics – March 04, 2026

<summary trimmed to fit>

#CryptoNews #DegenDaily #DailyCryptomics
```
Automatically trims the body at a sentence boundary to stay within 280 characters.

### Step 5 – Twitter Publishing (`TwitterPublishing`)

1. Uploads the PNG via the Twitter v1.1 media upload endpoint.
2. Creates the tweet (with `media_ids`) via the Twitter v2 `create_tweet` API.
3. Returns the live tweet URL on success.

## Architecture Decisions

- **Pure dataclass results**: every step returns a typed result object with a
  `success` bool; no exceptions propagate across step boundaries.
- **Early abort**: the orchestrator checks `result.success` after each step and
  stops cleanly with a descriptive `RunReport`.
- **Dependency injection**: all external clients are constructed in the agent
  from a single `Config` object, making each step trivially mockable in tests.
- **Immutable config**: `Config.from_env()` is called once at startup; steps
  never read `os.environ` directly.
