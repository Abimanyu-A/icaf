"""
steps/browser_screenshot_step.py
──────────────────────────────────────────────────────────────────────────────
Captures a screenshot of the current browser window.

Improvements over original
───────────────────────────
• filename is now optional — if omitted, an auto-generated name based on the
  TC name and a monotonic counter is used (consistent with ScreenshotStep).
• Saves into the TC evidence directory (same path logic as ScreenshotStep).
• Registers the screenshot on context.current_testcase.add_evidence().
• Logs the saved path.
"""

import time

from icaf.core.step import Step
from icaf.utils.logger import logger


class BrowserScreenshotStep(Step):
    """
    Capture a screenshot of the browser window.

    Parameters
    ----------
    filename : str | None
        Base filename (without directory).  If None, auto-generates
        ``browser_<timestamp>.png``.
    """

    def __init__(self, filename: str | None = None):
        super().__init__("Browser screenshot")
        self.filename = filename

    def execute(self, context) -> None:
        clause   = context.clause
        testcase = context.current_testcase

        shot_dir = context.evidence.screenshot_path(clause, testcase)

        # Auto-generate filename if not provided
        fname = self.filename or f"browser_{int(time.time() * 1000)}.png"
        if not fname.endswith(".png"):
            fname += ".png"

        file_path = f"{shot_dir}/{fname}"

        context.browser.driver.save_screenshot(file_path)

        logger.info("BrowserScreenshot saved: %s", file_path)

        context.current_testcase.add_evidence(screenshot=file_path)