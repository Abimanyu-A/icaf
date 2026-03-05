import subprocess
from core.step import Step


class ScreenshotStep(Step):

    def __init__(self, terminal):

        super().__init__("Capture screenshot")

        self.terminal = terminal

    def execute(self, context):

        clause = context.clause
        testcase = context.current_testcase

        path = context.evidence.screenshot_path(clause, testcase)

        file = f"{path}/{self.terminal}.png"

        subprocess.run(["scrot", file])

        return file