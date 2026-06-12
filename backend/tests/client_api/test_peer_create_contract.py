"""
ODN Connect contract tests for peer creation and client config rendering.

Guards the two halves of the self-service key contract:
- the create response must include the preshared key (the client writes it
  into its locally built .conf; without it the handshake fails)
- rendered configs must include PrivateKey only when the server generated
  the keypair — self-service private keys never leave the client device
"""
import pytest

from app.routers.peers import PeerCreatedOut, PeerOut
from app.services.wg_manager import WgManager


class FakePeer:
    name = "test-peer"
    assigned_ip = "10.8.0.2"
    dns = "1.1.1.1"
    allowed_ips = "0.0.0.0/0"
    preshared_key = "psk123"
    private_key = None


def test_create_response_includes_preshared_key():
    assert "preshared_key" in PeerCreatedOut.model_fields


def test_list_response_never_exposes_keys():
    assert "preshared_key" not in PeerOut.model_fields
    assert "private_key" not in PeerOut.model_fields


@pytest.mark.asyncio
async def test_self_service_config_omits_private_key():
    config = await WgManager().render_client_config(FakePeer())
    assert "PrivateKey" not in config
    assert "PresharedKey = psk123" in config


@pytest.mark.asyncio
async def test_server_generated_config_includes_private_key():
    peer = FakePeer()
    peer.private_key = "priv123"
    config = await WgManager().render_client_config(peer)
    assert "PrivateKey = priv123" in config
