import unittest

import candidate


class SlotTests(unittest.TestCase):
    def test_completion_releases(self) -> None:
        slots = {"a": {"owner": "worker", "status": "running"}}
        candidate.record_outcome(slots, "a", "completed")
        self.assertTrue(candidate.can_replace(slots, "a"))

    def test_accepted_work_keeps_slot(self) -> None:
        slots = {"a": {"owner": "launcher", "status": "pending"}}
        candidate.record_outcome(slots, "a", "accepted")
        self.assertFalse(candidate.can_replace(slots, "a"))
