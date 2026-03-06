from core.step import Step
from utils.logger import logger


class EnsureSSHDisconnectedStep(Step):

    def __init__(self, terminal):

        super().__init__("Ensure SSH disconnected")

        self.terminal = terminal

    def execute(self, context):

        tm = context.terminal_manager

        logger.info("Ensuring SSH session is closed")

        tm.run(self.terminal, "exit")