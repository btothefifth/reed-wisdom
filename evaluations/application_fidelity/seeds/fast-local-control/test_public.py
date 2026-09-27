import unittest

import candidate


class IncrementTests(unittest.TestCase):
    def test_zero(self) -> None:
        self.assertEqual(candidate.increment(0), 1)


if __name__ == "__main__":
    unittest.main()
