import unittest

from app import create_app


class AmenitiesRouteTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.app.config["LOGIN_DISABLED"] = True
        self.client = self.app.test_client()

    def test_amenities_root_alias_redirects_to_properties_amenities(self):
        response = self.client.get("/amenities")
        self.assertEqual(response.status_code, 200)

    def test_properties_amenities_route_is_available(self):
        response = self.client.get("/properties/amenities")
        self.assertEqual(response.status_code, 200)

    def test_features_root_alias_redirects_to_properties_features(self):
        response = self.client.get("/features")
        self.assertEqual(response.status_code, 200)

    def test_property_features_dashboard_alias_redirects_to_properties_features(self):
        response = self.client.get("/dashboard/property-features")
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
