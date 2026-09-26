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


def extract_links(text: str) -> list[str]:
    if not text:
        return []

    candidates = (text, html.unescape(text), text.replace("\\/", "/"))
    found: list[str] = []
    seen: set[str] = set()

    for candidate in candidates:
        for match in URL_RE.finditer(candidate):
            value = _clean(match.group("url"))
            key = value.lower()
            if key not in seen:
                seen.add(key)
                found.append(value)

    return found
