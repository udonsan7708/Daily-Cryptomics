"""Step 4 – Content Packaging.

Combines the AI-generated text summary with the image file path and
produces a ready-to-publish Twitter payload: tweet text + media path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


_MAX_TWEET_LENGTH = 280
_HEADER = "📰 Daily Cryptomics – {date}\n\n"
_FOOTER_TMPL = "\n\n{hashtags}"


@dataclass
class TweetPackage:
    """A fully assembled, publication-ready content unit."""

    tweet_text: str
    image_path: Optional[Path]
    date: str = field(default_factory=lambda: datetime.now(timezone.utc).strftime("%B %d, %Y"))
    hashtags: List[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return bool(self.tweet_text) and (self.image_path is None or self.image_path.exists())

    def __str__(self) -> str:
        return (
            f"TweetPackage(chars={len(self.tweet_text)}, "
            f"has_image={self.image_path is not None})"
        )


class ContentPackaging:
    """Assembles the final tweet text and image into a publication package."""

    def __init__(self, hashtags: List[str]) -> None:
        self._hashtags = hashtags

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def run(self, summary: str, image_path: Optional[Path]) -> TweetPackage:
        """Build a :class:`TweetPackage` from *summary* and *image_path*.

        The tweet text is constructed as:
          header (date line)
          + trimmed summary
          + footer (hashtags)

        It is automatically trimmed to fit inside the 280-character limit
        while preserving the header and footer.

        Args:
            summary:    Text summary from step 2.
            image_path: Path to the generated image from step 3 (may be None).

        Returns:
            A populated :class:`TweetPackage`.
        """
        date_str = datetime.now(timezone.utc).strftime("%B %d, %Y")
        header = _HEADER.format(date=date_str)
        footer = _FOOTER_TMPL.format(hashtags=" ".join(self._hashtags))

        body = self._fit_body(summary, header, footer)
        tweet_text = f"{header}{body}{footer}"

        return TweetPackage(
            tweet_text=tweet_text,
            image_path=image_path,
            date=date_str,
            hashtags=self._hashtags,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _fit_body(self, summary: str, header: str, footer: str) -> str:
        budget = _MAX_TWEET_LENGTH - len(header) - len(footer)
        if budget <= 0:
            return ""
        if len(summary) <= budget:
            return summary
        # Trim at the last sentence boundary that fits
        trimmed = summary[:budget - 1]
        last_dot = trimmed.rfind(".")
        if last_dot > budget // 2:
            trimmed = trimmed[: last_dot + 1]
        else:
            trimmed = trimmed.rstrip() + "…"
        return trimmed
