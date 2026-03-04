"""Daily Cryptomics Agent – Main Orchestrator.

Coordinates all five pipeline steps in sequence:
  1. TweetAcquisition  – fetch raw tweets
  2. AISummarization   – distil into a news briefing
  3. ImageCreation     – generate a comics-style visual
  4. ContentPackaging  – assemble the tweet payload
  5. TwitterPublishing – post to Twitter

Each step produces a typed result object that is logged and forwarded
to the next step.  Any step returning a falsy ``success`` flag causes
the run to abort early with a clear error message.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from src.steps.ai_summarization import AISummarization, SummarizationResult
from src.steps.content_packaging import ContentPackaging, TweetPackage
from src.steps.image_creation import ImageCreation, ImageCreationResult
from src.steps.tweet_acquisition import AcquisitionResult, TweetAcquisition
from src.steps.twitter_publishing import PublishingResult, TwitterPublishing
from src.utils.config import Config
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RunReport:
    """Aggregated report for a single agent run."""

    acquisition: Optional[AcquisitionResult] = None
    summarization: Optional[SummarizationResult] = None
    image: Optional[ImageCreationResult] = None
    package: Optional[TweetPackage] = None
    publishing: Optional[PublishingResult] = None
    aborted_at: Optional[str] = None
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.publishing is not None and self.publishing.success

    def log_summary(self) -> None:
        logger.info("═" * 60)
        logger.info("  Daily Cryptomics – Run Report")
        logger.info("═" * 60)
        if self.acquisition:
            logger.info("  [1] Acquisition  : %s", self.acquisition.summary)
        if self.summarization:
            logger.info("  [2] Summarization: %d tokens used", self.summarization.output_tokens)
        if self.image:
            status = "✓" if self.image.success else "✗"
            logger.info("  [3] Image        : %s %s", status, self.image.image_path or "N/A")
        if self.package:
            logger.info("  [4] Packaging    : %s", self.package)
        if self.publishing:
            logger.info("  [5] Publishing   : %s", self.publishing.summary)
        if self.aborted_at:
            logger.warning("  ⚠ Aborted at step: %s – %s", self.aborted_at, self.error)
        logger.info("  Result: %s", "SUCCESS ✓" if self.success else "FAILED ✗")
        logger.info("═" * 60)


class DailyCryptomicsAgent:
    """Orchestrates the full Daily Cryptomics pipeline."""

    def __init__(self, config: Config) -> None:
        self._cfg = config
        self._acquisition = TweetAcquisition(config.twitter, config.agent)
        self._summarization = AISummarization(config.ai)
        self._image_creation = ImageCreation(config.ai, config.agent)
        self._packaging = ContentPackaging(config.sources.get("hashtags", []))
        self._publishing = TwitterPublishing(config.twitter)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def run(self) -> RunReport:
        """Execute all five pipeline steps sequentially.

        Returns:
            A :class:`RunReport` capturing results from every step.
        """
        logger.info("Daily Cryptomics agent starting…")
        report = RunReport()

        # ── Step 1: Tweet Acquisition ──────────────────────────────────
        logger.info("[1/5] Tweet Acquisition")
        sources = self._cfg.sources.get("sources", [])
        report.acquisition = self._acquisition.run(sources)
        if not report.acquisition.success:
            return self._abort(report, "tweet_acquisition", "No tweets fetched.")

        # ── Step 2: AI Summarization ───────────────────────────────────
        logger.info("[2/5] AI Summarization")
        report.summarization = self._summarization.run(
            report.acquisition.tweets,
            lookback_hours=self._cfg.agent.lookback_hours,
        )
        if not report.summarization.success:
            return self._abort(report, "ai_summarization", "Empty summary returned.")

        # ── Step 3: Image Creation ─────────────────────────────────────
        logger.info("[3/5] Image Creation")
        image_style = self._cfg.sources.get("image_style", "")
        report.image = self._image_creation.run(
            summary=report.summarization.summary,
            image_style=image_style,
        )
        if not report.image.success:
            return self._abort(report, "image_creation", "Image file not produced.")

        # ── Step 4: Content Packaging ──────────────────────────────────
        logger.info("[4/5] Content Packaging")
        report.package = self._packaging.run(
            summary=report.summarization.summary,
            image_path=report.image.image_path,
        )
        if not report.package.success:
            return self._abort(report, "content_packaging", "Package validation failed.")

        # ── Step 5: Twitter Publishing ─────────────────────────────────
        logger.info("[5/5] Twitter Publishing")
        report.publishing = self._publishing.run(report.package)

        report.log_summary()
        return report

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _abort(report: RunReport, step: str, reason: str) -> RunReport:
        report.aborted_at = step
        report.error = reason
        logger.error("Pipeline aborted at '%s': %s", step, reason)
        report.log_summary()
        return report
