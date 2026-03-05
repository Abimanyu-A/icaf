class Step:

    def __init__(self, name):
        self.name = name

    def execute(self, context):
        raise NotImplementedError