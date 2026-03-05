from adapters.base_adapter import BaseAdapter


class OpenWrtAdapter(BaseAdapter):

    def get_os_info(self):

        self.tm.run("dut", "cat /etc/openwrt_release")

        return self.tm.capture("dut")

    def check_root_login(self):

        self.tm.run("dut", "uci show dropbear")

        output = self.tm.capture("dut")

        if "PasswordAuth='off'" in output:
            return True

        return False

    def get_users(self):

        self.tm.run("dut", "cat /etc/passwd")

        return self.tm.capture("dut")