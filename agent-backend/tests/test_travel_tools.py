import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.agent.core import _hotel_cards, _ticket_cards, _transport_cards
from app.agent.travel_tools import (
    TravelToolError,
    build_daily_itinerary,
    calculate_equal_split,
    compose_plan_options,
    execute_tool,
    search_attractions,
    search_hotels,
    search_transport,
    validate_trip_requirements,
)
from app.storage import TravelRepository


class TravelToolsTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repository = TravelRepository(Path(self.temp_dir.name) / "test.db")
        self.repository_patch = patch("app.agent.travel_tools.repository", self.repository)
        self.repository_patch.start()

    def tearDown(self):
        self.repository_patch.stop()
        self.temp_dir.cleanup()

    def test_validation_returns_next_missing_question(self):
        result = validate_trip_requirements({"adults": 5})
        self.assertFalse(result["valid"])
        self.assertEqual(result["missing_fields"][0], "出发城市")

    def test_validation_calculates_rooms_and_nights(self):
        result = validate_trip_requirements(
            {
                "origin": "北京",
                "destination": "上海",
                "start_date": "2026-10-01",
                "end_date": "2026-10-03",
                "adults": 5,
            }
        )
        self.assertTrue(result["valid"])
        self.assertEqual(result["trip"]["rooms"], 3)
        self.assertEqual(result["trip"]["days"], 3)
        self.assertEqual(result["trip"]["nights"], 2)

    def test_validation_enforces_prd_people_limit(self):
        with self.assertRaises(TravelToolError):
            validate_trip_requirements(
                {
                    "origin": "北京",
                    "destination": "上海",
                    "start_date": "2026-10-01",
                    "end_date": "2026-10-03",
                    "adults": 16,
                }
            )

    def test_equal_split_preserves_total_to_cent(self):
        result = calculate_equal_split(
            {
                "items": [
                    {"name": "交通", "amount_yuan": 100},
                    {"name": "酒店", "amount_yuan": 0.01},
                ],
                "payer_count": 3,
                "payer_names": ["A", "B", "C"],
            }
        )
        share_cents = [round(float(item["amount_yuan"]) * 100) for item in result["shares"]]
        self.assertEqual(sum(share_cents), 10001)

    def test_compose_plan_always_returns_abc(self):
        trip_id = validate_trip_requirements(
            {
                "origin": "北京",
                "destination": "上海",
                "start_date": "2026-10-01",
                "end_date": "2026-10-03",
                "adults": 5,
            }
        )["trip_id"]
        result = compose_plan_options(
            {
                "trip_id": trip_id,
                "travelers": 5,
                "transport": {"name": "高铁（演示）", "total_yuan": 5000},
                "hotels": [
                    {"name": "经济酒店", "location": "虹桥", "total_yuan": 3000},
                    {"name": "舒适酒店", "location": "外滩", "total_yuan": 6000},
                    {"name": "品质酒店", "location": "迪士尼", "total_yuan": 9000},
                ],
                "attractions": [{"name": "迪士尼", "total_yuan": 2500}],
            }
        )
        self.assertEqual([plan["id"] for plan in result["plans"]], ["A", "B", "C"])
        self.assertEqual(result["plan_count"], 3)

    def test_ticket_and_transport_results_are_saved_to_sqlite(self):
        trip = validate_trip_requirements(
            {
                "origin": "北京",
                "destination": "上海",
                "start_date": "2026-10-01",
                "end_date": "2026-10-03",
                "adults": 5,
                "attractions": ["迪士尼"],
            }
        )
        trip_id = trip["trip_id"]
        search_transport(
            {
                "trip_id": trip_id,
                "origin": "北京",
                "destination": "上海",
                "departure_date": "2026-10-01",
                "return_date": "2026-10-03",
                "travelers": 5,
            }
        )
        search_attractions(
            {
                "trip_id": trip_id,
                "destination": "上海",
                "travelers": 5,
                "attractions": ["迪士尼"],
            }
        )
        bundle = self.repository.get_trip_bundle(trip_id)
        self.assertEqual(len(bundle["transport_offers"]), 4)
        self.assertGreaterEqual(len(bundle["attraction_tickets"]), 4)

    def test_transport_tool_produces_clickable_ui_cards(self):
        trip_id = validate_trip_requirements(
            {
                "origin": "北京",
                "destination": "上海",
                "start_date": "2026-10-01",
                "end_date": "2026-10-03",
                "adults": 5,
            }
        )["trip_id"]
        raw = execute_tool(
            "search_transport",
            json.dumps(
                {
                    "trip_id": trip_id,
                    "origin": "北京",
                    "destination": "上海",
                    "departure_date": "2026-10-01",
                    "return_date": "2026-10-03",
                    "travelers": 5,
                }
            ),
        )
        cards = _transport_cards(raw)
        self.assertEqual([card["transport_type"] for card in cards], ["train", "train", "flight", "flight"])
        self.assertTrue(all(card["remaining_inventory"] >= 5 for card in cards))
        self.assertTrue(all(card["departure_time"] and card["arrival_time"] for card in cards))
        self.assertTrue(all(card["booking_url"].startswith("https://www.ly.com/") for card in cards))
        self.assertTrue(all(card["cta_label"] == "去预订" for card in cards))

    def test_hotel_tool_produces_multiple_inventory_cards(self):
        trip_id = validate_trip_requirements(
            {
                "origin": "北京",
                "destination": "上海",
                "start_date": "2026-10-01",
                "end_date": "2026-10-03",
                "adults": 5,
                "rooms": 3,
            }
        )["trip_id"]
        response = search_hotels(
            {
                "trip_id": trip_id,
                "destination": "上海",
                "checkin_date": "2026-10-01",
                "checkout_date": "2026-10-03",
                "rooms": 3,
                "preferred_locations": ["外滩", "迪士尼"],
            }
        )
        raw = json.dumps({"ok": True, "result": response}, ensure_ascii=False)
        cards = _hotel_cards(raw)
        self.assertEqual(len(cards), 6)
        self.assertTrue(all(card["remaining_inventory"] >= 3 for card in cards))
        self.assertTrue(all(card["booking_url"] == "https://www.ly.com/hotel" for card in cards))

    def test_ticket_tool_produces_selectable_link_cards(self):
        trip_id = validate_trip_requirements(
            {
                "origin": "北京",
                "destination": "上海",
                "start_date": "2026-10-01",
                "end_date": "2026-10-03",
                "adults": 5,
            }
        )["trip_id"]
        raw = execute_tool(
            "search_attractions",
            json.dumps(
                {
                    "trip_id": trip_id,
                    "destination": "上海",
                    "travelers": 5,
                    "attractions": ["上海迪士尼乐园"],
                }
            ),
        )
        cards = _ticket_cards(raw)
        self.assertGreaterEqual(len(cards), 4)
        self.assertEqual(cards[0]["attraction_name"], "上海迪士尼乐园")
        self.assertTrue(all(card["booking_url"] == "https://www.ly.com/scenery/" for card in cards))

    def test_product_catalog_stats_with_multi_city_products(self):
        stats = self.repository.product_catalog_stats()
        self.assertEqual(stats["cities"], 12)
        self.assertEqual(stats["transport_products"], 528)
        self.assertEqual(stats["hotel_products"], 111)
        self.assertEqual(stats["ticket_products"], 48)

    def test_full_day_attraction_uses_middle_day(self):
        trip = validate_trip_requirements(
            {
                "origin": "北京",
                "destination": "上海",
                "start_date": "2026-10-01",
                "end_date": "2026-10-03",
                "adults": 5,
            }
        )
        itinerary = build_daily_itinerary(
            {
                "trip_id": trip["trip_id"],
                "destination": "上海",
                "start_date": "2026-10-01",
                "end_date": "2026-10-03",
                "attractions": [{"name": "迪士尼", "duration_hours": 8}],
            }
        )
        day1 = json.dumps(itinerary["schedule"][0], ensure_ascii=False)
        day2 = json.dumps(itinerary["schedule"][1], ensure_ascii=False)
        self.assertNotIn("迪士尼", day1)
        self.assertIn("迪士尼", day2)

    def test_unknown_tool_returns_structured_error(self):
        result = json.loads(execute_tool("not_exists", "{}"))
        self.assertFalse(result["ok"])


if __name__ == "__main__":
    unittest.main()
