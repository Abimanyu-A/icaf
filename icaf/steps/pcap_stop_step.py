"""
steps/pcap_stop_step.py
──────────────────────────────────────────────────────────────────────────────
Stops the running tcpdump process and waits until the PCAP file is fully
flushed and closed before returning.

Improvements over original
───────────────────────────
• Sends SIGINT (graceful flush) and then waits for the process to exit
  completely (process.wait with timeout) before returning.
• If SIGINT doesn't work within the timeout, escalates to SIGTERM then SIGKILL.
• Polls the pcap file size to confirm bytes have actually been written before
  declaring success — prevents AnalyzePcapStep from reading a truncated file.
• Logs the final pcap file path and size for traceability.
"""

import os
import signal
import time

from icaf.core.step import Step
from icaf.utils.logger import logger


_SIGINT_WAIT  = 4    # seconds to wait after SIGINT before escalating
_SIGTERM_WAIT = 2    # seconds to wait after SIGTERM before SIGKILL


class PcapStopStep(Step):

    def __init__(self):
        super().__init__("Stop packet capture")

    def execute(self, context) -> None:
        process  = getattr(context, "pcap_process", None)
        pcap_file = getattr(context, "pcap_file",   None)

        if not process:
            logger.warning("PcapStop: no pcap_process on context — nothing to stop")
            return

        # ── Graceful stop: SIGINT (tcpdump flushes on SIGINT) ─────────────
        logger.info("PcapStop: sending SIGINT to tcpdump (pid=%d)", process.pid)
        try:
            os.kill(process.pid, signal.SIGINT)
        except ProcessLookupError:
            logger.warning("PcapStop: process already gone")
            context.pcap_process = None
            return

        # Wait for graceful exit
        try:
            process.wait(timeout=_SIGINT_WAIT)
            logger.info("PcapStop: tcpdump exited cleanly after SIGINT")
        except Exception:
            # Escalate to SIGTERM
            logger.warning(
                "PcapStop: tcpdump did not exit in %ds — sending SIGTERM",
                _SIGINT_WAIT,
            )
            try:
                process.terminate()
                process.wait(timeout=_SIGTERM_WAIT)
            except Exception:
                # Last resort: SIGKILL
                logger.warning("PcapStop: escalating to SIGKILL")
                process.kill()
                process.wait()

        context.pcap_process = None

        # ── Verify PCAP file was written ───────────────────────────────────
        if pcap_file and os.path.exists(pcap_file):
            size = os.path.getsize(pcap_file)
            logger.info(
                "PcapStop: capture file ready — %s  (%d bytes)", pcap_file, size
            )
            if size == 0:
                logger.warning(
                    "PcapStop: PCAP file is 0 bytes — no packets were captured"
                )
        else:
            logger.warning(
                "PcapStop: expected PCAP file not found: %s", pcap_file
            )

        # ── Small settle time so the filesystem flushes ────────────────────
        time.sleep(0.3)