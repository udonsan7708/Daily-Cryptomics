"""Tests for Step 2 – AISummarization."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.steps.ai_summarization import AISummarization, SummarizationResult
from src.steps.tweet_acquisition import Tweet
from src.utils.config import AIConfig


@pytest.fixture
def ai_cfg():
    return AIConfig(anthropic_api_key="test_key", gemini_api_key="gemini_key")


@pytest.fixture
def summarization(ai_cfg):
    with patch("src.steps.ai_summarization.anthropic.Anthropic"):
        return AISummarization(ai_cfg)


@pytest.fixture
def sample_tweets():
    return [
        Tweet(
            id="1",
            author_handle="hiwhaledegen",
            text="BTC breaking ATH again, up 15% in 24h 🚀",
            created_at=datetime(2024, 3, 1, 12, 0, tzinfo=timezone.utc),
        ),
        Tweet(
            id="2",
            author_handle="DegenerateNews",
            text="ETH ETFs approved, institutions flooding in",
            created_at=datetime(2024, 3, 1, 11, 0, tzinfo=timezone.utc),
        ),
    ]


class TestSummarizationResult:
    def test_success_false_when_empty_summary(self):
        result = SummarizationResult()
        assert result.success is False

    def test_success_true_when_summary_present(self):
        result = SummarizationResult(summary="📈 BTC pumping hard.")
        assert result.success is True


class TestAISummarization:
    def test_run_returns_summary(self, summarization, sample_tweets):
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="📈 BTC ATH. 🔥 Degen Take: ape in.")]
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50

        summarization._client.messages.create.return_value = mock_response

        result = summarization.run(sample_tweets)

        assert result.success
        assert "BTC" in result.summary
        assert result.input_tokens == 100
        assert result.output_tokens == 50
        assert result.tweet_count == 2

    def test_run_with_empty_tweets_returns_failure(self, summarization):
        result = summarization.run([])
        assert result.success is False
        assert result.tweet_count == 0
        summarization._client.messages.create.assert_not_called()

    def test_format_tweets_includes_handle_and_text(self, summarization, sample_tweets):
        formatted = summarization._format_tweets(sample_tweets)
        assert "@hiwhaledegen" in formatted
        assert "BTC breaking ATH" in formatted
        assert "@DegenerateNews" in formatted

    def test_format_tweets_handles_no_created_at(self, summarization):
        tweets = [Tweet(id="1", author_handle="anon", text="gm")]
        formatted = summarization._format_tweets(tweets)
        assert "n/a" in formatted

    def test_run_passes_lookback_hours_in_prompt(self, summarization, sample_tweets):
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Summary here.")]
        mock_response.usage.input_tokens = 50
        mock_response.usage.output_tokens = 20
        summarization._client.messages.create.return_value = mock_response

        summarization.run(sample_tweets, lookback_hours=48)

        call_kwargs = summarization._client.messages.create.call_args
        user_msg = call_kwargs[1]["messages"][0]["content"]
        assert "48" in user_msg
