"""Step 3 – Image Creation (nano-banana-pro / Gemini).

Takes the text summary from step 2 and generates a dynamic comics-style
image via the Google Gemini image generation API, then saves it to disk.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import google.generativeai as genai
from google.generativeai import types as genai_types

from src.utils.config import AIConfig, AgentConfig
from src.utils.file_manager import ensure_output_dir, run_id
from src.utils.logger import get_logger

logger = get_logger(__name__)

_IMAGE_PROMPT_TEMPLATE = """\
Create a vibrant, dynamic comics/cartoon-style illustration for a daily crypto
news digest called "Daily Cryptomics".

Style: thick outlines, bold colors, dynamic panel layout, speech bubbles,
superhero/action aesthetic. Think Marvel meets Wall Street Bets.

Today's crypto headlines to illustrate:
{summary}

Include: "DAILY CRYPTOMICS" as a bold banner title, today's date
sub-title, and energetic background elements (rocket ships, moon,
charts going up). Keep it fun and eye-catching.
"""


@dataclass
class ImageCreationResult:
    """Outcome of the image creation step."""

    image_path: Optional[Path] = None
    prompt_used: str = ""
    model_used: str = ""

    @property
    def success(self) -> bool:
        return self.image_path is not None and self.image_path.exists()


class ImageCreation:
    """Generates a comics-style image using Google Gemini."""

    def __init__(self, ai_cfg: AIConfig, agent_cfg: AgentConfig) -> None:
        genai.configure(api_key=ai_cfg.gemini_api_key)
        self._model_name = ai_cfg.gemini_model
        self._output_dir = agent_cfg.output_dir

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def run(self, summary: str, image_style: str = "") -> ImageCreationResult:
        """Generate an image from *summary* and save it to disk.

        Args:
            summary:     The text summary produced by step 2.
            image_style: Optional additional style instructions from sources.yaml.

        Returns:
            :class:`ImageCreationResult` with the saved file path.
        """
        prompt = self._build_prompt(summary, image_style)
        logger.info("Requesting image generation from %s…", self._model_name)

        image_data = self._generate_image(prompt)
        output_path = self._save_image(image_data)

        result = ImageCreationResult(
            image_path=output_path,
            prompt_used=prompt,
            model_used=self._model_name,
        )
        logger.info("Image saved → %s", output_path)
        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_prompt(self, summary: str, extra_style: str) -> str:
        base = _IMAGE_PROMPT_TEMPLATE.format(summary=summary)
        if extra_style:
            base += f"\n\nAdditional style notes: {extra_style}"
        return base

    def _generate_image(self, prompt: str) -> bytes:
        model = genai.GenerativeModel(self._model_name)
        response = model.generate_content(
            prompt,
            generation_config=genai_types.GenerationConfig(
                response_modalities=["image", "text"],
            ),
        )
        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                return base64.b64decode(part.inline_data.data)
        raise RuntimeError("Gemini returned no image data in the response.")

    def _save_image(self, data: bytes) -> Path:
        out_dir = ensure_output_dir(self._output_dir)
        filename = f"daily_cryptomics_{run_id()}.png"
        image_path = out_dir / filename
        image_path.write_bytes(data)
        return image_path
