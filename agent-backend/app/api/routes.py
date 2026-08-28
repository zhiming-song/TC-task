import json
import logging
import re
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from collections.abc import Iterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.agent.core import _hotel_cards, _ticket_cards, _transport_cards, agent
from app.agent.travel_tools import execute_tool, list_capabilities
from app.config import settings
from app.schemas import ChatRequest, ChatResponse, HealthResponse
from app.storage import repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["agent"])
_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()
_executor = ThreadPoolExecutor(max_workers=4)


def _ensure_cards(result, messages):
    history = "\n".join(message.content for message in messages)
    latest_user = next((message.content for message in reversed(messages) if message.role == "user"), "")
    if "旅行计划汇总" in latest_user or "完整行程草案" in latest_user or "生成旅行计划" in latest_user:
        result.cards = []
        return result
    # 首轮只整理信息，必须等待用户确认后再展示产品
    if not any(message.role == "assistant" for message in messages):
        result.cards = []
        return result
    # 按当前推荐环节兜底生成对应产品卡片
    wants_attractions = any(
        phrase in latest_user
        for phrase in (
            "推荐景点",
            "推荐门票",
            "景点/门票推荐",
            "推荐景点和门票",
            "搜索景点",
            "搜索门票",
            "推荐景区",
        )
    )
    if wants_attractions:
        # 如果用户明确要求景点，有景点卡片就直接返回
        if result.cards and all(card.get("type") == "ticket_offer" for card in result.cards):
            return result
        # 否则继续生成景点卡片
        expected_type = "ticket_offer"
    else:
        # 识别酒店或交通环节
        expected_type = ""
        wants_hotels = any(
            phrase in latest_user
            for phrase in ("酒店推荐", "推荐酒店", "酒店库存候选", "搜索酒店", "进入酒店", "执行酒店推荐")
        )
        if wants_hotels:
            expected_type = "hotel_offer"
        elif any(
            phrase in latest_user
            for phrase in ("开始推荐交通", "推荐交通", "交通方案推荐", "搜索交通", "信息确认无误")
        ):
            expected_type = "transport_offer"
        else:
            result.cards = []
            return result
    # 如果已有符合当前环节的卡片，无需补充
    if result.cards and all(card.get("type") == expected_type for card in result.cards):
        return result
    trip_id = getattr(result, "trip_id", "")
    if not trip_id:
        trip_match = re.search(r"trip_[A-Za-z0-9_]+", history)
        trip_id = trip_match.group(0) if trip_match else ""
    if not trip_id:
        return result
    bundle = repository.get_trip_bundle(trip_id)
    if not bundle or not bundle.get("trip"):
        return result
    trip = bundle["trip"]
    if expected_type == "transport_offer":
        args = json.dumps({
            "trip_id": trip_id,
            "origin": trip["origin"],
            "destination": trip["destination"],
            "departure_date": trip["start_date"],
            "return_date": trip["end_date"],
            "travelers": trip["travelers"],
        }, ensure_ascii=False)
        result.cards = _transport_cards(execute_tool("search_transport", args))
    elif expected_type == "hotel_offer":
        args = json.dumps({
            "trip_id": trip_id,
            "destination": trip["destination"],
            "checkin_date": trip["start_date"],
            "checkout_date": trip["end_date"],
            "rooms": trip["rooms"],
            "preferred_locations": trip.get("lodging_locations") or [],
        }, ensure_ascii=False)
        result.cards = _hotel_cards(execute_tool("search_hotels", args))
        # 从 reply 中检测 AI 推荐了几家酒店
        # 优先匹配新格式：「【推荐N家酒店】」
        count = re.search(r"【推荐(\d+)家酒店】", result.reply)
        if not count:
            count = re.search(r"【推荐(\d+)个(?:景点|景区)】", result.reply)
        if not count:
            # 备选：匹配 "推荐以下N家" 或 "以下.*家.*酒店" 等模式
            count = re.search(r"(?:以下|共|推荐)\s*(\d+)\s*(?:家|个).*?(?:酒店|住宿)", result.reply)
            count = int(count.group(1)) if count else 0
        else:
            count = int(count.group(1))
        if count:
            result.cards = result.cards[:count]
        # 保持 AI 原始回复，不覆盖推荐理由
    elif expected_type == "ticket_offer":
        args = json.dumps({"trip_id": trip_id, "destination": trip["destination"], "travelers": trip["travelers"]}, ensure_ascii=False)
        result.cards = _ticket_cards(execute_tool("search_attractions", args))
        # 从 reply 中检测 AI 推荐了几个景点
        count = re.search(r"【推荐(\d+)个(?:景点|景区|门票)】", result.reply)
        if not count:
            count = re.search(r"(?:以下|共|推荐)\s*(\d+)\s*(?:个|款|种).*?(?:景点|门票|景区|产品)", result.reply)
            count = int(count.group(1)) if count else 0
        else:
            count = int(count.group(1))
        if count:
            result.cards = result.cards[:count]
    result.trip_id = trip_id
    return result


def _run_job(job_id: str, request: ChatRequest) -> None:
    with _jobs_lock:
        _jobs[job_id]["status"] = "running"
        _jobs[job_id]["progress"] = "正在分析你的行程需求…"
    try:
        result = agent.run(request.messages, temperature=request.temperature)
        result = _ensure_cards(result, request.messages)
        with _jobs_lock:
            _jobs[job_id].update(
                status="completed",
                progress="已完成",
                reply=result.reply,
                cards=result.cards,
                trip_id=result.trip_id,
            )
    except Exception as exc:
        logger.exception("轮询任务执行失败")
        with _jobs_lock:
            _jobs[job_id].update(status="failed", progress="生成失败", error=str(exc))


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        model=agent.model,
        api_key_configured=bool(settings.deepseek_api_key),
        assistant="程心AI智能行程助手",
        tool_mode=settings.travel_tools_mode,
    )


@router.get("/capabilities")
def capabilities() -> dict:
    """返回当前行程助手可调用的业务工具。"""
    return {
        "assistant": "程心AI智能行程助手",
        "mode": settings.travel_tools_mode,
        "tools": list_capabilities(),
    }


@router.get("/storage")
def storage_status() -> dict:
    """SQLite数据库位置与各业务表记录数。"""
    return repository.stats()


@router.get("/trips/{trip_id}")
def trip_data(trip_id: str) -> dict:
    """读取一个行程及关联的车票、酒店、门票和方案数据。"""
    data = repository.get_trip_bundle(trip_id)
    if data is None:
        raise HTTPException(status_code=404, detail="行程不存在")
    return data


@router.post("/trips/{trip_id}/selections")
def save_trip_selection(trip_id: str, payload: dict) -> dict:
    category = str(payload.get("category") or "").strip()
    item = payload.get("item")
    if category not in {"transport", "hotel", "ticket"} or not isinstance(item, dict):
        raise HTTPException(status_code=422, detail="category 必须为 transport、hotel 或 ticket，且 item 必须为对象")
    if not repository.trip_exists(trip_id):
        raise HTTPException(status_code=404, detail="行程不存在")
    selection_id = repository.save_selection(trip_id, category, item)
    return {"id": selection_id, "trip_id": trip_id, "category": category, "item": item}


@router.get("/trips/{trip_id}/selections")
def trip_selections(trip_id: str) -> dict:
    if not repository.trip_exists(trip_id):
        raise HTTPException(status_code=404, detail="行程不存在")
    return {"trip_id": trip_id, "items": repository.get_selections(trip_id)}


@router.get("/trips")
def trips(limit: int = 50) -> dict:
    """列出SQLite中最近更新的行程。"""
    return {"items": repository.list_trips(limit), "limit": max(1, min(limit, 100))}


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """一次性返回完整回复。"""
    try:
        result = agent.run(request.messages, temperature=request.temperature)
    except Exception as exc:
        logger.exception("调用模型失败")
        raise HTTPException(status_code=502, detail=f"调用模型失败: {exc}") from exc
    result = _ensure_cards(result, request.messages)
    return ChatResponse(reply=result.reply, model=agent.model, cards=result.cards, trip_id=result.trip_id)


@router.post("/chat/jobs")
def create_chat_job(request: ChatRequest) -> dict:
    job_id = uuid.uuid4().hex
    with _jobs_lock:
        _jobs[job_id] = {"status": "pending", "progress": "正在排队…", "reply": "", "cards": []}
    _executor.submit(_run_job, job_id, request)
    return {"job_id": job_id, "status": "pending"}


@router.get("/chat/jobs/{job_id}")
def get_chat_job(job_id: str) -> dict:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="任务不存在")
        return {"job_id": job_id, **job}


@router.post("/chat/stream")
def chat_stream(request: ChatRequest) -> StreamingResponse:
    """以 SSE 逐字返回回复，前端可实现打字机效果。"""

    def event_source() -> Iterator[str]:
        try:
            result = agent.run(request.messages, temperature=request.temperature)
            result = _ensure_cards(result, request.messages)
            for index in range(0, len(result.reply), 24):
                token = result.reply[index : index + 24]
                yield f"data: {json.dumps({'token': token}, ensure_ascii=False)}\n\n"
            for card in result.cards:
                yield f"data: {json.dumps({'card': card}, ensure_ascii=False)}\n\n"
        except Exception as exc:
            logger.exception("流式调用模型失败")
            yield f"data: {json.dumps({'error': str(exc)}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
