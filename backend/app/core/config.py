from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://vpn:vpn@postgres:5432/vpn"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # JWT
    JWT_SECRET: str = "changeme-secret"
    JWT_ACCESS_TTL: int = 900        # 15 minutes
    JWT_REFRESH_TTL: int = 604800    # 7 days
    JWT_ALGORITHM: str = "HS256"

    # WireGuard
    WG_INTERFACE: str = "wg0"
    WG_CONFIG_PATH: str = "/etc/wireguard/wg0.conf"
    WG_SUBNET: str = "10.8.0.0/24"
    WG_DNS: str = "1.1.1.1,1.0.0.1"
    WG_SERVER_PUBLIC_IP: str = "127.0.0.1"
    WG_PORT: int = 51820

    # ODN Connect
    ODN_CLIENT_SELF_SERVICE: bool = True
    ODN_SERVER_NAME: str = "My VPN"

    @property
    def wg_dns_list(self) -> List[str]:
        return [d.strip() for d in self.WG_DNS.split(",")]


settings = Settings()
