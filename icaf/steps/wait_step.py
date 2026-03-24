import time
from icaf.core.step import Step


class WaitStep(Step):

    def __init__(self, seconds):

        super().__init__(f"Wait {seconds}s")

        self.seconds = seconds

    def execute(self, context):

        time.sleep(self.seconds)