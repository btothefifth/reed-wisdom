import unittest

import candidate


class NormalizerTests(unittest.TestCase):
    def test_direct_examples(self) -> None:
        self.assertEqual(candidate.normalize(None), "")
        self.assertEqual(candidate.normalize("  Alpha "), "alpha")
        self.assertEqual(candidate.normalize(""), "")
