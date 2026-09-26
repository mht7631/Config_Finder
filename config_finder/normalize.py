import base64
import json
from urllib.parse import unquote, urlsplit

from .models import Config


def _decode_base64(value: str) -> bytes | None:
    value = value.strip()
    if not value:
        return None
    padded = value + "=" * (-len(value) % 4)
    try:
        return base64.urlsafe_b64decode(padded.encode("ascii"))
    except Exception:
        try:
            return base64.b64decode(padded.encode("ascii"), validate=False)
        except Exception:
            return None


def _vmess_endpoint(link: str) -> tuple[str | None, int | None]:
    raw = link.split("://", 1)[1].strip()
    decoded = _decode_base64(raw)
    if not decoded:
        return None, None
    try:
        obj = json.loads(decoded.decode("utf-8", errors="strict"))
    except Exception:
        return None, None

    host = obj.get("add") or obj.get("host")
    port = obj.get("port")
    try:
        return (str(host) if host else None), (int(port) if port else None)
    except (TypeError, ValueError):
        return (str(host) if host else None), None


def _ss_endpoint(link: str) -> tuple[str | None, int | None]:
    parsed = urlsplit(link)
    if parsed.hostname and parsed.port:
        return parsed.hostname, parsed.port

    payload = parsed.netloc or parsed.path
    decoded = _decode_base64(payload)
    if not decoded:
        return None, None

    text = decoded.decode("utf-8", errors="replace")
    endpoint = text.rsplit("@", 1)[-1]
    endpoint = endpoint.split("?", 1)[0].split("#", 1)[0]

    try:
        if endpoint.startswith("["):
            end = endpoint.rfind("]")
            if end > 0 and endpoint[end + 1 :].startswith(":"):
                return endpoint[1:end], int(endpoint[end + 2 :])
        host, port = endpoint.rsplit(":", 1)
        return host, int(port)
    except (ValueError, IndexError):
        return None, None


def parse_config(link: str, source: str | None = None) -> Config:
    normalized = unquote(link.strip())
    scheme = normalized.split("://", 1)[0].lower() if "://" in normalized else ""

    host: str | None = None
    port: int | None = None

    if scheme == "vmess":
        host, port = _vmess_endpoint(normalized)
    elif scheme in {"ss", "shadowsocks"}:
        host, port = _ss_endpoint(normalized)
    else:
        try:
            parsed = urlsplit(normalized)
            host = parsed.hostname
            port = parsed.port
        except ValueError:
            pass

    return Config(
        scheme=scheme,
        link=normalized,
        host=host,
        port=port,
        source=source,
    )


def deduplicate(configs: list[Config]) -> list[Config]:
    result: list[Config] = []
    seen: set[str] = set()
    for config in configs:
        if config.link in seen:
            continue
        seen.add(config.link)
        result.append(config)
    return result
