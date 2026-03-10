from core.testcase import TestCase
from core.step_runner import StepRunner

from steps.command_step import CommandStep
from steps.expect_one_of_step import ExpectOneOfStep
from steps.screenshot_step import ScreenshotStep
from steps.input_step import InputStep
from steps.session_reset_step import SessionResetStep

from utils.logger import logger


class TC2SSHValidCredentials(TestCase):

    def __init__(self):

        super().__init__(
            "TC2_SSH_VALID_CREDENTIALS",
            "Tester connects to DUT via SSH with valid credentials"
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

            StepRunner([
                InputStep("tester", context.ssh_password)
            ]).run(context)

            # verify connection by executing command
            StepRunner([
                CommandStep("tester", "whoami")
            ]).run(context)

            output = tm.capture_output("tester")

            if context.ssh_user in output:

                logger.info("SSH login verified using command execution")

                ScreenshotStep("tester").execute(context)

                self.pass_test()

                return self

            logger.error("SSH login failed despite valid credentials")

            ScreenshotStep("tester").execute(context)

            self.fail_test()

            return self

        if pattern == "connection refused":

            logger.error("SSH connection refused")

            ScreenshotStep("tester").execute(context)

            self.fail_test()

            return self