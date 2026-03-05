from terminal.visible_terminal import VisibleTerminal


class TerminalFactory:

    @staticmethod
    def create(name: str, terminal_type="visible"):

        if terminal_type == "visible":
            return VisibleTerminal(name)

        raise Exception(f"Unknown terminal type: {terminal_type}")