example_created_response_with_warning = {
    "message": "Added as 20230606120000",
    "response": {
        "accepted_channels": [
            "PM-201-FE-CAM-1",
        ],
        "rejected_channels": {},
        "warnings": ["epac_ops_data_version major version was not 1"],
    },
}

example_updated_response = {
    "message": "Updated 20230606120000",
    "response": {
        "accepted_channels": [],
        "rejected_channels": {
            "PM-201-FE-CAM-1": "Channel is already present in existing record",
        },
        "warnings": [],
    },
}
