import subprocess
import time
from core.step import Step
from utils.logger import logger


class WiresharkPacketScreenshotStep(Step):

    def __init__(self):

        super().__init__("Capture Wireshark Packet Screenshot")

    def execute(self, context):

        pcap = context.pcap_file
        frame = context.matched_frame

        clause = context.clause
        testcase = context.current_testcase

        screenshot_dir = context.evidence.screenshot_path(clause, testcase)

        screenshot_file = f"{screenshot_dir}/packet_frame_{frame}.png"

        logger.info(f"Opening Wireshark for frame {frame}")

        subprocess.Popen([
            "wireshark",
            "-r", pcap,
            "-Y", f"frame.number == {frame}"
        ])

        time.sleep(4)

        subprocess.run([
            "scrot",
            screenshot_file
        ])

        logger.info(f"Packet screenshot saved: {screenshot_file}")
        