from core.testcase import TestCase
from core.step_runner import StepRunner
from steps.command_step import CommandStep
from steps.expect_one_of_step import ExpectOneOfStep
from steps.screenshot_step import ScreenshotStep
from steps.session_reset_step import SessionResetStep
from steps.clear_terminal_step import ClearTerminalStep

class TC7SSHv1Disabled(TestCase):

    def __init__(self):

        super().__init__(
            "TC7_SSHV1_DISABLED",
            "Verify SSH version 1 is not supported"
        )

    def run(self, context):

        ssh_cmd = f"ssh -1 {context.ssh_user}@{context.ssh_ip}"

        StepRunner([
            ClearTerminalStep("tester"),
            CommandStep("tester", ssh_cmd)
        ]).run(context)

        pattern, output = ExpectOneOfStep(
            "tester",
            [
                "no longer supported",
                "connection closed",
                "password"
            ]
        ).execute(context)

        if pattern == "password":

            # SSHv1 actually worked
            ScreenshotStep("tester").execute(context)

            self.fail_test()

            return self

        ScreenshotStep("tester").execute(context)

        self.pass_test()

        return self