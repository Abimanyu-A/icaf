from adapters.base_adapter import BaseAdapter
from utils.logger import logger


class LinuxAdapter(BaseAdapter):

    def get_os_info(self):

        self.tm.run("dut", "cat /etc/os-release")

        return self.tm.capture("dut")

    def check_root_login(self):

        logger.info("Checking root login configuration")

        self.tm.run("dut", "grep PermitRootLogin /etc/ssh/sshd_config")

        output = self.tm.capture("dut")

        if "no" in output:
            return True

        return False

    def get_users(self):

        self.tm.run("dut", "cut -d: -f1 /etc/passwd")

        return self.tm.capture("dut")