"""Step 1 – Tweet Acquisition.

Fetches recent tweets from a list of crypto Twitter handles using the
Twitter v2 API (read-only bearer token).  Returns a flat list of
:class:`Tweet` dataclasses ready for the summarisation step.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import tweepy

from src.utils.config import AgentConfig, TwitterConfig
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Tweet:
    """Lightweight representation of a single tweet."""

    id: str
    author_handle: str
    text: str
    created_at: Optional[datetime] = None
    url: str = ""
    retweet_count: int = 0
    like_count: int = 0

    def __post_init__(self) -> None:
        if not self.url and self.id:
            self.url = f"https://twitter.com/{self.author_handle}/status/{self.id}"


@dataclass
class AcquisitionResult:
    """Outcome of the tweet acquisition step."""

    tweets: List[Tweet] = field(default_factory=list)
    sources_queried: int = 0
    sources_failed: int = 0
    lookback_hours: int = 24

    @property
    def success(self) -> bool:
        return bool(self.tweets)

    @property
    def summary(self) -> str:
        return (
            f"Fetched {len(self.tweets)} tweets from "
            f"{self.sources_queried - self.sources_failed}/"
            f"{self.sources_queried} sources "
            f"(last {self.lookback_hours}h)"
        )


class TweetAcquisition:
    """Queries the Twitter v2 API and returns recent crypto tweets."""

    def __init__(self, twitter_cfg: TwitterConfig, agent_cfg: AgentConfig) -> None:
        self._bearer_token = twitter_cfg.bearer_token
        self._max_per_source = agent_cfg.max_tweets_per_source
        self._lookback_hours = agent_cfg.lookback_hours
        self._client: Optional[tweepy.Client] = None

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def run(self, sources: list[dict]) -> AcquisitionResult:
        """Fetch tweets for every handle listed in *sources*.

        Args:
            sources: List of dicts with at least a ``handle`` key.

        Returns:
            :class:`AcquisitionResult` populated with collected tweets.
        """
        result = AcquisitionResult(
            lookback_hours=self._lookback_hours,
            sources_queried=len(sources),
        )

        client = self._get_client()
        since = datetime.now(timezone.utc) - timedelta(hours=self._lookback_hours)

        for source in sources:
            handle = source.get("handle", "")
            if not handle:
                continue
            try:
                tweets = self._fetch_user_tweets(client, handle, since)
                result.tweets.extend(tweets)
                logger.info("  @%-20s → %d tweet(s)", handle, len(tweets))
            except Exception as exc:
                result.sources_failed += 1
                logger.warning("  @%-20s → failed: %s", handle, exc)

        logger.info(result.summary)
        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_client(self) -> tweepy.Client:
        if self._client is None:
            self._client = tweepy.Client(
                bearer_token=self._bearer_token,
                wait_on_rate_limit=True,
            )
        return self._client

    def _fetch_user_tweets(
        self,
        client: tweepy.Client,
        handle: str,
        since: datetime,
    ) -> list[Tweet]:
        user_resp = client.get_user(username=handle, user_fields=["id"])
        if not user_resp.data:
            raise ValueError(f"User not found: @{handle}")

        user_id = user_resp.data.id
        resp = client.get_users_tweets(
            id=user_id,
            max_results=min(self._max_per_source, 100),
            start_time=since,
            tweet_fields=["created_at", "public_metrics", "text"],
            exclude=["retweets", "replies"],
        )

        if not resp.data:
            return []

        tweets: list[Tweet] = []
        for tw in resp.data:
            metrics = tw.public_metrics or {}
            tweets.append(
                Tweet(
                    id=str(tw.id),
                    author_handle=handle,
                    text=tw.text,
                    created_at=tw.created_at,
                    retweet_count=metrics.get("retweet_count", 0),
                    like_count=metrics.get("like_count", 0),
                )
            )
        return tweets
