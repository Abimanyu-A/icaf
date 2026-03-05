from core.step import Step
from utils.logger import logger


class CheckOutputStep(Step):

    def __init__(self, terminal, expected_text):

        super().__init__(f"Check output contains: {expected_text}")

        self.terminal = terminal
        self.expected_text = expected_text

    def execute(self, context):

        tm = context.terminal_manager

        output = tm.capture(self.terminal)

        logger.info("Terminal output captured")

        if self.expected_text in output:

            logger.info("Expected text found")

            return True

        logger.warning("Expected text NOT found")

        return False