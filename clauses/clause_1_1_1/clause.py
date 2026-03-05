from core.clause import BaseClause
from .tc1_ssh_first_connection import TC1SSHFirstConnection


class Clause_1_1_1(BaseClause):

    def __init__(self, context):

        super().__init__(context)

        self.add_testcase(TC1SSHFirstConnection())