import unittest

import candidate


class NormalizeTests(unittest.TestCase):
    def test_nonempty_value(self) -> None:
        self.assertEqual(candidate.normalize("  Alpha "), "alpha")


if __name__ == "__main__":
    unittest.main()
