import tempfile
import unittest
from pathlib import Path

from app import fmt, migrate, schema, server


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


class FormatTest(unittest.TestCase):
    def test_newer_format_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "format").write_text(str(fmt.FORMAT + 1))
            with self.assertRaises(fmt.FormatTooNew):
                fmt.check(Path(d))

    def test_missing_format_is_format_1(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(fmt.check(Path(d)), 1)


class ItemsTest(unittest.TestCase):
    def test_items_are_counted_from_the_volume(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "items.log").write_text("1.5\n2.5\n")
            saved, server.DATA = server.DATA, Path(d)
            try:
                self.assertEqual(server.load_items(), 2)
            finally:
                server.DATA = saved


if __name__ == "__main__":
    unittest.main()
