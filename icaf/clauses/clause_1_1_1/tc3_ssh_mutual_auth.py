"""
TC3 — SSH Mutual Auth: positive (correct password) and negative (wrong password).
Test Scenario 1.1.1.3
"""

from icaf.core.testcase import TestCase
from icaf.core.step_runner import StepRunner
from icaf.steps.command_step import CommandStep
from icaf.steps.expect_one_of_step import ExpectOneOfStep
from icaf.steps.input_step import InputStep
from icaf.steps.screenshot_step import ScreenshotStep
from icaf.steps.pcap_start_step import PcapStartStep
from icaf.steps.pcap_stop_step import PcapStopStep
from icaf.steps.analyze_pcap_step import AnalyzePcapStep
from icaf.steps.wireshark_packet_screenshot_step import WiresharkPacketScreenshotStep
from icaf.steps.session_reset_step import SessionResetStep
from icaf.steps.clear_terminal_step import ClearTerminalStep
from icaf.utils.logger import logger


class TC3SSHMutualAuth(TestCase):
    protocol = "ssh"

    def __init__(self):
        super().__init__(
            "TC3_SSH_MUTUAL_AUTH",
            "Configure and verify successful and unsuccessful SSH mutual authentication",
        )

    def _ssh_cmd(self, context):
        base  = context.profile.get("ssh.base", "ssh")
        options = context.profile.get_list("ssh.connect_options")
        target  = context.profile.get("ssh.target", "{user}@{ip}").format(
            user=context.ssh_user, ip=context.ssh_ip)
        return " ".join([base] + options + [target])

    # ── verify SSH enabled ────────────────────────────────────────────────

    def _verify_ssh_enabled(self, context):
        ssh_cmd      = self._ssh_cmd(context)
        display_ssh_status = context.profile.get("ssh.commands.ssh_server_status")
        StepRunner([
            CommandStep("tester", ssh_cmd, settle_time=4),
        ]).run(context)
        ExpectOneOfStep("tester",
            context.profile.get_list("ssh.password_prompt"), timeout=10).execute(context)
        StepRunner([InputStep("tester", context.ssh_password)]).run(context)
        ExpectOneOfStep("tester", ["#", ">", "$"], timeout=10).execute(context)

        StepRunner([ClearTerminalStep("tester")]).run(context)

        # Query SSH server status
        StepRunner([CommandStep("tester", display_ssh_status, settle_time=2)]).run(context)
        ExpectOneOfStep("tester", ["SSH version", "version : 2", "Enable", "#"],
                        timeout=8).execute(context)
        ScreenshotStep(
            "tester",
            caption="TC3 Step 1 — DUT SSH server status confirms SSHv2 is enabled and running",
        ).execute(context)
        StepRunner([SessionResetStep("tester", post_reset_delay=2)]).run(context)

    # ── nmap cipher scan ──────────────────────────────────────────────────

    def _nmap_scan(self, context):
        cmd = f"nmap -p 22 --script ssh2-enum-algos {context.ssh_ip} -oN tc3_nmap_scan.txt"

        StepRunner([
            CommandStep("tester", cmd, settle_time=15, capture_evidence=False),
        ]).run(context)

        ExpectOneOfStep("tester", ["Nmap done", "kex_algorithms", "encryption_algorithms"],
                        timeout=30).execute(context)

        # Read the full file directly — no terminal truncation
        with open("tc3_nmap_scan.txt", "r") as f:
            full_output = f.read()

        context.current_testcase.add_evidence(
            command=cmd,
            output=full_output,
        )

        ScreenshotStep(
            "tester",
            caption="TC3 Step 2 — nmap ssh2-enum-algos scan shows supported key exchange and encryption algorithms on DUT port 22",
        ).execute(context)
        StepRunner([ClearTerminalStep("tester")]).run(context)

    # ── positive case ─────────────────────────────────────────────────────

    def _positive(self, context):
        ssh_cmd      = self._ssh_cmd(context)
        pass_prompts = context.profile.get_list("ssh.password_prompt")
        fail_prompts = context.profile.get_list("ssh.failure_prompt")
        success_p    = context.profile.get_list("ssh.success_prompt") or ["#", "$", ">"]

        StepRunner([
            PcapStartStep(interface="eth0", filename="tc3_ssh_positive.pcapng"),
            CommandStep("tester", ssh_cmd, settle_time=4),
        ]).run(context)

        pattern, _ = ExpectOneOfStep(
            "tester", pass_prompts + fail_prompts, timeout=12).execute(context)

        if pattern in fail_prompts:
            logger.error("TC3 Positive: SSH failed before password prompt")
            StepRunner([PcapStopStep()]).run(context)
            ScreenshotStep(
                "tester",
                caption="TC3 Step 3 — SSH connection attempt failed before password prompt (early rejection evidence)",
            ).execute(context)
            return False

        StepRunner([InputStep("tester", context.ssh_password)]).run(context)
        p2, _ = ExpectOneOfStep(
            "tester", success_p + fail_prompts, timeout=12).execute(context)

        StepRunner([PcapStopStep()]).run(context)
        ScreenshotStep(
            "tester",
            caption="TC3 Step 3 — SSH session established with correct credentials, DUT shell prompt received",
        ).execute(context)

        if p2 in fail_prompts:
            logger.error("TC3 Positive: DUT rejected correct credentials")
            StepRunner([SessionResetStep("tester", post_reset_delay=2)]).run(context)
            return False

        logger.info("TC3 Positive: SSH session established")
        StepRunner([
            AnalyzePcapStep("ssh"),
            WiresharkPacketScreenshotStep(
                "ssh",
                caption="TC3 Step 3 — Wireshark shows successful SSH handshake and encrypted session establishment",
            ),
            SessionResetStep("tester", post_reset_delay=2),
        ]).run(context)
        return True

    # ── negative case ─────────────────────────────────────────────────────

    def _negative(self, context):
        ssh_cmd  = self._ssh_cmd(context)
        bad_pass = context.profile.get("ssh.bad_password", "WrongPass@999!")
        
        # Priority order matters - put more specific patterns FIRST
        retry_msgs = [
            "Permission denied, please try again",
            "Permission denied",
            "Sorry, try again",
        ]
        
        final_fail_msgs = [
            "Permission denied (publickey,password)",
            "Too many authentication failures",
            "Disconnected",
            "Connection closed",
        ]
        
        # Password prompt - should be matched LAST
        pass_p = context.profile.get_list("ssh.password_prompt")
        
        # Combined list in PRIORITY order (most specific/important first)
        all_patterns = final_fail_msgs + retry_msgs + pass_p
        
        max_attempts = 3
        attempts = 0

        StepRunner([
            PcapStartStep(interface="eth0", filename="tc3_ssh_negative.pcapng"),
            CommandStep("tester", ssh_cmd, settle_time=4),
        ]).run(context)

        while attempts < max_attempts:
            pattern, _ = ExpectOneOfStep(
                "tester", all_patterns, timeout=15
            ).execute(context)

            # Check final failure FIRST (highest priority)
            if pattern in final_fail_msgs:
                logger.info("TC3 Negative: Final rejection — '%s'", pattern)

                StepRunner([PcapStopStep()]).run(context)
                ScreenshotStep(
                    "tester",
                    caption="TC3 Step 4 — DUT rejected SSH login after repeated wrong password attempts, connection closed",
                ).execute(context)

                StepRunner([
                    AnalyzePcapStep("ssh"),
                    WiresharkPacketScreenshotStep(
                        "ssh",
                        caption="TC3 Step 4 — Wireshark shows SSH disconnect packet confirming DUT terminated session after auth failures",
                    ),
                    ClearTerminalStep("tester"),
                ]).run(context)
                return True

            # Check retry messages next
            if pattern in retry_msgs:
                logger.info("TC3 Negative: Retry message received — '%s'", pattern)
                # After retry message, expect password prompt next
                # Continue loop to get the password prompt
                continue

            # Finally, check if it's a password prompt
            if pattern in pass_p:
                attempts += 1
                if attempts <= max_attempts:
                    logger.info(f"TC3 Negative: Attempt {attempts} - sending bad password")
                    StepRunner([InputStep("tester", bad_pass, settle_time=7)]).run(context)
                    continue
                else:
                    logger.error("TC3 Negative: Max attempts reached")
                    break

            # Unexpected pattern
            logger.error(f"TC3 Negative: Unexpected pattern '{pattern}'")
            break

        # If we exit the loop without proper rejection
        logger.error("TC3 Negative: Max attempts reached without proper rejection")

        StepRunner([PcapStopStep()]).run(context)
        ScreenshotStep(
            "tester",
            caption="TC3 Step 4 — FAIL: DUT did not reject SSH connection after maximum wrong password attempts",
        ).execute(context)
        StepRunner([ClearTerminalStep("tester")]).run(context)

        return False

    # ── entry point ────────────────────────────────────────────────────────

    def run(self, context):
        self._verify_ssh_enabled(context)
        self._nmap_scan(context)
        pos_ok = self._positive(context)
        neg_ok = self._negative(context)

        # Inter-TC cooldown
        # StepRunner([SessionResetStep("tester", post_reset_delay=4)]).run(context)

        self.pass_test() if (pos_ok and neg_ok) else self.fail_test()
        return self