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

            # wait for shell prompt
            pattern, output = ExpectOneOfStep(
                "tester",
                ["$", "#", "permission denied"]
            ).execute(context)

            if pattern in ["$", "#"]:

                logger.info("SSH login successful")

                ScreenshotStep("tester").execute(context)

                self.pass_test()
                return self

            if pattern == "permission denied":

                logger.error("SSH login failed with valid credentials")

                ScreenshotStep("tester").execute(context)

                self.fail_test()
                return self

        if pattern == "connection refused":

            logger.error("SSH connection refused")

            ScreenshotStep("tester").execute(context)

            self.fail_test()

            return self