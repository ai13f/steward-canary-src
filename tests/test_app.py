import tempfile
import unittest
from pathlib import Path

from app import migrate, schema, server


class MigrateTest(unittest.TestCase):
    def test_fresh_volume_migrates_to_the_build_schema(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(migrate.upgrade(Path(d), schema.SCHEMA_VERSION), schema.SCHEMA_VERSION)

    def test_newer_volume_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "schema").write_text(str(schema.SCHEMA_VERSION + 1))
            with self.assertRaises(migrate.SchemaTooNew):
                migrate.upgrade(Path(d), schema.SCHEMA_VERSION)


class StatusTest(unittest.TestCase):
    def test_status_payload_fields(self):
        payload = server.status_payload()
        for key in ("uptime_s", "ticks", "schema_version", "version", "started_at"):
            self.assertIn(key, payload)
        self.assertEqual(payload["schema_version"], schema.SCHEMA_VERSION)


if __name__ == "__main__":
    unittest.main()
