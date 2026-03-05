from adapters.linux_adapter import LinuxAdapter
from adapters.openwrt_adapter import OpenWrtAdapter
from adapters.cisco_adapter import CiscoAdapter


class AdapterFactory:

    @staticmethod
    def create(device_type, terminal_manager):

        if device_type == "linux":
            return LinuxAdapter(terminal_manager)

        if device_type == "openwrt":
            return OpenWrtAdapter(terminal_manager)

        if device_type == "cisco_ios":
            return CiscoAdapter(terminal_manager)

        raise Exception(f"No adapter available for {device_type}")