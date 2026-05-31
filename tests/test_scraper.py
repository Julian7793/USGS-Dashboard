import unittest

from scraper import _format_usace_precipitation


class FormatUsacePrecipitationTest(unittest.TestCase):
    def test_negative_precipitation_sentinel_displays_as_zero(self):
        self.assertEqual(_format_usace_precipitation(-901, "in"), "0 in")

    def test_positive_precipitation_keeps_value_and_unit(self):
        self.assertEqual(_format_usace_precipitation(1.25, "in"), "1.25 in")


if __name__ == "__main__":
    unittest.main()
