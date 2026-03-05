import time
from core.step import Step
from utils.logger import logger


class WaitForPatternStep(Step):

    def __init__(self, terminal, pattern, timeout=20, interval=1):

        super().__init__(f"Wait for pattern: {pattern}")

        self.terminal = terminal
        self.pattern = pattern
        self.timeout = timeout
        self.interval = interval

    def execute(self, context):

        tm = context.terminal_manager

        start = time.time()

        while True:

            output = tm.capture_output(self.terminal)

            if self.pattern.lower() in output.lower():

                logger.info(f"Pattern found: {self.pattern}")

                return output

            if time.time() - start > self.timeout:

                logger.error(f"Timeout waiting for pattern: {self.pattern}")

                raise Exception(f"Pattern not found: {self.pattern}")

            time.sleep(self.interval)