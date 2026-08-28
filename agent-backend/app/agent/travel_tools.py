"""程心AI行程规划工具。

所有金额都先转换为"分"计算，避免浮点误差。
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Callable
from uuid import uuid4

from app.storage import repository


MAX_TRAVELERS = 15
MAX_TRIP_DAYS = 15
MAX_HOTEL_LOCATIONS = 5
MAX_ROOMS = 8
MAX_TOOL_RESULT_ITEMS = 15


class TravelToolError(ValueError):
    pass


def _parse_date(value: Any, field: str) -> date:
    if not value:
        raise TravelToolError(f"缺少{field}")
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise TravelToolError(f"{field}必须使用 YYYY-MM-DD 格式") from exc


def _money_to_cents(value: Any) -> int:
    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception as exc:
        raise TravelToolError(f"非法金额：{value}") from exc
    if amount < 0:
        raise TravelToolError("金额不能为负数")
    return int(amount * 100)


def _cents_to_yuan(cents: int) -> str:
    return f"{Decimal(cents) / Decimal(100):.2f}"


def _stable_number(*parts: Any, modulo: int) -> int:
    raw = "|".join(str(part) for part in parts).encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    return int(digest[:8], 16) % modulo


def _clock_after(start_time: str, minutes: int) -> str:
    start = datetime.strptime(start_time, "%H:%M")
    return (start + timedelta(minutes=minutes)).strftime("%H:%M")


def _product_notice() -> dict[str, Any]:
    return {
        "data_mode": "product_catalog",
        "realtime": True,
        "bookable": True,
        "notice": "价格和库存来自同程商品库，请以实际预订时为准。",
    }


def _require_trip_id(args: dict[str, Any]) -> str:
    trip_id = str(args.get("trip_id") or "").strip()
    if not trip_id:
        raise TravelToolError("缺少trip_id，请先调用validate_trip_requirements创建行程")
    if not repository.trip_exists(trip_id):
        raise TravelToolError(f"行程不存在：{trip_id}")
    return trip_id


def validate_trip_requirements(args: dict[str, Any]) -> dict[str, Any]:
    required = {
        "origin": "出发城市",
        "destination": "目的城市",
        "start_date": "出发日期",
        "end_date": "返程日期",
        "adults": "成人数",
    }
    missing = [label for key, label in required.items() if args.get(key) in (None, "")]
    if missing:
        return {
            "valid": False,
            "status": "needs_confirmation",
            "missing_fields": missing,
            "next_question": f"请先确认{missing[0]}。",
        }

    origin = str(args["origin"]).strip()
    destination = str(args["destination"]).strip()
    if origin == destination:
        raise TravelToolError("出发城市和目的城市不能相同")

    start = _parse_date(args["start_date"], "出发日期")
    end = _parse_date(args["end_date"], "返程日期")
    if end < start:
        raise TravelToolError("返程日期不能早于出发日期")

    trip_days = (end - start).days + 1
    if trip_days > MAX_TRIP_DAYS:
        raise TravelToolError(f"单次行程最多支持{MAX_TRIP_DAYS}天")

    adults = int(args["adults"])
    children = int(args.get("children") or 0)
    if adults < 1 or children < 0:
        raise TravelToolError("至少需要1名成人，儿童人数不能为负数")
    travelers = adults + children
    if travelers > MAX_TRAVELERS:
        raise TravelToolError(f"单次规划最多支持{MAX_TRAVELERS}人")

    requested_rooms = args.get("rooms")
    rooms = int(requested_rooms) if requested_rooms not in (None, "") else math.ceil(travelers / 2)
    if rooms < 1 or rooms > MAX_ROOMS:
        raise TravelToolError(f"酒店房间数必须在1到{MAX_ROOMS}间")

    locations = [str(item).strip() for item in (args.get("lodging_locations") or []) if str(item).strip()]
    locations = list(dict.fromkeys(locations))[:MAX_HOTEL_LOCATIONS]
    attractions = [str(item).strip() for item in (args.get("attractions") or []) if str(item).strip()]

    trip = {
        "origin": origin,
        "destination": destination,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "days": trip_days,
        "nights": max((end - start).days, 0),
        "adults": adults,
        "children": children,
        "travelers": travelers,
        "rooms": rooms,
        "budget_per_person_yuan": args.get("budget_per_person_yuan"),
        "lodging_locations": locations,
        "attractions": attractions,
        "status": "CONFIRMED" if args.get("confirmed_by_user") else "NEEDS_USER_CONFIRMATION",
    }
    trip_id = repository.save_trip(trip, str(args.get("trip_id") or "").strip() or None)
    return {
        "valid": True,
        "status": "confirmed",
        "trip_id": trip_id,
        "trip": trip,
        "persistence": {"stored": True, "database": "sqlite"},
        "limits": {
            "max_travelers": MAX_TRAVELERS,
            "max_trip_days": MAX_TRIP_DAYS,
            "max_hotel_locations": MAX_HOTEL_LOCATIONS,
            "max_rooms": MAX_ROOMS,
        },
    }


def search_transport(args: dict[str, Any]) -> dict[str, Any]:
    trip_id = _require_trip_id(args)
    origin = str(args.get("origin") or "").strip()
    destination = str(args.get("destination") or "").strip()
    if not origin or not destination:
        raise TravelToolError("交通查询需要出发城市和目的城市")
    departure = _parse_date(args.get("departure_date"), "出发日期")
    return_date = _parse_date(args.get("return_date"), "返程日期")
    travelers = int(args.get("travelers") or 0)
    if not 1 <= travelers <= MAX_TRAVELERS:
        raise TravelToolError(f"交通查询人数必须在1到{MAX_TRAVELERS}之间")

    inventory_rows = repository.search_product_transport(origin, destination, travelers, limit=8)
    if not inventory_rows:
        raise TravelToolError(f"暂无{origin}到{destination}且库存满足{travelers}人的交通产品")

    candidates = []
    for row in inventory_rows:
        unit_cents = int(row["unit_price_cents"])
        remaining = int(row["remaining_inventory"])
        tags_raw = row.get("tags_json") or "{}"
        tags_json = json.loads(tags_raw) if isinstance(tags_raw, str) else (tags_raw or {})
        tags = tags_json if isinstance(tags_json, dict) else {}
        original_cents = int(tags.get("original_price_cents", int(unit_cents * 1.2)))
        recommended = tags.get("recommended", False)
        flight_type = tags.get("flight_type", "")
        candidates.append(
            {
                "id": row["product_id"],
                "type": row["transport_type"],
                "name": row["product_name"],
                "service_label": row["service_label"],
                "round_trip": True,
                "departure_time": row["departure_time"],
                "arrival_time": row["arrival_time"],
                "seat_class": row["seat_class"],
                "remaining_inventory": remaining,
                "inventory_status": "充足" if remaining >= travelers + 5 else "紧张",
                "estimated_unit_price_yuan": _cents_to_yuan(unit_cents),
                "estimated_total_yuan": _cents_to_yuan(unit_cents * travelers * 2),
                "original_price_yuan": _cents_to_yuan(original_cents),
                "estimated_one_way_duration_minutes": row["duration_minutes"],
                "recommended": recommended,
                "flight_type": flight_type,
                "booking_url": row["booking_url"],
                "catalog_source": "tongcheng_transport_catalog",
                "preference_notes": "价格和库存来自同程交通商品库。",
            }
        )
    response = {
        **_product_notice(),
        "trip_id": trip_id,
        "query": {
            "origin": origin,
            "destination": destination,
            "departure_date": departure.isoformat(),
            "return_date": return_date.isoformat(),
            "travelers": travelers,
        },
        "candidates": candidates,
    }
    response["persistence"] = {
        "stored": True,
        "database": "sqlite",
        "records": repository.save_transport(trip_id, response),
    }
    return response


def search_hotels(args: dict[str, Any]) -> dict[str, Any]:
    trip_id = _require_trip_id(args)
    destination = str(args.get("destination") or "").strip()
    if not destination:
        raise TravelToolError("酒店查询需要目的城市")
    checkin = _parse_date(args.get("checkin_date"), "入住日期")
    checkout = _parse_date(args.get("checkout_date"), "离店日期")
    nights = (checkout - checkin).days
    if nights < 1:
        raise TravelToolError("离店日期必须晚于入住日期")
    rooms = int(args.get("rooms") or 0)
    if not 1 <= rooms <= MAX_ROOMS:
        raise TravelToolError(f"酒店房间数必须在1到{MAX_ROOMS}之间")

    requested_locations = [
        str(item).strip() for item in (args.get("preferred_locations") or []) if str(item).strip()
    ]
    locations = list(dict.fromkeys(requested_locations))[:MAX_HOTEL_LOCATIONS]
    inventory_rows = repository.search_product_hotels(destination, rooms, limit=18)
    if not inventory_rows:
        raise TravelToolError(f"暂无{destination}且库存满足{rooms}间房的酒店产品")
    if locations:
        matched_rows = [
            row
            for row in inventory_rows
            if any(location in row["location"] or row["location"] in location for location in locations)
        ]
        if matched_rows:
            inventory_rows = matched_rows

    hotels: list[dict[str, Any]] = []
    for row in inventory_rows[:MAX_TOOL_RESULT_ITEMS]:
        nightly_cents = int(row["room_night_price_cents"])
        remaining_rooms = int(row["remaining_inventory"])
        tags_raw = row.get("tags_json") or "{}"
        tags_json = json.loads(tags_raw) if isinstance(tags_raw, str) else (tags_raw or {})
        tags = tags_json if isinstance(tags_json, dict) else {}
        original_cents = int(tags.get("original_price_cents", int(nightly_cents * 1.2)))
        hotels.append(
            {
                "id": row["product_id"],
                "name": row["product_name"],
                "location": row["location"],
                "tier": row["tier"],
                "estimated_price_per_room_night_yuan": _cents_to_yuan(nightly_cents),
                "original_price_yuan": _cents_to_yuan(original_cents),
                "estimated_total_yuan": _cents_to_yuan(nightly_cents * rooms * nights),
                "rooms": rooms,
                "nights": nights,
                "remaining_inventory": remaining_rooms,
                "inventory_status": "充足" if remaining_rooms >= rooms + 4 else "紧张",
                "rating": row["rating"],
                "room_type": tags.get("room_type", ""),
                "room_size": tags.get("room_size", ""),
                "bed_type": tags.get("bed_type", ""),
                "capacity": tags.get("capacity", 2),
                "distance_km": tags.get("distance_km", 0),
                "cancel_policy": tags.get("cancel_policy", "入住前可免费取消"),
                "services": tags.get("services", []),
                "image_count": tags.get("image_count", 4),
                "booking_url": row["booking_url"],
                "image_url": row["image_url"] if "image_url" in row.keys() else "",
                "catalog_source": "tongcheng_hotel_catalog",
            }
        )
    response = {
        **_product_notice(),
        "trip_id": trip_id,
        "query": {
            "destination": destination,
            "checkin_date": checkin.isoformat(),
            "checkout_date": checkout.isoformat(),
            "rooms": rooms,
        },
        "hotels": hotels[:MAX_TOOL_RESULT_ITEMS],
    }
    response["persistence"] = {
        "stored": True,
        "database": "sqlite",
        "records": repository.save_hotels(trip_id, response),
    }
    return response


def search_attractions(args: dict[str, Any]) -> dict[str, Any]:
    trip_id = _require_trip_id(args)
    destination = str(args.get("destination") or "").strip()
    if not destination:
        raise TravelToolError("景点查询需要目的城市")
    travelers = int(args.get("travelers") or 0)
    if not 1 <= travelers <= MAX_TRAVELERS:
        raise TravelToolError(f"景点查询人数必须在1到{MAX_TRAVELERS}之间")
    requested = [str(item).strip() for item in (args.get("attractions") or []) if str(item).strip()]
    inventory_rows = repository.search_product_tickets(destination, travelers, requested, limit=8)
    if not inventory_rows:
        raise TravelToolError(f"暂无{destination}且库存满足{travelers}人的门票产品")
    results = []
    for row in inventory_rows:
        unit_cents = int(row["unit_price_cents"])
        remaining = int(row["remaining_inventory"])
        results.append(
            {
                "id": row["product_id"],
                "name": row["product_name"],
                "attraction_name": row["attraction_name"],
                "category": row["category"],
                "estimated_unit_ticket_yuan": _cents_to_yuan(unit_cents),
                "estimated_total_yuan": _cents_to_yuan(unit_cents * travelers),
                "remaining_inventory": remaining,
                "inventory_status": "充足" if remaining >= travelers + 10 else "紧张",
                "suggested_duration_hours": row["duration_hours"],
                "opening_hours": row["opening_hours"],
                "booking_url": row["booking_url"],
                "image_url": row["image_url"] if "image_url" in row.keys() else "",
                "catalog_source": "tongcheng_ticket_catalog",
            }
        )
    response = {
        **_product_notice(),
        "trip_id": trip_id,
        "destination": destination,
        "travelers": travelers,
        "attractions": results,
    }
    response["persistence"] = {
        "stored": True,
        "database": "sqlite",
        "records": repository.save_tickets(trip_id, response),
    }
    return response


def build_daily_itinerary(args: dict[str, Any]) -> dict[str, Any]:
    trip_id = _require_trip_id(args)
    destination = str(args.get("destination") or "").strip()
    if not destination:
        raise TravelToolError("日程编排需要目的城市")
    start = _parse_date(args.get("start_date"), "出发日期")
    end = _parse_date(args.get("end_date"), "返程日期")
    if end < start:
        raise TravelToolError("返程日期不能早于出发日期")
    days = (end - start).days + 1
    if days > MAX_TRIP_DAYS:
        raise TravelToolError(f"单次行程最多支持{MAX_TRIP_DAYS}天")

    raw_attractions = args.get("attractions") or []
    attractions: list[dict[str, Any]] = []
    for item in raw_attractions:
        if isinstance(item, str):
            attractions.append({"name": item, "duration_hours": 4, "area": "待确认"})
        elif isinstance(item, dict) and item.get("name"):
            attractions.append(
                {
                    "name": str(item["name"]),
                    "duration_hours": max(1, min(int(item.get("duration_hours") or 4), 10)),
                    "area": str(item.get("area") or "待确认"),
                }
            )

    schedule = []
    attraction_index = 0
    for day_index in range(days):
        current = start + timedelta(days=day_index)
        is_first = day_index == 0
        is_last = day_index == days - 1
        slots: list[dict[str, str]] = []
        if is_first:
            slots.append({"period": "上午/抵达前", "activity": "前往目的地并办理入住", "status": "需结合实际班次校验"})
        # 三天及以上的行程，抵达日和返程日不安排全天核心景点。
        can_schedule_attraction = attraction_index < len(attractions) and (
            days <= 2 or (not is_first and not is_last)
        )
        if can_schedule_attraction:
            attraction = attractions[attraction_index]
            slots.append(
                {
                    "period": "全天" if attraction["duration_hours"] >= 7 else "下午",
                    "activity": attraction["name"],
                    "area": attraction["area"],
                    "status": "待确认开放时间与交通耗时",
                }
            )
            attraction_index += 1
        else:
            slots.append({"period": "下午", "activity": f"{destination}就近自由活动", "status": "可调整"})
        if is_last:
            slots.append({"period": "返程前", "activity": "退房并前往车站/机场", "status": "需结合实际班次校验"})
        else:
            slots.append({"period": "晚上", "activity": "酒店附近用餐与休息", "status": "可调整"})
        schedule.append({"day": day_index + 1, "date": current.isoformat(), "slots": slots})

    unscheduled = attractions[attraction_index:]
    response = {
        "status": "draft",
        "trip_id": trip_id,
        "destination": destination,
        "schedule": schedule,
        "unscheduled_attractions": unscheduled,
        "warnings": [
            "这是日程草案；接入POI、营业时间和实时交通接口后才能完成可行性校验。",
            "同一区域景点应优先安排在同一天，减少往返。",
        ],
    }
    response["persistence"] = {
        "stored": True,
        "database": "sqlite",
        "version": repository.save_itinerary(trip_id, response),
    }
    return response


def compose_plan_options(args: dict[str, Any]) -> dict[str, Any]:
    trip_id = _require_trip_id(args)
    travelers = int(args.get("travelers") or 0)
    payer_count = int(args.get("payer_count") or travelers)
    if not 1 <= travelers <= MAX_TRAVELERS or not 1 <= payer_count <= MAX_TRAVELERS:
        raise TravelToolError("人数或费用承担人数不合法")
    transport = args.get("transport") or {}
    hotels = args.get("hotels") or []
    attractions = args.get("attractions") or []
    if not transport.get("name") or transport.get("total_yuan") is None:
        raise TravelToolError("生成方案需要已选择的交通及总价")
    if len(hotels) < 3:
        raise TravelToolError("生成ABC方案至少需要3个酒店候选")

    transport_cents = _money_to_cents(transport["total_yuan"])
    attraction_cents = sum(_money_to_cents(item.get("total_yuan") or 0) for item in attractions)
    normalized_hotels = []
    for hotel in hotels:
        if not hotel.get("name") or hotel.get("total_yuan") is None:
            continue
        normalized_hotels.append({**hotel, "total_cents": _money_to_cents(hotel["total_yuan"])})
    if len(normalized_hotels) < 3:
        raise TravelToolError("有效酒店候选不足3个")
    normalized_hotels.sort(key=lambda item: item["total_cents"])

    selected = [
        ("C", "经济型", normalized_hotels[0]),
        ("B", "均衡型", normalized_hotels[len(normalized_hotels) // 2]),
        ("A", "舒适型", normalized_hotels[-1]),
    ]
    plans = []
    for plan_id, label, hotel in selected:
        total_cents = transport_cents + hotel["total_cents"] + attraction_cents
        base_share, remainder = divmod(total_cents, payer_count)
        plans.append(
            {
                "id": plan_id,
                "label": label,
                "transport": transport["name"],
                "hotel": hotel["name"],
                "hotel_location": hotel.get("location"),
                "attractions": [item.get("name") for item in attractions if item.get("name")],
                "total_yuan": _cents_to_yuan(total_cents),
                "per_payer_yuan": _cents_to_yuan(base_share),
                "remainder_cents": remainder,
                "pricing_note": "余数按分依次分配给前N名费用承担者，确保个人金额之和等于总价。",
            }
        )
    plans.sort(key=lambda plan: plan["id"])
    response = {
        "status": "draft",
        "trip_id": trip_id,
        "plan_count": 3,
        "travelers": travelers,
        "payer_count": payer_count,
        "plans": plans,
        "pricing_warning": "预订前必须刷新实时价格与库存。",
    }
    response["persistence"] = {
        "stored": True,
        "database": "sqlite",
        "records": repository.save_plans(trip_id, response),
    }
    return response


def calculate_equal_split(args: dict[str, Any]) -> dict[str, Any]:
    items = args.get("items") or []
    payer_names = [str(name).strip() for name in (args.get("payer_names") or []) if str(name).strip()]
    payer_count = int(args.get("payer_count") or len(payer_names) or 0)
    if not 1 <= payer_count <= MAX_TRAVELERS:
        raise TravelToolError(f"费用承担人数必须在1到{MAX_TRAVELERS}之间")
    if payer_names and len(payer_names) != payer_count:
        raise TravelToolError("费用承担者姓名数量与payer_count不一致")
    if not payer_names:
        payer_names = [f"成员{i + 1}" for i in range(payer_count)]

    normalized_items = []
    total_cents = 0
    for item in items:
        name = str(item.get("name") or "未命名费用")
        cents = _money_to_cents(item.get("amount_yuan") or 0)
        total_cents += cents
        normalized_items.append({"name": name, "amount_yuan": _cents_to_yuan(cents)})
    if total_cents <= 0:
        raise TravelToolError("均摊总金额必须大于0")

    base, remainder = divmod(total_cents, payer_count)
    shares = []
    for index, name in enumerate(payer_names):
        amount = base + (1 if index < remainder else 0)
        shares.append({"payer": name, "amount_yuan": _cents_to_yuan(amount)})
    return {
        "rule": "V1默认按费用承担者等额均摊；儿童是否单独承担费用必须由组织者确认。",
        "items": normalized_items,
        "total_yuan": _cents_to_yuan(total_cents),
        "shares": shares,
        "invariant": "所有成员应付金额之和等于总价，精确到分。",
    }


def create_vote_draft(args: dict[str, Any]) -> dict[str, Any]:
    trip_id = _require_trip_id(args)
    plans = args.get("plans") or []
    if len(plans) != 3:
        raise TravelToolError("投票草案必须包含ABC三套方案")
    deadline_hours = int(args.get("deadline_hours") or 24)
    if not 1 <= deadline_hours <= 24 * 7:
        raise TravelToolError("投票时长最短1小时、最长7天")
    created_at = datetime.now().astimezone()
    response = {
        "status": "draft_only",
        "trip_id": trip_id,
        "vote_id": f"vote_{uuid4().hex[:12]}",
        "created_at": created_at.isoformat(),
        "deadline": (created_at + timedelta(hours=deadline_hours)).isoformat(),
        "plans": plans,
        "shareable": False,
        "notice": "已生成投票草案；尚未接入投票数据库、微信身份和H5服务，因此不能生成真实分享链接。",
    }
    repository.save_vote(trip_id, response)
    response["persistence"] = {"stored": True, "database": "sqlite"}
    return response


def get_trip_data(args: dict[str, Any]) -> dict[str, Any]:
    trip_id = _require_trip_id(args)
    bundle = repository.get_trip_bundle(trip_id)
    return {"trip_id": trip_id, "database": "sqlite", "data": bundle}


TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "validate_trip_requirements",
            "description": "校验行程必要信息与PRD边界，并计算天数、晚数和默认房间数。收集或确认行程时必须调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "trip_id": {"type": "string", "description": "已有行程ID；首次校验可不传"},
                    "confirmed_by_user": {"type": "boolean", "description": "用户是否明确确认了结构化信息"},
                    "origin": {"type": "string", "description": "出发城市"},
                    "destination": {"type": "string", "description": "目的城市"},
                    "start_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "end_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "adults": {"type": "integer"},
                    "children": {"type": "integer"},
                    "rooms": {"type": "integer"},
                    "budget_per_person_yuan": {"type": "number"},
                    "lodging_locations": {"type": "array", "items": {"type": "string"}},
                    "attractions": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_transport",
            "description": "从同程交通商品库查询可满足人数的火车票和机票产品，返回多个可比较候选。",
            "parameters": {
                "type": "object",
                "properties": {
                    "trip_id": {"type": "string"},
                    "origin": {"type": "string"},
                    "destination": {"type": "string"},
                    "departure_date": {"type": "string"},
                    "return_date": {"type": "string"},
                    "travelers": {"type": "integer"},
                },
                "required": ["trip_id", "origin", "destination", "departure_date", "return_date", "travelers"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_hotels",
            "description": "从同程酒店商品库按目的城市、房间数和位置偏好查询多个酒店产品。",
            "parameters": {
                "type": "object",
                "properties": {
                    "trip_id": {"type": "string"},
                    "destination": {"type": "string"},
                    "checkin_date": {"type": "string"},
                    "checkout_date": {"type": "string"},
                    "rooms": {"type": "integer"},
                    "preferred_locations": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["trip_id", "destination", "checkin_date", "checkout_date", "rooms"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_attractions",
            "description": "从同程门票商品库按目的城市、人数和景点意向查询多个门票产品。",
            "parameters": {
                "type": "object",
                "properties": {
                    "trip_id": {"type": "string"},
                    "destination": {"type": "string"},
                    "travelers": {"type": "integer"},
                    "attractions": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["trip_id", "destination", "travelers"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "build_daily_itinerary",
            "description": "生成按天行程草案，标记开放时间、班次和交通耗时等待校验项。",
            "parameters": {
                "type": "object",
                "properties": {
                    "trip_id": {"type": "string"},
                    "destination": {"type": "string"},
                    "start_date": {"type": "string"},
                    "end_date": {"type": "string"},
                    "attractions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "duration_hours": {"type": "integer"},
                                "area": {"type": "string"},
                            },
                            "required": ["name"],
                        },
                    },
                },
                "required": ["trip_id", "destination", "start_date", "end_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compose_plan_options",
            "description": "使用已选择的交通、至少3个酒店和景点金额，精确生成ABC三套方案与人均金额。",
            "parameters": {
                "type": "object",
                "properties": {
                    "trip_id": {"type": "string"},
                    "travelers": {"type": "integer"},
                    "payer_count": {"type": "integer"},
                    "transport": {
                        "type": "object",
                        "properties": {"name": {"type": "string"}, "total_yuan": {"type": "number"}},
                        "required": ["name", "total_yuan"],
                    },
                    "hotels": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "location": {"type": "string"},
                                "total_yuan": {"type": "number"},
                            },
                            "required": ["name", "total_yuan"],
                        },
                    },
                    "attractions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"name": {"type": "string"}, "total_yuan": {"type": "number"}},
                            "required": ["name", "total_yuan"],
                        },
                    },
                },
                "required": ["trip_id", "travelers", "transport", "hotels", "attractions"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_equal_split",
            "description": "按分精确计算V1默认等额均摊，保证所有成员应付之和等于总价。",
            "parameters": {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"name": {"type": "string"}, "amount_yuan": {"type": "number"}},
                            "required": ["name", "amount_yuan"],
                        },
                    },
                    "payer_count": {"type": "integer"},
                    "payer_names": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["items", "payer_count"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_vote_draft",
            "description": "为ABC三套方案生成投票草案；当前不生成真实H5链接。",
            "parameters": {
                "type": "object",
                "properties": {
                    "trip_id": {"type": "string"},
                    "plans": {"type": "array", "minItems": 3, "maxItems": 3, "items": {"type": "object"}},
                    "deadline_hours": {"type": "integer", "minimum": 1, "maximum": 168},
                },
                "required": ["trip_id", "plans"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_trip_data",
            "description": "从SQLite读取指定行程及关联的交通、酒店、门票、日程、方案和投票数据。",
            "parameters": {
                "type": "object",
                "properties": {"trip_id": {"type": "string"}},
                "required": ["trip_id"],
            },
        },
    },
]


TOOL_HANDLERS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "validate_trip_requirements": validate_trip_requirements,
    "search_transport": search_transport,
    "search_hotels": search_hotels,
    "search_attractions": search_attractions,
    "build_daily_itinerary": build_daily_itinerary,
    "compose_plan_options": compose_plan_options,
    "calculate_equal_split": calculate_equal_split,
    "create_vote_draft": create_vote_draft,
    "get_trip_data": get_trip_data,
}


def execute_tool(name: str, raw_arguments: str) -> str:
    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        return json.dumps({"ok": False, "error": f"未知工具：{name}"}, ensure_ascii=False)
    try:
        arguments = json.loads(raw_arguments or "{}")
        result = handler(arguments)
        return json.dumps({"ok": True, "result": result}, ensure_ascii=False)
    except (json.JSONDecodeError, TypeError, ValueError, TravelToolError) as exc:
        return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)


def list_capabilities() -> list[dict[str, str]]:
    return [
        {
            "name": item["function"]["name"],
            "description": item["function"]["description"],
        }
        for item in TOOL_DEFINITIONS
    ]
