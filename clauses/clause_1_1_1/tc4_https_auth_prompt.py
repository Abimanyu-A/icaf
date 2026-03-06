from core.testcase import TestCase
from core.step_runner import StepRunner
from steps.open_url_step import OpenURLStep
from steps.browser_screenshot_step import BrowserScreenshotStep

class TC4HTTPSAuthPrompt(TestCase):

    def __init__(self):

        super().__init__(
            "TC4_HTTPS_AUTH_PROMPT",
            "HTTPS authentication page must appear"
        )

    def run(self, context):

        url = f"http://{context.ssh_ip}/dvwa/login.php"

        StepRunner([
            OpenURLStep(url),
            BrowserScreenshotStep("https_login_page.png")
        ]).run(context)

        self.pass_test()

        return self