import uuid
from datetime import datetime
from evidence.manager import EvidenceManager


class RuntimeContext:
    """
    Shared runtime state used across the TCAF framework.
    """

    def __init__(self, clause=None, section=None, ssh_user=None, ssh_ip=None, ssh_password=None):

        self.execution_id = str(uuid.uuid4())

        self.start_time = datetime.utcnow()

        # CLI parameters
        self.clause = clause
        self.section = section
        self.ssh_user = ssh_user
        self.ssh_ip = ssh_ip
        self.ssh_password = ssh_password

        # Core subsystems (initialized later)
        self.ssh_connection = None
        self.terminal_manager = None

        # Device information
        self.device_type = None
        self.device_info = {}

        # Adapter
        self.adapter = None

        # Evidence tracking
        self.evidence = EvidenceManager()

        self.current_testcase = None

    def summary(self):
        """
        Return basic execution summary.
        """

        return {
            "execution_id": self.execution_id,
            "clause": self.clause,
            "section": self.section,
            "device_type": self.device_type,
            "start_time": str(self.start_time),
        }