import base64
import json

from config_finder.normalize import parse_config


def test_vless_endpoint():
    config = parse_config("vless://uuid@example.com:443?security=tls")
    assert config.scheme == "vless"
    assert config.host == "example.com"
    assert config.port == 443


def test_vmess_endpoint():
    payload = base64.urlsafe_b64encode(
        json.dumps({"add": "example.com", "port": 443}).encode()
    ).decode().rstrip("=")
    config = parse_config(f"vmess://{payload}")
    assert config.host == "example.com"
    assert config.port == 443


def test_invalid_port_does_not_crash():
    config = parse_config("trojan://secret@example.com:not-a-port")
    assert config.host is None
    assert config.port is None
