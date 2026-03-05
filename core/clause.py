class BaseClause:

    def __init__(self, context):

        self.context = context
        self.testcases = []

    def add_testcase(self, tc):

        self.testcases.append(tc)

    def run(self):

        results = []

        for tc in self.testcases:

            result = tc.run(self.context)

            results.append(result)

        return results