# Config Finder

Config Finder is a local Python CLI for discovering publicly exposed proxy configuration links from configured public sources, normalizing them, storing them in SQLite, checking advertised TCP endpoints, and exporting usable datasets.

## Supported protocols

- VLESS
- VMess
- Trojan
- Shadowsocks / SS

## Pipeline

Public sources → discovery/crawler → extraction → normalization/parsing → deduplication → SQLite → TCP testing → export

TCP reachability is only an endpoint check. It does not prove that a proxy is valid or that authentication/transport negotiation succeeds.

## Requirements

- Python 3.11+
- Internet access

## Install

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e .
```

## Configure sources

Put public HTTP/HTTPS pages in `config/sources.txt`, one URL per line.

Put discovery queries in `config/queries.txt` if you want the optional search stage.

## Commands

```powershell
python -m config_finder crawl
python -m config_finder discover
python -m config_finder test --limit 500
python -m config_finder stats
python -m config_finder export
python -m config_finder all
```

The default `all` command runs crawl, test, and export. Discovery is explicit because search-engine availability and rate limits vary.

## Output

Generated under `data/`:

- `configs.db`
- `all.txt`
- `reachable.txt`
- `unreachable.txt`
- `vless.txt`
- `vmess.txt`
- `trojan.txt`
- `shadowsocks.txt`
- `summary.json`

## Safety and operational limits

Only public URLs explicitly configured or discovered through public search results are fetched. Crawling is bounded by concurrency, response size, timeout, and optional page limits. Endpoint testing is performed only against host/port pairs extracted from collected public configuration links.

No credential harvesting, private-target scanning, or arbitrary port-range scanning is implemented.
