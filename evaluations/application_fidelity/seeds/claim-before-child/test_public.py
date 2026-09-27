import unittest

import candidate


class LaunchTests(unittest.TestCase):
    def test_created_child_receives_claim(self) -> None:
        registry = {}
        self.assertEqual(
            candidate.launch(registry, "c1", serialize_ok=True, creation="created"),
            "created",
        )
        self.assertEqual(registry["c1"], "child")


if __name__ == "__main__":
    unittest.main()
