class BaseAdapter:
    """
    Base adapter class for all device types.
    """

    def __init__(self, terminal_manager):

        self.tm = terminal_manager

    def get_os_info(self):
        raise NotImplementedError

    def check_root_login(self):
        raise NotImplementedError

    def get_users(self):
        raise NotImplementedError