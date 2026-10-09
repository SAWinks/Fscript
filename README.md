# Fscript

OSINT multi-tool orchestrator. Combines 7 powerful tools into one interactive CLI.

## Features

| Category | Tools |
|----------|-------|
| **Username** | maigret, linkook, sherlock, user-scanner, socialscan, nexfil, gitfive |
| **Email** | holehe, h8mail, user-scanner, socialscan |

## Installation

```bash
pip install rich pipx
pipx ensurepath
```

That's it. Everything else Fscript installs automatically.

## Usage

```bash
python fscript.py
```

Menu:

```
[1] Search by username
[2] Search by email
[3] Settings
[0] Exit
```

Reports are saved to `reports/`.

## Requirements

- Python 3.10+
- Windows, Linux or macOS
- Internet connection

## How it works

Fscript is an orchestrator: it doesn't bundle the OSINT tools, it invokes
them via `pipx` in isolated environments and parses their output into
clean tables. This avoids dependency conflicts and keeps the repo small.

## Disclaimer

This tool is for **educational purposes and legal OSINT only**.
Do not use it to stalk, harass, or violate anyone's privacy.
All tools work exclusively with publicly available data.

## License

MIT — see [LICENSE](LICENSE).
