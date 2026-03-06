from core.step import Step


class BrowserScreenshotStep(Step):

    def __init__(self, filename):

        super().__init__("Browser screenshot")

        self.filename = filename

    def execute(self, context):

        clause = context.clause
        testcase = context.current_testcase

        path = context.evidence.screenshot_path(clause, testcase)

        file = f"{path}/{self.filename}"

        context.browser.driver.save_screenshot(file)

        context.current_testcase.add_evidence(file)