from utils.logger import logger
from runtime.context import RuntimeContext
from core.clause_runner import ClauseRunner
from terminal.manager import TerminalManager
from reporting.pdf_generator import DOCXGenerator
from browser.manager import BrowserManager


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

        logger.info("Runtime environment ready")

        runner = ClauseRunner(self.context)

        results = runner.run()

        for tc in results:
            logger.info(f"{tc.name} → {tc.status}")

        # Generate PDF report
        reporter = DOCXGenerator(self.context.evidence.run_dir)

        report_file = reporter.generate(self.context, results)

        logger.info(f"PDF report generated: {report_file}")

    def initialize_runtime(self):

        logger.info("Initializing runtime environment")

        # Initialize terminal manager
        self.context.terminal_manager = TerminalManager()
        self.context.browser = BrowserManager()

        tm = self.context.terminal_manager

        # Create shared terminals
        tm.create_terminal("tester")
        tm.create_terminal("dut")

        logger.info("Terminals created")

        logger.info("Terminal manager initialized")