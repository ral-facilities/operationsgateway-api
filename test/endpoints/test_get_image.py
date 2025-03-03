import io
import json
from urllib.parse import quote

from fastapi.testclient import TestClient
import imagehash
from PIL import Image
import pytest

from test.conftest import set_preferred_colourmap, unset_preferred_colourmap


class TestGetImage:
    @pytest.mark.parametrize(
        [
            "record_id",
            "channel_name",
            "original_image",
            "use_preferred_colourmap",
            "lower_level",
            "upper_level",
            "limit_bit_depth",
            "colourmap_name",
            "expected_image_phash",
        ],
        [
            pytest.param(
                "20230605100000",
                "FE-204-NSO-P1-CAM-1",
                True,
                False,
                None,
                None,
                None,
                None,
                "c8b624a4275e37b5",
                id="Original image",
            ),
            pytest.param(
                "20230605100000",
                "FE-204-NSO-P1-CAM-1",
                False,
                False,
                None,
                None,
                None,
                None,
                "c4073b6f3832c799",
                id="Image with default false colour settings",
            ),
            # repeat the above test but with the user's preferred colour map set to
            # check that the preference is used when no specific map is chosen
            pytest.param(
                "20230605100000",
                "FE-204-NSO-P1-CAM-1",
                False,
                True,
                None,
                None,
                None,
                None,
                "c417386737333a1b",
                id="Image using user's preferred colourmap",
            ),
            pytest.param(
                "20230605100000",
                "FE-204-NSO-P1-CAM-1",
                None,
                False,
                50,
                200,
                None,
                "jet_r",
                "8000000000000000",
                id="Image with all false colour params specified",
            ),
            # repeat the test above but with the user's preferred colour map set to
            # ensure that it is ignored and the specified colour map used
            pytest.param(
                "20230605100000",
                "FE-204-NSO-P1-CAM-1",
                None,
                True,
                50,
                200,
                None,
                "jet_r",
                "8000000000000000",
                id="Image with all false colour params specified (ignoring "
                "user's pref)",
            ),
            pytest.param(
                "20230606120000",
                "CM-202-CVC-CAM-1",
                True,
                False,
                None,
                None,
                None,
                None,
                "d5aa5455525542fd",
                id="v1.1 12 bit image, original",
            ),
            pytest.param(
                "20230606120000",
                "CM-202-CVC-CAM-1",
                None,
                False,
                32,
                63,
                8,
                "jet_r",
                "c37e0c3330db33cc",
                id="v1.1 12 bit image, limits in 8 bit",
            ),
            pytest.param(
                "20230606120000",
                "CM-202-CVC-CAM-1",
                None,
                False,
                512,
                1023,
                12,
                "jet_r",
                "c37e0c3330db33cc",
                id="v1.1 12 bit image, limits in 12 bit",
            ),
        ],
    )
    @pytest.mark.parametrize(
        "functions",
        [
            pytest.param(
                None,
                id="Functions undefined",
            ),
            pytest.param(
                {"name": "a"},
                id="Functions defined",
            ),
        ],
    )
    def test_valid_get_image(
        self,
        test_app: TestClient,
        login_and_get_token,
        record_id,
        channel_name,
        original_image,
        use_preferred_colourmap,
        lower_level,
        upper_level,
        limit_bit_depth,
        colourmap_name,
        expected_image_phash,
        functions: "dict[str, str]",
    ):
        set_preferred_colourmap(test_app, login_and_get_token, use_preferred_colourmap)

        query_string = ""
        query_params_array = []

        if original_image is not None:
            # allow setting of "original_image=False"
            query_params_array.append(f"original_image={original_image}")
        if lower_level:
            query_params_array.append(f"lower_level={lower_level}")
        if upper_level:
            query_params_array.append(f"upper_level={upper_level}")
        if limit_bit_depth:
            query_params_array.append(f"limit_bit_depth={limit_bit_depth}")
        if colourmap_name:
            query_params_array.append(f"colourmap_name={colourmap_name}")
        if functions:
            functions["expression"] = channel_name
            query_params_array.append(f"functions={quote(json.dumps(functions))}")
            channel_name = functions["name"]

        if len(query_params_array) > 0:
            query_string = "?" + "&".join(query_params_array)

        test_response = test_app.get(
            f"/images/{record_id}/{channel_name}{query_string}",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        unset_preferred_colourmap(
            test_app,
            login_and_get_token,
            use_preferred_colourmap,
        )

        assert test_response.status_code == 200, test_response.content.decode()

        bytes_image = test_response.content
        img = Image.open(io.BytesIO(bytes_image))
        image_checksum = str(imagehash.phash(img))
        assert expected_image_phash == image_checksum
