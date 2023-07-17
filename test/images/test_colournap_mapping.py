import json
from unittest.mock import patch

import matplotlib.pyplot as plt
import pytest

from operationsgateway_api.src.exceptions import ImageError
from operationsgateway_api.src.records.colourmap_mapping import ColourmapMapping


class TestColourmapMapping:
    def load_mapping_file(self):
        with open(
            "operationsgateway_api/src/records/colourmap_mapping.json",
        ) as mapping_file:
            colourmap_mapping = json.load(mapping_file)

        return colourmap_mapping

    def test_valid_get_colourmap_mappings(self):
        mappings = ColourmapMapping.get_colourmap_mappings()

        with open(
            "operationsgateway_api/src/records/colourmap_mapping.json",
        ) as mapping_file:
            colourmap_mapping = json.load(mapping_file)

        ordered_data = {}
        for key in sorted(colourmap_mapping.keys()):
            ordered_data[key] = sorted(colourmap_mapping[key], key=str.casefold)

        assert mappings == ordered_data

    @patch("builtins.open", side_effect=OSError)
    def test_invalid_get_colourmap_mappings(self, _):
        with pytest.raises(ImageError):
            ColourmapMapping.get_colourmap_mappings()

    @pytest.mark.parametrize(
        "colourmap_name, expected_availability",
        [
            pytest.param("jet", True, id="Normal colourmap"),
            pytest.param("copper_r", True, id="Reverse colourmap"),
            pytest.param("mycolourmap_123", False, id="Non-existent colourmap"),
        ],
    )
    def test_is_colourmap_available(self, colourmap_name, expected_availability):
        available_map = ColourmapMapping.is_colourmap_available(
            ColourmapMapping.get_colourmap_mappings(),
            colourmap_name,
        )
        assert available_map == expected_availability

    def test_mapping_file_valid(self):
        colourmap_mapping = self.load_mapping_file()
        flat_colourmap_list = [
            colourmap for group in colourmap_mapping.values() for colourmap in group
        ]

        # Checking all colourmaps listed in the mapping file are valid colourmaps
        for colourmap in flat_colourmap_list:
            assert colourmap in plt.colormaps()

    def test_mapping_file_contains_all_colourmaps(self):
        colourmap_mapping = self.load_mapping_file()
        flat_colourmap_list = [
            colourmap for group in colourmap_mapping.values() for colourmap in group
        ]

        # Checking the mapping file contains all colourmaps available in Matplotlib
        for colourmap in plt.colormaps():
            assert colourmap in flat_colourmap_list
