from utils.logger import logger
import subprocess


class TerminalSession:
    """
    Represents a tmux terminal session.
    """

    def __init__(self, name: str):

        self.name = name

        logger.info(f"Creating tmux terminal: {name}")

        subprocess.run(
            f"tmux new-session -d -s {name}",
            shell=True
        )

    def run(self, command: str):
        """
        Send command to tmux terminal.
        """

        logger.info(f"[{self.name}] Running command: {command}")

        subprocess.run(
            f'tmux send-keys -t {self.name} "{command}" Enter',
            shell=True
        )