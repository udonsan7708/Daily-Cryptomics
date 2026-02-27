"""Step 2 – AI Summarization.

Sends the collected tweets to Claude (Anthropic) and returns a
concise, structured summary of the day's top crypto news.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import anthropic

from src.steps.tweet_acquisition import Tweet
from src.utils.config import AIConfig
from src.utils.logger import get_logger

logger = get_logger(__name__)

_SYSTEM_PROMPT = """\
You are Daily Cryptomics, an expert crypto analyst and engaging storyteller.
Your job is to read a batch of raw crypto tweets and produce a sharp, concise
daily briefing that a degen trader will actually read in full.

Rules:
- Write in English.
- Produce exactly 5 bullet points, each starting with a relevant emoji.
- Each bullet should be one punchy sentence (max 30 words).
- End with one "🔥 Degen Take" sentence capturing the overall mood.
- Do NOT include links, usernames, or hashtags in the output.
- Tone: informed, direct, slightly irreverent — like a Wall Street Bets post
  written by a crypto native.
"""

_USER_TEMPLATE = """\
Here are today's crypto tweets (last {hours}h). Summarise them:

{raw_tweets}
"""


@dataclass
class SummarizationResult:
    """Outcome of the AI summarisation step."""

    summary: str = ""
    model_used: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    tweet_count: int = 0

    @property
    def success(self) -> bool:
        return bool(self.summary)


class AISummarization:
    """Summarises raw tweets using the Anthropic Claude API."""

    def __init__(self, ai_cfg: AIConfig) -> None:
        self._client = anthropic.Anthropic(api_key=ai_cfg.anthropic_api_key)
        self._model = ai_cfg.claude_model

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def run(self, tweets: List[Tweet], lookback_hours: int = 24) -> SummarizationResult:
        """Generate a news summary from *tweets*.

        Args:
            tweets:         List of :class:`Tweet` objects from step 1.
            lookback_hours: Time window label used in the prompt.

        Returns:
            :class:`SummarizationResult` with the generated summary text.
        """
        if not tweets:
            logger.warning("No tweets to summarise.")
            return SummarizationResult(tweet_count=0)

        raw = self._format_tweets(tweets)
        user_msg = _USER_TEMPLATE.format(hours=lookback_hours, raw_tweets=raw)

        logger.info("Sending %d tweets to %s for summarisation…", len(tweets), self._model)

        response = self._client.messages.create(
            model=self._model,
            max_tokens=512,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )

        summary = response.content[0].text.strip()
        result = SummarizationResult(
            summary=summary,
            model_used=self._model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            tweet_count=len(tweets),
        )
        logger.info(
            "Summary generated (%d in / %d out tokens).",
            result.input_tokens,
            result.output_tokens,
        )
        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_tweets(tweets: List[Tweet]) -> str:
        lines: list[str] = []
        for tw in tweets:
            date_str = tw.created_at.strftime("%Y-%m-%d %H:%M") if tw.created_at else "n/a"
            lines.append(f"[@{tw.author_handle} | {date_str}] {tw.text}")
        return "\n".join(lines)
