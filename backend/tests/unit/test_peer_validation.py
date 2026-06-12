"""Input validation on peer create/update schemas (P1 hardening)."""
import pytest
from pydantic import ValidationError

from app.routers.peers import PeerCreate, PeerUpdate

VALID_KEY = "A" * 43 + "="


def test_valid_peer_create():
    p = PeerCreate(name="Ross's MacBook", public_key=VALID_KEY, allowed_ips="0.0.0.0/0")
    assert p.name == "Ross's MacBook"
    assert p.public_key == VALID_KEY


@pytest.mark.parametrize("name", [
    "",
    " ",
    "a\nPublicKey = evil",      # newline → wg0.conf stanza injection
    "[Peer]",
    "../../etc/passwd",         # path traversal via .conf filename
    "x" * 64,                   # too long
    "-starts-with-dash",
])
def test_bad_peer_names_rejected(name):
    with pytest.raises(ValidationError):
        PeerCreate(name=name)


@pytest.mark.parametrize("key", [
    "not-a-key",
    "A" * 44,                   # missing '=' padding
    "A" * 42 + "==",
    VALID_KEY + "\nPresharedKey = x",
])
def test_bad_public_keys_rejected(key):
    with pytest.raises(ValidationError):
        PeerCreate(name="ok", public_key=key)


def test_allowed_ips_accepts_cidr_list():
    p = PeerCreate(name="ok", allowed_ips="10.0.0.0/8, 192.168.1.0/24")
    assert p.allowed_ips == "10.0.0.0/8, 192.168.1.0/24"


@pytest.mark.parametrize("cidrs", ["", "not-a-cidr", "10.0.0.0/8,bogus", "0.0.0.0/0; rm -rf"])
def test_bad_allowed_ips_rejected(cidrs):
    with pytest.raises(ValidationError):
        PeerCreate(name="ok", allowed_ips=cidrs)


def test_dns_validation():
    assert PeerCreate(name="ok", dns="1.1.1.1, 8.8.8.8").dns == "1.1.1.1,8.8.8.8"
    with pytest.raises(ValidationError):
        PeerCreate(name="ok", dns="dns.example.com")  # hostnames not allowed


def test_peer_update_validates_too():
    with pytest.raises(ValidationError):
        PeerUpdate(name="bad\nname")
    with pytest.raises(ValidationError):
        PeerUpdate(allowed_ips="bogus")
    assert PeerUpdate(enabled=False).enabled is False
