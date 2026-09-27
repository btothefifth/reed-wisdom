import unittest

import candidate


class PrimaryGateTests(unittest.TestCase):
    def test_primary_rejects_pending(self) -> None:
        self.assertFalse(candidate.primary_can_act("pending"))

    def test_primary_accepts_ready(self) -> None:
        self.assertTrue(candidate.primary_can_act("ready"))


if __name__ == "__main__":
    unittest.main()
