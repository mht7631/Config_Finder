from config_finder.models import Config
from config_finder.ranking import quality_score, rank_configs


def test_unreachable_score_is_zero():
    config = Config("vless", "vless://example", tcp_status="unreachable")
    assert quality_score(config) == 0.0


def test_lower_latency_scores_higher():
    fast = Config("vless", "vless://fast", tcp_status="reachable", latency_ms=40)
    slow = Config("vless", "vless://slow", tcp_status="reachable", latency_ms=500)
    ranked = rank_configs([slow, fast])
    assert ranked[0][0].link == "vless://fast"
