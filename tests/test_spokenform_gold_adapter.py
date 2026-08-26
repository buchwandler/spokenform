import unittest

from benchmarks.spokenform_gold_adapter import prepare_gold_record
from spokenform import prepare


class SpokenformGoldAdapterTests(unittest.TestCase):
    def test_adapter_uses_frozen_profile_and_returns_plain_text(self):
        profile = {
            "name": "gold-v1",
            "prepare_kwargs": {
                "use_spacy": False,
                "normalize_literals": True,
                "sequence_fallback_mode": "preserve",
            },
        }
        text = "The value is 2."
        output = prepare_gold_record(text, "en", "en-US", profile)
        expected = prepare(
            text,
            language="en",
            use_spacy=False,
            normalize_literals=True,
            sequence_fallback_mode="preserve",
        ).spoken_text
        self.assertEqual(output, expected)
        self.assertIsInstance(output, str)

    def test_adapter_rejects_missing_profile(self):
        with self.assertRaisesRegex(ValueError, "gold-v1"):
            prepare_gold_record("Hello", "en", "en-US", None)

    def test_adapter_rejects_language_locale_mismatch(self):
        with self.assertRaisesRegex(ValueError, "does not match locale"):
            prepare_gold_record("Hallo", "de", "en-US", {})


if __name__ == "__main__":
    unittest.main()
