"""
steps/verify_output_step.py
──────────────────────────────────────────────────────────────────────────────
Checks terminal output for the presence (or absence) of one or more patterns.

Improvements over original
───────────────────────────
• Accepts either a single string pattern or a list of patterns.
  Any match = satisfied (OR semantics).
• Returns True/False instead of raising an exception — the TC is responsible
  for deciding whether a failed verification is a test failure.
• Optionally raises on mismatch if raise_on_failure=True (default False)
  so callers who prefer exception-driven flow can opt in.
• Logs which specific pattern matched or which patterns were missing.
"""

from icaf.core.step import Step
from icaf.utils.logger import logger


class VerifyOutputStep(Step):
    """
    Verify terminal output contains (or does not contain) expected patterns.

    Parameters
    ----------
    terminal : str
        Terminal name.
    patterns : str | list[str]
        One pattern string or a list.  Match is case-insensitive.
        Any single match satisfies a positive check.
    should_exist : bool
        True  → at least one pattern must be present  (default).
        False → none of the patterns must be present.
    raise_on_failure : bool
        If True, raise an Exception when the check fails instead of just
        returning False.  Default False.
    """

    def __init__(
        self,
        terminal: str,
        patterns,
        should_exist: bool = True,
        raise_on_failure: bool = False,
    ):
        label = patterns if isinstance(patterns, str) else str(patterns)
        super().__init__(f"Verify output: {label}")
        self.terminal        = terminal
        self.patterns        = (
            [patterns] if isinstance(patterns, str) else list(patterns)
        )
        self.should_exist    = should_exist
        self.raise_on_failure = raise_on_failure

    def execute(self, context) -> bool:
        tm     = context.terminal_manager
        output = tm.capture_output(self.terminal).lower()

        if self.should_exist:
            for pattern in self.patterns:
                if pattern.lower() in output:
                    logger.info("VerifyOutput: matched pattern '%s'", pattern)
                    return True
            # None matched
            logger.warning(
                "VerifyOutput: NONE of the expected patterns found: %s",
                self.patterns,
            )
            if self.raise_on_failure:
                raise AssertionError(
                    f"Expected one of {self.patterns} in output but found none"
                )
            return False

        else:  # should_exist = False
            matched = [p for p in self.patterns if p.lower() in output]
            if not matched:
                logger.info(
                    "VerifyOutput: correctly absent — none of %s found",
                    self.patterns,
                )
                return True
            logger.warning(
                "VerifyOutput: unexpected pattern(s) found in output: %s",
                matched,
            )
            if self.raise_on_failure:
                raise AssertionError(
                    f"Unexpected pattern(s) found in output: {matched}"
                )
            return False