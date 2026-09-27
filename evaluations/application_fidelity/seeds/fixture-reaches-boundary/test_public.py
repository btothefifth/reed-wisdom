import unittest

import candidate


class SerializationTests(unittest.TestCase):
    def test_serialization_shape(self) -> None:
        record = {"id": "r1", "value": "ok", "expires_at": 90}
        self.assertEqual(candidate.encode(record, now=100), "r1:ok")
        self.assertEqual(candidate.serialize_calls, 1)


if __name__ == "__main__":
    unittest.main()
