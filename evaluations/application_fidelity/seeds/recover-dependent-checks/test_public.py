import unittest

import candidate


class RecoveryTests(unittest.TestCase):
    def test_single_check(self) -> None:
        self.assertEqual(candidate.recover({"x": {"reads": ["a"]}}, ["a"]), {"invalidated": ["x"], "retained": []})
