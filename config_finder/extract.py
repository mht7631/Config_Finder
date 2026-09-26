import base64
import html
import re
from urllib.parse import unquote

SCHEME_PATTERN = r"(?:vless|vmess|trojan|ss|shadowsocks)"
URL_RE = re.compile(
    rf"""(?P<url>{SCHEME_PATTERN}://[^\s<>'"\\]+)""",
    re.IGNORECASE,
)


def _clean(value: str) -> str:
    value = html.unescape(value)
    value = value.replace("\\/", "/")
    value = unquote(value)
    return value.rstrip("),;]}\\").strip()


def _extract_direct(text: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()

    candidates = (text, html.unescape(text), text.replace("\\/", "/"))
    for candidate in candidates:
        for match in URL_RE.finditer(candidate):
            value = _clean(match.group("url"))
            key = value.lower()
            if key not in seen:
                seen.add(key)
                found.append(value)

    return found


def _decode_subscription(text: str) -> str | None:
    compact = re.sub(r"\s+", "", text)
    if len(compact) < 16 or len(compact) > 10_000_000:
        return None
    if not re.fullmatch(r"[A-Za-z0-9+/=_-]+", compact):
        return None

    padded = compact + "=" * (-len(compact) % 4)
    for decoder in (base64.b64decode, base64.urlsafe_b64decode):
        try:
            decoded = decoder(padded.encode("ascii"))
            result = decoded.decode("utf-8", errors="strict")
            if "://" in result:
                return result
        except Exception:
            continue
    return None


def extract_links(text: str) -> list[str]:
    if not text:
        return []

    found = _extract_direct(text)
    if found:
        return found

    decoded = _decode_subscription(text)
    if decoded:
        return _extract_direct(decoded)

    return []
