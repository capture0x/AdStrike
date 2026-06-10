"""
utils/helpers.py
AdStrike — Professional UI / UX helpers
"""
import subprocess, sys, os, json, datetime, threading, time, shutil, shlex

# ── 16-color ANSI ─────────────────────────────────────────────────────────────
R    = "\033[38;2;253;38;54m"    # AdStrike red
G    = "\033[92m"     # green
Y    = "\033[93m"     # yellow
B    = "\033[38;5;45m"            # AdStrike blue
M    = "\033[38;2;253;38;54m"    # AdStrike red
C    = "\033[38;5;45m"            # AdStrike blue
W    = "\033[97m"     # white
DIM  = "\033[2m"
BOLD = "\033[1m"
ITAL = "\033[3m"
UND  = "\033[4m"
BLINK= "\033[5m"
RST  = "\033[0m"

# ── ANSI palettes for brand effects ───────────────────────────────────────────
def fg(n):  return f"\033[38;5;{n}m"
def bg(n):  return f"\033[48;5;{n}m"
def fg_rgb(r, g, b): return f"\033[38;2;{r};{g};{b}m"
def bg_rgb(r, g, b): return f"\033[48;2;{r};{g};{b}m"

# AdStrike brand theme: #FD2636 red, legacy terminal blue, white.
ADSTRIKE_RED  = fg_rgb(253, 38, 54)
ADSTRIKE_BLUE = fg(45)

# Keep ADSTRIKE_PINK / ADSTRIKE_PURPLE as aliases so new modules compile cleanly
ADSTRIKE_PINK   = ADSTRIKE_RED
ADSTRIKE_PURPLE = ADSTRIKE_BLUE

BABY_BLUE   = ADSTRIKE_BLUE
SKY_BLUE    = ADSTRIKE_BLUE
LIGHT_PINK  = ADSTRIKE_RED
SOFT_PINK   = ADSTRIKE_RED
PURE_WHITE  = fg(255)
SOFT_WHITE  = fg(252)
MIST        = ADSTRIKE_BLUE
SLATE       = fg(245)
STEEL       = fg(250)
SILVER      = fg(255)

NEON_RED    = ADSTRIKE_RED
NEON_ORG    = LIGHT_PINK
NEON_YEL    = fg(230)
NEON_GRN    = BABY_BLUE
NEON_CYN    = BABY_BLUE
NEON_BLU    = SKY_BLUE
NEON_PUR    = LIGHT_PINK
NEON_PNK    = SOFT_PINK

SEV_COLOR = {
    "Critical": LIGHT_PINK + BOLD,
    "High":     SOFT_PINK + BOLD,
    "Medium":   fg(230) + BOLD,
    "Low":      BABY_BLUE,
    "Info":     SKY_BLUE,
}

# ── Basic output ──────────────────────────────────────────────────────────────
def cprint(msg, color=W): print(f"{color}{msg}{RST}")
def success(msg):         print(f"  {BABY_BLUE}[+]{RST} {msg}")
def warn(msg):            print(f"  {Y}[!]{RST} {msg}")
def info(msg):            print(f"  {SKY_BLUE}[*]{RST} {msg}")
def error(msg):           print(f"  {LIGHT_PINK}[-]{RST} {msg}")
def debug(msg):           print(f"  {DIM}[.]{RST} {DIM}{msg}{RST}")
def critical(msg):        print(f"  {NEON_RED}{BOLD}[!!]{RST} {NEON_RED}{msg}{RST}")
def prompt(msg):          return input(f"  {LIGHT_PINK}[?]{RST} {msg}: ").strip()

def shell_quote(value) -> str:
    """Quote a value for shell command construction."""
    return shlex.quote("" if value is None else str(value))

def mask_secret(value: str, keep: int = 4) -> str:
    """Mask secrets for display and reports."""
    if not value:
        return ""
    s = str(value)
    if len(s) <= keep * 2:
        return "*" * len(s)
    return f"{s[:keep]}...{s[-keep:]}"

def pause(msg="[Enter] to return"):
    import sys, os
    try:
        _tty = os.open("/dev/tty", os.O_RDONLY)
        sys.stdout.write(f"  {M}{msg}{RST}\n")
        sys.stdout.flush()
        os.read(_tty, 1024)
        os.close(_tty)
    except Exception:
        pass

def section(title):
    """Thin section divider used inside modules."""
    line = "─" * (70 - len(title) - 4)
    print(f"\n  {NEON_CYN}── {BOLD}{title}{RST}{NEON_CYN} {line}{RST}")

def arrow(msg, color=NEON_CYN):
    print(f"  {color}▶{RST} {msg}")

def kv(key, value, color=NEON_CYN):
    print(f"  {color}•{RST} {BOLD}{key:<18}{RST}{DIM}:{RST} {value}")

# ── Banners ───────────────────────────────────────────────────────────────────
def print_banner(title, subtitle=""):
    """Module-level banner with double-line frame and gradient title."""
    inner = max(len(title), len(subtitle)) + 8
    top   = "╔" + "═" * inner + "╗"
    mid   = "╠" + "═" * inner + "╣"
    bot   = "╚" + "═" * inner + "╝"
    print()
    print(f"  {LIGHT_PINK}{top}{RST}")
    pad = (inner - len(title)) // 2
    rpad = inner - len(title) - pad
    print(f"  {LIGHT_PINK}║{RST}{' '*pad}{BOLD}{BABY_BLUE}{title}{RST}{' '*rpad}{LIGHT_PINK}║{RST}")
    if subtitle:
        print(f"  {LIGHT_PINK}{mid}{RST}")
        pad = (inner - len(subtitle)) // 2
        rpad = inner - len(subtitle) - pad
        print(f"  {LIGHT_PINK}║{RST}{' '*pad}{SOFT_WHITE}{subtitle}{RST}{' '*rpad}{LIGHT_PINK}║{RST}")
    print(f"  {LIGHT_PINK}{bot}{RST}")
    print()

def print_table(headers, rows, title=""):
    if title: info(title)
    col_w = [max(len(str(h)), max((len(_strip_ansi(str(r[i]))) for r in rows), default=0))
             for i, h in enumerate(headers)]
    top = "┌" + "┬".join("─"*(w+2) for w in col_w) + "┐"
    mid = "├" + "┼".join("─"*(w+2) for w in col_w) + "┤"
    bot = "└" + "┴".join("─"*(w+2) for w in col_w) + "┘"
    print(f"  {DIM}{top}{RST}")
    hdr = "  " + DIM + "│" + RST + DIM + "│".join(
        f" {BOLD}{C}{str(h):<{w}}{RST}{DIM} " for h, w in zip(headers, col_w)
    ) + "│" + RST
    print(hdr)
    print(f"  {DIM}{mid}{RST}")
    for row in rows:
        line = "  " + DIM + "│" + RST
        for cell, w in zip(row, col_w):
            s = str(cell)
            pad = w - len(_strip_ansi(s))
            line += f" {s}{' '*pad} " + DIM + "│" + RST
        print(line)
    print(f"  {DIM}{bot}{RST}")

def _strip_ansi(s: str) -> str:
    import re
    return re.sub(r"\033\[[0-9;]*m", "", s)

# ── Progress / spinner ────────────────────────────────────────────────────────
def spinner(label="Working"):
    frames = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
    stop_ev = threading.Event()
    def _spin():
        i = 0
        while not stop_ev.is_set():
            sys.stdout.write(f"\r  {NEON_CYN}{frames[i % len(frames)]}{RST} {DIM}{label}...{RST}")
            sys.stdout.flush()
            time.sleep(0.08)
            i += 1
        sys.stdout.write("\r" + " " * (len(label) + 20) + "\r")
        sys.stdout.flush()
    threading.Thread(target=_spin, daemon=True).start()
    return stop_ev.set

def progress_bar(current, total, width=40, label=""):
    pct = current / total if total else 0
    filled = int(width * pct)
    bar = NEON_GRN + "█" * filled + DIM + "░" * (width - filled) + RST
    sys.stdout.write(f"\r  {bar} {BOLD}{int(pct*100):3d}%{RST} {DIM}{label}{RST}")
    sys.stdout.flush()
    if current >= total:
        sys.stdout.write("\n")

# ── Command execution ─────────────────────────────────────────────────────────
def run_cmd(cmd, capture=False, silent=False, log=True, timeout=120, return_code=False):
    if not silent:
        print(f"\n  {DIM}┌─[ {NEON_ORG}CMD{RST}{DIM} ]─────────────────────────────────────────{RST}")
        # wrap long commands for readability
        wrapped = cmd if len(cmd) < 120 else cmd[:117] + "..."
        print(f"  {DIM}│{RST} {Y}{wrapped}{RST}")
        print(f"  {DIM}└──────────────────────────────────────────────────{RST}")
    if log:
        try:
            from config.settings import SESSION
            SESSION["commands_run"].append({
                "cmd": cmd,
                "time": str(datetime.datetime.now()),
            })
        except Exception:
            pass
    # Use /dev/tty for interactive commands so subprocesses never consume main stdin
    try:
        tty = open("/dev/tty", "r") if os.path.exists("/dev/tty") else None
    except OSError:
        tty = None

    try:
        if capture:
            res = subprocess.run(cmd, shell=True, capture_output=True,
                                 text=True, timeout=timeout)
            return res.stdout + res.stderr
        res = subprocess.run(cmd, shell=True, stdin=tty)
        return res.returncode if return_code else ""
    except subprocess.TimeoutExpired:
        error(f"Timeout after {timeout}s: {cmd}")
        return 124 if return_code else ""
    except KeyboardInterrupt:
        warn("Interrupted")
        return 130 if return_code else ""
    except Exception as e:
        error(str(e))
        return 1 if return_code else ""

_SYSPY   = "/usr/bin/python3"
_IMP_DIR = "/usr/share/doc/python3-impacket/examples"

def imp(script: str) -> str:
    """Return system-python3 call to an impacket example script.
    Bypasses the venv whose python3 lacks pyasn1/impacket.
    Usage: run_cmd(f"{imp('secretsdump.py')} {dom}/...")
    """
    return f"{_SYSPY} {_IMP_DIR}/{script}"

def check_tools(*names):
    missing = [n for n in names if not shutil.which(n.split()[0])]
    if missing:
        warn(f"Missing tools: {NEON_RED}{', '.join(missing)}{RST}")
    return missing

def nxc_auth(username="", password="", nt_hash="", domain="", dc_ip="") -> str:
    """Build NetExec/CrackMapExec auth flags from explicit values or SESSION."""
    from config.settings import SESSION
    user = username or SESSION.get("username", "")
    pw   = password if password != "" else SESSION.get("password", "")
    h    = nt_hash or SESSION.get("nt_hash", "")
    dom  = domain or SESSION.get("domain", "")
    dc   = dc_ip or SESSION.get("dc_ip", "")

    if SESSION.get("use_kerberos"):
        kdc = f" --kdcHost {shell_quote(dc)}" if dc else ""
        return f"-u {shell_quote(user)} -k -d {shell_quote(dom)}{kdc}"
    if h:
        return f"-u {shell_quote(user)} -H {shell_quote(h.split(':')[-1])} -d {shell_quote(dom)}"
    if pw:
        return f"-u {shell_quote(user)} -p {shell_quote(pw)} -d {shell_quote(dom)}"
    return f"-u '' -p '' -d {shell_quote(dom)}"

def impacket_auth_target(target="", username="", password="", nt_hash="", domain="") -> str:
    """Build an impacket target string with current auth mode."""
    from config.settings import SESSION
    tgt  = target or SESSION.get("dc_ip", "")
    user = username or SESSION.get("username", "")
    pw   = password if password != "" else SESSION.get("password", "")
    h    = nt_hash or SESSION.get("nt_hash", "")
    dom  = domain or SESSION.get("domain", "")
    base = f"{dom}/{user}@{tgt}"

    if SESSION.get("use_kerberos"):
        return f"{shell_quote(base)} -k -no-pass"
    if h:
        return f"{shell_quote(base)} -hashes :{shell_quote(h.split(':')[-1])}"
    if pw:
        return f"{shell_quote(f'{dom}/{user}:{pw}@{tgt}')}"
    return shell_quote(base)

def evil_winrm_auth(target="", username="", password="", nt_hash="", domain="") -> str:
    """Build evil-winrm flags with password, hash, or Kerberos ccache support."""
    from config.settings import SESSION
    tgt  = target or SESSION.get("dc_fqdn") or SESSION.get("dc_ip", "")
    user = username or SESSION.get("username", "")
    pw   = password if password != "" else SESSION.get("password", "")
    h    = nt_hash or SESSION.get("nt_hash", "")
    dom  = domain or SESSION.get("domain", "")
    if SESSION.get("use_kerberos"):
        realm = dom.upper()
        return f"-i {shell_quote(tgt)} -u {shell_quote(user)} -r {shell_quote(realm)}"
    if h:
        return f"-i {shell_quote(tgt)} -u {shell_quote(user)} -H {shell_quote(h.split(':')[-1])}"
    return f"-i {shell_quote(tgt)} -u {shell_quote(user)} -p {shell_quote(pw)}"

def require_session(*keys) -> bool:
    """Validate that required SESSION keys are populated before module execution."""
    from config.settings import SESSION
    missing = [k for k in keys if not SESSION.get(k)]
    if missing:
        error(f"Missing session values: {', '.join(missing)}")
        info("Run Session Setup first or fill the prompted values.")
        return False
    return True

# ── Persistence helpers ───────────────────────────────────────────────────────
def save_result(data, filename, subdir=""):
    from config.settings import SESSION, OUTPUT_DIR
    base = os.path.join(SESSION.get("output_dir") or str(OUTPUT_DIR), subdir)
    os.makedirs(base, exist_ok=True)
    path = os.path.join(base, filename)
    mode = "w" if isinstance(data, str) else "wb"
    with open(path, mode) as f:
        f.write(data)
    success(f"Saved → {NEON_CYN}{path}{RST}")
    return path

# Evidence-grade proof levels (ordered weakest → strongest). A finding's
# proof_level states how strongly it was established, so a report can separate
# "we saw a service" from "we exploited it and own the host".
PROOF_LEVELS = ("observed", "validated", "exploitable", "exploited", "owned")


def add_finding(name, severity, description, recommendation, evidence="",
                proof_level="observed", command=""):
    """Record a finding.

    New (additive, optional) evidence-grade fields — existing callers are
    unaffected since these default:
      proof_level: how strongly it was established (see PROOF_LEVELS).
      command:     the exact command/tool invocation that produced the evidence.
    """
    from config.settings import SESSION
    if proof_level not in PROOF_LEVELS:
        proof_level = "observed"
    key = (
        str(name).strip().lower(),
        str(severity).strip().lower(),
        str(description).strip().lower(),
        str(recommendation).strip().lower(),
    )
    for existing in SESSION.get("findings", []):
        existing_key = (
            str(existing.get("name", "")).strip().lower(),
            str(existing.get("severity", "")).strip().lower(),
            str(existing.get("description", "")).strip().lower(),
            str(existing.get("recommendation", "")).strip().lower(),
        )
        if existing_key == key:
            # Keep the STRONGEST proof level / fill missing evidence on a repeat.
            try:
                if PROOF_LEVELS.index(proof_level) > PROOF_LEVELS.index(
                        existing.get("proof_level", "observed")):
                    existing["proof_level"] = proof_level
            except ValueError:
                pass
            if command and not existing.get("command"):
                existing["command"] = command
            if evidence and not existing.get("evidence"):
                existing["evidence"] = evidence
            debug(f"Duplicate finding skipped: {name}")
            return existing

    SESSION["findings"].append({
        "id": len(SESSION["findings"]) + 1,
        "name": name,
        "severity": severity,
        "description": description,
        "recommendation": recommendation,
        "evidence": evidence,
        "proof_level": proof_level,
        "command": command,
        "timestamp": str(datetime.datetime.now()),
    })
    color = SEV_COLOR.get(severity, W)
    _pl = f" {DIM}({proof_level}){RST}" if proof_level != "observed" else ""
    print(f"  {color}[FINDING] [{severity:<8}]{RST} {BOLD}{name}{RST}{_pl}")
    return SESSION["findings"][-1]

def dedupe_findings(findings=None):
    """Return findings without exact duplicates, preserving original order."""
    from config.settings import SESSION
    source = findings if findings is not None else SESSION.get("findings", [])
    seen = set()
    unique = []
    for f in source:
        key = (
            str(f.get("name", "")).strip().lower(),
            str(f.get("severity", "")).strip().lower(),
            str(f.get("description", "")).strip().lower(),
            str(f.get("recommendation", "")).strip().lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        nf = dict(f)
        nf["id"] = len(unique) + 1
        unique.append(nf)
    return unique

def get_session_creds():
    from config.settings import SESSION
    return (SESSION["dc_ip"], SESSION["domain"], SESSION["username"],
            SESSION["password"], SESSION["nt_hash"])

def input_or_session(key: str, label: str, secret: bool = False) -> str:
    """Use session value if set, otherwise prompt."""
    from config.settings import SESSION
    existing = SESSION.get(key, "")
    if existing:
        display = "***" if secret or key in ("password", "nt_hash") else existing
        print(f"  {DIM}[auto] {label:<22}:{RST} {NEON_CYN}{display}{RST}")
        return existing
    val = input(f"  {M}[?]{RST} {label:<22}: ").strip()
    if val:
        SESSION[key] = val
        from config.settings import _refresh_derived
        _refresh_derived()
    return val
