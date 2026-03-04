"""Configuration management for the Daily Cryptomics agent."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parents[2]


@dataclass
class TwitterConfig:
    bearer_token: str
    api_key: str
    api_secret: str
    access_token: str
    access_token_secret: str


@dataclass
class AIConfig:
    anthropic_api_key: str
    gemini_api_key: str
    claude_model: str = "claude-sonnet-4-6"
    gemini_model: str = "gemini-2.0-flash-exp"


@dataclass
class AgentConfig:
    lookback_hours: int = 24
    max_tweets_per_source: int = 10
    output_dir: Path = field(default_factory=lambda: ROOT_DIR / "output")
    log_level: str = "INFO"
    sources_file: Path = field(default_factory=lambda: ROOT_DIR / "config" / "sources.yaml")


@dataclass
class Config:
    twitter: TwitterConfig
    ai: AIConfig
    agent: AgentConfig
    sources: dict

    @classmethod
    def from_env(cls) -> "Config":
        twitter = TwitterConfig(
            bearer_token=_require("TWITTER_BEARER_TOKEN"),
            api_key=_require("TWITTER_API_KEY"),
            api_secret=_require("TWITTER_API_SECRET"),
            access_token=_require("TWITTER_ACCESS_TOKEN"),
            access_token_secret=_require("TWITTER_ACCESS_TOKEN_SECRET"),
        )
        ai = AIConfig(
            anthropic_api_key=_require("ANTHROPIC_API_KEY"),
            gemini_api_key=_require("GEMINI_API_KEY"),
        )
        agent = AgentConfig(
            lookback_hours=int(os.getenv("LOOKBACK_HOURS", "24")),
            max_tweets_per_source=int(os.getenv("MAX_TWEETS_PER_SOURCE", "10")),
            output_dir=Path(os.getenv("OUTPUT_DIR", str(ROOT_DIR / "output"))),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )
        sources = _load_sources(agent.sources_file)
        return cls(twitter=twitter, ai=ai, agent=agent, sources=sources)


def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise EnvironmentError(f"Missing required environment variable: {key}")
    return value


def _load_sources(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)
