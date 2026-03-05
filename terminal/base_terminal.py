class BaseTerminal:
    """
    Base class for all terminal types.
    """

    def __init__(self, name: str):
        self.name = name

    def run(self, command: str):
        raise NotImplementedError

    def capture(self):
        raise NotImplementedError