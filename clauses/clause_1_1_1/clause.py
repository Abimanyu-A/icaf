from core.clause import BaseClause
from .tc1_ssh_first_connection import TC1SSHFirstConnection
from .tc2_ssh_valid_credentials import TC2SSHValidCredentials
from .tc3_ssh_invalid_credentials import TC3SSHInvalidCredentials
from .tc4_https_auth_prompt import TC4HTTPSAuthPrompt

class Clause_1_1_1(BaseClause):

    def __init__(self, context):

        super().__init__(context)

        self.add_testcase(TC1SSHFirstConnection())
        self.add_testcase(TC2SSHValidCredentials())
        self.add_testcase(TC3SSHInvalidCredentials())
        self.add_testcase(TC4HTTPSAuthPrompt())