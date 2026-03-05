import subprocess
import time
from utils.logger import logger
from terminal.base_terminal import BaseTerminal


class VisibleTerminal(BaseTerminal):

    def __init__(self, name):

        super().__init__(name)

        self.session = f"TCAF-{name}"

        logger.info(f"Creating tmux session: {self.session}")

        subprocess.run(
            ["tmux", "new-session", "-d", "-s", self.session]
        )

        logger.info(f"Launching visible terminal for {self.session}")

        subprocess.Popen([
            "gnome-terminal",
            "--",
            "tmux",
            "attach",
            "-t",
            self.session
        ])

        time.sleep(1)

        self.window_id = self._find_window()

    def _find_window(self):

        for _ in range(20):

            try:
                result = subprocess.run(
                    ["xdotool", "search", "--onlyvisible", "--class", "gnome-terminal"],
                    capture_output=True,
                    text=True
                )

                ids = result.stdout.strip().split()

                if ids:
                    window_id = ids[-1]  # newest window
                    logger.info(f"{self.title} window id: {window_id}")
                    return window_id

            except Exception as e:
                logger.debug(f"xdotool search failed: {e}")

            time.sleep(0.5)

        logger.error("Failed to find terminal window")
        return None

    def run(self, command):

        logger.info(f"[{self.name}] {command}")

        subprocess.run([
            "tmux",
            "send-keys",
            "-t",
            self.session,
            command,
            "Enter"
        ])

    def capture(self):

        screenshot_path = f"output/screenshots/{self.name}.png"

        logger.info(f"Capturing screenshot: {screenshot_path}")

        subprocess.run(
            [
                "scrot",
                screenshot_path
            ]
        )

        return screenshot_path
    
    def capture_output(self):

        result = subprocess.run(
            [
                "tmux",
                "capture-pane",
                "-t",
                self.session,
                "-p"
            ],
            capture_output=True,
            text=True
        )

        return result.stdout