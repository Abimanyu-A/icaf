from utils.logger import logger
from config.settings import settings
from runtime.context import RuntimeContext
from terminal.manager import TerminalManager
from device.detector import DeviceDetector
from clauses.clause_1_1_1.clause import Clause_1_1_1
import time


class Engine:

    def __init__(self, clause=None, section=None, ssh_user=None, ssh_ip=None, ssh_password=None):

        self.context = RuntimeContext(
            clause=clause,
            section=section,
            ssh_user=ssh_user,
            ssh_ip=ssh_ip,
            ssh_password=ssh_password
        )

        logger.info("Engine initialized")

    def start(self):

        logger.info("Starting TCAF engine")

        logger.info(f"Execution ID: {self.context.execution_id}")

        if self.context.clause:
            logger.info(f"Execution mode: Clause {self.context.clause}")

        elif self.context.section:
            logger.info(f"Execution mode: Section {self.context.section}")

        else:
            logger.info("Execution mode: Full evaluation")

        self.initialize_runtime()
        
    def initialize_runtime(self):

        logger.info("Initializing runtime environment")

        # Initialize terminal manager
        self.context.terminal_manager = TerminalManager()

        tm = self.context.terminal_manager

        # Create terminals
        tm.create_terminal("dut")

        logger.info("Terminals created")
        self.context.clause = "clause_1_1_1"

        # Connect DUT via SSH
        # if self.context.ssh_command:
        #     logger.info("Connecting to DUT via SSH")

        #     tm.run("dut", self.context.ssh_command)
            
        #     time.sleep(3)
            
        #     detector = DeviceDetector(self.context.terminal_manager)

        #     device_type = detector.detect()

        #     self.context.device_type = device_type
            
        #     tm.screenshot("dut")

        #     logger.info(f"DUT device type: {device_type}")


        clause = Clause_1_1_1(self.context)

        results = clause.run()

        for tc in results:

            logger.info(f"{tc.name} → {tc.status}")

        logger.info("Runtime environment ready")