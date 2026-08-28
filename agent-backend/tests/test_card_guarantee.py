import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.api.routes import _ensure_cards


class CardGuaranteeTest(unittest.TestCase):
    def setUp(self):
        self.trip = {
            "origin": "北京",
            "destination": "上海",
            "start_date": "2026-10-01",
            "end_date": "2026-10-03",
            "travelers": 5,
            "rooms": 3,
            "lodging_locations": [],
        }
        self.messages = [
            SimpleNamespace(role="assistant", content="行程ID：trip_test123"),
        ]

    def ensure_for(self, user_content, expected_tool, converter_name, expected_type):
        messages = [*self.messages, SimpleNamespace(role="user", content=user_content)]
        result = SimpleNamespace(reply="已为你推荐候选产品", cards=[], trip_id="")
        raw_result = json.dumps({"ok": True, "result": {}})
        expected_cards = [{"type": expected_type, "id": "card-1"}]

        with (
            patch("app.api.routes.repository.get_trip_bundle", return_value={"trip": self.trip}),
            patch("app.api.routes.execute_tool", return_value=raw_result) as execute_mock,
            patch(f"app.api.routes.{converter_name}", return_value=expected_cards),
        ):
            ensured = _ensure_cards(result, messages)

        self.assertEqual(ensured.cards, expected_cards)
        tool_name, raw_args = execute_mock.call_args.args
        self.assertEqual(tool_name, expected_tool)
        self.assertEqual(json.loads(raw_args)["trip_id"], "trip_test123")

    def test_transport_recommendation_always_has_cards(self):
        self.ensure_for(
            "信息确认无误，请开始推荐交通方案",
            "search_transport",
            "_transport_cards",
            "transport_offer",
        )

    def test_hotel_recommendation_always_has_cards(self):
        self.ensure_for("请执行酒店推荐", "search_hotels", "_hotel_cards", "hotel_offer")

    def test_ticket_recommendation_always_has_cards(self):
        self.ensure_for("请推荐景点和门票", "search_attractions", "_ticket_cards", "ticket_offer")

    def test_current_run_trip_id_supports_transport_card_fallback(self):
        messages = [SimpleNamespace(role="user", content="信息确认无误，请开始推荐交通方案")]
        result = SimpleNamespace(reply="已推荐交通方案", cards=[], trip_id="trip_current123")

        with (
            patch("app.api.routes.repository.get_trip_bundle", return_value={"trip": self.trip}),
            patch("app.api.routes.execute_tool", return_value="{}"),
            patch("app.api.routes._transport_cards", return_value=[{"type": "transport_offer"}]),
        ):
            ensured = _ensure_cards(result, messages)

        self.assertEqual(ensured.cards[0]["type"], "transport_offer")


if __name__ == "__main__":
    unittest.main()
