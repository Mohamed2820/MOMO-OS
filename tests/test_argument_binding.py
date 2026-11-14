import unittest

from intelligence.runtime.argument_binding import (
    ArgumentBindingError,
    canonical_arguments,
    parse_and_bind,
    parse_arguments,
)


class ArgumentBindingTests(unittest.TestCase):
    def test_object_key_order_does_not_change_digest(self):
        left = parse_and_bind('{"z":2,"a":1}')
        right = parse_and_bind('{"a":1,"z":2}')
        self.assertEqual(left[1], right[1])
        self.assertEqual(left[2], right[2])

    def test_unicode_is_canonicalized_as_utf8(self):
        arguments, encoded, digest = parse_and_bind('{"message":"مرحبا"}')
        self.assertEqual(arguments["message"], "مرحبا")
        self.assertIn("مرحبا", encoded)
        self.assertEqual(len(digest), 64)

    def test_duplicate_object_keys_are_rejected(self):
        with self.assertRaises(ArgumentBindingError):
            parse_arguments('{"path":"safe","path":"unsafe"}')

    def test_non_standard_numbers_are_rejected(self):
        for payload in ('{"value":NaN}', '{"value":Infinity}', '{"value":-Infinity}'):
            with self.subTest(payload=payload), self.assertRaises(ArgumentBindingError):
                parse_arguments(payload)

    def test_root_must_be_an_object(self):
        with self.assertRaises(ArgumentBindingError):
            parse_arguments('[1,2,3]')

    def test_invalid_utf8_is_rejected(self):
        with self.assertRaises(ArgumentBindingError):
            parse_arguments(b'{"x":"\xff"}')

    def test_lone_surrogate_text_is_rejected(self):
        with self.assertRaises(ArgumentBindingError):
            parse_arguments('{"x":"\\ud800"}')
        with self.assertRaises(ArgumentBindingError):
            canonical_arguments({"x": "\\ud800"})

    def test_payload_size_is_bounded(self):
        with self.assertRaises(ArgumentBindingError):
            parse_arguments('{"x":"' + ('a' * 100) + '"}', max_bytes=32)

    def test_integer_range_is_bounded(self):
        with self.assertRaises(ArgumentBindingError):
            canonical_arguments({"x": 1 << 63})

    def test_non_string_object_keys_are_rejected(self):
        with self.assertRaises(ArgumentBindingError):
            canonical_arguments({1: "not-json"})

    def test_unsupported_python_values_are_rejected(self):
        with self.assertRaises(ArgumentBindingError):
            canonical_arguments({"x": object()})

    def test_nesting_depth_is_bounded(self):
        value = {}
        current = value
        for _ in range(34):
            current["next"] = {}
            current = current["next"]
        with self.assertRaises(ArgumentBindingError):
            canonical_arguments(value)

    def test_float_must_be_finite(self):
        with self.assertRaises(ArgumentBindingError):
            canonical_arguments({"x": float("nan")})


if __name__ == "__main__":
    unittest.main()
