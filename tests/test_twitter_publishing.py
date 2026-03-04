"""Tests for Step 5 – TwitterPublishing."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.steps.content_packaging import TweetPackage
from src.steps.twitter_publishing import PublishingResult, TwitterPublishing
from src.utils.config import TwitterConfig


@pytest.fixture
def twitter_cfg():
    return TwitterConfig(
        bearer_token="bearer",
        api_key="key",
        api_secret="secret",
        access_token="token",
        access_token_secret="token_secret",
    )


@pytest.fixture
def publishing(twitter_cfg):
    with (
        patch("src.steps.twitter_publishing.tweepy.Client"),
        patch("src.steps.twitter_publishing.tweepy.OAuth1UserHandler"),
        patch("src.steps.twitter_publishing.tweepy.API"),
    ):
        return TwitterPublishing(twitter_cfg)


@pytest.fixture
def sample_package(tmp_path):
    img = tmp_path / "img.png"
    img.write_bytes(b"fake png data")
    return TweetPackage(
        tweet_text="📰 Daily Cryptomics – March 04, 2026\n\n📈 BTC breaks ATH.",
        image_path=img,
    )


class TestPublishingResult:
    def test_success_false_when_no_tweet_id(self):
        result = PublishingResult()
        assert result.success is False

    def test_success_true_when_tweet_id_present(self):
        result = PublishingResult(tweet_id="12345")
        assert result.success is True

    def test_summary_on_success(self):
        result = PublishingResult(tweet_id="1", tweet_url="https://twitter.com/x/1")
        assert "https://twitter.com" in result.summary

    def test_summary_on_failure(self):
        result = PublishingResult(error="rate limit hit")
        assert "rate limit hit" in result.summary


class TestTwitterPublishing:
    def test_run_success(self, publishing, sample_package):
        media_mock = MagicMock()
        media_mock.media_id_string = "media_99"
        publishing._v1.media_upload.return_value = media_mock
        publishing._v2.create_tweet.return_value = MagicMock(data={"id": "tweet_42"})

        result = publishing.run(sample_package)

        assert result.success
        assert result.tweet_id == "tweet_42"
        assert result.media_id == "media_99"
        assert "tweet_42" in result.tweet_url

    def test_run_returns_failure_on_exception(self, publishing, sample_package):
        publishing._v1.media_upload.side_effect = Exception("upload failed")

        result = publishing.run(sample_package)

        assert result.success is False
        assert "upload failed" in result.error

    def test_upload_media_skipped_when_no_image(self, publishing):
        package = TweetPackage(tweet_text="text only", image_path=None)
        publishing._v2.create_tweet.return_value = MagicMock(data={"id": "99"})

        result = publishing.run(package)

        publishing._v1.media_upload.assert_not_called()
        assert result.success

    def test_post_tweet_passes_media_id(self, publishing):
        publishing._post_tweet("hello", "media_id_123")
        call_kwargs = publishing._v2.create_tweet.call_args[1]
        assert call_kwargs["media"]["media_ids"] == ["media_id_123"]

    def test_post_tweet_without_media_id(self, publishing):
        publishing._v2.create_tweet.return_value = MagicMock(data={"id": "1"})
        publishing._post_tweet("hello world", None)
        call_kwargs = publishing._v2.create_tweet.call_args[1]
        assert "media" not in call_kwargs
