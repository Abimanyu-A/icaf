from core.testcase import TestCase
from core.step_runner import StepRunner

from steps.command_step import CommandStep
from steps.expect_one_of_step import ExpectOneOfStep
from steps.screenshot_step import ScreenshotStep
from steps.input_step import InputStep
from steps.session_reset_step import SessionResetStep

from utils.logger import logger


class TC3SSHInvalidCredentials(TestCase):

    def __init__(self):

        super().__init__(
            "TC3_SSH_INVALID_CREDENTIALS",
            "Tester should not connect with invalid SSH credentials"
        )

    def run(self, context):

        ssh_cmd = f"ssh -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa {context.ssh_user}@{context.ssh_ip}"

        tm = context.terminal_manager

        StepRunner([
            SessionResetStep("tester"),
            CommandStep("tester", ssh_cmd)
        ]).run(context)

        pattern, output = ExpectOneOfStep(
            "tester",
            [
                "password",
                "continue connecting",
                "connection refused"
            ]
        ).execute(context)

        if pattern == "continue connecting":

            StepRunner([
                InputStep("tester", "yes")
            ]).run(context)

            pattern, output = ExpectOneOfStep(
                "tester",
                ["password"]
            ).execute(context)

        if pattern == "password":

            # try wrong password multiple times
            StepRunner([
                InputStep("tester", "wrongpassword"),
                InputStep("tester", "wrongpassword"),
                InputStep("tester", "wrongpassword")
            ]).run(context)

            output = tm.capture_output("tester")

            if "Permission denied" in output:

                logger.info("Invalid credentials correctly rejected")

                ScreenshotStep("tester").execute(context)

                self.pass_test()

                return self

            logger.error("SSH login succeeded with invalid credentials")

            ScreenshotStep("tester").execute(context)

            self.fail_test()

            return self

        if pattern == "connection refused":

            logger.error("SSH connection refused")

            ScreenshotStep("tester").execute(context)

            self.fail_test()

            return self