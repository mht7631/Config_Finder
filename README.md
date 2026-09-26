# Config Finder

Config Finder is a Windows-friendly Python application for discovering publicly exposed proxy configuration links from public sources, normalizing them, storing them in SQLite, checking advertised TCP endpoints, ranking reachable endpoints, and exporting clean datasets.

## Run it without the CLI

The normal user interface is the desktop application.

~~~powershell
py run.py
~~~

A window opens with Start Full Scan. Press that button and the application automatically searches public sources, collects subscription pages, extracts supported links, decodes supported Base64 subscriptions, removes duplicates, tests advertised endpoints, and exports the results.

## Output

- data/all.txt — every unique collected configuration
- data/vless.txt
- data/vmess.txt
- data/trojan.txt
- data/ss.txt
- data/shadowsocks.txt
- data/reachable.txt
- data/unreachable.txt
- data/summary.json
- data/configs.db

## Requirements

- Windows
- Python 3.11+
- Internet access

## Installation

~~~powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e .
~~~

Then:

~~~powershell
py run.py
~~~

You do not need to use the CLI.

## Discovery and scale

Discovery uses multiple focused public search queries plus seeded public source lists. Crawling is asynchronous and bounded by concurrency, response size and timeout. The query list can be expanded without changing the application code.

## Important interpretation

reachable.txt means that the advertised TCP endpoint accepted a connection when tested. It does not prove that the proxy protocol, credentials, TLS settings, routing or authentication are valid in a real client.

## Operational limits

Only public HTTP/HTTPS sources and public configuration links are processed. Endpoint testing is restricted to host/port values extracted from collected configurations. The project does not perform arbitrary port-range scanning, private-target discovery, credential harvesting, or access to private resources.

## Development

~~~powershell
pytest -q
~~~
