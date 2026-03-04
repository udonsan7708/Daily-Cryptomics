"""Tests for Step 3 – ImageCreation."""

from __future__ import annotations

import base64
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.steps.image_creation import ImageCreation, ImageCreationResult
from src.utils.config import AIConfig, AgentConfig


@pytest.fixture
def ai_cfg():
    return AIConfig(anthropic_api_key="key", gemini_api_key="gemini_key")


@pytest.fixture
def agent_cfg(tmp_path):
    cfg = AgentConfig()
    cfg.output_dir = tmp_path
    return cfg


@pytest.fixture
def image_creation(ai_cfg, agent_cfg):
    with patch("src.steps.image_creation.genai.configure"):
        return ImageCreation(ai_cfg, agent_cfg)


_FAKE_PNG = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64).decode()


class TestImageCreationResult:
    def test_success_false_when_no_path(self):
        result = ImageCreationResult()
        assert result.success is False

    def test_success_false_when_path_does_not_exist(self, tmp_path):
        result = ImageCreationResult(image_path=tmp_path / "ghost.png")
        assert result.success is False

    def test_success_true_when_file_exists(self, tmp_path):
        p = tmp_path / "img.png"
        p.write_bytes(b"data")
        result = ImageCreationResult(image_path=p)
        assert result.success is True


class TestImageCreation:
    @patch("src.steps.image_creation.genai.GenerativeModel")
    def test_run_saves_image_to_disk(self, mock_model_cls, image_creation):
        model = MagicMock()
        mock_model_cls.return_value = model

        part = MagicMock()
        part.inline_data.mime_type = "image/png"
        part.inline_data.data = _FAKE_PNG

        candidate = MagicMock()
        candidate.content.parts = [part]
        model.generate_content.return_value = MagicMock(candidates=[candidate])

        result = image_creation.run("BTC to 100k, ETH ETF approved")

        assert result.success
        assert result.image_path.suffix == ".png"
        assert result.image_path.exists()

    @patch("src.steps.image_creation.genai.GenerativeModel")
    def test_run_raises_when_no_image_part(self, mock_model_cls, image_creation):
        model = MagicMock()
        mock_model_cls.return_value = model

        part = MagicMock()
        part.inline_data = None  # text-only response
        candidate = MagicMock()
        candidate.content.parts = [part]
        model.generate_content.return_value = MagicMock(candidates=[candidate])

        with pytest.raises(RuntimeError, match="no image data"):
            image_creation._generate_image("some prompt")

    @patch("src.steps.image_creation.genai.GenerativeModel")
    def test_build_prompt_includes_summary(self, _mock, image_creation):
        prompt = image_creation._build_prompt("ETH flippening happening", "")
        assert "ETH flippening" in prompt
        assert "Daily Cryptomics" in prompt

    @patch("src.steps.image_creation.genai.GenerativeModel")
    def test_build_prompt_appends_extra_style(self, _mock, image_creation):
        prompt = image_creation._build_prompt("summary", "neon cyberpunk vibes")
        assert "neon cyberpunk vibes" in prompt
