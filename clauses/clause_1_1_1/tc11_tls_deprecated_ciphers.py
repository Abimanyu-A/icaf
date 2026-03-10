from core.testcase import TestCase
from core.step_runner import StepRunner
from steps.command_step import CommandStep
from steps.screenshot_step import ScreenshotStep
from steps.session_reset_step import SessionResetStep

class TC11TLSDeprecatedCiphers(TestCase):

    def __init__(self):

        super().__init__(
            "TC11_TLS_DEPRECATED_CIPHERS",
            "Verify deprecated TLS ciphers are not present"
        )

    def run(self, context):

        cmd = f"nmap --script ssl-enum-ciphers -p 443 {context.ssh_ip}"

        StepRunner([
            # SessionResetStep("tester"),
            CommandStep("tester", cmd)
        ]).run(context)

        tm = context.terminal_manager

        output = tm.capture_output("tester")

        forbidden = [
            "RC4",
            "3DES",
            "DES",
            "MD5",
            "EXPORT",
            "NULL"
        ]

        for cipher in forbidden:

            if cipher in output:

                ScreenshotStep("tester").execute(context)

                self.fail_test()

                return self

        ScreenshotStep("tester").execute(context)

        self.pass_test()

        return self