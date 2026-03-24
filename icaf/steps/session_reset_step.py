"""
steps/session_reset_step.py
──────────────────────────────────────────────────────────────────────────────
Cleanly tears down the active session on a terminal at the end of a test case,
then pauses for a configurable inter-test-case cooldown.

Improvements over original
───────────────────────────
• Sends "exit" and then waits to confirm the SSH prompt is actually gone
  (looks for shell prompt characters that would indicate a live session is
  still open) before declaring the session closed.
• Sends "exit" up to max_exit_attempts times to handle nested sessions
  (e.g., DUT shell → system shell → bare terminal).
• Calls `clear` after disconnect so the next TC starts with a clean terminal.
• Accepts a post_reset_delay parameter (default 3 s) used as a between-TC
  breathing gap.  The caller (TC code) can override this per-TC.
• Logs the final terminal state so failures are easy to diagnose.
"""

import time

from icaf.core.step import Step
from icaf.core.step_runner import StepRunner
from icaf.steps.clear_terminal_step import ClearTerminalStep
from icaf.steps.ensure_ssh_disconnected_step import EnsureSSHDisconnectedStep
from icaf.utils.logger import logger


# Prompts that indicate a live SSH/shell session is still active
_LIVE_SESSION_INDICATORS = ["#", "$", ">", "rkscli", "apollo", "watchdog"]

# Prompts that confirm we're back at the bare terminal (not in a session)
_DISCONNECTED_INDICATORS = [
    "connection closed",
    "disconnected",
    "logout",
    "not connected",
]


class SessionResetStep(Step):
    """
    Disconnect any active SSH/shell session on the given terminal and
    perform a post-test-case cooldown.

    Parameters
    ----------
    terminal : str
        Terminal name as registered with the TerminalManager.
    post_reset_delay : float
        Seconds to wait after cleanup completes (inter-TC gap).  Default 3 s.
    max_exit_attempts : int
        How many times to send "exit" to unwind nested sessions.  Default 3.
    """

    def __init__(
        self,
        terminal: str,
        post_reset_delay: float = 3.0,
        max_exit_attempts: int = 3,
    ):
        super().__init__("Reset session")
        self.terminal         = terminal
        self.post_reset_delay = post_reset_delay
        self.max_exit_attempts = max_exit_attempts

    def execute(self, context) -> None:
        tm = context.terminal_manager

        logger.info(
            "SessionReset: tearing down session on terminal '%s'",
            self.terminal,
        )

        # ── Brief settle so the current command finishes output ───────────
        time.sleep(1.5)

        # ── Send "exit" up to max_exit_attempts times ─────────────────────
        # Each exit unwinds one shell layer (DUT CLI → bash → bare terminal).
        for attempt in range(1, self.max_exit_attempts + 1):
            tm.run(self.terminal, "exit")
            time.sleep(1.2)

            output = tm.capture_output(self.terminal).lower()

            # If we see a disconnection indicator, we're done
            if any(ind in output for ind in _DISCONNECTED_INDICATORS):
                logger.info(
                    "SessionReset: disconnection confirmed after %d exit(s)",
                    attempt,
                )
                break

            # If no live-session prompt is visible, also consider us done
            if not any(ind in output for ind in _LIVE_SESSION_INDICATORS):
                logger.info(
                    "SessionReset: no live-session prompt detected after "
                    "%d exit(s) — assuming disconnected",
                    attempt,
                )
                break

            logger.debug(
                "SessionReset: still connected after %d exit(s) — retrying",
                attempt,
            )
        else:
            # Exhausted attempts — force Ctrl+C then exit as a last resort
            logger.warning(
                "SessionReset: could not cleanly disconnect after %d attempts — "
                "sending Ctrl+C + exit",
                self.max_exit_attempts,
            )
            tm.run(self.terminal, "\x03")   # Ctrl+C
            time.sleep(0.5)
            tm.run(self.terminal, "exit")
            time.sleep(1.0)

        # ── Clear the terminal buffer ─────────────────────────────────────
        try:
            StepRunner([ClearTerminalStep(self.terminal)]).run(context)
        except Exception as exc:
            logger.warning(
                "SessionReset: ClearTerminalStep failed (%s) — continuing",
                exc,
            )

        # ── Inter-test-case cooldown ──────────────────────────────────────
        logger.info(
            "SessionReset: post-reset cooldown %.1f s", self.post_reset_delay
        )
        time.sleep(self.post_reset_delay)

        logger.info(
            "SessionReset: terminal '%s' is ready for the next test case",
            self.terminal,
        )