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


if __name__ == "__main__":
    unittest.main()
