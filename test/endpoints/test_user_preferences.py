import json

from fastapi.testclient import TestClient


class TestUserPreferences:

    test_values_dict = {
        "string_pref": "string value",
        "int_pref": 123,
        "float_pref": 123.456,
        "bool_pref": True,
    }

    def test_all_pref_types(self, test_app: TestClient, login_and_get_token):
        for pref_name, pref_value in TestUserPreferences.test_values_dict.items():
            # check all types of user preference can be set
            save_response = test_app.post(
                "/users/preferences",
                content=json.dumps({"name": pref_name, "value": pref_value}),
                headers={"Authorization": f"Bearer {login_and_get_token}"},
            )
            assert save_response.status_code == 201

        for pref_name, pref_value in TestUserPreferences.test_values_dict.items():
            # check that the preference values are returned correctly
            get_response = test_app.get(
                f"/users/preferences/{pref_name}",
                headers={"Authorization": f"Bearer {login_and_get_token}"},
            )
            assert get_response.status_code == 200
            assert get_response.json() == pref_value
            # check that the types actually match (not just eg. True == 1)
            assert type(get_response.json()) == type(pref_value)

        for pref_name in TestUserPreferences.test_values_dict:
            # check that the preference values can be deleted
            delete_response = test_app.delete(
                f"/users/preferences/{pref_name}",
                headers={"Authorization": f"Bearer {login_and_get_token}"},
            )
            assert delete_response.status_code == 204

        for pref_name in TestUserPreferences.test_values_dict:
            # check that an error is returned now that the preferences are deleted
            get_response = test_app.get(
                f"/users/preferences/{pref_name}",
                headers={"Authorization": f"Bearer {login_and_get_token}"},
            )
            assert get_response.status_code == 404

    def test_non_existent_get(self, test_app: TestClient, login_and_get_token):
        # check that an error is returned for a preference that is not set
        get_response = test_app.get(
            "/users/preferences/non_existent",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )
        assert get_response.status_code == 404

    def test_non_existent_delete(self, test_app: TestClient, login_and_get_token):
        # check that an error is returned for a preference that is not set
        delete_response = test_app.delete(
            "/users/preferences/non_existent",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )
        assert delete_response.status_code == 404
