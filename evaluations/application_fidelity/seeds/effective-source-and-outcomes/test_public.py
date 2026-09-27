import unittest

import candidate


class PlannerTests(unittest.TestCase):
    def test_explicit_clock(self) -> None:
        planner = candidate.Planner(lambda: 42)
        self.assertEqual(planner.timestamp(), 42)

    def test_enabled_job_count(self) -> None:
        destinations = [("east", True), ("west", True), ("north", True)]
        self.assertEqual(len(candidate.jobs(destinations)), 2)


if __name__ == "__main__":
    unittest.main()
