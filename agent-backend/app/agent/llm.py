from functools import lru_cache

import httpx
from openai import OpenAI

from app.config import settings


@lru_cache(maxsize=1)
def get_client() -> OpenAI:
    """DeepSeek 提供 OpenAI 兼容接口，直接复用官方 SDK。"""
    return OpenAI(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        http_client=httpx.Client(trust_env=False),
        timeout=60.0,
    )
