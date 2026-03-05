from core.step import Step
from utils.logger import logger


class VerifyOutputStep(Step):

    def __init__(self, terminal, pattern, should_exist=True):

        super().__init__(f"Verify output: {pattern}")

        self.terminal = terminal
        self.pattern = pattern
        self.should_exist = should_exist

    def execute(self, context):

        tm = context.terminal_manager

        output = tm.capture_output(self.terminal)

        logger.info("Verifying terminal output")

        if self.should_exist:

            if self.pattern.lower() in output.lower():

                logger.info(f"Pattern verified: {self.pattern}")

                return True

            logger.error(f"Expected pattern not found: {self.pattern}")

            raise Exception(f"Verification failed: {self.pattern}")

        else:

            if self.pattern.lower() not in output.lower():

                logger.info(f"Pattern correctly absent: {self.pattern}")

                return True

            logger.error(f"Unexpected pattern found: {self.pattern}")

            raise Exception(f"Unexpected pattern detected: {self.pattern}")