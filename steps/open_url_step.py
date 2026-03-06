from core.step import Step


class OpenURLStep(Step):

    def __init__(self, url):

        super().__init__("Open URL")

        self.url = url

    def execute(self, context):

        context.browser.open(self.url)