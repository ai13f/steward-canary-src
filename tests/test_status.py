import time
import unittest

from app import status


class UptimeTest(unittest.TestCase):
    def test_uptime_is_seconds(self):
        self.assertAlmostEqual(status.uptime_s(time.monotonic() - 5), 5, delta=1)


if __name__ == "__main__":
    unittest.main()
