from core.step import Step
from utils.logger import logger


class ClearTerminalStep(Step):

    def __init__(self, terminal):

        super().__init__("Clear terminal")

        self.terminal = terminal

    def execute(self, context):

        tm = context.terminal_manager

        logger.info(f"Clearing terminal {self.terminal}")

        tm.run(self.terminal, "clear")