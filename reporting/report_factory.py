from reporting.clause_reports.clause_1_1_1_report import Clause111Report

class ReportFactory:

    @staticmethod
    def create(context, results):

        clause = context.clause

        if clause == "1.1.1":
            return Clause111Report(context, results)

        raise Exception(f"No report template for clause {clause}")