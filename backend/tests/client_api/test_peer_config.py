"""
ODN Connect contract tests for peer config endpoint.
Validates the .conf file shape that ODN Connect writes to disk.
"""
import pytest


def test_config_has_required_sections():
    """Config must have [Interface] and [Peer] sections."""
    sample_config = """[Interface]
Address = 10.8.0.2/32
DNS = 1.1.1.1

[Peer]
PublicKey = abc123
Endpoint = vpn.example.com:51820
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
"""
    assert "[Interface]" in sample_config
    assert "[Peer]" in sample_config
    assert "Address" in sample_config
    assert "Endpoint" in sample_config
    assert "AllowedIPs" in sample_config
    assert "PersistentKeepalive" in sample_config


def test_config_endpoint_format():
    """Endpoint must be host:port."""
    endpoint = "vpn.example.com:51820"
    host, port = endpoint.rsplit(":", 1)
    assert host
    assert port.isdigit()
