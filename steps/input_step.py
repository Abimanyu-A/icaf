from core.step import Step
import time


class InputStep(Step):

    def __init__(self, terminal, text):

        super().__init__(f"Input: {text}")

        self.terminal = terminal
        self.text = text

    def execute(self, context):

        tm = context.terminal_manager

        tm.run(self.terminal, self.text)

        time.sleep(3)