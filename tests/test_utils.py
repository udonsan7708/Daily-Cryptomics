"""Tests for utility modules (config, logger, file_manager)."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from src.utils.file_manager import ensure_output_dir, run_id, save_text


class TestFileManager:
    def test_ensure_output_dir_creates_dated_subdir(self, tmp_path):
        result = ensure_output_dir(tmp_path)
        assert result.is_dir()
        # Directory name should match YYYY-MM-DD pattern
        assert len(result.name) == 10
        assert result.name.count("-") == 2

    def test_save_text_writes_file(self, tmp_path):
        path = tmp_path / "sub" / "test.txt"
        returned = save_text("hello world", path)
        assert returned == path
        assert path.read_text() == "hello world"

    def test_run_id_is_unique(self):
        id1 = run_id()
        id2 = run_id()
        # Both should be non-empty strings
        assert id1 and id2

    def test_run_id_with_prefix(self):
        result = run_id(prefix="img_")
        assert result.startswith("img_")


class TestConfig:
    def test_config_raises_on_missing_env(self):
        from src.utils.config import Config

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(EnvironmentError):
                Config.from_env()

    def test_config_loads_from_env(self, tmp_path):
        from src.utils.config import Config

        # Write a minimal sources yaml
        sources_dir = tmp_path / "config"
        sources_dir.mkdir()
        sources_yaml = sources_dir / "sources.yaml"
        sources_yaml.write_text("sources: []\nhashtags: []\nimage_style: ''\n")

        env = {
            "TWITTER_BEARER_TOKEN": "b",
            "TWITTER_API_KEY": "k",
            "TWITTER_API_SECRET": "s",
            "TWITTER_ACCESS_TOKEN": "t",
            "TWITTER_ACCESS_TOKEN_SECRET": "ts",
            "ANTHROPIC_API_KEY": "ak",
            "GEMINI_API_KEY": "gk",
        }
        with patch.dict(os.environ, env, clear=True):
            with patch("src.utils.config.ROOT_DIR", tmp_path):
                cfg = Config.from_env()

        assert cfg.twitter.bearer_token == "b"
        assert cfg.ai.anthropic_api_key == "ak"
        assert cfg.agent.lookback_hours == 24


class TestLogger:
    def test_get_logger_returns_logger(self):
        from src.utils.logger import get_logger

        logger = get_logger("test.module")
        assert logger.name == "test.module"

    def test_get_logger_does_not_duplicate_handlers(self):
        from src.utils.logger import get_logger

        logger = get_logger("test.dedup")
        count_before = len(logger.handlers)
        get_logger("test.dedup")
        assert len(logger.handlers) == count_before
