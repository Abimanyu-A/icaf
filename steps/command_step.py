from core.step import Step


class CommandStep(Step):

    def __init__(self, terminal, command):

        super().__init__(f"Run command: {command}")

        self.terminal = terminal
        self.command = command

    def execute(self, context):

        tm = context.terminal_manager

        tm.run(self.terminal, self.command)