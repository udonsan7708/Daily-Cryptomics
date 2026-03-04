"""Tests for Step 1 – TweetAcquisition."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.steps.tweet_acquisition import AcquisitionResult, Tweet, TweetAcquisition
from src.utils.config import AgentConfig, TwitterConfig


@pytest.fixture
def twitter_cfg():
    return TwitterConfig(
        bearer_token="test_bearer",
        api_key="key",
        api_secret="secret",
        access_token="token",
        access_token_secret="token_secret",
    )


@pytest.fixture
def agent_cfg(tmp_path):
    cfg = AgentConfig()
    cfg.output_dir = tmp_path
    cfg.max_tweets_per_source = 5
    cfg.lookback_hours = 24
    return cfg


@pytest.fixture
def acquisition(twitter_cfg, agent_cfg):
    return TweetAcquisition(twitter_cfg, agent_cfg)


class TestTweetDataclass:
    def test_url_auto_generated(self):
        tw = Tweet(id="123", author_handle="degenuser", text="moon soon")
        assert tw.url == "https://twitter.com/degenuser/status/123"

    def test_url_not_overwritten_if_provided(self):
        tw = Tweet(id="123", author_handle="user", text="hi", url="https://custom.url")
        assert tw.url == "https://custom.url"


class TestAcquisitionResult:
    def test_success_false_when_no_tweets(self):
        result = AcquisitionResult()
        assert result.success is False

    def test_success_true_when_tweets_present(self):
        tw = Tweet(id="1", author_handle="a", text="b")
        result = AcquisitionResult(tweets=[tw])
        assert result.success is True

    def test_summary_format(self):
        result = AcquisitionResult(
            tweets=[Tweet(id="1", author_handle="a", text="b")],
            sources_queried=3,
            sources_failed=1,
            lookback_hours=24,
        )
        assert "1 tweet" in result.summary
        assert "2/3" in result.summary
        assert "24h" in result.summary


class TestTweetAcquisition:
    @patch("src.steps.tweet_acquisition.tweepy.Client")
    def test_run_returns_tweets_on_success(self, mock_client_cls, acquisition):
        client = MagicMock()
        mock_client_cls.return_value = client

        # Simulate get_user response
        user_data = MagicMock()
        user_data.id = "42"
        client.get_user.return_value = MagicMock(data=user_data)

        # Simulate get_users_tweets response
        tw_mock = MagicMock()
        tw_mock.id = "999"
        tw_mock.text = "BTC to the moon!"
        tw_mock.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        tw_mock.public_metrics = {"retweet_count": 5, "like_count": 20}
        client.get_users_tweets.return_value = MagicMock(data=[tw_mock])

        sources = [{"handle": "hiwhaledegen"}]
        result = acquisition.run(sources)

        assert result.success
        assert len(result.tweets) == 1
        assert result.tweets[0].text == "BTC to the moon!"
        assert result.tweets[0].like_count == 20

    @patch("src.steps.tweet_acquisition.tweepy.Client")
    def test_run_tracks_failed_sources(self, mock_client_cls, acquisition):
        client = MagicMock()
        mock_client_cls.return_value = client
        client.get_user.side_effect = Exception("rate limited")

        result = acquisition.run([{"handle": "failuser"}])

        assert result.sources_failed == 1
        assert result.success is False

    @patch("src.steps.tweet_acquisition.tweepy.Client")
    def test_run_skips_source_without_handle(self, mock_client_cls, acquisition):
        client = MagicMock()
        mock_client_cls.return_value = client

        result = acquisition.run([{"label": "no handle here"}])

        client.get_user.assert_not_called()
        assert result.sources_queried == 1

    @patch("src.steps.tweet_acquisition.tweepy.Client")
    def test_run_handles_empty_tweets_response(self, mock_client_cls, acquisition):
        client = MagicMock()
        mock_client_cls.return_value = client
        user_data = MagicMock()
        user_data.id = "1"
        client.get_user.return_value = MagicMock(data=user_data)
        client.get_users_tweets.return_value = MagicMock(data=None)

        result = acquisition.run([{"handle": "silent_whale"}])

        assert result.success is False
        assert result.tweets == []
