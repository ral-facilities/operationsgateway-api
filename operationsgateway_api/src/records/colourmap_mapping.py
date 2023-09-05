import json
from pathlib import Path
from typing import Dict, List

from operationsgateway_api.src.exceptions import ImageError


class ColourmapMapping:
    @staticmethod
    def get_colourmap_mappings() -> Dict[str, List[str]]:  # noqa: B902
        """
        Colourmaps are loaded from a categorised JSON file as there's nowhere in
        Matplotlib where's colourmaps grouped together. The categories (and which
        colourmaps go in them) have been used from the following article on matplotlib's
        website: https://matplotlib.org/stable/tutorials/colors/colormaps.html.

        The mappings are alphabetically ordered so that no matter the ordering in the
        JSON file, the API will store the colourmaps in the same order. The mapping is
        stored in FalseColourHandler.colourmap_names so this function only needs to be
        executed once.
        """

        try:
            with open(
                Path(__file__).parent / "colourmap_mapping.json",
            ) as mapping_file:
                colourmap_mapping = json.load(mapping_file)
        except OSError as exc:
            raise ImageError("Cannot open colourmap mapping file") from exc

        ordered_data = {}
        for key in sorted(colourmap_mapping.keys()):
            ordered_data[key] = sorted(colourmap_mapping[key], key=str.casefold)

        return ordered_data

    @staticmethod
    def is_colourmap_available(
        colourmap_mapping: Dict[str, List[str]],
        colourmap_name: str,
    ) -> bool:
        """
        Search through colourmap mapping stored in `colourmap_names` and see if the
        given colourmap is one that's present in Matplotlib
        """

        for colourmaps in colourmap_mapping.values():
            if colourmap_name in colourmaps:
                return True

        return False
