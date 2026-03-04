"""Step 5 – Twitter Publishing.

Uploads the image as a media attachment and posts the assembled tweet
to Twitter using the v1.1 (media upload) + v2 (tweet creation) APIs
via Tweepy.

Twitter API requirements for this step:
  - OAuth 1.0a credentials (api_key, api_secret, access_token, access_token_secret)
  - App must have "Read and Write" permissions
  - Media upload uses v1.1 endpoint; tweet creation uses v2 endpoint
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import tweepy

from src.steps.content_packaging import TweetPackage
from src.utils.config import TwitterConfig
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PublishingResult:
    """Outcome of the Twitter publishing step."""

    tweet_id: Optional[str] = None
    tweet_url: Optional[str] = None
    media_id: Optional[str] = None
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.tweet_id is not None

    @property
    def summary(self) -> str:
        if self.success:
            return f"Published → {self.tweet_url}"
        return f"Publishing failed: {self.error}"


class TwitterPublishing:
    """Posts a tweet with an optional image attachment."""

    def __init__(self, twitter_cfg: TwitterConfig) -> None:
        # v2 client for tweet creation
        self._v2 = tweepy.Client(
            consumer_key=twitter_cfg.api_key,
            consumer_secret=twitter_cfg.api_secret,
            access_token=twitter_cfg.access_token,
            access_token_secret=twitter_cfg.access_token_secret,
        )
        # v1.1 API for media upload (not yet available in tweepy v2 client)
        auth = tweepy.OAuth1UserHandler(
            consumer_key=twitter_cfg.api_key,
            consumer_secret=twitter_cfg.api_secret,
            access_token=twitter_cfg.access_token,
            access_token_secret=twitter_cfg.access_token_secret,
        )
        self._v1 = tweepy.API(auth)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def run(self, package: TweetPackage) -> PublishingResult:
        """Publish *package* to Twitter.

        Args:
            package: The :class:`TweetPackage` assembled in step 4.

        Returns:
            :class:`PublishingResult` with the live tweet URL on success.
        """
        try:
            media_id = self._upload_media(package.image_path)
            tweet_id = self._post_tweet(package.tweet_text, media_id)
            url = f"https://twitter.com/i/web/status/{tweet_id}"
            result = PublishingResult(tweet_id=tweet_id, tweet_url=url, media_id=media_id)
            logger.info(result.summary)
            return result
        except Exception as exc:
            logger.error("Failed to publish tweet: %s", exc, exc_info=True)
            return PublishingResult(error=str(exc))

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _upload_media(self, image_path: Optional[Path]) -> Optional[str]:
        if image_path is None or not image_path.exists():
            logger.warning("No image to upload.")
            return None
        media = self._v1.media_upload(filename=str(image_path))
        logger.info("Media uploaded (id=%s, size=%d bytes).", media.media_id_string, image_path.stat().st_size)
        return media.media_id_string

    def _post_tweet(self, text: str, media_id: Optional[str]) -> str:
        kwargs: dict = {"text": text}
        if media_id:
            kwargs["media"] = {"media_ids": [media_id]}
        response = self._v2.create_tweet(**kwargs)
        return str(response.data["id"])
