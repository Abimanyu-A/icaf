from utils.logger import logger


class StepRunner:

    def __init__(self, steps):
        self.steps = steps

    def run(self, context):

        for step in self.steps:

            logger.info(f"Running step: {step.name}")

            step.execute(context)