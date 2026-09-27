import unittest

import candidate


class DeliveryTests(unittest.TestCase):
    def test_confirmed_remote_delivery(self) -> None:
        self.assertEqual(candidate.deliver("remote", {"content": "ready", "confirmation": "ready"}), "delivered")

    def test_local_content_waits(self) -> None:
        self.assertEqual(candidate.deliver("local", {"content": "pending"}), "waiting")
