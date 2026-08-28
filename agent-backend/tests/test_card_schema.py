import unittest

from pydantic import ValidationError

from app.schemas import ChatResponse


class CardSchemaTest(unittest.TestCase):
    def test_rejects_card_missing_frontend_field(self):
        with self.assertRaises(ValidationError):
            ChatResponse(
                reply="ok",
                model="test",
                cards=[{"type": "transport_offer", "id": "card-1"}],
            )

    def test_rejects_unknown_card_type(self):
        with self.assertRaises(ValidationError):
            ChatResponse(
                reply="ok",
                model="test",
                cards=[{"type": "custom_card", "id": "card-1"}],
            )


if __name__ == "__main__":
    unittest.main()
