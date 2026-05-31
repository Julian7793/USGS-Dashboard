import unittest
from unittest.mock import Mock, patch

from scraper import _format_usace_precipitation, fetch_usace_brookville_data


class FormatUsacePrecipitationTest(unittest.TestCase):
    def test_negative_precipitation_sentinel_displays_as_zero(self):
        self.assertEqual(_format_usace_precipitation(-901, "in"), "0 in")

    def test_positive_precipitation_keeps_value_and_unit(self):
        self.assertEqual(_format_usace_precipitation(1.25, "in"), "1.25 in")


class FetchUsaceBrookvilleDataTest(unittest.TestCase):
    @patch("scraper.requests.get")
    def test_inflow_and_outflow_timeseries_ids_are_returned(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "timeseries": [
                    {
                        "label": "Inflow",
                        "latest_value": 100,
                        "unit": "cfs",
                        "delta24hr": 12,
                        "tsid": "Brookville.Flow-Inflow.Ave.1Hour.6Hours.lrldlb-comp",
                    },
                    {
                        "label": "Outflow",
                        "latest_value": 90,
                        "unit": "cfs",
                        "delta24hr": -2,
                        "tsid": "Brookville.Flow-Outflow.Ave.1Hour.1Hour.lrldlb-comp",
                    },
                ]
            }
        ]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        data = fetch_usace_brookville_data()

        self.assertEqual(
            data["inflow_tsid"],
            "Brookville.Flow-Inflow.Ave.1Hour.6Hours.lrldlb-comp",
        )
        self.assertEqual(
            data["outflow_tsid"],
            "Brookville.Flow-Outflow.Ave.1Hour.1Hour.lrldlb-comp",
        )


if __name__ == "__main__":
    unittest.main()
