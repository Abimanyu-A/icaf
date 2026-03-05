import time
from core.step import Step
from utils.logger import logger


class ExpectOneOfStep(Step):

    def __init__(self, terminal, patterns, timeout=20, interval=1):

        super().__init__(f"Expect one of: {patterns}")

        self.terminal = terminal
        self.patterns = patterns
        self.timeout = timeout
        self.interval = interval

    def execute(self, context):

        tm = context.terminal_manager

        start = time.time()

        while True:

            output = tm.capture_output(self.terminal)

            lower_output = output.lower()

            for pattern in self.patterns:

                if pattern.lower() in lower_output:

                    logger.info(f"Pattern matched: {pattern}")

                    return pattern, output

            if time.time() - start > self.timeout:

                logger.error(f"Timeout waiting for patterns: {self.patterns}")

                raise Exception("Expected patterns not found")

            time.sleep(self.interval)