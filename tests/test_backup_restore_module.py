import unittest

from app import create_app
from app.admin.models import SystemBackup


class BackupRestoreModuleTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.app.config["LOGIN_DISABLED"] = True
        self.client = self.app.test_client()

    def test_system_backup_model_contract(self):
        self.assertEqual(SystemBackup.__tablename__, "system_backups")
        self.assertTrue(SystemBackup.backup_number.property.columns[0].unique)
        self.assertEqual(SystemBackup.status.property.columns[0].default.arg, "Completed")
        self.assertEqual(
            next(iter(SystemBackup.created_by.property.columns[0].foreign_keys)).target_fullname,
            "users.id",
        )

    def test_backup_routes_are_registered(self):
        self.assertIn("admin.backups_index", self.app.view_functions)
        self.assertIn("admin.backup_create", self.app.view_functions)
        self.assertIn("admin.backup_detail", self.app.view_functions)
        self.assertIn("admin.backup_notes", self.app.view_functions)

    def test_backup_module_requires_backup_manage_permission(self):
        response = self.client.get("/admin/backups")
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
