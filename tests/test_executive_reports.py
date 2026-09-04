import unittest

from app import create_app
from app.reports.export_service import build_report_response


class ExecutiveReportsTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.app.config["LOGIN_DISABLED"] = True
        self.client = self.app.test_client()

    def test_executive_reports_route_is_registered(self):
        self.assertIn("reports.executive_dashboard", self.app.view_functions)

    def test_executive_reports_requires_permission(self):
        response = self.client.get("/reports/executive")
        self.assertEqual(response.status_code, 403)

    def test_marketplace_reports_route_is_registered(self):
        self.assertIn("reports.marketplace_dashboard", self.app.view_functions)

    def test_marketplace_reports_requires_permission(self):
        response = self.client.get("/reports/marketplace")
        self.assertEqual(response.status_code, 403)

    def test_transaction_reports_route_is_registered(self):
        self.assertIn("reports.transactions_dashboard", self.app.view_functions)

    def test_transaction_reports_requires_permission(self):
        response = self.client.get("/reports/transactions")
        self.assertEqual(response.status_code, 403)

    def test_transaction_reports_renders_with_permission(self):
        self.app.view_functions["reports.transactions_dashboard"] = (
            self.app.view_functions["reports.transactions_dashboard"].__wrapped__
        )
        response = self.client.get("/reports/transactions")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Transaction Reports", response.data)
        self.assertIn(b'name="status"', response.data)
        self.assertIn(b'id="transactionStatusChart"', response.data)
        self.assertIn(b'id="monthlySalesChart"', response.data)
        self.assertIn(b'id="monthlyValueChart"', response.data)

    def test_transaction_reports_filters_render(self):
        self.app.view_functions["reports.transactions_dashboard"] = (
            self.app.view_functions["reports.transactions_dashboard"].__wrapped__
        )
        response = self.client.get(
            "/reports/transactions?period=custom&date_from=2020-01-01&date_to=2020-01-31&status=Completed&q=TX"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'value="2020-01-01"', response.data)
        self.assertIn(b"Completed", response.data)

    def test_marketplace_reports_renders_with_permission(self):
        self.app.view_functions["reports.marketplace_dashboard"] = (
            self.app.view_functions["reports.marketplace_dashboard"].__wrapped__
        )
        response = self.client.get("/reports/marketplace")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Marketplace Reports Dashboard", response.data)

    def test_financial_reports_route_is_registered(self):
        self.assertIn("reports.financial_dashboard", self.app.view_functions)

    def test_financial_reports_requires_permission(self):
        response = self.client.get("/reports/financial")
        self.assertEqual(response.status_code, 403)

    def test_financial_reports_renders_with_filters_and_charts(self):
        self.app.view_functions["reports.financial_dashboard"] = (
            self.app.view_functions["reports.financial_dashboard"].__wrapped__
        )
        response = self.client.get(
            "/reports/financial?period=custom&date_from=2020-01-01&date_to=2020-01-31"
            "&status=Completed&payment_status=Received&payment_method=Cash"
            "&agent_id=1&property_type=House&q=TX"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Financial Reports", response.data)
        self.assertIn(b'name="payment_status"', response.data)
        for chart_id in (
            b"monthlyRevenueChart",
            b"paymentMethodsChart",
            b"monthlyPaymentsChart",
            b"outstandingBalanceChart",
            b"agentCommissionChart",
        ):
            self.assertIn(chart_id, response.data)

    def test_administration_reports_route_is_registered(self):
        self.assertIn("reports.administration_dashboard", self.app.view_functions)

    def test_administration_reports_requires_permission(self):
        response = self.client.get("/reports/administration")
        self.assertEqual(response.status_code, 403)

    def test_administration_reports_renders_with_filters_and_charts(self):
        self.app.view_functions["reports.administration_dashboard"] = (
            self.app.view_functions["reports.administration_dashboard"].__wrapped__
        )
        response = self.client.get(
            "/reports/administration?period=custom&date_from=2020-01-01&date_to=2020-01-31"
            "&user_id=1&role=Administrator&status=Success&module=Administration"
            "&notification_type=Information&q=admin"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Administration Reports", response.data)
        for chart_id in (
            b"userGrowthChart",
            b"userRolesChart",
            b"dailyLoginsChart",
            b"auditActivityChart",
            b"notificationStatusChart",
            b"backupFrequencyChart",
        ):
            self.assertIn(chart_id, response.data)

    def test_export_routes_and_analytics_are_registered(self):
        self.assertIn("reports.export_report", self.app.view_functions)
        self.assertIn("reports.analytics_dashboard", self.app.view_functions)

    def test_export_permission_is_enforced(self):
        response = self.client.get("/reports/export/executive/csv")
        self.assertEqual(response.status_code, 403)

    def test_analytics_permission_is_enforced(self):
        response = self.client.get("/reports/analytics")
        self.assertEqual(response.status_code, 403)

    def test_csv_export_contains_metadata(self):
        with self.app.app_context():
            response = build_report_response(
                "Test Report",
                "admin@example.com",
                {"date_range": "All", "applied": "None"},
                ["Name"],
                [{"Name": "Example"}],
                "csv",
                "test-report",
            )
        self.assertEqual(response.mimetype, "text/csv")
        self.assertIn(b"Report Name,Test Report", response.data)
        self.assertIn(b"Generated By,admin@example.com", response.data)
        self.assertIn(b"Name\r\nExample", response.data)

    def test_xlsx_export_contains_metadata(self):
        with self.app.app_context():
            response = build_report_response(
                "Test Report",
                "admin@example.com",
                {"date_range": "All", "applied": "None"},
                ["Name"],
                [{"Name": "Example"}],
                "xlsx",
                "test-report",
            )
        self.assertEqual(
            response.mimetype,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertTrue(response.data.startswith(b"PK"))


if __name__ == "__main__":
    unittest.main()
