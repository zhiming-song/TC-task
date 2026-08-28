import logging
import os
import random

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

app = FastAPI(title="DeepSeek Agent API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

# 挂载静态图片目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JIUDIAN_DIR = os.path.join(BASE_DIR, "..", "jiudian")
JINGDIAN_DIR = os.path.join(BASE_DIR, "..", "jingdian")
os.makedirs(JIUDIAN_DIR, exist_ok=True)
os.makedirs(JINGDIAN_DIR, exist_ok=True)
app.mount("/images/jiudian", StaticFiles(directory=JIUDIAN_DIR), name="jiudian")
app.mount("/images/jingdian", StaticFiles(directory=JINGDIAN_DIR), name="jingdian")


@app.get("/")
def root() -> dict[str, str]:
    return {"name": "DeepSeek Agent API", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=settings.app_host, port=settings.app_port, reload=True)
