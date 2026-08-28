from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict


ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
DEFAULT_SQLITE_PATH = ENV_FILE.parent / "data" / "travel_agent.db"

# 本地开发时，项目自己的 .env 是唯一可信配置源。
# override=True 可清除终端/IDE 已启动进程中残留的旧 Key 覆盖问题。
load_dotenv(ENV_FILE, override=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    travel_tools_mode: str = "demo"
    sqlite_path: str = str(DEFAULT_SQLITE_PATH)
    tongcheng_train_booking_url: str = "https://www.ly.com/huochepiao/"
    tongcheng_flight_booking_url: str = "https://www.ly.com/flights/home"
    tongcheng_hotel_booking_url: str = "https://www.ly.com/hotel"
    tongcheng_ticket_booking_url: str = "https://www.ly.com/scenery/"

    app_host: str = "0.0.0.0"
    app_port: int = 8000
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


settings = Settings()
