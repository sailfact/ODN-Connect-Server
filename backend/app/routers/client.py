from fastapi import APIRouter
from app.core.config import settings
from app.services.wg_manager import WgManager

router = APIRouter(prefix="/api/client", tags=["client"])


@router.get("/server-info")
async def server_info():
    """
    Unauthenticated endpoint consumed by ODN Connect during onboarding.
    Returns only public, non-sensitive information.
    """
    wg = WgManager()
    public_key = await wg.get_server_public_key()

    return {
        "server_name": settings.ODN_SERVER_NAME,
        "public_key": public_key,
        "endpoint": f"{settings.WG_SERVER_PUBLIC_IP}:{settings.WG_PORT}",
        "dns": settings.wg_dns_list,
        "allowed_ips": "0.0.0.0/0",
        "api_base_url": f"https://{settings.WG_SERVER_PUBLIC_IP}",
    }
