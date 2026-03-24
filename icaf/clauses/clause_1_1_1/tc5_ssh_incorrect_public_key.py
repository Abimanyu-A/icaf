"""
TC5 — SSH Incorrect Public Key
Test Scenario 1.1.1.5
"""

from icaf.core.testcase import TestCase
from icaf.core.step_runner import StepRunner
from icaf.steps.command_step import CommandStep
from icaf.steps.expect_one_of_step import ExpectOneOfStep
from icaf.steps.screenshot_step import ScreenshotStep
from icaf.steps.pcap_start_step import PcapStartStep
from icaf.steps.pcap_stop_step import PcapStopStep
from icaf.steps.analyze_pcap_step import AnalyzePcapStep
from icaf.steps.wireshark_packet_screenshot_step import WiresharkPacketScreenshotStep
from icaf.steps.session_reset_step import SessionResetStep
from icaf.steps.clear_terminal_step import ClearTerminalStep
from icaf.utils.logger import logger


class TC5SSHIncorrectPublicKey(TestCase):

    def __init__(self):
        super().__init__(
            "TC5_SSH_INCORRECT_PUBLIC_KEY",
            "Configure and verify SSH login using the incorrect public key",
        )

    def run(self, context):
        wrong_key   = context.profile.get("ssh.pubkey.wrong_key_path", "~/.ssh/wrong_keyy")
        pubkey_user = context.profile.get("ssh.pubkey.dut_user", "Test5")

        # Generate an unregistered key
        StepRunner([
            CommandStep("tester",
                        f"ssh-keygen -t ecdsa -b 256 -f {wrong_key} -N ''",
                        settle_time=4),
        ]).run(context)
        ExpectOneOfStep("tester",
            ["Your public key", "already exists", "SHA256"], timeout=10).execute(context)
        ScreenshotStep("tester").execute(context)

        ssh_cmd = (f"ssh -o IdentitiesOnly=yes -i {wrong_key} "
                   f"{pubkey_user}@{context.ssh_ip}")
        reject_p = ["Permission denied (publickey)", "Permission denied",
                    "publickey", "denied", "closed"]
        success_p = context.profile.get_list("ssh.success_prompt") or ["#", "$", ">"]

        StepRunner([
            PcapStartStep(interface="eth0", filename="tc5_ssh_wrong_key.pcapng"),
            CommandStep("tester", ssh_cmd, settle_time=4),
        ]).run(context)

        pattern, _ = ExpectOneOfStep(
            "tester", reject_p + success_p, timeout=12).execute(context)

        StepRunner([PcapStopStep()]).run(context)
        ScreenshotStep("tester").execute(context)

        if any(sp in pattern for sp in success_p):
            logger.error("TC5: DUT accepted wrong public key — FAIL")
            StepRunner([SessionResetStep("tester", post_reset_delay=4)]).run(context)
            self.fail_test()
            return self

        logger.info("TC5: DUT correctly rejected wrong public key — '%s'", pattern)
        StepRunner([
            AnalyzePcapStep("ssh"),
            WiresharkPacketScreenshotStep("ssh"),
        ]).run(context)
        StepRunner([ClearTerminalStep("tester")]).run(context)
        StepRunner([SessionResetStep("tester", post_reset_delay=4)]).run(context)
        self.pass_test()
        return self