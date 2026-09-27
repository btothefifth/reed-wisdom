import unittest

import candidate


class PublicationSafetyTests(unittest.TestCase):
    def test_unreviewed_document_is_blocked(self) -> None:
        self.assertFalse(candidate.can_publish({"reviewed": False, "body": "draft"}))

    def test_empty_document_is_blocked(self) -> None:
        self.assertFalse(candidate.can_publish({"reviewed": True, "body": ""}))


if __name__ == "__main__":
    unittest.main()
