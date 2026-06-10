"""
config/settings.py
AdStrike v5.0 — Session, Config & Kerberos Management
"""
import os
import json
import re
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

# ── Base paths ────────────────────────────────────────────────────────────────
BASE_DIR     = Path(__file__).parent.parent
ENV_FILE     = BASE_DIR / ".env"
SESSION_FILE = BASE_DIR / "output" / "session.json"
OUTPUT_DIR   = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# ── Load .env ─────────────────────────────────────────────────────────────────
def load_env(path: Path = ENV_FILE) -> dict:
    env = {}
    if not path.exists():
        return env
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, val = line.partition("=")
                env[key.strip()] = val.strip().strip('"').strip("'")
    return env

_ENV = load_env()

def _ip_for_iface(iface: str) -> str:
    """Best-effort local IPv4 lookup for listener/coercion callbacks."""
    iface = (iface or "").strip()
    if not iface:
        return ""
    try:
        out = subprocess.check_output(
            ["ip", "-4", "-o", "addr", "show", "dev", iface],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=2,
        )
    except Exception:
        return ""
    m = re.search(r"\binet\s+(\d+\.\d+\.\d+\.\d+)/", out)
    return m.group(1) if m else ""

_ATTACKER_IFACE = _ENV.get("ATTACKER_IFACE", "tun0")
_ATTACKER_IP = _ENV.get("ATTACKER_IP", "") or _ip_for_iface(_ATTACKER_IFACE)

# ── SESSION ───────────────────────────────────────────────────────────────────
SESSION: dict = {
    # Target
    "dc_ip":           _ENV.get("DC_IP", ""),
    "dc_fqdn":         _ENV.get("DC_FQDN", ""),
    "domain":          _ENV.get("DOMAIN", ""),
    "base_dn":         _ENV.get("BASE_DN", ""),

    # Credentials
    "username":        _ENV.get("USERNAME", ""),
    "password":        _ENV.get("PASSWORD", ""),
    "nt_hash":         _ENV.get("NT_HASH", ""),

    # Kerberos
    "use_kerberos":    _ENV.get("USE_KERBEROS", "false").lower() == "true",
    "krb5_ccache":     _ENV.get("KRB5_CCACHE", ""),
    "krb5_config":     _ENV.get("KRB5_CONFIG", "/etc/krb5.conf"),
    "tgt_auto_renew":  _ENV.get("TGT_AUTO_RENEW", "true").lower() == "true",

    # Derived
    "domain_user":     "",
    "upn":             "",

    # Attacker
    "attacker_ip":     _ATTACKER_IP,
    "attacker_iface":  _ATTACKER_IFACE,

    # Engagement
    "engagement":      _ENV.get("ENGAGEMENT_NAME", ""),
    "output_dir":      _ENV.get("OUTPUT_DIR", str(OUTPUT_DIR)),
    "start_time":      datetime.now().isoformat(),

    # Runtime
    "hostname":        "",
    "commands_run":    [],
    "findings":        [],
    "owned_users":     [],
    "owned_machines":  [],
    "loot":            {},
}

CONFIG: dict = {
    "version": "5.0",
    "author":  "tmrswrr",
}

SHOW_SECRETS = _ENV.get("ADSTRIKE_SHOW_SECRETS", "false").lower() in ("1", "true", "yes", "on")

SECRET_KEYS = {
    "password", "nt_hash", "attacker_pass", "neo4j_password",
    "hash", "hashes", "lmhash", "nthash",
}

def _walk_secret_values(value) -> list[str]:
    values: list[str] = []
    if isinstance(value, dict):
        for k, v in value.items():
            lk = str(k).lower()
            if lk in SECRET_KEYS and isinstance(v, str) and v and v != "***":
                values.append(v)
            values.extend(_walk_secret_values(v))
    elif isinstance(value, list):
        for item in value:
            values.extend(_walk_secret_values(item))
    elif isinstance(value, tuple):
        for item in value:
            values.extend(_walk_secret_values(item))
    return values

def redact_text(text: str) -> str:
    """Mask credentials and hashes before writing logs, reports, or console dumps."""
    if text is None:
        return ""
    if SHOW_SECRETS:
        return str(text)
    s = str(text)

    for secret in sorted(set(_walk_secret_values(SESSION)), key=len, reverse=True):
        if len(secret) >= 4:
            s = s.replace(secret, "***")

    # JSON/Python-like key-value secrets.
    s = re.sub(r'("?(?:password|nt_hash|attacker_pass|neo4j_password)"?\s*[:=]\s*)("[^"]*"|\'[^\']*\'|[^\s,}]+)',
               r'\1"***"', s, flags=re.I)

    # Common command-line auth forms.
    s = re.sub(r"(-p(?:assword)?\s+)'[^']*'", r"\1'***'", s, flags=re.I)
    s = re.sub(r'(-p(?:assword)?\s+)"[^"]*"', r'\1"***"', s, flags=re.I)
    s = re.sub(r"(-H(?:ashes)?\s+)'?[:a-fA-F0-9]{32,65}'?", r"\1'***'", s, flags=re.I)
    s = re.sub(r"(-hashes\s+)':?[a-fA-F0-9]{32,65}'", r"\1'***'", s, flags=re.I)

    # Tool/result formats.
    s = re.sub(r"(VALID CRED\s*\[[^\]]+\]\s*:\s*[^:\s]+):[^\s`]+", r"\1:***", s, flags=re.I)
    s = re.sub(r"(NT Hash\s*\[[^\]]+\]\s*:\s*)[a-fA-F0-9]{32}", r"\1***", s, flags=re.I)
    s = re.sub(r"(passwords\s*=\s*)\[[^\]]*\]", r"\1['***']", s, flags=re.I)
    s = re.sub(r"(\[['\"][^'\"]+['\"],\s*['\"][^'\"]+['\"]\]\s*:\s*)\[[^\]]*\]", r"\1['***']", s)
    s = re.sub(r"(Valid credential found:\s*[^:\s]+):[^\s`]+", r"\1:***", s, flags=re.I)
    s = re.sub(r"([A-Za-z0-9_.-]+\\[A-Za-z0-9_$.-]+):([^\s`]+)", r"\1:***", s)
    s = re.sub(r"(`?[^`\s]+`?\s*(?:→|->)\s*`?)[a-fA-F0-9]{32}(`?)", r"\1***\2", s)
    s = re.sub(r"\b[a-fA-F0-9]{32}\b", "***", s)
    return s

def redact_obj(value):
    """Return a copy of an object with secret fields masked for display/storage."""
    if SHOW_SECRETS:
        return value
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            lk = str(k).lower()
            if lk in SECRET_KEYS:
                out[k] = "***"
            elif lk == "loot":
                out[k] = {acct: "***" for acct in dict(v).keys()} if isinstance(v, dict) else "***"
            else:
                out[k] = redact_obj(v)
        return out
    if isinstance(value, list):
        return [redact_obj(v) for v in value]
    if isinstance(value, tuple):
        return tuple(redact_obj(v) for v in value)
    if isinstance(value, str):
        return redact_text(value)
    return value

def scrub_masked_secrets(value):
    """Convert redacted placeholders back to empty values so they are never reused as credentials."""
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            lk = str(k).lower()
            if lk in SECRET_KEYS and v == "***":
                out[k] = ""
            elif lk == "loot" and isinstance(v, dict):
                out[k] = {acct: hv for acct, hv in v.items() if hv != "***"}
            else:
                out[k] = scrub_masked_secrets(v)
        return out
    if isinstance(value, list):
        return [scrub_masked_secrets(v) for v in value]
    if isinstance(value, tuple):
        return tuple(scrub_masked_secrets(v) for v in value)
    return value

# ── Derived fields ────────────────────────────────────────────────────────────
def _refresh_derived():
    dom  = SESSION.get("domain", "")
    user = SESSION.get("username", "")
    if dom and user:
        SESSION["domain_user"] = f"{dom}\\{user}"
        SESSION["upn"]         = f"{user}@{dom}"
    if not SESSION.get("base_dn") and dom:
        SESSION["base_dn"] = "DC=" + dom.replace(".", ",DC=")
    # Set KRB5 env vars if kerberos is active
    if SESSION.get("use_kerberos"):
        if SESSION.get("krb5_ccache"):
            os.environ["KRB5CCNAME"] = SESSION["krb5_ccache"]
        if SESSION.get("krb5_config"):
            os.environ["KRB5_CONFIG"] = SESSION["krb5_config"]

_refresh_derived()

PER_ENGAGEMENT_DEFAULTS = {
    "commands_run": [],
    "findings": [],
    "owned_users": [],
    "owned_machines": [],
    "loot": {},
    "agent_intel": {},
    "winrm_dead_for": [],
    "winrm_attempted_for": [],
    "network_unreachable": False,
    "network_unreachable_hits": 0,
    "ntlm_disabled": False,
    "ntlm_disabled_hint": False,
    "use_kerberos": False,
    "krb5_ccache": "",
    "krb5_config": _ENV.get("KRB5_CONFIG", "/etc/krb5.conf"),
    "dc_fqdn": "",
    "hostname": "",
    "dc_hostname": "",
    "base_dn": "",
}

def _norm_target(value: str, *, domain: bool = False) -> str:
    value = str(value or "").strip()
    return value.lower().rstrip(".") if domain else value

def target_changed(dc_ip: str = "", domain: str = "") -> bool:
    """Return True when a non-empty target field differs from the loaded session."""
    old_dc = _norm_target(SESSION.get("dc_ip", ""))
    old_dom = _norm_target(SESSION.get("domain", ""), domain=True)
    new_dc = _norm_target(dc_ip)
    new_dom = _norm_target(domain, domain=True)
    return bool(
        (old_dc and new_dc and old_dc != new_dc)
        or (old_dom and new_dom and old_dom != new_dom)
    )

def reset_engagement_state() -> None:
    """Clear state that belongs to one target/domain and must not cross engagements."""
    for key, default in PER_ENGAGEMENT_DEFAULTS.items():
        if isinstance(default, dict):
            SESSION[key] = dict(default)
        elif isinstance(default, list):
            SESSION[key] = list(default)
        else:
            SESSION[key] = default
    SESSION["start_time"] = datetime.now().isoformat()
    os.environ.pop("KRB5CCNAME", None)
    os.environ.pop("KRB5_CONFIG", None)
    # NOTE: deliberately does NOT delete *.pfx/*.ccache on disk — those are
    # loot/evidence. Cross-engagement cert leakage is prevented at the decision
    # layer instead: the rule engine scopes leftover PFX to the current domain
    # via _pfx_cert_domain(), and adcs_scan runs regardless of an existing hash.
    _refresh_derived()

def reset_session_for_target_change(dc_ip: str = "", domain: str = "") -> bool:
    """Reset per-engagement state before switching to a different target/domain."""
    changed = target_changed(dc_ip=dc_ip, domain=domain)
    if changed:
        reset_engagement_state()
    if dc_ip:
        SESSION["dc_ip"] = str(dc_ip).strip()
    if domain:
        SESSION["domain"] = str(domain).strip()
    _refresh_derived()
    return changed

# ══════════════════════════════════════════════════════════════════════════════
# KERBEROS FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def krb5_request_tgt(
    username: str = "",
    password: str = "",
    nt_hash:  str = "",
    domain:   str = "",
    dc_ip:    str = "",
    ccache:   str = "",
) -> bool:
    """
    Request a TGT using kinit (password) or impacket-getTGT (hash/pass).
    Saves ticket to ccache file and updates SESSION.
    Returns True on success.
    """
    user   = username or SESSION.get("username", "")
    pw     = password or SESSION.get("password", "")
    h      = nt_hash  or SESSION.get("nt_hash", "")
    dom    = domain   or SESSION.get("domain", "")
    dc     = dc_ip    or SESSION.get("dc_ip", "")
    cache  = ccache   or SESSION.get("krb5_ccache", "") or f"/tmp/{user}_{dom}.ccache"

    if not user or not dom:
        return False

    print(f"\n  [*] Requesting TGT for {user}@{dom}...")

    # Method 1 — impacket getTGT (bypass venv: use system python3 directly)
    _syspy   = "/usr/bin/python3"
    _imp_dir = "/usr/share/doc/python3-impacket/examples"
    getTGT_script = Path(_imp_dir) / "getTGT.py"
    if getTGT_script.exists():
        if h:
            nt = h.split(":")[-1]
            cmd = f"{_syspy} {getTGT_script} {dom}/{user} -hashes :{nt} -dc-ip {dc}"
        elif pw:
            cmd = f"{_syspy} {getTGT_script} {dom}/{user}:'{pw}' -dc-ip {dc}"
        else:
            return False

        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            # impacket saves as user.ccache in current dir
            default_ccache = f"{user}.ccache"
            if Path(default_ccache).exists():
                import shutil as _shutil; _shutil.move(default_ccache, cache)
            SESSION["krb5_ccache"] = cache
            SESSION["use_kerberos"] = True
            os.environ["KRB5CCNAME"] = cache
            print(f"  [+] TGT obtained → {cache}")
            return True
        else:
            print(f"  [!] getTGT failed: {result.stderr.strip()}")
            return False

    # Method 2 — kinit (requires Kerberos client installed + krb5.conf)
    kinit = shutil.which("kinit")
    if kinit and pw:
        cmd = f"echo '{pw}' | kinit {user}@{dom.upper()}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            SESSION["use_kerberos"] = True
            # Copy ccache to desired location
            default = os.environ.get("KRB5CCNAME", f"/tmp/krb5cc_{os.getuid()}")
            if default != cache:
                subprocess.run(f"cp {default} {cache}", shell=True)
            SESSION["krb5_ccache"] = cache
            os.environ["KRB5CCNAME"] = cache
            print(f"  [+] TGT obtained via kinit → {cache}")
            return True
        else:
            print(f"  [!] kinit failed: {result.stderr.strip()}")
            return False

    print("  [!] No TGT method available (install impacket or krb5-user)")
    return False


def krb5_load_ticket(ccache_path: str) -> bool:
    """Load an existing .ccache ticket file into session."""
    p = Path(ccache_path)
    if not p.exists():
        print(f"  [!] Ticket file not found: {ccache_path}")
        return False
    SESSION["krb5_ccache"]  = str(p)
    SESSION["use_kerberos"] = True
    os.environ["KRB5CCNAME"] = str(p)
    print(f"  [+] Ticket loaded: {p}")
    return True


def krb5_inject_ticket(kirbi_or_b64: str) -> bool:
    """
    Convert a .kirbi file or Base64 blob to .ccache and load it.
    Uses impacket-ticketConverter.
    """
    converter = shutil.which("impacket-ticketConverter") or \
                shutil.which("ticketConverter.py")
    if not converter:
        print("  [!] impacket-ticketConverter not found")
        return False

    # Detect if input is Base64 or file path
    if Path(kirbi_or_b64).exists():
        kirbi_path = kirbi_or_b64
    else:
        # Assume Base64 — write to temp file
        import base64
        tmp_kirbi = "/tmp/ticket_inject.kirbi"
        with open(tmp_kirbi, "wb") as f:
            f.write(base64.b64decode(kirbi_or_b64))
        kirbi_path = tmp_kirbi

    ccache_out = kirbi_path.replace(".kirbi", ".ccache")
    cmd = f"{converter} {kirbi_path} {ccache_out}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    if result.returncode == 0:
        return krb5_load_ticket(ccache_out)
    else:
        print(f"  [!] Ticket conversion failed: {result.stderr.strip()}")
        return False


def krb5_list_tickets() -> str:
    """Run klist and return output."""
    klist = shutil.which("klist")
    if not klist:
        return "  [!] klist not found (install krb5-user)"
    ccache = SESSION.get("krb5_ccache", "")
    cmd = f"klist -c {ccache}" if ccache else "klist"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout or result.stderr


def krb5_destroy() -> None:
    """Destroy current TGT / flush ccache."""
    kdestroy = shutil.which("kdestroy")
    ccache   = SESSION.get("krb5_ccache", "")
    if kdestroy:
        subprocess.run(f"kdestroy -c {ccache}" if ccache else "kdestroy",
                       shell=True, capture_output=True)
    elif ccache and Path(ccache).exists():
        Path(ccache).unlink()
    SESSION["use_kerberos"] = False
    SESSION["krb5_ccache"]  = ""
    os.environ.pop("KRB5CCNAME", None)
    print("  [+] Kerberos ticket destroyed")


def krb5_renew() -> bool:
    """Renew TGT before it expires."""
    kinit = shutil.which("kinit")
    if not kinit:
        return False
    ccache = SESSION.get("krb5_ccache", "")
    cmd = f"kinit -R -c {ccache}" if ccache else "kinit -R"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print("  [+] TGT renewed successfully")
        return True
    print(f"  [!] TGT renewal failed: {result.stderr.strip()}")
    return False

# ══════════════════════════════════════════════════════════════════════════════
# AUTH STRING HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def get_auth_string() -> str:
    """
    Best impacket-compatible auth string.
    Priority: Kerberos > NT Hash > Password > Anonymous
    """
    dom  = SESSION.get("domain", "")
    user = SESSION.get("username", "")
    pw   = SESSION.get("password", "")
    h    = SESSION.get("nt_hash", "")
    krb  = SESSION.get("use_kerberos", False)

    base = f"{dom}/{user}"

    if krb:
        return f"{base} -k -no-pass"
    elif h:
        if ":" not in h:
            h = f"aad3b435b51404eeaad3b435b51404ee:{h}"
        return f"{base} -hashes {h}"
    elif pw:
        return f"{base}:'{pw}'"
    else:
        return f"{base}"


def get_cme_auth() -> str:
    """CrackMapExec auth flags."""
    user = SESSION.get("username", "")
    pw   = SESSION.get("password", "")
    dom  = SESSION.get("domain", "")
    h    = SESSION.get("nt_hash", "")
    krb  = SESSION.get("use_kerberos", False)

    if krb:
        return f"-u '{user}' -k -d {dom}"
    elif h:
        nt = h.split(":")[-1]
        return f"-u '{user}' -H '{nt}' -d {dom}"
    elif pw:
        return f"-u '{user}' -p '{pw}' -d {dom}"
    else:
        return f"-u '' -p '' -d {dom}"


def get_evil_winrm_auth() -> str:
    """Evil-WinRM auth flags."""
    user = SESSION.get("username", "")
    pw   = SESSION.get("password", "")
    h    = SESSION.get("nt_hash", "")
    dc   = SESSION.get("dc_ip", "")
    krb  = SESSION.get("use_kerberos", False)

    if krb:
        return f"-i {dc} -u {user} -r {SESSION.get('domain','').upper()}"
    elif h:
        nt = h.split(":")[-1]
        return f"-i {dc} -u {user} -H {nt}"
    else:
        return f"-i {dc} -u {user} -p '{pw}'"


def get_auth_mode() -> str:
    """Human-readable current auth mode."""
    if SESSION.get("use_kerberos"):
        cache = SESSION.get("krb5_ccache", "default")
        return f"Kerberos (ccache: {cache})"
    elif SESSION.get("nt_hash"):
        return "Pass-the-Hash (NT hash)"
    elif SESSION.get("password"):
        return "Password"
    else:
        return "Anonymous / No Creds"


def has_creds() -> bool:
    return bool(
        SESSION.get("username") and (
            SESSION.get("password") or
            SESSION.get("nt_hash") or
            SESSION.get("use_kerberos")
        )
    )

def has_domain_creds() -> bool:
    return bool(SESSION.get("domain") and has_creds())

# ── Session persistence ───────────────────────────────────────────────────────
def save_session(path: Path = SESSION_FILE, redact: bool = False) -> None:
    path.parent.mkdir(exist_ok=True)
    data = {k: v for k, v in SESSION.items() if k != "commands_run"}
    if redact and not SHOW_SECRETS:
        data = redact_obj(data)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)

def load_session(path: Path = SESSION_FILE) -> bool:
    if not path.exists():
        return False
    with open(path) as f:
        data = json.load(f)
    data = scrub_masked_secrets(data)
    SESSION.update(data)
    _refresh_derived()
    return True

def update_session(**kwargs) -> None:
    SESSION.update(kwargs)
    _refresh_derived()

def add_owned_user(username: str, method: str = "") -> None:
    entry = {"user": username, "method": method, "time": datetime.now().isoformat()}
    if entry not in SESSION["owned_users"]:
        SESSION["owned_users"].append(entry)

def add_owned_machine(machine: str, method: str = "") -> None:
    entry = {"machine": machine, "method": method, "time": datetime.now().isoformat()}
    if entry not in SESSION["owned_machines"]:
        SESSION["owned_machines"].append(entry)

def add_loot(key: str, value: str) -> None:
    SESSION["loot"][key] = value

# Auto-load
load_session()
