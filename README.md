# Config Finder

Config Finder is a local Python CLI for discovering publicly exposed proxy configuration links from public sources, normalizing them, storing them in SQLite, checking advertised TCP endpoints, ranking reachable endpoints by latency, and exporting datasets.

## Supported protocols

- VLESS
- VMess
- Trojan
- Shadowsocks / SS

## Pipeline

Public search → source discovery → bounded crawler → extraction → protocol parsing → deduplication → SQLite → TCP endpoint test → ranking → export

TCP reachability is only an endpoint check. It does not prove that a proxy configuration is valid, authenticated, or usable through a real client.

## Requirements

- Python 3.11+
- Internet access

## Install

```powershell
py -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install -U pip
pip install -e ".[test]"
```

## Configure discovery

Put public HTTP/HTTPS pages in `config/sources.txt`, one URL per line.

Put public search queries in `config/queries.txt`, one query per line.

Example queries:

```text
"vless://" public configs
"vmess://" public configs
"trojan://" public configs
"ss://" public configs
```

## Commands

```powershell
python -m config_finder discover
python -m config_finder crawl
python -m config_finder test --limit 500
python -m config_finder top --limit 50
python -m config_finder stats
python -m config_finder export
python -m config_finder all
```

`discover` searches the configured public queries and adds resulting HTTP/HTTPS pages to `config/sources.txt`.

`crawl` fetches those pages with bounded concurrency and extracts supported configuration links.

`test` checks only the host/port advertised by collected configurations. It does not perform arbitrary port scanning.

`top` ranks TCP-reachable configurations using the measured connection latency. The score is an operational heuristic, not a guarantee of proxy usability.

`all` runs discovery, crawling, testing, and export.

## Output

Generated under `data/`:

- `configs.db`
- `all.txt`
- `reachable.txt`
- `unreachable.txt`
- `vless.txt`
- `vmess.txt`
- `trojan.txt`
- `ss.txt`
- `shadowsocks.txt`
- `summary.json`

## Development

Run the test suite:

```powershell
pytest -q
```

GitHub Actions runs compilation and the test suite on pushes and pull requests.

## Operational limits

Only public URLs explicitly configured or discovered through public search results are fetched. Crawling is bounded by request concurrency, response size, and timeout. Search requests are deliberately serialized with a delay. Endpoint testing is bounded by concurrency and timeout and is limited to endpoints extracted from collected public configuration links.

No credential harvesting, private-target scanning, or arbitrary port-range scanning is implemented.
