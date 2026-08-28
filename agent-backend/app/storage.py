"""SQLite persistence for trip planning data."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

from app.config import settings


def _now() -> str:
    return datetime.now().astimezone().isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _cents(value: Any) -> int | None:
    if value in (None, ""):
        return None
    amount = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return int(amount * 100)


class TravelRepository:
    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path or settings.sqlite_path).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_schema()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def init_schema(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS trip_sessions (
                    id TEXT PRIMARY KEY,
                    origin TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    adults INTEGER NOT NULL,
                    children INTEGER NOT NULL DEFAULT 0,
                    travelers INTEGER NOT NULL,
                    rooms INTEGER NOT NULL,
                    budget_per_person_cents INTEGER,
                    lodging_locations_json TEXT NOT NULL DEFAULT '[]',
                    attractions_json TEXT NOT NULL DEFAULT '[]',
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS transport_offers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trip_id TEXT NOT NULL REFERENCES trip_sessions(id) ON DELETE CASCADE,
                    offer_ref TEXT NOT NULL,
                    transport_type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    departure_date TEXT NOT NULL,
                    return_date TEXT NOT NULL,
                    unit_price_cents INTEGER,
                    total_price_cents INTEGER,
                    duration_minutes INTEGER,
                    data_mode TEXT NOT NULL,
                    realtime INTEGER NOT NULL DEFAULT 0,
                    bookable INTEGER NOT NULL DEFAULT 0,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_transport_trip ON transport_offers(trip_id, created_at);

                CREATE TABLE IF NOT EXISTS hotel_offers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trip_id TEXT NOT NULL REFERENCES trip_sessions(id) ON DELETE CASCADE,
                    offer_ref TEXT NOT NULL,
                    name TEXT NOT NULL,
                    location TEXT,
                    tier TEXT,
                    checkin_date TEXT NOT NULL,
                    checkout_date TEXT NOT NULL,
                    rooms INTEGER NOT NULL,
                    nights INTEGER NOT NULL,
                    room_night_price_cents INTEGER,
                    total_price_cents INTEGER,
                    rating TEXT,
                    data_mode TEXT NOT NULL,
                    realtime INTEGER NOT NULL DEFAULT 0,
                    bookable INTEGER NOT NULL DEFAULT 0,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_hotel_trip ON hotel_offers(trip_id, created_at);

                CREATE TABLE IF NOT EXISTS attraction_tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trip_id TEXT NOT NULL REFERENCES trip_sessions(id) ON DELETE CASCADE,
                    offer_ref TEXT NOT NULL,
                    name TEXT NOT NULL,
                    unit_price_cents INTEGER,
                    total_price_cents INTEGER,
                    duration_hours INTEGER,
                    opening_hours TEXT,
                    data_mode TEXT NOT NULL,
                    realtime INTEGER NOT NULL DEFAULT 0,
                    bookable INTEGER NOT NULL DEFAULT 0,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_ticket_trip ON attraction_tickets(trip_id, created_at);

                CREATE TABLE IF NOT EXISTS itinerary_drafts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trip_id TEXT NOT NULL REFERENCES trip_sessions(id) ON DELETE CASCADE,
                    version INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(trip_id, version)
                );

                CREATE TABLE IF NOT EXISTS plan_options (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trip_id TEXT NOT NULL REFERENCES trip_sessions(id) ON DELETE CASCADE,
                    plan_ref TEXT NOT NULL,
                    label TEXT NOT NULL,
                    total_price_cents INTEGER NOT NULL,
                    per_payer_cents INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_plan_trip ON plan_options(trip_id, created_at);

                CREATE TABLE IF NOT EXISTS vote_drafts (
                    id TEXT PRIMARY KEY,
                    trip_id TEXT NOT NULL REFERENCES trip_sessions(id) ON DELETE CASCADE,
                    deadline TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS trip_selections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trip_id TEXT NOT NULL REFERENCES trip_sessions(id) ON DELETE CASCADE,
                    category TEXT NOT NULL,
                    item_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_selection_trip ON trip_selections(trip_id, created_at);

                CREATE TABLE IF NOT EXISTS product_transport_inventory (
                    product_id TEXT PRIMARY KEY,
                    origin TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    transport_type TEXT NOT NULL,
                    product_name TEXT NOT NULL,
                    service_label TEXT NOT NULL,
                    departure_time TEXT NOT NULL,
                    arrival_time TEXT NOT NULL,
                    duration_minutes INTEGER NOT NULL,
                    seat_class TEXT NOT NULL,
                    unit_price_cents INTEGER NOT NULL,
                    remaining_inventory INTEGER NOT NULL,
                    booking_url TEXT NOT NULL,
                    tags_json TEXT NOT NULL DEFAULT '[]',
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_product_transport_route
                    ON product_transport_inventory(origin, destination, transport_type, unit_price_cents);

                CREATE TABLE IF NOT EXISTS product_hotel_inventory (
                    product_id TEXT PRIMARY KEY,
                    city TEXT NOT NULL,
                    product_name TEXT NOT NULL,
                    location TEXT NOT NULL,
                    tier TEXT NOT NULL,
                    rating TEXT NOT NULL,
                    room_night_price_cents INTEGER NOT NULL,
                    remaining_inventory INTEGER NOT NULL,
                    booking_url TEXT NOT NULL,
                    tags_json TEXT NOT NULL DEFAULT '[]',
                    image_url TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_product_hotel_city
                    ON product_hotel_inventory(city, location, room_night_price_cents);

                CREATE TABLE IF NOT EXISTS product_ticket_inventory (
                    product_id TEXT PRIMARY KEY,
                    city TEXT NOT NULL,
                    product_name TEXT NOT NULL,
                    attraction_name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    unit_price_cents INTEGER NOT NULL,
                    remaining_inventory INTEGER NOT NULL,
                    duration_hours INTEGER NOT NULL,
                    opening_hours TEXT NOT NULL,
                    booking_url TEXT NOT NULL,
                    tags_json TEXT NOT NULL DEFAULT '[]',
                    image_url TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_product_ticket_city
                    ON product_ticket_inventory(city, attraction_name, unit_price_cents);

                """
            )
            for table in ("product_hotel_inventory", "product_ticket_inventory"):
                columns = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}
                if "image_url" not in columns:
                    connection.execute(
                        f"ALTER TABLE {table} ADD COLUMN image_url TEXT NOT NULL DEFAULT ''"
                    )
            self._seed_product_catalog(connection)

    def _seed_product_catalog(self, connection: sqlite3.Connection) -> None:
        """预置多城市同程精选商品库；使用INSERT OR IGNORE保留人工调整的库存。"""
        cities = {
            "北京": (["王府井", "国贸", "前门"], ["故宫博物院", "八达岭长城", "颐和园", "北京城市观光"]),
            "上海": (["外滩", "迪士尼", "虹桥火车站"], ["上海迪士尼乐园", "东方明珠", "上海博物馆", "上海城市观光"]),
            "广州": (["珠江新城", "北京路", "广州南站"], ["广州塔", "长隆旅游度假区", "陈家祠", "广州城市观光"]),
            "深圳": (["福田中心区", "南山", "深圳北站"], ["世界之窗", "深圳欢乐谷", "大梅沙", "深圳城市观光"]),
            "杭州": (["西湖", "武林广场", "杭州东站"], ["西湖游船", "灵隐寺", "宋城", "杭州城市观光"]),
            "成都": (["春熙路", "宽窄巷子", "成都东站"], ["成都大熊猫繁育研究基地", "武侯祠", "都江堰", "成都城市观光"]),
            "重庆": (["解放碑", "观音桥", "重庆北站"], ["洪崖洞", "长江索道", "武隆天生三桥", "重庆城市观光"]),
            "西安": (["钟楼", "大雁塔", "西安北站"], ["秦始皇帝陵博物院", "大唐芙蓉园", "西安城墙", "西安城市观光"]),
            "南京": (["新街口", "夫子庙", "南京南站"], ["中山陵", "夫子庙秦淮风光带", "南京博物院", "南京城市观光"]),
            "武汉": (["江汉路", "楚河汉街", "武汉站"], ["黄鹤楼", "东湖", "湖北省博物馆", "武汉城市观光"]),
            "苏州": (["观前街", "金鸡湖", "苏州站"], ["拙政园", "虎丘", "寒山寺", "苏州城市观光"]),
            "厦门": (["中山路", "环岛路", "厦门北站"], ["鼓浪屿", "厦门园林植物园", "胡里山炮台", "厦门城市观光"]),
        }
        timestamp = _now()
        city_names = list(cities)

        transport_rows = []
        for origin_index, origin in enumerate(city_names):
            for destination_index, destination in enumerate(city_names):
                if origin == destination:
                    continue
                route_score = (origin_index + 3) * 37 + (destination_index + 5) * 53
                specs = (
                    ("train", "A", "07:30", 170 + route_score % 260, 22000 + route_score % 36000, 26000, "二等座", 8, "直达", False),
                    ("train", "B", "13:20", 195 + route_score % 280, 26000 + route_score % 39000, 31000, "二等座", 14, "直达", False),
                    ("flight", "A", "09:10", 95 + route_score % 95, 43000 + route_score % 65000, 52000, "经济舱", 9, "直飞", True),
                    ("flight", "B", "18:40", 110 + route_score % 105, 51000 + route_score % 72000, 61000, "经济舱", 15, "直飞", False),
                )
                for (transport_type, suffix, departure_time, duration, price, original_price, seat_class, inventory, flight_type, recommended) in specs:
                    arrival_time = (
                        datetime.strptime(departure_time, "%H:%M") + timedelta(minutes=duration)
                    ).strftime("%H:%M")
                    product_id = f"tc_{origin}_{destination}_{transport_type}_{suffix}".lower()
                    if transport_type == "train":
                        company = f"{origin[:2]}路局 {suffix}次"
                        name = f"{origin}→{destination} 高铁 {suffix}"
                    else:
                        company = f"{origin[:2]}航空 {suffix}次"
                        name = f"{origin[:2]}航空 CZ{route_score % 9000 + 1000}"
                    transport_rows.append(
                        (
                            product_id,
                            origin,
                            destination,
                            transport_type,
                            name,
                            f"{company}",
                            departure_time,
                            arrival_time,
                            duration,
                            seat_class,
                            price,
                            inventory + route_score % 6,
                            settings.tongcheng_train_booking_url if transport_type == "train" else settings.tongcheng_flight_booking_url,
                            _json({"tags": ["同程精选", "可比较", "库存候选"], "original_price_cents": original_price, "recommended": recommended, "flight_type": flight_type}),
                            timestamp,
                        )
                    )
        connection.executemany(
            """
            INSERT OR IGNORE INTO product_transport_inventory (
                product_id, origin, destination, transport_type, product_name, service_label,
                departure_time, arrival_time, duration_minutes, seat_class, unit_price_cents,
                remaining_inventory, booking_url, tags_json, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            transport_rows,
        )

        hotel_rows = []
        ticket_rows = []

        # 上海迪士尼区域酒店（特殊图片）
        disney_hotels = {
            "economic": ("唯季酒店", "tc_shanghai_disney_economic", 42000, 4.5, "经济型", "标准大床房", "20-25m²", "1.8m大床", 2),
            "balanced": ("万信酒店", "tc_shanghai_disney_balanced", 88000, 4.7, "舒适型", "高级大床房", "18-22m²", "1.5m大床", 2),
            "comfort": ("诺阁雅精选酒店", "tc_shanghai_disney_comfort", 128000, 4.9, "品质型", "豪华大床房", "16-18m²", "1.8m大床", 2),
        }

        # 上海真实酒店数据
        real_shanghai_hotels = (
            ("tc_hotel_shanghai_jiquan_quanji", "全季酒店（上海中山公园江苏路店）", "中山公园",
             "balanced", "4.5", 44300, 8,
             _json(["江苏路站2/11号线换乘", "去迪士尼11号线直达约40分钟", "去外滩2号线约12分钟"]),
             "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=400&q=60"),
            ("tc_hotel_shanghai_hyatt_place_hongqiao", "上海虹桥商务区凯悦嘉轩酒店", "虹桥火车站",
             "comfort", "4.6", 49300, 6,
             _json(["步行10分钟进虹桥站", "外滩2号线直达约35分钟", "35平双床房"]),
             "https://images.unsplash.com/photo-1590073242678-70ee3fc28e8e?w=400&q=60"),
            ("tc_hotel_shanghai_cordis_hongqiao", "上海虹桥康得思酒店", "虹桥火车站",
             "comfort", "4.8", 69900, 5,
             _json(["地下连廊直通高铁站", "豪华型41平客房", "带泳池"]),
             "https://images.unsplash.com/photo-1582719508461-905c673771fd?w=400&q=60"),
        )

        tiers = (
            ("economic", "经济型", 28000, "标准间", "15-18m²", "1.2m双床", 2),
            ("balanced", "舒适型", 52000, "高级大床房", "18-22m²", "1.5m大床", 2),
            ("comfort", "品质型", 86000, "豪华套房", "25-30m²", "1.8m大床", 2),
        )

        for city_index, (city, (areas, attractions)) in enumerate(cities.items()):
            # 上海特殊处理：迪士尼区域 + 真实酒店数据
            if city == "上海":
                # 添加迪士尼区域特殊酒店
                for area in ["外滩", "迪士尼", "虹桥火车站"]:
                    for tier_index, (tier, tier_name, base_price, room_type, room_size, bed_type, capacity) in enumerate(tiers):
                        # 迪士尼区域有特殊数据
                        if area == "迪士尼" and tier in disney_hotels:
                            pname, product_id, price, rating, tier_name, room_type, room_size, bed_type, capacity = disney_hotels[tier]
                            original_price = int(price * 1.25)
                            distance_km = 1.5
                            hotel_rows.append(
                                (
                                    product_id,
                                    city,
                                    pname,
                                    area,
                                    tier,
                                    f"{rating}",
                                    price,
                                    4 + tier_index * 2,
                                    settings.tongcheng_hotel_booking_url,
                                    _json({
                                        "tags": [area, tier_name, "同程精选"],
                                        "original_price_cents": original_price,
                                        "room_type": room_type,
                                        "room_size": room_size,
                                        "bed_type": bed_type,
                                        "capacity": capacity,
                                        "distance_km": distance_km,
                                        "cancel_policy": "入住前24:00可免费取消",
                                        "services": ["立即确认", "免押金"] + (["含早餐"] if tier == "economic" else []),
                                        "image_count": 4 + tier_index * 3,
                                    }),
                                    "",
                                    timestamp,
                                )
                            )
                        else:
                            product_id = f"tc_hotel_{city}_{area}_{tier}".lower()
                            price = base_price + ((city_index + 1) * 41 + tier_index * 29) % 12000
                            original_price = int(price * 1.25)
                            distance_km = 1.5 + tier_index * 0.5
                            hotel_rows.append(
                                (
                                    product_id,
                                    city,
                                    f"{city}{area}{tier_name}酒店",
                                    area,
                                    tier,
                                    f"{4.3 + tier_index * 0.2:.1f}",
                                    price,
                                    5 + tier_index % 12,
                                    settings.tongcheng_hotel_booking_url,
                                    _json({
                                        "tags": [area, tier_name, "同程精选"],
                                        "original_price_cents": original_price,
                                        "room_type": room_type,
                                        "room_size": room_size,
                                        "bed_type": bed_type,
                                        "capacity": capacity,
                                        "distance_km": distance_km,
                                        "cancel_policy": "入住前24:00可免费取消",
                                        "services": ["立即确认", "免押金"] + (["含早餐"] if tier == "economic" else []),
                                        "image_count": 4 + tier_index * 3,
                                    }),
                                    "",
                                    timestamp,
                                )
                            )
                # 添加上海真实酒店
                for pid, name, location, tier, rating, price, inventory, tags, image_url in real_shanghai_hotels:
                    hotel_rows.append(
                        (pid, city, name, location, tier, rating, price, inventory,
                         settings.tongcheng_hotel_booking_url, tags, image_url, timestamp)
                    )
            else:
                for area_index, area in enumerate(areas):
                    for tier_index, (tier, tier_name, base_price, room_type, room_size, bed_type, capacity) in enumerate(tiers):
                        product_id = f"tc_hotel_{city}_{area}_{tier}".lower()
                        price = base_price + ((city_index + 1) * 41 + area_index * 67 + tier_index * 29) % 12000
                        original_price = int(price * 1.25)
                        distance_km = 1.5 + (area_index * 1.2 + tier_index * 0.5)
                        hotel_rows.append(
                            (
                                product_id,
                                city,
                                f"{city}{area}{tier_name}酒店",
                                area,
                                tier,
                                f"{4.3 + ((city_index + area_index + tier_index) % 6) / 10:.1f}",
                                price,
                                5 + (city_index * 3 + area_index * 2 + tier_index) % 12,
                                settings.tongcheng_hotel_booking_url,
                                _json({
                                    "tags": [area, tier_name, "同程精选"],
                                    "original_price_cents": original_price,
                                    "room_type": room_type,
                                    "room_size": room_size,
                                    "bed_type": bed_type,
                                    "capacity": capacity,
                                    "distance_km": distance_km,
                                    "cancel_policy": "入住前24:00可免费取消",
                                    "services": ["立即确认", "免押金"] + (["含早餐"] if tier == "economic" else []),
                                    "image_count": 4 + tier_index * 3,
                                }),
                                "",
                                timestamp,
                            )
                        )

            for attraction_index, attraction in enumerate(attractions):
                product_id = f"tc_ticket_{city}_{attraction_index + 1}".lower()
                unit_price = 6000 + ((city_index + 2) * 71 + attraction_index * 97) % 38000
                ticket_rows.append(
                    (
                        product_id,
                        city,
                        f"{attraction}标准票",
                        attraction,
                        "主题乐园" if "乐园" in attraction or "迪士尼" in attraction else "景点门票",
                        unit_price,
                        18 + (city_index * 5 + attraction_index * 7) % 80,
                        3 + attraction_index % 6,
                        "建议游玩前在同程确认开放时间",
                        settings.tongcheng_ticket_booking_url,
                        _json([attraction, "可退规则待确认", "同程精选"]),
                        "",
                        timestamp,
                    )
                )

        connection.executemany(
            """
            INSERT OR IGNORE INTO product_hotel_inventory (
                product_id, city, product_name, location, tier, rating,
                room_night_price_cents, remaining_inventory, booking_url, tags_json, image_url, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            hotel_rows,
        )
        connection.executemany(
            """
            INSERT OR IGNORE INTO product_ticket_inventory (
                product_id, city, product_name, attraction_name, category, unit_price_cents,
                remaining_inventory, duration_hours, opening_hours, booking_url, tags_json, image_url, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ticket_rows,
        )

    def save_trip(self, trip: dict[str, Any], trip_id: str | None = None) -> str:
        identifier = trip_id or f"trip_{uuid4().hex[:12]}"
        timestamp = _now()
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO trip_sessions (
                    id, origin, destination, start_date, end_date, adults, children,
                    travelers, rooms, budget_per_person_cents, lodging_locations_json,
                    attractions_json, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    origin=excluded.origin,
                    destination=excluded.destination,
                    start_date=excluded.start_date,
                    end_date=excluded.end_date,
                    adults=excluded.adults,
                    children=excluded.children,
                    travelers=excluded.travelers,
                    rooms=excluded.rooms,
                    budget_per_person_cents=excluded.budget_per_person_cents,
                    lodging_locations_json=excluded.lodging_locations_json,
                    attractions_json=excluded.attractions_json,
                    status=excluded.status,
                    updated_at=excluded.updated_at
                """,
                (
                    identifier,
                    trip["origin"],
                    trip["destination"],
                    trip["start_date"],
                    trip["end_date"],
                    trip["adults"],
                    trip["children"],
                    trip["travelers"],
                    trip["rooms"],
                    _cents(trip.get("budget_per_person_yuan")),
                    _json(trip.get("lodging_locations") or []),
                    _json(trip.get("attractions") or []),
                    trip.get("status") or "NEEDS_USER_CONFIRMATION",
                    timestamp,
                    timestamp,
                ),
            )
        return identifier

    def trip_exists(self, trip_id: str) -> bool:
        with self.connect() as connection:
            return connection.execute(
                "SELECT 1 FROM trip_sessions WHERE id = ?",
                (trip_id,),
            ).fetchone() is not None

    def search_product_transport(
        self, origin: str, destination: str, travelers: int, limit: int = 8
    ) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM product_transport_inventory
                WHERE origin = ? AND destination = ? AND remaining_inventory >= ?
                ORDER BY transport_type DESC, unit_price_cents ASC, departure_time ASC
                LIMIT ?
                """,
                (origin, destination, travelers, max(1, min(limit, 12))),
            ).fetchall()
            return [dict(row) for row in rows]

    def search_product_hotels(
        self, city: str, rooms: int, locations: list[str] | None = None, limit: int = 12
    ) -> list[dict[str, Any]]:
        locations = [item for item in (locations or []) if item]
        with self.connect() as connection:
            if locations:
                placeholders = ",".join("?" for _ in locations)
                rows = connection.execute(
                    f"""
                    SELECT * FROM product_hotel_inventory
                    WHERE city = ? AND remaining_inventory >= ? AND location IN ({placeholders})
                    ORDER BY location ASC, room_night_price_cents ASC
                    LIMIT ?
                    """,  # noqa: S608 -- placeholders only, values remain parameterized
                    (city, rooms, *locations, max(1, min(limit, 18))),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT * FROM product_hotel_inventory
                    WHERE city = ? AND remaining_inventory >= ?
                    ORDER BY location ASC, room_night_price_cents ASC
                    LIMIT ?
                    """,
                    (city, rooms, max(1, min(limit, 18))),
                ).fetchall()
            return [dict(row) for row in rows]

    def search_product_tickets(
        self, city: str, travelers: int, attractions: list[str] | None = None, limit: int = 8
    ) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM product_ticket_inventory
                WHERE city = ? AND remaining_inventory >= ?
                ORDER BY unit_price_cents ASC
                """,
                (city, travelers),
            ).fetchall()
        products = [dict(row) for row in rows]
        requested = [item.strip() for item in (attractions or []) if item.strip()]
        if requested:
            matched = [
                product
                for product in products
                if any(
                    keyword in product["attraction_name"] or product["attraction_name"] in keyword
                    for keyword in requested
                )
            ]
            if matched:
                products = matched + [product for product in products if product not in matched]
        return products[: max(1, min(limit, 12))]

    def product_catalog_stats(self) -> dict[str, int]:
        with self.connect() as connection:
            return {
                "transport_products": connection.execute(
                    "SELECT COUNT(*) FROM product_transport_inventory"
                ).fetchone()[0],
                "hotel_products": connection.execute(
                    "SELECT COUNT(*) FROM product_hotel_inventory"
                ).fetchone()[0],
                "ticket_products": connection.execute(
                    "SELECT COUNT(*) FROM product_ticket_inventory"
                ).fetchone()[0],
                "cities": connection.execute(
                    """
                    SELECT COUNT(DISTINCT city) FROM (
                        SELECT city FROM product_hotel_inventory
                        UNION SELECT city FROM product_ticket_inventory
                    )
                    """
                ).fetchone()[0],
            }

    # 保留 mock_* 别名方法以兼容旧代码
    def search_mock_transport(
        self, origin: str, destination: str, travelers: int, limit: int = 8
    ) -> list[dict[str, Any]]:
        return self.search_product_transport(origin, destination, travelers, limit)

    def search_mock_hotels(
        self, city: str, rooms: int, locations: list[str] | None = None, limit: int = 12
    ) -> list[dict[str, Any]]:
        return self.search_product_hotels(city, rooms, locations, limit)

    def search_mock_tickets(
        self, city: str, travelers: int, attractions: list[str] | None = None, limit: int = 8
    ) -> list[dict[str, Any]]:
        return self.search_product_tickets(city, travelers, attractions, limit)

    def mock_catalog_stats(self) -> dict[str, int]:
        return self.product_catalog_stats()

    def save_transport(self, trip_id: str, response: dict[str, Any]) -> int:
        query = response["query"]
        timestamp = _now()
        rows = []
        for offer in response.get("candidates", []):
            rows.append(
                (
                    trip_id,
                    offer["id"],
                    offer["type"],
                    offer["name"],
                    query["departure_date"],
                    query["return_date"],
                    _cents(offer.get("estimated_unit_price_yuan")),
                    _cents(offer.get("estimated_total_yuan")),
                    offer.get("estimated_one_way_duration_minutes"),
                    response["data_mode"],
                    int(response["realtime"]),
                    int(response["bookable"]),
                    _json(offer),
                    timestamp,
                )
            )
        with self.connect() as connection:
            connection.executemany(
                """
                INSERT INTO transport_offers (
                    trip_id, offer_ref, transport_type, name, departure_date, return_date,
                    unit_price_cents, total_price_cents, duration_minutes, data_mode,
                    realtime, bookable, payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
        return len(rows)

    def save_hotels(self, trip_id: str, response: dict[str, Any]) -> int:
        query = response["query"]
        timestamp = _now()
        rows = []
        for offer in response.get("hotels", []):
            rows.append(
                (
                    trip_id,
                    offer["id"],
                    offer["name"],
                    offer.get("location"),
                    offer.get("tier"),
                    query["checkin_date"],
                    query["checkout_date"],
                    offer["rooms"],
                    offer["nights"],
                    _cents(offer.get("estimated_price_per_room_night_yuan")),
                    _cents(offer.get("estimated_total_yuan")),
                    offer.get("rating"),
                    response["data_mode"],
                    int(response["realtime"]),
                    int(response["bookable"]),
                    _json(offer),
                    timestamp,
                )
            )
        with self.connect() as connection:
            connection.executemany(
                """
                INSERT INTO hotel_offers (
                    trip_id, offer_ref, name, location, tier, checkin_date, checkout_date,
                    rooms, nights, room_night_price_cents, total_price_cents, rating,
                    data_mode, realtime, bookable, payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
        return len(rows)

    def save_tickets(self, trip_id: str, response: dict[str, Any]) -> int:
        timestamp = _now()
        rows = []
        for offer in response.get("attractions", []):
            rows.append(
                (
                    trip_id,
                    offer["id"],
                    offer["name"],
                    _cents(offer.get("estimated_unit_ticket_yuan")),
                    _cents(offer.get("estimated_total_yuan")),
                    offer.get("suggested_duration_hours"),
                    offer.get("opening_hours"),
                    response["data_mode"],
                    int(response["realtime"]),
                    int(response["bookable"]),
                    _json(offer),
                    timestamp,
                )
            )
        with self.connect() as connection:
            connection.executemany(
                """
                INSERT INTO attraction_tickets (
                    trip_id, offer_ref, name, unit_price_cents, total_price_cents,
                    duration_hours, opening_hours, data_mode, realtime, bookable,
                    payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
        return len(rows)

    def save_itinerary(self, trip_id: str, response: dict[str, Any]) -> int:
        with self.connect() as connection:
            version = connection.execute(
                "SELECT COALESCE(MAX(version), 0) + 1 FROM itinerary_drafts WHERE trip_id = ?",
                (trip_id,),
            ).fetchone()[0]
            connection.execute(
                "INSERT INTO itinerary_drafts (trip_id, version, payload_json, created_at) VALUES (?, ?, ?, ?)",
                (trip_id, version, _json(response), _now()),
            )
        return int(version)

    def save_plans(self, trip_id: str, response: dict[str, Any]) -> int:
        timestamp = _now()
        rows = [
            (
                trip_id,
                plan["id"],
                plan["label"],
                _cents(plan["total_yuan"]),
                _cents(plan["per_payer_yuan"]),
                _json(plan),
                timestamp,
            )
            for plan in response.get("plans", [])
        ]
        with self.connect() as connection:
            connection.executemany(
                """
                INSERT INTO plan_options (
                    trip_id, plan_ref, label, total_price_cents, per_payer_cents,
                    payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
        return len(rows)

    def save_vote(self, trip_id: str, response: dict[str, Any]) -> str:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO vote_drafts (id, trip_id, deadline, status, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    response["vote_id"],
                    trip_id,
                    response["deadline"],
                    response["status"],
                    _json(response),
                    _now(),
                ),
            )
        return response["vote_id"]

    def get_trip_bundle(self, trip_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            trip = connection.execute("SELECT * FROM trip_sessions WHERE id = ?", (trip_id,)).fetchone()
            if trip is None:
                return None
            result: dict[str, Any] = {"trip": dict(trip)}
            for table in (
                "transport_offers",
                "hotel_offers",
                "attraction_tickets",
                "itinerary_drafts",
                "plan_options",
                "vote_drafts",
                "trip_selections",
            ):
                rows = connection.execute(
                    f"SELECT * FROM {table} WHERE trip_id = ? ORDER BY created_at DESC",  # noqa: S608
                    (trip_id,),
                ).fetchall()
                result[table] = [dict(row) for row in rows]
            return result

    def save_selection(self, trip_id: str, category: str, item: dict[str, Any]) -> int:
        with self.connect() as connection:
            cursor = connection.execute(
                "INSERT INTO trip_selections (trip_id, category, item_id, payload_json, created_at) VALUES (?, ?, ?, ?, ?)",
                (trip_id, category, str(item.get("id") or ""), _json(item), _now()),
            )
            return int(cursor.lastrowid)

    def get_selections(self, trip_id: str) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT id, category, item_id, payload_json, created_at FROM trip_selections WHERE trip_id = ? ORDER BY created_at",
                (trip_id,),
            ).fetchall()
            return [{**dict(row), "item": json.loads(row["payload_json"])} for row in rows]

    def list_trips(self, limit: int = 50) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 100))
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM trip_sessions ORDER BY updated_at DESC LIMIT ?",
                (safe_limit,),
            ).fetchall()
            return [dict(row) for row in rows]

    def stats(self) -> dict[str, Any]:
        with self.connect() as connection:
            tables = (
                "trip_sessions",
                "transport_offers",
                "hotel_offers",
                "attraction_tickets",
                "itinerary_drafts",
                "plan_options",
                "vote_drafts",
                "trip_selections",
                "product_transport_inventory",
                "product_hotel_inventory",
                "product_ticket_inventory",
            )
            return {
                "database": str(self.db_path),
                "counts": {
                    table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]  # noqa: S608
                    for table in tables
                },
            }


repository = TravelRepository()
