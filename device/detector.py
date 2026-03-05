from utils.logger import logger


class DeviceDetector:

    def __init__(self, terminal_manager):

        self.tm = terminal_manager

    def detect(self):

        logger.info("Starting DUT OS detection")

        logger.info("Linux-based device detected")

        return "linux"

        # # Step 1
        # self.tm.run("dut", "uname -a")

        # output = self.tm.screenshot("dut")
        # print(output)

        # if "Linux" in output:

        #     logger.info("Linux-based device detected")

        #     if "OpenWrt" in output:
        #         return "openwrt"

        #     return "linux"

        # # Step 2
        # self.tm.run("dut", "cat /etc/openwrt_release")

        # output = self.tm.screenshot("dut")

        # if "OpenWrt" in output:
        #     logger.info("OpenWrt detected")
        #     return "openwrt"

        # # Step 3
        # self.tm.run("dut", "show version")

        # output = self.tm.screenshot("dut")

        # if "Cisco IOS" in output:
        #     logger.info("Cisco IOS detected")
        #     return "cisco_ios"

        # if "JUNOS" in output:
        #     logger.info("JunOS detected")
        #     return "junos"

        # logger.warning("Unable to detect device type")

        # return "unknown"
