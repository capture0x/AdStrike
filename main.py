#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════╗
║  AdStrike — Professional Active Directory Attack Framework           ║
║  AUTHORISED PENETRATION TESTING & RED TEAM ENGAGEMENTS ONLY          ║
║                                               By TMRSWRR             ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import sys, os, json, datetime, importlib, platform, argparse, time, shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOOLS_BIN_DIR = os.path.join(BASE_DIR, "tools", "bin")

sys.path.insert(0, BASE_DIR)
if os.path.isdir(TOOLS_BIN_DIR):
    current_path = os.environ.get("PATH", "")
    path_parts = current_path.split(os.pathsep) if current_path else []
    if TOOLS_BIN_DIR not in path_parts:
        os.environ["PATH"] = os.pathsep.join([TOOLS_BIN_DIR, *path_parts])

from utils.helpers import (
    R, G, Y, B, M, C, W, DIM, BOLD, ITAL, UND, RST,
    NEON_RED, NEON_ORG, NEON_YEL, NEON_GRN, NEON_CYN, NEON_BLU,
    NEON_PUR, NEON_PNK, BABY_BLUE, SKY_BLUE, LIGHT_PINK, SOFT_PINK,
    PURE_WHITE, SOFT_WHITE, MIST, SLATE, STEEL, SILVER, fg,
    ADSTRIKE_PINK, ADSTRIKE_PURPLE,
    success, warn, info, error, prompt, pause, cprint,
    print_banner, print_table, spinner,
)
from config.settings import (
    SESSION, CONFIG, save_session, load_session, get_auth_mode, redact_obj,
    reset_engagement_state, reset_session_for_target_change,
)

VERSION  = "5.0"
CODENAME = "AdStrike"
AUTHOR   = "tmrswrr"
BUILD    = "2026.04"

# ══════════════════════════════════════════════════════════════════════════════
#  BANNER  —  AdStrike red × blue professional aesthetic
# ══════════════════════════════════════════════════════════════════════════════
_ART = r"""

╭━━━┳━━━╮╱╱╭━━━┳━━━━┳━━━┳━━┳╮╭━┳━━━╮
┃╭━╮┣╮╭╮┃╱╱┃╭━╮┃╭╮╭╮┃╭━╮┣┫┣┫┃┃╭┫╭━━╯
┃┃╱┃┃┃┃┃┃╱╱┃╰━━╋╯┃┃╰┫╰━╯┃┃┃┃╰╯╯┃╰━━╮
┃╰━╯┃┃┃┃┣━━╋━━╮┃╱┃┃╱┃╭╮╭╯┃┃┃╭╮┃┃╭━━╯
┃╭━╮┣╯╰╯┣━━┫╰━╯┃╱┃┃╱┃┃┃╰┳┫┣┫┃┃╰┫╰━━╮
╰╯╱╰┻━━━╯╱╱╰━━━╯╱╰╯╱╰╯╰━┻━━┻╯╰━┻━━━╯"""

# ── Colour palette — AdStrike red / blue / white ─────────────────────────────
_C1    = BABY_BLUE    # legacy blue primary accent / phase labels
_C2    = LIGHT_PINK   # #FD2636 red secondary / keys
_C3    = fg(245)      # separators / frames
_CDIM  = fg(252)      # readable hints
_BLINK = ""        # no blink
_GLITCH = ""

# Keep old aliases so existing code doesn't break
_PINK = LIGHT_PINK
_PURP = BABY_BLUE

SHOW_MAIN_BANNER = True
_BANNER_ANIMATED = False


def _render_banner(offset: int = 0, indent: int = 0) -> str:
    """Render the main ASCII logo with an optional one-shot motion frame."""
    palette = [LIGHT_PINK, BABY_BLUE]
    prefix = " " * max(indent, 0)
    out = []
    for i, line in enumerate(ln for ln in _ART.splitlines() if ln.strip()):
        color = palette[(i + offset) % len(palette)]
        out.append(f"{prefix}{color}{BOLD}{line}{RST}")
    return "\n".join(out)

def _tagline() -> str:
    sep  = f"{LIGHT_PINK}{'─' * 84}{RST}"
    blu  = BABY_BLUE
    pink = LIGHT_PINK
    dim  = SOFT_WHITE

    row1 = (
        f"  {blu}{BOLD}ACTIVE DIRECTORY STRIKE FRAMEWORK{RST}"
        f"  {fg(252)}|{RST}  "
        f"{pink}{BOLD}v{VERSION} «{CODENAME}»{RST}"
        f"  {fg(252)}|  build {BUILD}{RST}"
    )
    row2 = (
        f"  {dim}25 menu entries  |  5 active phases  |  OSCP edition  |  reports  |  creator: tmrswrr{RST}"
    )
    row3 = (
        f"  {LIGHT_PINK}{BOLD}[!]{RST}  "
        f"{PURE_WHITE}Authorised penetration testing and red-team engagements only{RST}"
    )
    return f"{sep}\n{row1}\n{row2}\n{row3}\n{sep}"

def _clear_screen():
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()

def _animate_banner_once():
    """One-shot ASCII-logo slide animation for the initial menu draw."""
    if not sys.stdout.isatty() or os.environ.get("ADSTRIKE_NO_ANIMATION"):
        return False

    sys.stdout.write("\033[?25l")
    try:
        for frame, indent in enumerate([18, 14, 10, 6, 3, 0]):
            sys.stdout.write("\033[H\033[J")
            print()
            print(_render_banner(offset=frame, indent=indent))
            sys.stdout.flush()
            time.sleep(0.055)
        sys.stdout.write("\033[H\033[J")
        print()
        print(_render_banner())
        sys.stdout.flush()
        time.sleep(1)
        return True
    finally:
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()

def show_banner(clear: bool = True, animate: bool = False):
    global _BANNER_ANIMATED
    if not SHOW_MAIN_BANNER:
        return
    if clear:
        _clear_screen()
    banner_already_drawn = False
    if animate and not _BANNER_ANIMATED:
        banner_already_drawn = _animate_banner_once()
        _BANNER_ANIMATED = True
    if not banner_already_drawn:
        print()
        print(_render_banner())
    print(_tagline())
    print()

# ══════════════════════════════════════════════════════════════════════════════
#  MODULE REGISTRY  —  grouped by kill-chain phase
# ══════════════════════════════════════════════════════════════════════════════
PHASES = [
    ("0", "RECONNAISSANCE",      _C2, [
        ("1",  "Recon & OSINT",             "modules.recon_osint",        "DNS · WHOIS · email harvest · crt.sh"),
        ("2",  "Network Discovery",         "modules.network_discovery",  "nmap · masscan · nbtscan · IPv6"),
    ]),
    ("1", "INITIAL ACCESS",       _C1, [
        ("3",  "Initial Access (No Creds)", "modules.initial_access",     "NTLM capture · relay · ARP · DHCPv6 · RID"),
        # [OSCP-HIDDEN] ("4",  "CVE / AD Exploits",         "modules.cve_exploits",       "NoPac · PrintNightmare · Zerologon"),
        # [OSCP-HIDDEN] ("5",  "AMSI / Defense Evasion",    "modules.amsi_bypass",        "AMSI bypass · CLM · AppLocker · Codecepticon"),
        # [OSCP-HIDDEN] ("6",  "EDR / AV Evasion",          "modules.edr_evasion",        "NanoDump+MockingJay · RWXfinder · BOF · syscalls"),
        # [OSCP-HIDDEN] ("7",  "UAC Bypass",                "modules.uac_bypass",         "fodhelper · eventvwr · CMSTP · token"),
        # [OSCP-HIDDEN] ("8",  "Pre2K & Timeroasting",      "modules.pre2k_timeroast",    "Pre-Win2K accounts · MS-SNTP hash · MAQ abuse"),
        # [OSCP-HIDDEN] ("9",  "WSUS Attack",               "modules.wsus_attack",        "WSUS HTTP spoof · pywsus · SYSTEM code exec"),
    ]),
    ("2", "ENUMERATION",          _C2, [
        ("10", "AD Enumeration",            "modules.enum_ad",            "LDAP · SMB · GPO · DNS · Trust · SPN · LAPS"),
        ("11", "PowerView Enumeration",     "modules.powerview_enum",     "Full PowerView cmdlet reference"),
        ("12", "BloodHound Helper",         "modules.bloodhound_helper",  "SOAPHound · RustHound · ADExplorer · Neo4j"),
        ("13", "File & Share Hunter",       "modules.snaffler_hunter",    "Snaffler · SYSVOL · GPP · spider_plus"),
        ("14", "NetExec / NXC Suite",       "modules.netexec_suite",      "nxc smb · ldap · mssql · winrm · rdp"),
        ("15", "User Hunting",              "modules.user_hunting",       "SessionHunter · UserHunter · NetCease bypass"),
        ("16", "ADIDNS Abuse",              "modules.adidns_abuse",       "Wildcard DNS · WPAD · record inject · DNSAdmins"),
    ]),
    ("3", "PRIVILEGE ESCALATION", _C1, [
        ("17", "Local Privilege Escalation","modules.local_privesc",      "PowerUp · KrbRelayUp · Potatoes · JEA"),
        ("18", "Kerberos Attacks",          "modules.kerberos_attacks",   "Golden · Silver · Diamond · Sapphire · Roast"),
        ("19", "Rubeus Toolkit",            "modules.rubeus_module",      "TGT · TGS · Roast · PTT · S4U · monitor"),
        # [OSCP-HIDDEN] ("20", "Shadow Credentials",        "modules.shadow_credentials", "msDS-KeyCredentialLink · PKINIT"),
        # [OSCP-HIDDEN] ("21", "RBCD Full Chain",           "modules.rbcd_attacks",       "Powermad · S4U2Proxy · /altservice · Bronze Bit"),
        ("22", "ACL / ACE Abuse",           "modules.acl_abuse",          "GenericAll · WriteDACL · ForceChange"),
        # [OSCP-HIDDEN] ("23", "Certificate Abuse (ADCS)",  "modules.cert_abuse",         "ESC1–ESC13 · certipy · CertSync"),
        # [OSCP-HIDDEN] ("24", "RODC Attacks",              "modules.rodc_attacks",       "PRP abuse · Key List · RODC Golden Ticket"),
        # [OSCP-HIDDEN] ("25", "Golden Certificate",        "modules.golden_certificate", "ESC13/14/15/16 · CA key theft · UnPAC · PassTheCert"),
        # [OSCP-HIDDEN] ("26", "UnPAC / PassTheCert",       "modules.unpac_passthecert",  "Targeted Kerberoast · UnPAC · PassTheCert · SPN-Jack"),
        # [OSCP-HIDDEN] ("27", "JEA Attacks",               "modules.jea_attacks",        "JEA bypass · PSReadLine history · CLM escape"),
    ]),
    ("4", "LATERAL MOVEMENT",     _C2, [
        ("28", "Lateral Movement",          "modules.lateral_movement",   "PSExec · WMI · DCOM · Evil-WinRM · WinRS"),
        ("29", "Coercion Attacks",          "modules.coercion_attacks",   "PrinterBug · PetitPotam · Relay→ShadowCreds"),
        ("30", "MSSQL Abuse",               "modules.mssql_abuse",        "xp_cmdshell · PowerUpSQL · linked server RCE"),
        ("31", "Password Attacks",          "modules.password_attacks",   "Spray · kerbrute · stuffing · relay"),
        # [OSCP-HIDDEN] ("32", "SCCM / MECM Abuse",         "modules.sccm_abuse",         "NAA · relay · push · AdminService"),
    ]),
    ("5", "CREDENTIAL ACCESS",    _C1, [
        ("33", "Credential Dumping",        "modules.credential_dump",    "LSASS · SAM · NTDS · lsassy · nanodump"),
        # [OSCP-HIDDEN] ("34", "DPAPI & Credential Vault",  "modules.dpapi_creds",        "dploot bulk · SharpDPAPI · LaZagne · KeeThief"),
        ("35", "DCSync / DCShadow",         "modules.dcsync_dcshadow",    "Full domain hash dump · rogue DC"),
        ("36", "Shadow Copies Abuse",       "modules.shadow_copies",      "VSS · NTDS.dit · SAM · SYSTEM extract"),
    ]),
    ("6", "PERSISTENCE",          _C2, [
        # [OSCP-HIDDEN] ("37", "Domain Persistence",        "modules.persistence",        "Golden · AdminSDHolder · NPPSPY · TTL group"),
        # [OSCP-HIDDEN] ("38", "Local Persistence",         "modules.local_persistence",  "SharPersist · WMI · Registry · Startup"),
        # [OSCP-HIDDEN] ("39", "GPO Abuse",                 "modules.gpo_abuse",          "GPO create · link · exec · hijack · logon"),
        # [OSCP-HIDDEN] ("40", "DNSAdmins Abuse",           "modules.dnsadmins_abuse",    "DLL injection via DNS service"),
        # [OSCP-HIDDEN] ("41", "Trust Attacks",             "modules.trust_attacks",      "TrustKey · SIDHistoryDC · PAM · Multi-Hop"),
        # [OSCP-HIDDEN] ("42", "AD Misc Abuse",             "modules.ad_abuse_extra",     "BackupOps · Skeleton Key · Exchange"),
    ]),
    ("7", "CLOUD / HYBRID",       _C1, [
        # [OSCP-HIDDEN] ("43", "Azure AD / Entra ID",       "modules.azure_ad",           "AADConnect · PTA · PHS · PRT · token"),
        # [OSCP-HIDDEN] ("44", "Entra Hybrid Attacks",      "modules.entra_hybrid_attacks","MSOL DCSync · adconnect.ps1 · DeviceCode · PTA"),
        # [OSCP-HIDDEN] ("45", "gMSA Attacks",              "modules.gmsa_attacks",       "Enum · extract · PTH · shadow-creds · DSInternals"),
        # [OSCP-HIDDEN] ("46", "ADFS & Golden SAML",        "modules.adfs_attacks",       "Token signing cert · Golden SAML · AADInternals"),
        # [OSCP-HIDDEN] ("47", "AiTM / MFA Bypass",         "modules.aitm_mfa_bypass",    "Evilginx2 · MFA fatigue · cookie replay · hybrid pivot"),
        # [OSCP-HIDDEN] ("48", "M365 / Teams Attacks",      "modules.m365_teams_attacks", "MailSniper · Graph API · Teams phishing · Intune abuse"),
    ]),
    ("8", "ADVANCED OPERATIONS",  _C2, [
        # [OSCP-HIDDEN] ("47", "Exploit Chains",            "modules.exploit_chains",     "8 pre-built full-DA attack paths"),
        # [OSCP-HIDDEN] ("48", "C2 Integration",            "modules.c2_integration",     "Sliver · Havoc · MSF · CS payload delivery"),
        # [OSCP-HIDDEN] ("49", "Loot Parser & Analyzer",    "modules.loot_parser",        "Parse · dedup · score · export creds"),
        # [OSCP-HIDDEN] ("50", "AD Advanced Playbook",      "modules.ad_advanced_playbook","WDAC · MDE/MDI · WMI filters · trusts · deception"),
    ]),
]

UTILITIES = [
    # [OSCP-HIDDEN] ("51", "AdStrike Agent (AI)",  "modules.red_team_agent",   "Claude AI · autonomous attack orchestrator · all modules"),
    # [OSCP-HIDDEN] ("52", "Smart Analyst",        "modules.analyst",          "Parse outputs · build attack plan · auto-execute"),
    ("53", "Kerberos Manager",     "modules.kerberos_manager", "TGT · PTT · S4U · ccache · krb5.conf"),
    ("54", "Generate Report",      "modules.reporting",        "HTML · Markdown · JSON pentest report"),
    ("55", "Session Manager",      None,                       "Save · load · switch · clear sessions"),
    ("56", "Tool Checker",         None,                       "Verify all 45+ required offensive tools"),
    ("0",  "Exit",                 None,                       "Save session & quit"),
]

def _number_menu(phases, utilities):
    """Assign stable sequential menu keys from the visible menu order."""
    next_key = 1
    numbered_phases = []
    for phase_num, phase, color, items in phases:
        numbered_items = []
        for _old_key, name, mod_path, desc in items:
            numbered_items.append((str(next_key), name, mod_path, desc))
            next_key += 1
        numbered_phases.append((phase_num, phase, color, numbered_items))

    numbered_utilities = []
    for old_key, name, mod_path, desc in utilities:
        if old_key == "0":
            numbered_utilities.append((old_key, name, mod_path, desc))
            continue
        numbered_utilities.append((str(next_key), name, mod_path, desc))
        next_key += 1

    return numbered_phases, numbered_utilities


PHASES, UTILITIES = _number_menu(PHASES, UTILITIES)

# Flatten for dispatch
MODULES: dict = {}
for _, _, _, items in PHASES:
    for key, name, mod_path, _desc in items:
        MODULES[key] = (name, mod_path)
for key, name, mod_path, _desc in UTILITIES:
    MODULES[key] = (name, mod_path)


def _key_for_name(name: str) -> str:
    for key, (item_name, _mod_path) in MODULES.items():
        if item_name == name:
            return key
    return ""


def _key_for_module(mod_path: str) -> str:
    for key, (_name, item_mod_path) in MODULES.items():
        if item_mod_path == mod_path:
            return key
    return ""


KEY_ENUM = _key_for_module("modules.enum_ad")
KEY_AI_AGENT = _key_for_module("modules.red_team_agent")
KEY_REPORT = _key_for_module("modules.reporting")
KEY_SESSION_MANAGER = _key_for_name("Session Manager")
KEY_TOOL_CHECKER = _key_for_name("Tool Checker")

# ══════════════════════════════════════════════════════════════════════════════
#  DASHBOARD  —  top status strip
# ══════════════════════════════════════════════════════════════════════════════
def _auth_badge():
    if SESSION.get("use_kerberos"):
        return f"{_C1}{BOLD}⚷ KERBEROS{RST}"
    if SESSION.get("nt_hash"):
        return f"{LIGHT_PINK}{BOLD}# PASS-THE-HASH{RST}"
    if SESSION.get("password"):
        return f"{BABY_BLUE}{BOLD}✓ PASSWORD{RST}"
    return f"{SOFT_WHITE}○ ANON{RST}"

def _dashboard():
    dc       = SESSION.get("dc_ip",    "") or f"{DIM}—{RST}"
    dom      = SESSION.get("domain",   "") or f"{DIM}—{RST}"
    user     = SESSION.get("username", "") or f"{DIM}—{RST}"
    eng      = SESSION.get("engagement","") or f"{DIM}—{RST}"
    findings = len(SESSION.get("findings", []))
    cmds     = len(SESSION.get("commands_run", []))
    pwned_u  = len(SESSION.get("owned_users", []))
    pwned_m  = len(SESSION.get("owned_machines", []))

    import shutil
    from utils.helpers import _strip_ansi

    term_cols = shutil.get_terminal_size((100, 24)).columns
    W = max(58, min(96, term_cols - 4))
    frame = LIGHT_PINK
    sep   = f"{SOFT_WHITE}│{RST}"

    top = f"{frame}┌{'─' * W}┐{RST}"
    bot = f"{frame}└{'─' * W}┘{RST}"

    target = f"{_C2}{BOLD}TARGET{RST}  {PURE_WHITE}{user}@{dom}{RST}  {SOFT_WHITE}▶{RST}  {_C1}{dc}{RST}"
    auth = f"{_C2}{BOLD}AUTH{RST}   {_auth_badge()}"
    engage = f"{_C2}{BOLD}ENGAGE{RST}  {PURE_WHITE}{eng}{RST}"
    stats = (
        f"{_C2}{BOLD}STATS{RST}  "
        f"{PURE_WHITE}{BOLD}{cmds}{RST}{SOFT_WHITE} cmd{RST}  "
        f"{SOFT_WHITE}|{RST}  "
        f"{PURE_WHITE}{BOLD}{findings}{RST}{SOFT_WHITE} findings{RST}  "
        f"{SOFT_WHITE}|{RST}  "
        f"{PURE_WHITE}{BOLD}{pwned_u}u/{pwned_m}m{RST}{SOFT_WHITE} owned{RST}"
    )

    def single_row(content):
        content_vis = _strip_ansi(content)
        clipped = content
        if len(content_vis) > W - 4:
            clipped = f"{content_vis[:max(W - 7, 0)]}..."
            content_vis = _strip_ansi(clipped)
        inner = f"  {clipped}{' ' * max(W - 2 - len(content_vis), 0)}"
        return f"{frame}│{RST}{inner}{frame}│{RST}"

    def double_row(left, right):
        left_vis = _strip_ansi(left)
        right_vis = _strip_ansi(right)
        left_col = max(26, (W - 5) // 2)
        left_pad = max(left_col - len(left_vis), 0)
        used = 2 + len(left_vis) + left_pad + 2 + 1 + 2 + len(right_vis)
        right_pad = max(W - used, 1)
        inner = f"  {left}{' ' * left_pad}  {sep}  {right}{' ' * right_pad}"
        return f"{frame}│{RST}{inner}{frame}│{RST}"

    print(top)
    if W < 86:
        print(single_row(target))
        print(single_row(auth))
        print(single_row(engage))
        print(single_row(stats))
    else:
        print(double_row(target, auth))
        print(double_row(engage, stats))
    print(bot)

# ══════════════════════════════════════════════════════════════════════════════
#  MAIN MENU
# ══════════════════════════════════════════════════════════════════════════════
def print_menu():
    show_banner(clear=True, animate=True)
    _dashboard()
    print()
    print(
        f"  {BABY_BLUE}{BOLD}Quick path:{RST} "
        f"{PURE_WHITE}[{KEY_SESSION_MANAGER}] Session{RST} {SOFT_WHITE}-> "
        f"{PURE_WHITE}[{KEY_TOOL_CHECKER}] Tool Checker{RST} {SOFT_WHITE}-> "
        f"{PURE_WHITE}[{KEY_ENUM}] Enum{RST} {SOFT_WHITE}-> "
        f"{PURE_WHITE}[{KEY_REPORT}] Report{RST}"
    )
    print()

    for num, phase, color, items in PHASES:
        label  = f"  PHASE {num}  {phase}  "
        line   = f"{LIGHT_PINK}{'─' * (74 - len(label))}{RST}"
        print(f"  {color}{BOLD}{label}{RST}{line}")
        for key, name, _mod, desc in items:
            print(f"    {_C2}[{key:>2}]{RST}  {PURE_WHITE}{BOLD}{name:<32}{RST}  {SOFT_WHITE}{desc}{RST}")
        print()

    # Utilities
    label = "  UTILITIES  "
    line  = f"{LIGHT_PINK}{'─' * (74 - len(label))}{RST}"
    print(f"  {_C1}{BOLD}{label}{RST}{line}")
    for key, name, _mod, desc in UTILITIES:
        marker = f"{LIGHT_PINK}{BOLD}[ {key}]{RST}" if key == "0" else f"{_C2}[{key:>2}]{RST}"
        print(f"    {marker}  {PURE_WHITE}{BOLD}{name:<32}{RST}  {SOFT_WHITE}{desc}{RST}")
    print()

# ══════════════════════════════════════════════════════════════════════════════
#  AUTO-DISCOVERY  —  scan the target with nmap + LDAP + nxc
# ══════════════════════════════════════════════════════════════════════════════

# Critical AD ports
_AD_PORTS = "53,88,135,139,389,445,464,593,636,3268,3269,3389,5985,9389"

# Service labels by port
_SVC_LABEL = {
    "53":   ("DNS",         "Simple DNS Plus"),
    "88":   ("Kerberos",    "Microsoft Kerberos"),
    "135":  ("RPC",         "Microsoft RPC"),
    "139":  ("NetBIOS",     "NetBIOS-SSN"),
    "389":  ("LDAP",        "Active Directory LDAP"),
    "445":  ("SMB",         "Microsoft SMB"),
    "464":  ("kpasswd",     "Kerberos pw change"),
    "593":  ("RPC/HTTP",    "RPC over HTTP"),
    "636":  ("LDAPS",       "LDAP over SSL"),
    "3268": ("LDAP GC",     "Global Catalog"),
    "3269": ("LDAPS GC",    "Global Catalog SSL"),
    "3389": ("RDP",         "Remote Desktop"),
    "5985": ("WinRM",       "Windows Remote Mgmt"),
    "9389": ("AD WS",       ".NET Message Framing"),
}


def _parse_nmap(output: str) -> dict:
    """Parse nmap output: extract domain, hostname, OS, open ports, clock skew."""
    import ipaddress, re
    result = {"open_ports": [], "clock_skew": None}

    def _is_ip(value: str) -> bool:
        try:
            ipaddress.ip_address(value)
            return True
        except ValueError:
            return False

    for line in output.splitlines():
        # Domain: corp.local
        m = re.search(r"Domain:\s*([\w\.-]+)", line)
        if m and not result.get("domain"):
            dom = m.group(1).rstrip("0")  # nmap sometimes appends a stray trailing 0
            result["domain"] = dom
            result["base_dn"] = "DC=" + dom.replace(".", ",DC=")

        # Hostname: DC01
        m = re.search(r"Nmap scan report for ([\w\.-]+)", line)
        if m and not result.get("hostname"):
            h = m.group(1)
            if not _is_ip(h):
                result["hostname"] = h

        m = re.search(r"\((\w+[\w\.-]+)\)", line)
        if m and "." in m.group(1) and not result.get("dc_fqdn"):
            candidate = m.group(1)
            if not _is_ip(candidate):
                result["dc_fqdn"] = candidate

        # OS
        m = re.search(r"OS:\s*(.+)", line)
        if m:
            result["os"] = m.group(1).strip()

        m = re.search(r"Service Info:.*OS:\s*([\w ]+)", line)
        if m and not result.get("os"):
            result["os"] = m.group(1).strip()

        # Clock skew  (clock-skew: mean: +7h58m...)
        m = re.search(r"clock-skew.*?([+-]\d+h\d+m|\d+ seconds?)", line, re.I)
        if m:
            result["clock_skew"] = m.group(1)

        # Open port line:  445/tcp   open  microsoft-ds
        m = re.match(r"\s*(\d+)/tcp\s+open", line)
        if m:
            result["open_ports"].append(m.group(1))

    return result


def _show_recon_table(ip: str, nmap_data: dict):
    """Display discovered services as a formatted table."""
    ports  = nmap_data.get("open_ports", [])
    domain = nmap_data.get("domain", "")
    fqdn   = nmap_data.get("dc_fqdn", "")
    os_    = nmap_data.get("os", "")
    skew   = nmap_data.get("clock_skew")

    print(f"\n  {BABY_BLUE}{BOLD}{'─'*68}{RST}")
    print(f"  {BABY_BLUE}{BOLD}  NMAP RESULTS  —  {ip}{RST}")
    print(f"  {BABY_BLUE}{BOLD}{'─'*68}{RST}")

    if domain:
        print(f"  {LIGHT_PINK}  Domain   {RST}  {PURE_WHITE}{BOLD}{domain}{RST}")
    if fqdn:
        print(f"  {LIGHT_PINK}  FQDN     {RST}  {PURE_WHITE}{BOLD}{fqdn}{RST}")
    if os_:
        print(f"  {LIGHT_PINK}  OS       {RST}  {SOFT_WHITE}{os_}{RST}")

    if skew:
        print(f"\n  {LIGHT_PINK}{BOLD}  [!] Clock Skew: {skew}{RST}  "
              f"{SOFT_WHITE}→ Clock sync required before Kerberos attacks{RST}")
        print(f"  {SOFT_WHITE}      sudo ntpdate {ip}   or   sudo rdate -n {ip}{RST}")

    if ports:
        print(f"\n  {LIGHT_PINK}  {'PORT':<8}  {'SERVICE':<12}  DESCRIPTION{RST}")
        print(f"  {LIGHT_PINK}  {'─'*50}{RST}")
        for p in ports:
            lbl = _SVC_LABEL.get(p, ("", ""))
            svc, desc = lbl[0], lbl[1]
            icon = BABY_BLUE + "●" + RST
            print(f"  {icon}  {PURE_WHITE}{BOLD}{p:<8}{RST}  {BABY_BLUE}{svc:<12}{RST}  {SOFT_WHITE}{desc}{RST}")

    # /etc/hosts suggestion
    if fqdn and domain:
        hostname = fqdn.split(".")[0]
        print(f"\n  {LIGHT_PINK}{BOLD}  Add to /etc/hosts:{RST}")
        print(f"  {SOFT_WHITE}  echo \"{ip} {domain} {fqdn} {hostname}\" | sudo tee -a /etc/hosts{RST}")

    print(f"  {BABY_BLUE}{BOLD}{'─'*68}{RST}\n")


def _auto_discover(ip: str) -> dict:
    """
    Fast target discovery:
    1. LDAP rootDSE first because it is usually sub-second and gives domain/FQDN.
    2. nxc smb fallback if LDAP anonymous/rootDSE does not reveal the domain.
    3. Short nmap port check only for service visibility, not blocking deep scan.
    """
    import subprocess, re
    result = {}

    # ── STEP 1: LDAP rootDSE (fast path) ─────────────────────────────────────
    print(f"\n  {BABY_BLUE}[1/3]{RST} Querying LDAP rootDSE {SOFT_WHITE}(fast){RST}...")
    try:
        from ldap3 import Server, Connection, ALL
        srv = Server(ip, get_info=ALL, connect_timeout=2)
        con = Connection(srv, receive_timeout=3)
        if con.bind():
            info_ = srv.info
            if info_:
                ctx = info_.other.get("defaultNamingContext")
                if ctx:
                    base_dn = str(ctx[0])
                    result["base_dn"] = base_dn
                    result["domain"]  = base_dn.replace("DC=","").replace(",",".").lower()
                dns = info_.other.get("dnsHostName")
                if dns:
                    result["dc_fqdn"] = str(dns[0])
                srv_name = info_.other.get("ldapServiceName")
                if srv_name and not result.get("dc_fqdn"):
                    result["dc_fqdn"] = str(srv_name[0]).split(":")[0]
            con.unbind()
            success("LDAP rootDSE successful")
    except Exception:
        warn("LDAP rootDSE failed or blocked")

    # ── STEP 2: nxc smb fallback ─────────────────────────────────────────────
    if not result.get("domain"):
        print(f"  {BABY_BLUE}[2/3]{RST} nxc smb fallback {SOFT_WHITE}(quick){RST}...")
        try:
            out = subprocess.run(
                ["nxc", "smb", ip],
                capture_output=True, text=True, timeout=6
            ).stdout
            m = re.search(r"\(domain:([^)]+)\)", out)
            if m:
                dom = m.group(1).strip()
                result["domain"]  = dom
                result["base_dn"] = "DC=" + dom.replace(".", ",DC=")
            m = re.search(r"\(name:([^)]+)\)", out)
            if m:
                host = m.group(1).strip()
                dom  = result.get("domain","")
                result["dc_fqdn"] = f"{host}.{dom}" if dom else host
        except Exception:
            warn("nxc fallback failed or timed out")
    else:
        print(f"  {BABY_BLUE}[2/3]{RST} Domain found — skipping nxc fallback")

    # ── STEP 3: optional quick nmap service visibility ───────────────────────
    # Keep session setup fast. If LDAP/nxc already identified the domain, skip
    # nmap by default; operators can run module [2] for full discovery.
    if result.get("domain") and os.environ.get("ADSTRIKE_PORT_CHECK", "").lower() not in ("1", "true", "yes"):
        print(f"  {BABY_BLUE}[3/3]{RST} Port check skipped {SOFT_WHITE}(run [2] Network Discovery when needed){RST}")
        if result.get("dc_fqdn") and not result.get("hostname"):
            result["hostname"] = result["dc_fqdn"].split(".")[0]
        return result

    print(f"  {BABY_BLUE}[3/3]{RST} Quick AD port check {SOFT_WHITE}(~5-10 seconds){RST}...")
    try:
        nmap_out = subprocess.run(
            [
                "nmap", "-Pn", "-n", "-p", _AD_PORTS, "--open",
                "--max-retries", "1", "--host-timeout", "10s", ip,
            ],
            capture_output=True, text=True, timeout=12
        ).stdout

        # Save output to file
        from pathlib import Path
        from config.settings import OUTPUT_DIR
        out_dir = Path(SESSION.get("output_dir") or str(OUTPUT_DIR))
        out_dir.mkdir(exist_ok=True)
        (out_dir / "nmap_recon.txt").write_text(nmap_out)

        nmap_data = _parse_nmap(nmap_out)
        for k, v in nmap_data.items():
            if v and not result.get(k):
                result[k] = v
        _show_recon_table(ip, nmap_data)

    except Exception as e:
        warn(f"quick nmap skipped/failed: {e}")

    # Extract hostname from dc_fqdn
    if result.get("dc_fqdn") and not result.get("hostname"):
        result["hostname"] = result["dc_fqdn"].split(".")[0]

    return result


# ══════════════════════════════════════════════════════════════════════════════
#  SESSION SETUP
# ══════════════════════════════════════════════════════════════════════════════
def session_setup(announce_loaded: bool = True):
    # Already fully configured
    if SESSION.get("dc_ip") and SESSION.get("domain") and SESSION.get("username"):
        if announce_loaded:
            info(
                f"Session loaded  "
                f"{_C1}{SESSION.get('username')}@{SESSION.get('domain')}{RST}"
                f"  {DIM}▶{RST}  "
                f"{_C2}{SESSION.get('dc_ip')}{RST}"
            )
        return

    print_banner("SESSION SETUP", "Configure target — press Enter to skip a field")
    discovered_values = {}

    # Step 1: get DC IP first, then auto-discover domain
    current_ip = SESSION.get("dc_ip", "")
    hint = f"{DIM}[{current_ip}]{RST}" if current_ip else ""
    ip_val = input(f"  {LIGHT_PINK}[?]{RST} {'DC IP Address':<30} {hint}: ").strip()
    if ip_val:
        if reset_session_for_target_change(dc_ip=ip_val):
            warn("Target changed — cleared prior engagement state (Kerberos, loot, owned hosts, findings).")
    elif current_ip:
        ip_val = current_ip

    # Auto-discover: always run (re-scan if IP changed)
    if ip_val:
        discovered = _auto_discover(ip_val)
        if discovered:
            discovered_values = dict(discovered)
            disc_dom = discovered.get("domain", "")
            disc_fqdn = discovered.get("dc_fqdn", "")
            if disc_dom and disc_fqdn:
                fqdn_l = disc_fqdn.lower()
                dom_l = disc_dom.lower()
                if not (fqdn_l == dom_l or fqdn_l.endswith("." + dom_l)):
                    host = discovered.get("hostname") or disc_fqdn.split(".")[0] or "DC01"
                    suggested = f"{host}.{disc_dom}"
                    warn(
                        f"Discovered DC FQDN '{disc_fqdn}' does not match domain '{disc_dom}'. "
                        f"Suggested: {suggested}"
                    )
                    discovered["dc_fqdn"] = suggested
                    discovered_values["dc_fqdn"] = suggested
            for k, v in discovered.items():
                if k == "open_ports":
                    continue
                if v and not SESSION.get(k):
                    SESSION[k] = v
            # Clock skew → sync time before Kerberos attacks
            skew = discovered.get("clock_skew")
            if skew:
                SESSION["_clock_skew"] = skew
                warn(f"Clock skew detected: {skew}  — Sync before Kerberos attacks!")
                print(f"  {DIM}  sudo ntpdate {ip_val}{RST}")
            dom  = SESSION.get("domain","")
            fqdn = SESSION.get("dc_fqdn","")
            if dom:
                success(f"Discovered  domain={_C1}{dom}{RST}  fqdn={_C1}{fqdn}{RST}")

    fields = [
        ("domain",        f"Domain (e.g. {discovered_values.get('domain') or 'corp.local'})"),
        ("dc_fqdn",       f"DC FQDN (e.g. {discovered_values.get('dc_fqdn') or 'DC01.corp.local'})"),
        ("username",      "Username"),
        ("password",      "Password (blank to use hash)"),
        ("nt_hash",       "NTLM Hash (blank if using password)"),
        ("attacker_ip",   "Attacker / Listener IP"),
        ("attacker_iface","Network Interface (e.g. tun0, eth0)"),
        ("engagement",    "Engagement Name"),
    ]
    for key, label in fields:
        current = SESSION.get(key, "")
        disp    = "***" if key in ("password", "nt_hash") and current else current
        detected = discovered_values.get(key, "")
        if detected and detected != current:
            hint = f"{DIM}[current: {disp or '-'} | detected: {detected}]{RST}"
        else:
            hint = f"{DIM}[{disp}]{RST}" if current else ""
        val = input(f"  {LIGHT_PINK}[?]{RST} {label:<30} {hint}: ").strip()
        if val:
            if key == "domain":
                if reset_session_for_target_change(domain=val):
                    warn("Domain changed — cleared prior engagement state (Kerberos, loot, owned hosts, findings).")
            else:
                SESSION[key] = val

    success("Session configured!")
    save_session()

# ══════════════════════════════════════════════════════════════════════════════
#  TOOL CHECKER
# ══════════════════════════════════════════════════════════════════════════════
def tool_checker():
    import shutil, ast
    from pathlib import Path
    print_banner("TOOL CHECKER", "Verifying installed offensive tooling")
    groups = {
        "Impacket": [
            "impacket-secretsdump", "impacket-GetNPUsers", "impacket-GetUserSPNs",
            "impacket-ticketer", "impacket-psexec", "impacket-wmiexec",
            "impacket-smbexec", "impacket-atexec", "impacket-dcomexec",
            "impacket-dacledit", "impacket-ntlmrelayx", "impacket-lookupsid",
            "impacket-addcomputer", "impacket-getTGT", "impacket-getST",
            "impacket-rbcd", "impacket-findDelegation", "impacket-reg",
        ],
        "Core":      ["nxc", "crackmapexec", "evil-winrm", "bloodhound-python",
                      "ldapsearch", "certipy", "enum4linux-ng", "bloodyAD"],
        "Cracking":  ["hashcat", "john", "hydra", "cewl"],
        "Network":   ["nmap", "masscan", "nbtscan", "netdiscover", "rustscan"],
        "Relay":     ["responder", "mitm6", "ntlmrelayx.py"],
        "Kerberos":  ["kerbrute", "klist", "kinit", "kdestroy", "faketime"],
        "Coercion":  ["coercer", "PetitPotam.py", "printerbug.py"],
        "Creds":     ["lsassy", "dploot", "pypykatz", "lazagne"],
        "ADCS":      ["certipy", "certsync"],
        "SCCM":      ["sccmhunter", "SharpSCCM.exe"],
        "Cloud":     ["roadrecon", "roadtx", "AADInternals"],
        "C2":        ["sliver-server", "havoc", "msfconsole"],
        "Misc":      ["dig", "dnstool.py", "rpcclient", "smbclient", "jq"],
    }
    optional_tools = {
        "rustscan", "lazagne", "certsync", "sccmhunter", "SharpSCCM.exe",
        "AADInternals", "sliver-server", "havoc",
    }

    total = sum(len(v) for v in groups.values())
    required_total = sum(1 for tools in groups.values() for t in tools if t not in optional_tools)
    found = 0
    required_found = 0
    rows  = []
    for group, tools in groups.items():
        for t in tools:
            present = bool(shutil.which(t) or shutil.which(t.split(".")[0]))
            optional = t in optional_tools
            if present:
                found += 1
                if not optional:
                    required_found += 1
                status = f"{BABY_BLUE}{BOLD}● READY{RST}"
            elif optional:
                status = f"{SOFT_WHITE}○ OPTIONAL{RST}"
            else:
                status = f"{LIGHT_PINK}{BOLD}○ MISSING{RST}"
            rows.append([group, t, status])

    print_table(["Group", "Tool", "Status"], rows,
                f"Tool availability — required {BABY_BLUE}{required_found}{RST}/{required_total} ready · total {BABY_BLUE}{found}{RST}/{total} ready")

    module_rows = []
    module_health = {"total": 0, "ok": 0, "missing_run": 0, "errors": []}
    for key, (name, mod_path) in sorted(MODULES.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 999):
        if not mod_path:
            continue
        module_health["total"] += 1
        rel = Path(*mod_path.split(".")).with_suffix(".py")
        try:
            tree = ast.parse(rel.read_text())
            has_run = any(isinstance(n, ast.FunctionDef) and n.name == "run" for n in tree.body)
            if has_run:
                module_health["ok"] += 1
                status = f"{BABY_BLUE}{BOLD}● OK{RST}"
            else:
                module_health["missing_run"] += 1
                status = f"{SOFT_PINK}{BOLD}○ NO RUN(){RST}"
            module_rows.append([key, name, str(rel), status])
        except Exception as e:
            module_health["errors"].append({"module": mod_path, "error": str(e)})
            module_rows.append([key, name, str(rel), f"{LIGHT_PINK}{BOLD}○ ERROR{RST}"])

    print()
    print_table(["#", "Module", "File", "Health"], module_rows,
                f"Module health — {BABY_BLUE}{module_health['ok']}{RST}/{module_health['total']} import-ready")

    audit = {
        "generated": datetime.datetime.now().isoformat(),
        "tools": {
            "ready": found,
            "total": total,
            "required_ready": required_found,
            "required_total": required_total,
            "optional_tools": sorted(optional_tools),
            "groups": groups,
        },
        "modules": module_health,
        "session": {
            "domain": SESSION.get("domain", ""),
            "dc_ip": SESSION.get("dc_ip", ""),
            "auth_mode": get_auth_mode(),
        },
    }
    out_dir = os.path.join(SESSION.get("output_dir") or "output", "audit")
    os.makedirs(out_dir, exist_ok=True)
    audit_path = os.path.join(out_dir, "capability_audit.json")
    with open(audit_path, "w") as fh:
        json.dump(audit, fh, indent=2, default=str)
    success(f"Capability audit saved → {audit_path}")

    print(f"""
  {BABY_BLUE}▸ Install commands:{RST}
    {Y}repair{RST}: bash scripts/repair_tools.sh --check
            bash scripts/repair_tools.sh -y
    {Y}apt{RST} : sudo apt install -y impacket-scripts crackmapexec evil-winrm \\
               bloodhound ldap-utils hashcat john hydra nmap masscan nbtscan \\
               netdiscover responder krb5-user dnsutils samba-common-bin
    {Y}pip{RST} : pip install netexec certipy-ad bloodhound mitm6 lsassy dploot \\
               roadrecon roadtx coercer
    {Y}bin{RST} : kerbrute — manual install from GitHub releases
""")
    pause("[Enter] to return")

# ══════════════════════════════════════════════════════════════════════════════
#  SESSION MANAGER
# ══════════════════════════════════════════════════════════════════════════════
def session_manager():
    print_banner("SESSION MANAGER")
    print(f"""
  {BABY_BLUE}[1]{RST} Show current session
  {BABY_BLUE}[2]{RST} Save session to file
  {BABY_BLUE}[3]{RST} Load session from file
  {BABY_BLUE}[4]{RST} Clear credentials
  {BABY_BLUE}[5]{RST} Edit credentials
  {LIGHT_PINK}[0]{RST} Back
""")
    c = input(f"  {M}Choice{RST}: ").strip()
    if c == "1":
        safe = {k: v for k, v in SESSION.items() if k not in ("commands_run",)}
        safe = redact_obj(safe)
        print(json.dumps(safe, indent=2, default=str))
    elif c == "2":
        save_session()
        success("Session saved!")
    elif c == "3":
        path = prompt("Session file path")
        if os.path.exists(path):
            with open(path) as f:
                SESSION.update(json.load(f))
            success("Session loaded!")
        else:
            error("File not found")
    elif c == "4":
        reset_engagement_state()
        for k in ["dc_ip", "domain", "username", "password",
                  "nt_hash", "attacker_ip", "attacker_iface"]:
            SESSION[k] = ""
        success("Session cleared")
    elif c == "5":
        fields = [
            ("dc_ip",         "DC IP / Target", SESSION.get("dc_ip", "")),
            ("domain",        "Domain",        SESSION.get("domain", "")),
            ("username",      "Username",      SESSION.get("username", "")),
            ("password",      "Password",      ""),
            ("nt_hash",       "NT Hash",       ""),
            ("attacker_ip",   "Attacker IP",   SESSION.get("attacker_ip", "")),
        ]
        print()
        for key, label, current in fields:
            display = f" [{current}]" if current and key not in ("password","nt_hash") else ""
            val = prompt(f"{label}{display} (Enter to keep)")
            if val:
                SESSION[key] = val
        from config.settings import _refresh_derived; _refresh_derived()
        save_session()
        success("Credentials updated")
    input(f"\n  {M}[Enter]{RST} to return...")

# ══════════════════════════════════════════════════════════════════════════════
#  DISPATCH
# ══════════════════════════════════════════════════════════════════════════════
def dispatch(choice: str):
    if choice not in MODULES:
        warn("Invalid choice")
        return False
    name, mod_path = MODULES[choice]
    if mod_path is None:
        return True
    try:
        mod = importlib.import_module(mod_path)
        importlib.reload(mod)
        mod.run()
        return True
    except ImportError as e:
        error(f"Module load error: {e}")
        warn(f"Check that modules/{mod_path.split('.')[-1]}.py exists")
    except KeyboardInterrupt:
        warn("Interrupted — returning to menu")
    except Exception as e:
        error(f"Unexpected error in [{name}]: {e}")
        import traceback
        warn(traceback.format_exc())
    return False


def _module_file(mod_path: str):
    from pathlib import Path
    return Path(*mod_path.split(".")).with_suffix(".py")


def validate_registry() -> tuple[list[str], dict]:
    """Validate menu numbering and module entry health."""
    import ast
    from collections import Counter

    issues = []
    entries = [(key, name, mod_path) for key, (name, mod_path) in MODULES.items()]
    numeric_keys = [int(key) for key, _name, _mod_path in entries if key.isdigit() and key != "0"]
    key_counts = Counter(key for key, _name, _mod_path in entries)
    duplicate_keys = sorted(key for key, count in key_counts.items() if count > 1)
    if duplicate_keys:
        issues.append(f"Duplicate menu keys: {', '.join(duplicate_keys)}")

    expected = list(range(1, len(numeric_keys) + 1))
    if sorted(numeric_keys) != expected:
        missing = sorted(set(expected) - set(numeric_keys))
        extra = sorted(set(numeric_keys) - set(expected))
        if missing:
            issues.append(f"Missing menu keys: {', '.join(map(str, missing))}")
        if extra:
            issues.append(f"Unexpected menu keys: {', '.join(map(str, extra))}")

    module_health = {"total": 0, "ok": 0, "missing_file": 0, "missing_run": 0, "errors": []}
    for key, name, mod_path in sorted(entries, key=lambda item: int(item[0]) if item[0].isdigit() else 999):
        if not mod_path:
            continue
        module_health["total"] += 1
        rel = _module_file(mod_path)
        if not rel.exists():
            module_health["missing_file"] += 1
            module_health["errors"].append({"key": key, "module": name, "error": f"missing file: {rel}"})
            continue
        try:
            tree = ast.parse(rel.read_text())
            has_run = any(isinstance(n, ast.FunctionDef) and n.name == "run" for n in tree.body)
            if has_run:
                module_health["ok"] += 1
            else:
                module_health["missing_run"] += 1
                module_health["errors"].append({"key": key, "module": name, "error": "missing run()"})
        except Exception as exc:
            module_health["errors"].append({"key": key, "module": name, "error": str(exc)})

    if module_health["missing_file"]:
        issues.append(f"{module_health['missing_file']} module file(s) missing")
    if module_health["missing_run"]:
        issues.append(f"{module_health['missing_run']} module(s) missing run()")

    return issues, module_health


def self_check() -> int:
    print_banner("SELF CHECK", "Menu registry and module health")
    issues, module_health = validate_registry()
    if issues:
        for item in issues:
            error(item)
    else:
        success("Menu numbering is contiguous and unique")

    total = module_health["total"]
    ok = module_health["ok"]
    if ok == total:
        success(f"Module health OK: {ok}/{total}")
    else:
        warn(f"Module health: {ok}/{total} OK")
        for entry in module_health["errors"][:20]:
            warn(f"[{entry['key']}] {entry['module']}: {entry['error']}")
        if len(module_health["errors"]) > 20:
            warn(f"{len(module_health['errors']) - 20} more issue(s) omitted")
    return 1 if issues or ok != total else 0


def load_session_file(path: str) -> bool:
    from pathlib import Path
    try:
        if load_session(Path(path)):
            success(f"Session loaded: {path}")
            return True
        error(f"Session file not found: {path}")
    except json.JSONDecodeError as exc:
        error(f"Invalid session JSON: {exc}")
    except Exception as exc:
        error(f"Could not load session: {exc}")
    return False


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="AdStrike Active Directory Strike Framework",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--check", action="store_true", help="validate menu registry and module health, then exit")
    parser.add_argument("--module", metavar="N", help="run a menu module directly by number, then exit")
    parser.add_argument("--session", metavar="PATH", help="load a session JSON file before running")
    parser.add_argument("--no-banner", action="store_true", help="suppress the main ASCII banner")
    return parser.parse_args(argv)

# ══════════════════════════════════════════════════════════════════════════════
#  PREFLIGHT
# ══════════════════════════════════════════════════════════════════════════════
def _preflight():
    """Minimal environment sanity check shown once at start-up."""
    try:
        py = platform.python_version()
        if tuple(map(int, py.split("."))) < (3, 8):
            warn(f"Python {py} detected — recommend 3.10+")
    except Exception:
        pass

# ══════════════════════════════════════════════════════════════════════════════
#  MAIN LOOP
# ══════════════════════════════════════════════════════════════════════════════
def main(argv=None):
    global SHOW_MAIN_BANNER
    args = parse_args(argv)
    if args.no_banner:
        SHOW_MAIN_BANNER = False
    if args.session and not load_session_file(args.session):
        sys.exit(1)
    if args.check:
        sys.exit(self_check())

    try:
        _preflight()
        session_setup(announce_loaded=False)

        if args.module:
            choice = args.module.strip()
            if choice == "0":
                save_session()
                sys.exit(0)
            if choice == KEY_SESSION_MANAGER:
                session_manager()
            elif choice == KEY_TOOL_CHECKER:
                tool_checker()
            else:
                if not dispatch(choice):
                    sys.exit(1)
            sys.exit(0)

        while True:
            print_menu()
            try:
                choice = input(f"\n  {LIGHT_PINK}┌─[{RST}{_C1}{BOLD}AdStrike{RST}{LIGHT_PINK}]─[{RST}{_C2}v{VERSION}{LIGHT_PINK}]{RST}\n  {LIGHT_PINK}└──▶{RST} ").strip()
            except EOFError:
                # stdin exhausted — reconnect from /dev/tty
                try:
                    sys.stdin = open("/dev/tty", "r")
                    choice = input(f"\n  {LIGHT_PINK}┌─[{RST}{_C1}{BOLD}AdStrike{RST}{LIGHT_PINK}]─[{RST}{_C2}v{VERSION}{LIGHT_PINK}]{RST}\n  {LIGHT_PINK}└──▶{RST} ").strip()
                except Exception:
                    choice = ""

            if choice == "0":
                save_session()
                print()
                print(f"  {_C2}  Commands run : {PURE_WHITE}{BOLD}{len(SESSION.get('commands_run', []))}{RST}")
                print(f"  {_C2}  Findings     : {PURE_WHITE}{BOLD}{len(SESSION.get('findings', []))}{RST}")
                print(f"  {_C2}  Users pwned  : {PURE_WHITE}{BOLD}{len(SESSION.get('owned_users', []))}{RST}")
                print(f"\n  {LIGHT_PINK}{'─' * 40}{RST}")
                print(f"  {BABY_BLUE}{BOLD}Session saved. Happy hunting.{RST}")
                print(f"  {LIGHT_PINK}{'─' * 40}{RST}\n")
                sys.exit(0)
            elif choice == KEY_SESSION_MANAGER:
                session_manager()
            elif choice == KEY_TOOL_CHECKER:
                tool_checker()
            else:
                dispatch(choice)

    except KeyboardInterrupt:
        print(f"\n\n  {LIGHT_PINK}{BOLD}[!] Caught Ctrl-C — saving session…{RST}")
        save_session()
        sys.exit(0)


if __name__ == "__main__":
    main()
