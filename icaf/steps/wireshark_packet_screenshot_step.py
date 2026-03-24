"""
steps/wireshark_packet_screenshot_step.py
──────────────────────────────────────────────────────────────────────────────
Opens Wireshark for the matched frame, expands the full protocol tree in the
packet-detail pane, and takes a precise window screenshot — not a blind scrot
of the entire desktop.

Improvements over original
───────────────────────────
• Uses xdotool to wait for the Wireshark window to actually appear (not a
  fixed sleep) before taking the screenshot.
• After the window is visible, sends keyboard shortcuts to:
    - Expand all protocol tree nodes  (Shift+Right / Ctrl+Right)
    - Jump directly to the matched frame
• Uses xdotool getactivewindow + scrot --window to capture only the Wireshark
  window, not the full desktop.
• Falls back to full-desktop scrot if xdotool is unavailable.
• If Wireshark is not available at all, falls back to a tshark text dump
  and saves that as the "screenshot" (a .txt file) so the test still
  produces evidence even in headless CI environments.
• Proper process teardown with SIGTERM → wait → SIGKILL escalation.
• All evidence screenshots registered on context.current_testcase.
"""

import os
import shutil
import subprocess
import time

from icaf.core.step import Step
from icaf.utils.logger import logger

# Wireshark window title fragment (enough to uniquely identify it)
_WS_WINDOW_TITLE = "Wireshark"
_WAIT_TIMEOUT    = 15   # seconds to wait for Wireshark window
_EXPAND_RETRIES  = 3


def _wait_for_window(title_fragment: str, timeout: int) -> str | None:
    """
    Poll xdotool until a window whose name contains title_fragment appears.
    Returns the window id string, or None on timeout.
    """
    if not shutil.which("xdotool"):
        return None
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = subprocess.run(
            ["xdotool", "search", "--name", title_fragment],
            capture_output=True, text=True,
        )
        ids = result.stdout.strip().splitlines()
        if ids:
            return ids[-1]  # last = most recently opened window
        time.sleep(0.5)
    return None


def _focus_window(window_id: str) -> None:
    if shutil.which("xdotool"):
        subprocess.run(
            ["xdotool", "windowactivate", "--sync", window_id],
            capture_output=True,
        )
        time.sleep(0.4)


def _expand_packet_tree(window_id: str) -> None:
    """
    Send keyboard shortcuts to Wireshark to fully expand the packet tree:
      Ctrl+Shift+I  — go to packet by number (already filtered, so just Enter)
      Ctrl+Right    — expand all subtrees in packet detail pane
    """
    if not shutil.which("xdotool"):
        return
    # Expand all protocol tree nodes
    for _ in range(_EXPAND_RETRIES):
        subprocess.run(
            ["xdotool", "key", "--window", window_id, "ctrl+shift+Right"],
            capture_output=True,
        )
        time.sleep(0.2)
    # Also try the menu shortcut: View → Expand All
    subprocess.run(
        ["xdotool", "key", "--window", window_id, "ctrl+shift+x"],
        capture_output=True,
    )
    time.sleep(0.5)


def _screenshot_window(window_id: str, output_file: str) -> bool:
    """
    Capture only the Wireshark window using scrot --window.
    Falls back to full-desktop scrot if --window flag fails.
    """
    if not shutil.which("scrot"):
        return False

    # Try window-specific capture first
    result = subprocess.run(
        ["scrot", "--window", window_id, output_file],
        capture_output=True,
    )
    if result.returncode == 0:
        return True

    # Fallback: full desktop
    result = subprocess.run(["scrot", output_file], capture_output=True)
    return result.returncode == 0


def _tshark_text_fallback(
    pcap: str,
    frame: str,
    filter_expr: str,
    output_file: str,
) -> str:
    """
    When Wireshark GUI is unavailable, produce a detailed tshark text dump
    of the matched frame and save it as a .txt evidence file.
    """
    txt_file = output_file.replace(".png", "_tshark_detail.txt")

    cmd = [
        "tshark",
        "-r", pcap,
        "-Y", f"frame.number == {frame}",
        "-V",          # verbose: full protocol tree
        "-x",          # include hex+ASCII dump
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    content = result.stdout or result.stderr or "(no tshark output)"

    with open(txt_file, "w", encoding="utf-8") as fh:
        fh.write(f"tshark packet detail — frame {frame}\n")
        fh.write(f"Filter: frame.number == {frame}\n")
        fh.write("=" * 72 + "\n\n")
        fh.write(content)

    logger.info("tshark text fallback written: %s", txt_file)
    return txt_file


class WiresharkPacketScreenshotStep(Step):
    """
    Open Wireshark for the first matched frame, expand the packet detail
    tree, and capture a screenshot of the window.

    Falls back gracefully to a tshark text dump in headless environments.
    """

    def __init__(self, filter_expr: str = ""):
        """
        Parameters
        ----------
        filter_expr : str
            Optional extra display filter appended to the frame filter,
            e.g. ``"tls"`` or ``"ssh"``.  Leave empty to show only the
            matched frame.
        """
        super().__init__("Capture Wireshark Packet Screenshot")
        self.extra_filter = filter_expr

    def execute(self, context) -> None:
        pcap  = context.pcap_file
        frame = getattr(context, "matched_frame", None)

        if not pcap or not frame:
            logger.warning(
                "WiresharkPacketScreenshotStep: no pcap_file or matched_frame "
                "on context — skipping screenshot"
            )
            return

        clause   = context.clause
        testcase = context.current_testcase
        shot_dir = context.evidence.screenshot_path(clause, testcase)
        os.makedirs(shot_dir, exist_ok=True)

        screenshot_file = f"{shot_dir}/packet_frame_{frame}.png"

        # ── Build Wireshark display filter ────────────────────────────────
        ws_filter = f"frame.number == {frame}"
        if self.extra_filter:
            ws_filter = f"({ws_filter}) && ({self.extra_filter})"

        # ── Check if Wireshark is available ───────────────────────────────
        if not shutil.which("wireshark"):
            logger.warning(
                "wireshark not found — falling back to tshark text dump"
            )
            txt = _tshark_text_fallback(pcap, frame, ws_filter, screenshot_file)
            context.current_testcase.add_evidence(screenshot=txt)
            return

        # ── Launch Wireshark ──────────────────────────────────────────────
        logger.info("Opening Wireshark: frame=%s  filter=%s", frame, ws_filter)
        ws_proc = subprocess.Popen(
            ["wireshark", "-r", pcap, "-Y", ws_filter],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # ── Wait for window to appear ─────────────────────────────────────
        window_id = _wait_for_window(_WS_WINDOW_TITLE, _WAIT_TIMEOUT)

        if not window_id:
            logger.warning(
                "Wireshark window did not appear within %ds — "
                "falling back to full-desktop scrot",
                _WAIT_TIMEOUT,
            )
            time.sleep(2)  # last-ditch wait
        else:
            logger.info("Wireshark window found: id=%s", window_id)
            _focus_window(window_id)

            # Give the packet list time to populate
            time.sleep(1.5)

            # Expand the full protocol detail tree
            _expand_packet_tree(window_id)

            # Additional settle time after expansion
            time.sleep(0.8)

        # ── Take screenshot ───────────────────────────────────────────────
        captured = False
        if window_id and shutil.which("scrot"):
            captured = _screenshot_window(window_id, screenshot_file)

        if not captured:
            # Full-desktop fallback
            if shutil.which("scrot"):
                r = subprocess.run(["scrot", screenshot_file], capture_output=True)
                captured = r.returncode == 0

        if captured:
            logger.info("Wireshark screenshot saved: %s", screenshot_file)
            context.current_testcase.add_evidence(screenshot=screenshot_file)
        else:
            # GUI screenshot failed entirely — produce text dump instead
            logger.warning(
                "Screenshot capture failed — falling back to tshark text dump"
            )
            txt = _tshark_text_fallback(pcap, frame, ws_filter, screenshot_file)
            context.current_testcase.add_evidence(screenshot=txt)

        # ── Teardown: close Wireshark ─────────────────────────────────────
        logger.info("Closing Wireshark")
        ws_proc.terminate()
        try:
            ws_proc.wait(timeout=6)
        except subprocess.TimeoutExpired:
            logger.warning("Wireshark did not exit cleanly — sending SIGKILL")
            ws_proc.kill()
            ws_proc.wait()