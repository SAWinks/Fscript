# fscript.py
import sys
import os
import shutil
import subprocess
import json
import re
import urllib.request
import urllib.parse
from pathlib import Path

# ============================================================
# BOOTSTRAP: rich + pipx
# ============================================================
def _pip_install(pkg):
    subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", pkg], check=True)

def _bootstrap():
    try:
        import rich  # noqa
    except ImportError:
        print("[*] Installing rich...")
        _pip_install("rich")
    if not shutil.which("pipx"):
        print("[*] Installing pipx...")
        try:
            _pip_install("pipx")
            subprocess.run([sys.executable, "-m", "pipx", "ensurepath"],
                           check=False, capture_output=True)
        except Exception as e:
            print(f"[!] pipx install failed: {e}")

_bootstrap()

# ============================================================
# IMPORTS
# ============================================================
from rich import print
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.console import Console

console = Console()
PROJECT = "[red]F[/red]script"
BASE_DIR = Path(__file__).resolve().parent
REPORTS_DIR = BASE_DIR / "reports"

# ============================================================
# REGISTRY
# ============================================================
TOOLS = {
    "maigret":      ("maigret",              "maigret",      ["username"]),
    "linkook":      ("linkook",              "linkook",      ["username"]),
    "sherlock":     ("sherlock-project",     "sherlock",     ["username"]),
    "user-scanner": ("user-scanner",         "user-scanner", ["username", "email"]),
    "socialscan":   ("socialscan",           "socialscan",   ["username", "email"]),
    "nexfil":       ("nexfil",               "nexfil",       ["username"]),
    "gitfive":      ("gitfive",              "gitfive",      ["username"]),
    "holehe":       ("holehe",               "holehe",       ["email"]),
    "h8mail":       ("h8mail",               "h8mail",       ["email"]),
}

# ============================================================
# BANNER
# ============================================================
def greet():
    print("""                                       -+                -+                          
                                      #**%              %**%                         
                                     #*=-*%            %*=-*%                        
                                    #*=--=*#          %*=--=*%                       
                          -@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@                 
                          -@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@                 
                          -@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@                
                          -@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@                 
                          -@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@                 
                          -@@@@@@@@@+                                               
                          -@@@@@@@@@+                                               
                            @@@@@@@@+                                               
                          [red]=##[/red] @@@@@@+                                               
                          [red]=###[/red] @@@@@+                                               
                          [red]=######[/red] @@@@@@@@@@@@@@@@@@@@@@                           
                          [red]=#######[/red]  @@@@@@@@@@@@@@@@@@@@                           
                          [red]=#########[/red]  @@@@@@@@@@@@@@@@@@                           
                          [red]=###########[/red]  @@@@@@@@@@@@@@@@                           
                          [red]=##############[/red]  @@@@@@@@@@@@@                           
                          [red]=#########*[/red]                                               
                          [red]=#########*[/red]                                               
                          [red]=#########*[/red]                                               
                          [red]=#########*[/red]                                               
                          [red]=#########*[/red]                                               
                          [red]=#########*[/red]                                               
                          [red]=#########*[/red]                                               
                          [red]=#########*[/red]                                               
                          [red]=#########*[/red]                                               
                          [red]=#########*[/red]                                               
                          [red]=#########*[/red]                                               
                          [red]=#########*[/red]                                               
                          [red]=#########*[/red]                                               
                          [red]=#########*[/red]""")
    print(f"[blue]WELCOME TO[/blue] {PROJECT}")
    print("[green]CREATED BY:[/green] [purple]SAWinks[/purple]")

# ============================================================
# INSTALLER
# ============================================================
def is_installed(cli):
    return shutil.which(cli) is not None

def ensure_tool(name):
    if name not in TOOLS:
        print(f"[red][!] Unknown tool: {name}[/red]")
        return False
    pipx_pkg, cli, _ = TOOLS[name]
    if is_installed(cli):
        return True
    print(f"[cyan][*][/cyan] Installing [bold]{name}[/bold]...")
    try:
        subprocess.run(["pipx", "install", pipx_pkg], check=True)
        return True
    except Exception as e:
        print(f"[red][!] Failed to install {name}: {e}[/red]")
        return False

# ============================================================
# RUNNER
# ============================================================
def _env_utf8():
    return {
        **os.environ,
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1",
        "PYTHONLEGACYWINDOWSSTDIO": "0",
        "NO_COLOR": "1",
        "TERM": "dumb",
        "LC_ALL": "C.UTF-8",
    }

def run_quiet(args, timeout=300, cwd=None):
    try:
        p = subprocess.run(
            args, capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace", env=_env_utf8(), cwd=cwd,
        )
        return p.stdout, p.stderr, p.returncode
    except subprocess.TimeoutExpired:
        return "", "timeout", 1
    except FileNotFoundError:
        return "", "not found", 1
    except Exception as e:
        return "", str(e), 1

def _looks_like_traceback(text):
    return "Traceback (most recent call last)" in text

# ============================================================
# TOOL: maigret
# ============================================================
def _normalize_site(name):
    return re.sub(r"\s*\[[^\]]+\]\s*$", "", name).strip()

def _maigret_collect(node, name=None, buckets=None):
    if buckets is None:
        buckets = {}
    if isinstance(node, dict):
        status = node.get("status")
        if isinstance(status, dict):
            status = status.get("status")
        if isinstance(status, str) and status.lower() in ("claimed", "found"):
            raw_site = str(node.get("site_name") or name or "?")
            site = _normalize_site(raw_site)
            bucket = buckets.setdefault(site, {"url": "", "tags": []})
            url = node.get("url_user") or node.get("url_main")
            if url and not bucket["url"]:
                bucket["url"] = str(url)
            tags = node.get("tags") or []
            if isinstance(tags, str):
                tags = [tags]
            for t in tags:
                if t and t not in bucket["tags"]:
                    bucket["tags"].append(t)
        for k, v in node.items():
            _maigret_collect(v, k, buckets)
    elif isinstance(node, list):
        for item in node:
            _maigret_collect(item, name, buckets)
    return buckets

def tool_maigret(target):
    if not ensure_tool("maigret"):
        return None
    REPORTS_DIR.mkdir(exist_ok=True)
    tmp = REPORTS_DIR / f"maigret_{target}"
    run_quiet(
        ["maigret", target, "--json", "simple",
         "--no-progressbar", "--no-color", "-fo", str(tmp)],
        timeout=600,
    )
    files = list(Path(str(tmp)).glob("*.json")) or list(REPORTS_DIR.glob(f"report_{target}*.json"))
    if not files:
        return {"error": "no report generated"}
    raw_path = REPORTS_DIR / f"maigret_{target}.json"
    try:
        shutil.copy(files[0], raw_path)
    except Exception:
        pass
    try:
        with open(files[0], encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return {"error": f"parse error: {e}"}
    buckets = _maigret_collect(data)
    found = [
        {"site": s, "url": b["url"], "tags": ", ".join(b["tags"])}
        for s, b in buckets.items()
    ]
    found.sort(key=lambda r: r["site"].lower())
    return {"found": found, "total": len(found), "raw_file": str(raw_path)}

# ============================================================
# TOOL: linkook
# ============================================================
_LINKOOK_SITE_RE = re.compile(
    r"\[\+\]\s*Site Name:\s*(.+?)\s*\n.*?Profile URL:\s*(\S+)",
    re.DOTALL | re.IGNORECASE,
)

def tool_linkook(target):
    if not ensure_tool("linkook"):
        return None
    stdout, stderr, rc = run_quiet(["linkook", target], timeout=300)
    text = stdout or stderr
    found = []
    for m in _LINKOOK_SITE_RE.finditer(text):
        found.append({"site": m.group(1).strip(), "url": m.group(2).strip(), "tags": ""})
    emails = []
    em = re.search(r"Found\s+(\d+)\s+related emails", text, re.IGNORECASE)
    if em and int(em.group(1)) > 0:
        emails = re.findall(r"[\w\.\-]+@[\w\.\-]+\.\w+", text)
    return {"found": found, "total": len(found), "emails": emails}

# ============================================================
# TOOL: sherlock
# ============================================================
_SHERLOCK_RE = re.compile(r"^\[\+\]\s*(.+?):\s*(https?://\S+)\s*$", re.MULTILINE)

def tool_sherlock(target):
    if not ensure_tool("sherlock"):
        return None
    stdout, stderr, rc = run_quiet(
        ["sherlock", "--print-found", "--no-color", target],
        timeout=300,
    )
    text = stdout or stderr
    found = []
    for m in _SHERLOCK_RE.finditer(text):
        found.append({"site": m.group(1).strip(), "url": m.group(2).strip(), "tags": ""})
    return {"found": found, "total": len(found)}

# ============================================================
# TOOL: socialscan (username + email)
# ============================================================
def tool_socialscan(target):
    if not ensure_tool("socialscan"):
        return None
    stdout, stderr, rc = run_quiet(["socialscan", target], timeout=180)
    text = (stdout or "") + "\n" + (stderr or "")
    if _looks_like_traceback(text):
        return {"error": "socialscan crashed"}

    found = []
    for line in text.splitlines():
        line = line.strip()
        if not line or len(line) < 3:
            continue
        if line.lower().startswith(("starting", "scanning", "checking")):
            continue
        # показываем всё, что содержит статус
        if any(k in line.lower() for k in
               ["taken", "available", "registered", "not found", "found", "exists", "free"]):
            found.append({"site": line[:100], "url": "", "tags": ""})
    return {"found": found[:30], "total": len(found), "raw": text[:3000]}


def tool_socialscan_username(target):
    return tool_socialscan(target)

def tool_socialscan_email(target):
    return tool_socialscan(target)

# ============================================================
# TOOL: nexfil
# ============================================================
def tool_nexfil(target):
    if not ensure_tool("nexfil"):
        return None
    stdout, stderr, rc = run_quiet(["nexfil", "-u", target], timeout=180)
    text = (stdout or "") + "\n" + (stderr or "")
    if _looks_like_traceback(text):
        return {"error": "nexfil crashed"}

    found = []
    for line in text.splitlines():
        line = line.strip()
        if not line or len(line) < 3:
            continue
        # nexfil prints: [+] site: url  or  [*] site
        if line.startswith("[+]") or line.startswith("[*]") or "http" in line.lower():
            found.append({"site": line[:100], "url": "", "tags": ""})
    return {"found": found[:30], "total": len(found), "raw": text[:3000]}

# ============================================================
# TOOL: user-scanner
# ============================================================
def tool_user_scanner(target, target_type):
    if not ensure_tool("user-scanner"):
        return None

    pattern = re.compile(r"\[[✔✓]\]\s*(\S+?)\s*\(.*?\):\s*(.+)")

    if target_type == "username":
        args = ["user-scanner", "-u", target]
    else:
        args = ["user-scanner", "-e", target]

    print("[dim]user-scanner: running (may take 5-15 min)...[/dim]")
    stdout, stderr, rc = run_quiet(args, timeout=1200)
    text = stdout or stderr
    if _looks_like_traceback(text):
        return {"error": "user-scanner crashed"}

    found = []
    seen = set()
    for m in pattern.finditer(text):
        site = m.group(1).strip()
        status = m.group(2).strip()
        key = (site.lower(), status.lower())
        if key in seen:
            continue
        seen.add(key)
        found.append({
            "site": site,
            "url": f"https://{site.lower().replace(' ', '')}.com",
            "tags": status,
        })
    return {"found": found, "total": len(found), "raw": text[:3000]}

def tool_user_scanner_username(target):
    return tool_user_scanner(target, "username")

def tool_user_scanner_email(target):
    return tool_user_scanner(target, "email")

# ============================================================
# TOOL: gitfive
# ============================================================
def tool_gitfive(target):
    if not ensure_tool("gitfive"):
        return None
    stdout, stderr, rc = run_quiet(["gitfive", target, "--no-color"], timeout=300)
    text = stdout or stderr
    if _looks_like_traceback(text):
        return {"error": "gitfive crashed"}
    found = []
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("[") and ":" in line:
            k, v = line.split(":", 1)
            found.append({"site": k.strip()[:50], "url": "", "tags": v.strip()[:100]})
    return {"found": found, "total": len(found), "raw": text[:2000]}

# ============================================================
# TOOL: holehe
# ============================================================
_HOLEHE_RE = re.compile(r"^\[\+\]\s*(\S+)\s*$", re.MULTILINE)

def tool_holehe(target):
    if not ensure_tool("holehe"):
        return None
    stdout, stderr, rc = run_quiet(["holehe", target, "--no-color"], timeout=300)
    text = stdout or stderr
    found = [{"site": m.group(1), "url": "", "tags": ""} for m in _HOLEHE_RE.finditer(text)]
    return {"found": found, "total": len(found)}

# ============================================================
# TOOL: h8mail
# ============================================================
def tool_h8mail(target):
    if not ensure_tool("h8mail"):
        return None
    stdout, stderr, rc = run_quiet(["h8mail", "-t", target], timeout=300)
    text = stdout or stderr
    leaks = re.findall(r"^\[\>\]\s*(.+)$", text, re.MULTILINE)
    leaks = [l.strip() for l in leaks if l.strip()]
    found = [{"site": l, "url": "", "tags": "leak"} for l in leaks]
    return {"found": found, "total": len(found), "raw": text[:3000]}

# ============================================================
# REGISTRY — callables
# ============================================================
USERNAME_TOOLS = [
    ("maigret",      tool_maigret),
    ("linkook",      tool_linkook),
    ("sherlock",     tool_sherlock),
    ("user-scanner", tool_user_scanner_username),
    ("socialscan",   tool_socialscan_username),
    ("nexfil",       tool_nexfil),
    ("gitfive",      tool_gitfive),
]

EMAIL_TOOLS = [
    ("holehe",       tool_holehe),
    ("h8mail",       tool_h8mail),
    ("user-scanner", tool_user_scanner_email),
    ("socialscan",   tool_socialscan_email),
]

# ============================================================
# OUTPUT
# ============================================================
def print_results(results):
    for tool_name, payload in results:
        if payload is None:
            continue
        if "error" in payload:
            print(f"[yellow][!] {tool_name}: {payload['error']}[/yellow]")
            continue
        found = payload.get("found") or []
        emails = payload.get("emails") or []
        if not found and not emails:
            print(f"[dim]{tool_name}: no results[/dim]")
            continue
        if found:
            table = Table(
                title=f"[bold green]{tool_name}[/bold green] — {len(found)} found",
                show_lines=False,
            )
            table.add_column("Site", style="cyan", no_wrap=True)
            table.add_column("URL", style="white", overflow="fold")
            table.add_column("Tags", style="dim")
            for row in found:
                table.add_row(row["site"], row["url"], row["tags"])
            console.print(table)
        if emails:
            print(f"[bold]{tool_name} emails:[/bold] {', '.join(set(emails))}")

# ============================================================
# SEARCH
# ============================================================
def search_username():
    target = Prompt.ask("[bold green]Username (without @)[/bold green]").strip()
    if not target:
        return
    print(f"\n[yellow][*] Searching username:[/yellow] [bold]{target}[/bold]\n")
    results = []
    for name, fn in USERNAME_TOOLS:
        print(f"[cyan][>][/cyan] {name}")
        try:
            payload = fn(target)
        except Exception as e:
            payload = {"error": str(e)}
        results.append((name, payload))
    print()
    print_results(results)

def search_email():
    target = Prompt.ask("[bold green]Email[/bold green]").strip()
    if not target:
        return
    print(f"\n[yellow][*] Searching email:[/yellow] [bold]{target}[/bold]\n")
    results = []
    for name, fn in EMAIL_TOOLS:
        print(f"[cyan][>][/cyan] {name}")
        try:
            payload = fn(target)
        except Exception as e:
            payload = {"error": str(e)}
        results.append((name, payload))
    print()
    print_results(results)

def settings():
    print(Panel(
        "[1] Show installed tools\n"
        "[2] Show reports folder\n"
        "[3] Back",
        title="[bold green]Settings[/bold green]",
        border_style="green",
    ))
    sub = Prompt.ask("[bold green]Choose[/bold green]", choices=["1", "2", "3"], default="3")
    if sub == "1":
        table = Table(title="Installed tools")
        table.add_column("Tool", style="cyan")
        table.add_column("Command", style="white")
        table.add_column("Status", style="green")
        for name, (_, cli, _) in TOOLS.items():
            status = "OK" if is_installed(cli) else "missing"
            color = "green" if status == "OK" else "red"
            table.add_row(name, cli, f"[{color}]{status}[/{color}]")
        console.print(table)
        Prompt.ask("[dim]Press Enter to go back[/dim]", default="")
    elif sub == "2":
        if REPORTS_DIR.exists():
            files = list(REPORTS_DIR.iterdir())
            if files:
                for f in files:
                    print(f"  [cyan]{f}[/cyan]")
            else:
                print("[dim]reports/ is empty[/dim]")
        else:
            print("[dim]reports/ does not exist yet[/dim]")
        Prompt.ask("[dim]Press Enter to go back[/dim]", default="")

# ============================================================
# MENU
# ============================================================
def main_menu():
    while True:
        print()
        print(Panel(
            "[1] Search by [cyan]username[/cyan]\n"
            "[2] Search by [cyan]email[/cyan]\n"
            "[3] [white]Settings[/white]\n"
            "[0] [red]Exit[/red]",
            title=f"[bold green]{PROJECT}[/bold green]",
            border_style="green",
        ))
        choice = Prompt.ask(
            "[bold green]Choose[/bold green]",
            choices=["0", "1", "2", "3"],
            default="0",
        )
        if choice == "1":
            search_username()
        elif choice == "2":
            search_email()
        elif choice == "3":
            settings()
        elif choice == "0":
            print("[red]Bye.[/red]")
            return

# ============================================================
# ENTRY
# ============================================================
if __name__ == "__main__":
    greet()
    main_menu()