from config_finder.extract import extract_links


def test_extracts_html_entities():
    links = extract_links(
        "navigator.clipboard.writeText('vless://example.com:443?x=1&amp;y=2')"
    )
    assert links
    assert links[0].startswith("vless://example.com:443")
    assert "&y=2" in links[0]


def test_extracts_multiple_protocols():
    text = "vless://a.example:443 vmess://YWJjZA== trojan://x@b.example:443"
    links = extract_links(text)
    assert len(links) == 3
