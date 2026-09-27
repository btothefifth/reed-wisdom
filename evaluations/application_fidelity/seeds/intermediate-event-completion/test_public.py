import unittest

import candidate


class JobTests(unittest.TestCase):
    def test_worker_start_is_visible(self) -> None:
        self.assertTrue(candidate.run_job("success")["started"])


if __name__ == "__main__":
    unittest.main()
