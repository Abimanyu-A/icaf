from core.testcase import TestCase
from core.step_runner import StepRunner
from steps.command_step import CommandStep
from steps.expect_one_of_step import ExpectOneOfStep
from steps.screenshot_step import ScreenshotStep
from steps.session_reset_step import SessionResetStep

class TC8TLS10Disabled(TestCase):

    def __init__(self):

        super().__init__(
            "TC8_TLS10_DISABLED",
            "Verify TLS 1.0 is disabled"
        )

    def run(self, context):

        cmd = f"openssl s_client -connect {context.ssh_ip}:443 -tls1"

        StepRunner([
            # SessionResetStep("tester"),
            CommandStep("tester", cmd)
        ]).run(context)

        pattern, output = ExpectOneOfStep(
            "tester",
            [
                "error",
                "protocol version",
                "Cipher"
            ]
        ).execute(context)

        if pattern == "Cipher":

            ScreenshotStep("tester").execute(context)

            self.fail_test()

            return self

        ScreenshotStep("tester").execute(context)

        self.pass_test()

        return self