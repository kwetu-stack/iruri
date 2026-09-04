import unittest

from app import create_app


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


if __name__ == "__main__":
    unittest.main()
