import json
import logging
import threading
import uuid
import re
from concurrent.futures import ThreadPoolExecutor
from collections.abc import Iterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.agent.core import _hotel_cards, _ticket_cards, agent
from app.agent.travel_tools import execute_tool, list_capabilities
from app.config import settings
from app.schemas import ChatRequest, ChatResponse, HealthResponse
from app.storage import repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["agent"])
_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()
_executor = ThreadPoolExecutor(max_workers=4)


def _hotel_reply(cards):
    lines = ["已生成酒店候选（演示估价、非实时库存、不可直接预订）：", "", "酒店候选："]
    for index, card in enumerate(cards, 1):
        lines.append(
            f"{index}. {card.get('title')}；位置：{card.get('location')}；"
            f"{card.get('rooms')}间×{card.get('nights')}晚总价：¥{card.get('total_price_yuan')}"
        )
    lines.append("\n以上价格与库存来自 Mock 商品库，真实价格与空房需刷新确认。")
    return "\n".join(lines)


def _ensure_cards(result, messages):
    if result.cards:
        return result
    history = "\n".join(message.content for message in messages)
    trip_match = re.search(r"trip_[A-Za-z0-9_]+", history)
    if not trip_match:
        return result
    trip_id = trip_match.group(0)
    bundle = repository.get_trip_bundle(trip_id)
    if not bundle or not bundle.get("trip"):
        return result
    trip = bundle["trip"]
    args = json.dumps({"trip_id": trip_id, "destination": trip["destination"], "travelers": trip["travelers"]}, ensure_ascii=False)
    if "酒店" in history or "住宿" in history:
        result.cards = _hotel_cards(execute_tool("search_hotels", args))
        count = len(re.findall(r"(?m)^\s*\d+[.、]", result.reply))
        if count:
            result.cards = result.cards[:count]
        if result.cards:
            result.reply = _hotel_reply(result.cards)
    elif "景点" in history or "门票" in history:
        result.cards = _ticket_cards(execute_tool("search_attractions", args))
    return result


def _run_job(job_id: str, request: ChatRequest) -> None:
    with _jobs_lock:
        _jobs[job_id]["status"] = "running"
        _jobs[job_id]["progress"] = "正在分析你的行程需求…"
    try:
        result = agent.run(request.messages, temperature=request.temperature)
        if not result.cards:
            history = "\n".join(message.content for message in request.messages)
            if "景点" in history or "门票" in history:
                history += "\n鏅偣 闂ㄧエ"
            if "景点" in history or "门票" in history:
                match = re.search(r'(?:行程ID：|trip_id[：:"]+)(trip_[A-Za-z0-9_]+)', history)
                if not match:
                    match = re.search(r"(trip_[A-Za-z0-9_]+)", history)
                if match:
                    trip_id = match.group(1)
                    bundle = repository.get_trip_bundle(trip_id)
                    if bundle and bundle.get("trip"):
                        trip = bundle["trip"]
                        raw = execute_tool("search_attractions", json.dumps({"trip_id": trip_id, "destination": trip["destination"], "travelers": trip["travelers"]}, ensure_ascii=False))
                        result.cards = _ticket_cards(raw)
        result = _ensure_cards(result, request.messages)
        with _jobs_lock:
            _jobs[job_id].update(status="completed", progress="已完成", reply=result.reply, cards=result.cards)
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
        assistant="程星AI智能行程助手",
        tool_mode=settings.travel_tools_mode,
    )


@router.get("/capabilities")
def capabilities() -> dict:
    """返回当前行程助手可调用的业务工具。"""
    return {
        "assistant": "程星AI智能行程助手",
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
    return ChatResponse(reply=result.reply, model=agent.model, cards=result.cards)


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
