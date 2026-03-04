"""Integration-style tests for the DailyCryptomicsAgent orchestrator."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.agents.daily_cryptomics import DailyCryptomicsAgent, RunReport
from src.steps.ai_summarization import SummarizationResult
from src.steps.content_packaging import TweetPackage
from src.steps.image_creation import ImageCreationResult
from src.steps.tweet_acquisition import AcquisitionResult, Tweet
from src.steps.twitter_publishing import PublishingResult
from src.utils.config import AgentConfig, AIConfig, Config, TwitterConfig


@pytest.fixture
def mock_config(tmp_path):
    twitter = TwitterConfig(
        bearer_token="b",
        api_key="k",
        api_secret="s",
        access_token="at",
        access_token_secret="ats",
    )
    ai = AIConfig(anthropic_api_key="ak", gemini_api_key="gk")
    agent = AgentConfig(output_dir=tmp_path)
    sources = {
        "sources": [{"handle": "hiwhaledegen"}],
        "hashtags": ["#CryptoNews"],
        "image_style": "comics",
    }
    return Config(twitter=twitter, ai=ai, agent=agent, sources=sources)


@pytest.fixture
def agent(mock_config):
    with (
        patch("src.agents.daily_cryptomics.TweetAcquisition"),
        patch("src.agents.daily_cryptomics.AISummarization"),
        patch("src.agents.daily_cryptomics.ImageCreation"),
        patch("src.agents.daily_cryptomics.ContentPackaging"),
        patch("src.agents.daily_cryptomics.TwitterPublishing"),
    ):
        return DailyCryptomicsAgent(mock_config)


@pytest.fixture
def sample_tweet():
    return Tweet(id="1", author_handle="hiwhaledegen", text="BTC moon")


@pytest.fixture
def sample_image(tmp_path):
    img = tmp_path / "img.png"
    img.write_bytes(b"data")
    return img


def _wire_success(agent, sample_tweet, sample_image):
    agent._acquisition.run.return_value = AcquisitionResult(
        tweets=[sample_tweet], sources_queried=1
    )
    agent._summarization.run.return_value = SummarizationResult(
        summary="📈 BTC ATH.", output_tokens=30
    )
    agent._image_creation.run.return_value = ImageCreationResult(image_path=sample_image)
    agent._packaging.run.return_value = TweetPackage(
        tweet_text="Daily Cryptomics…", image_path=sample_image
    )
    agent._publishing.run.return_value = PublishingResult(
        tweet_id="999", tweet_url="https://twitter.com/i/web/status/999"
    )


class TestDailyCryptomicsAgent:
    def test_full_pipeline_success(self, agent, sample_tweet, sample_image):
        _wire_success(agent, sample_tweet, sample_image)
        report = agent.run()
        assert report.success

    def test_aborts_when_no_tweets(self, agent):
        agent._acquisition.run.return_value = AcquisitionResult(tweets=[])
        report = agent.run()
        assert not report.success
        assert report.aborted_at == "tweet_acquisition"

    def test_aborts_when_summary_empty(self, agent, sample_tweet):
        agent._acquisition.run.return_value = AcquisitionResult(tweets=[sample_tweet])
        agent._summarization.run.return_value = SummarizationResult(summary="")
        report = agent.run()
        assert report.aborted_at == "ai_summarization"

    def test_aborts_when_image_missing(self, agent, sample_tweet, tmp_path):
        agent._acquisition.run.return_value = AcquisitionResult(tweets=[sample_tweet])
        agent._summarization.run.return_value = SummarizationResult(summary="📈 Good news.")
        agent._image_creation.run.return_value = ImageCreationResult(
            image_path=tmp_path / "missing.png"  # does not exist
        )
        report = agent.run()
        assert report.aborted_at == "image_creation"

    def test_aborts_when_package_fails(self, agent, sample_tweet, tmp_path):
        agent._acquisition.run.return_value = AcquisitionResult(tweets=[sample_tweet])
        agent._summarization.run.return_value = SummarizationResult(summary="📈 News.")
        img = tmp_path / "img.png"
        img.write_bytes(b"data")
        agent._image_creation.run.return_value = ImageCreationResult(image_path=img)
        # tweet_text empty → success=False
        agent._packaging.run.return_value = TweetPackage(tweet_text="", image_path=None)
        report = agent.run()
        assert report.aborted_at == "content_packaging"

    def test_run_report_failure_when_publishing_fails(self, agent, sample_tweet, sample_image):
        _wire_success(agent, sample_tweet, sample_image)
        agent._publishing.run.return_value = PublishingResult(error="network error")
        report = agent.run()
        assert not report.success
        assert report.publishing is not None
