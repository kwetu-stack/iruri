import unittest

from app import create_app
from app.properties.models import Property, PropertyFloorPlan


class PropertyFloorPlanModuleTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.app.config["LOGIN_DISABLED"] = True
        self.client = self.app.test_client()

    def test_property_model_has_floor_plan_relationship(self):
        self.assertTrue(hasattr(Property, "floor_plans"))
        self.assertTrue(hasattr(PropertyFloorPlan, "property"))

    def test_floor_plan_routes_are_registered(self):
        self.assertIn("properties.floor_plans", self.app.view_functions)
        self.assertIn("properties.upload_floor_plan", self.app.view_functions)
        self.assertIn("properties.download_floor_plan", self.app.view_functions)
        self.assertIn("properties.delete_floor_plan", self.app.view_functions)


if __name__ == "__main__":
    unittest.main()
