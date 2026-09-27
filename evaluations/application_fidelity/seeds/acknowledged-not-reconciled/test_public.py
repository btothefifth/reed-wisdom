import unittest

import candidate


class CancellationTests(unittest.TestCase):
    def test_successful_request_records_progress(self) -> None:
        state = {"cancel_state": "active", "occupied": True}
        candidate.acknowledge_cancel(state, 200)
        self.assertNotEqual(state["cancel_state"], "active")


if __name__ == "__main__":
    unittest.main()
