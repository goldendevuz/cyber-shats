"""
CYBER SHATS V1.3 — Xavfsiz terminal simulyatori

Bu modul HAQIQIY tizim buyruqlarini bajarmaydi. Faqat oldindan
tayyorlangan buyruq->javob lug'ati orqali ishlaydi. Bu real
xavfsizlik xatari yaratmaydi (Remote Code Execution emas).

Har bir yo'nalish uchun mos "terminal shaxsi" bor:
- cyber-security: Kali Linux terminal simulyatori
- python: Python REPL simulyatori
- web-dev / javascript: Node.js / browser console simulyatori
- boshqalar: umumiy Linux terminal
"""
import re
from hacker_lab import check_command_safety, report_dangerous_command


KALI_RESPONSES = {
    "whoami": "root",
    "pwd": "/root",
    "uname -a": "Linux kali 6.6.9-amd64 #1 SMP x86_64 GNU/Linux",
    "id": "uid=0(root) gid=0(root) groups=0(root)",
    "ls": "Desktop  Documents  Downloads  tools  wordlists",
    "ls -la": "drwxr-xr-x  5 root root 4096 Jan 1 00:00 .\ndrwxr-xr-x 20 root root 4096 Jan 1 00:00 ..\ndrwxr-xr-x  2 root root 4096 Jan 1 00:00 Desktop\ndrwxr-xr-x  2 root root 4096 Jan 1 00:00 tools",
    "nmap -sV demo-lab.local": "Starting Nmap 7.94...\nNmap scan report for demo-lab.local\n22/tcp open ssh OpenSSH 8.9\n80/tcp open http Apache 2.4.54\n443/tcp open https Apache 2.4.54\nNmap done: 1 IP address scanned",
    "nmap -sV": "Foydalanish: nmap -sV <maqsad>\nMisol: nmap -sV demo-lab.local",
    "msfconsole": "Metasploit Framework Console\n     =[ metasploit v6.3 ]\n+ -- --=[ 2370 exploits - 1234 auxiliary ]\nmsf6 >",
    "searchsploit apache": "------------------------------ ---------------------------\n Exploit Title                | Path\n------------------------------ ---------------------------\nApache 2.4.54 mod_cgi RCE     | linux/remote/50383.py\n------------------------------ ---------------------------",
    "sqlmap -u demo-lab.local": "sqlmap/1.7 - automatic SQL injection tool\n[INFO] testing connection to the target URL\n[INFO] testing if URL is stable... it is stable\n[WARNING] this is a SIMULATED demo, no real request was sent",
    "hydra -l admin -P wordlist.txt demo-lab.local ssh": "Hydra v9.4 starting...\n[DATA] max 16 tasks per 1 server\n[ATTEMPT] target demo-lab.local - login \"admin\" - pass \"123456\"\n[SIMULATED] demo rejimida haqiqiy hujum amalga oshirilmaydi",
    "aircrack-ng": "Aircrack-ng 1.7\n[SIMULATED] WiFi monitoring uchun haqiqiy adapter kerak (demo rejimda mavjud emas)",
    "wireshark": "[SIMULATED] Wireshark GUI dasturi — bu yerda faqat CLI (tshark) simulyatsiyasi mavjud",
    "john --wordlist=rockyou.txt hash.txt": "John the Ripper 1.9.0\nLoaded 1 password hash\n[SIMULATED] demo: 'password123' (hash1) — namuna natija",
    "cat /etc/passwd": "root:x:0:0:root:/root:/bin/bash\ndaemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin\n[DEMO] bu sandbox faylida haqiqiy tizim ma'lumotlari yo'q",
    "help": "Mavjud demo buyruqlar: whoami, pwd, ls, nmap, msfconsole, searchsploit, sqlmap, hydra, john, cat /etc/passwd\nBarcha buyruqlar SIMULATSIYA — haqiqiy tarmoq so'rovi yuborilmaydi.",
    "clear": "__CLEAR__",
}

PYTHON_RESPONSES = {
    "print('hello')": "hello",
    'print("hello")': "hello",
    "print('hello world')": "hello world",
    "2+2": "4",
    "2 + 2": "4",
    "import sys; print(sys.version)": "3.12.0 (CYBER SHATS sandbox)",
    "help()": "Python yordamchisi: bu sandbox REPL. print(), oddiy matematik amallar va o'zgaruvchilar qo'llab-quvvatlanadi.",
    "exit()": "__CLEAR__",
}

GENERIC_RESPONSES = {
    "whoami": "student",
    "pwd": "/home/student",
    "ls": "projects  notes.txt  README.md",
    "help": "Mavjud demo buyruqlar: whoami, pwd, ls, echo <matn>",
    "clear": "__CLEAR__",
}


def get_terminal_type(direction_slug: str) -> str:
    if direction_slug == "cyber-security":
        return "kali"
    if direction_slug == "python":
        return "python"
    return "generic"


def execute_command(direction_slug: str, command: str) -> dict:
    """
    Sandbox buyrug'ini "bajaradi" (aslida lug'atdan javob qaytaradi).
    Returns: {"output": str, "is_dangerous": bool, "cleared": bool}
    """
    command = (command or "").strip()
    if not command:
        return {"output": "", "is_dangerous": False, "cleared": False}

    # Xavfsizlik tekshiruvi — har doim, terminal turidan qat'iy nazar
    is_dangerous = check_command_safety(command)

    term_type = get_terminal_type(direction_slug)
    responses = {
        "kali": KALI_RESPONSES,
        "python": PYTHON_RESPONSES,
    }.get(term_type, GENERIC_RESPONSES)

    # echo <matn> — generic uchun maxsus ishlov
    if command.startswith("echo "):
        output = command[5:]
        return {"output": output, "is_dangerous": is_dangerous, "cleared": False}

    cmd_lower = command.lower().strip()
    output = responses.get(cmd_lower)

    if output is None:
        # nmap kabi parametrli buyruqlar uchun moslashuvchan moslik
        if cmd_lower.startswith("nmap") and term_type == "kali":
            output = KALI_RESPONSES.get("nmap -sV")
        elif cmd_lower.startswith("print(") and term_type == "python":
            # Oddiy print() simulyatsiyasi: ichidagi matnni chiqaramiz
            m = re.match(r"print\((.+)\)", command.strip())
            if m:
                inner = m.group(1).strip().strip("'\"")
                output = inner
            else:
                output = "SyntaxError: demo REPL faqat oddiy print() ni qo'llab-quvvatlaydi"
        else:
            output = f"command not found: {command}\n(Bu sandbox terminal — 'help' yozib mavjud buyruqlarni ko'ring)"

    cleared = output == "__CLEAR__"
    return {"output": "" if cleared else output, "is_dangerous": is_dangerous, "cleared": cleared}
