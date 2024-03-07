from operationsgateway_api.src.records.thumbnail_handler import ThumbnailHandler

class TestTruncator:
    def test_base_64_truncator(self):
        text = "09876543210987654321098765432109876543210987654321unwantedtext"
        return_text = "09876543210987654321098765432109876543210987654321"
        assert ThumbnailHandler.truncate_base64(text) == return_text