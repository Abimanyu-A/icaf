from adapters.base_adapter import BaseAdapter


class CiscoAdapter(BaseAdapter):

    def get_os_info(self):

        self.tm.run("dut", "show version")

        return self.tm.capture("dut")

    def check_root_login(self):

        self.tm.run("dut", "show running-config")

        output = self.tm.capture("dut")

        if "no ip ssh" in output:
            return False

        return True

    def get_users(self):

        self.tm.run("dut", "show running-config | include username")

        return self.tm.capture("dut")