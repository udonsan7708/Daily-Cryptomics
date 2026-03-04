"""Tests for Step 4 – ContentPackaging."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.steps.content_packaging import ContentPackaging, TweetPackage, _MAX_TWEET_LENGTH


@pytest.fixture
def packaging():
    return ContentPackaging(hashtags=["#CryptoNews", "#DegenDaily", "#DailyCryptomics"])


@pytest.fixture
def sample_summary():
    return (
        "📈 BTC breaks $100k for the first time.\n"
        "🐋 Whale wallets accumulating ETH hard.\n"
        "💸 SEC approves spot ETH ETF unanimously.\n"
        "🔥 Meme coins up 500% across the board.\n"
        "🚀 Solana overtakes Ethereum in daily DEX volume.\n"
        "🔥 Degen Take: we're all gonna make it."
    )


class TestTweetPackage:
    def test_success_with_text_and_no_image(self):
        pkg = TweetPackage(tweet_text="hello", image_path=None)
        assert pkg.success is True

    def test_success_false_with_missing_image(self, tmp_path):
        pkg = TweetPackage(tweet_text="hello", image_path=tmp_path / "missing.png")
        assert pkg.success is False

    def test_success_true_with_existing_image(self, tmp_path):
        img = tmp_path / "img.png"
        img.write_bytes(b"data")
        pkg = TweetPackage(tweet_text="hello", image_path=img)
        assert pkg.success is True


class TestContentPackaging:
    def test_run_produces_tweet_under_280_chars(self, packaging, sample_summary):
        pkg = packaging.run(sample_summary, image_path=None)
        assert len(pkg.tweet_text) <= _MAX_TWEET_LENGTH

    def test_run_includes_hashtags(self, packaging, sample_summary):
        pkg = packaging.run(sample_summary, image_path=None)
        assert "#CryptoNews" in pkg.tweet_text
        assert "#DegenDaily" in pkg.tweet_text

    def test_run_includes_header_date(self, packaging, sample_summary):
        pkg = packaging.run(sample_summary, image_path=None)
        assert "Daily Cryptomics" in pkg.tweet_text

    def test_run_with_very_long_summary_still_under_limit(self, packaging):
        long_summary = "📈 Some very long crypto news sentence. " * 20
        pkg = packaging.run(long_summary, image_path=None)
        assert len(pkg.tweet_text) <= _MAX_TWEET_LENGTH

    def test_run_preserves_short_summary_intact(self, packaging):
        short = "📈 BTC up. 🔥 Degen Take: ape in."
        pkg = packaging.run(short, image_path=None)
        assert short in pkg.tweet_text

    def test_run_assigns_image_path(self, packaging, sample_summary, tmp_path):
        img = tmp_path / "img.png"
        img.write_bytes(b"data")
        pkg = packaging.run(sample_summary, image_path=img)
        assert pkg.image_path == img

    def test_fit_body_trims_at_sentence_boundary(self, packaging):
        # Create a body that is slightly too long
        header = "Daily Cryptomics – March 04, 2026\n\n"
        footer = "\n\n#CryptoNews"
        budget = _MAX_TWEET_LENGTH - len(header) - len(footer)
        long_body = ("This is sentence one. This is sentence two. " * 10)[:budget + 10]
        result = packaging._fit_body(long_body, header, footer)
        assert len(result) <= budget
