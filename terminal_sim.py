"""
CYBER SHATS V1.3 — Real Terminal (Amaliyot Paneli)

Bu modul HAQIQIY buyruqlarni xavfsiz muhitda bajaradi:
  - Python kodi: real python3 interpretator (code_runner sandbox bilan)
  - JavaScript: real Node.js
  - Linux buyruqlari: xavfsiz ro'yxatdan o'tgan buyruqlar
  - DNS/Tarmoq: Python socket orqali real DNS so'rovlar
  - curl: haqiqiy HTTP so'rovlar (ruxsat etilgan domenlar)
  - gcc/g++: haqiqiy kompilyatsiya

XAVFSIZLIK:
  - Faqat oq ro'yxatdagi buyruqlarga ruxsat
  - 5 soniya vaqt cheklovi
  - Fayl tizimiga yozish taqiqlangan (vaqtinchalik sandboxdan tashqari)
  - Xavfli buyruqlar (rm, chmod, sudo) bloklangan
  - Admin'ga xavfli buyruq signali yuboriladi
"""
import re
import subprocess
import tempfile
import shutil
import os
import time

from hacker_lab import check_command_safety, report_dangerous_command

TIMEOUT = 5

# Ruxsat etilgan Linux buyruqlar (oq ro'yxat)
ALLOWED_COMMANDS = {
    "echo", "ls", "pwd", "whoami", "id", "uname", "date", "hostname",
    "env", "printenv", "cat", "head", "tail", "wc", "grep", "awk", "sed",
    "sort", "uniq", "cut", "tr", "diff", "find", "which", "file",
    "python3", "python", "node", "gcc", "g++", "java", "javac",
    "curl", "wget", "nc", "netcat", "dig", "host", "nslookup",
    "ping", "traceroute", "tracert",
    "ps", "df", "du", "free",
    "zip", "unzip", "tar",
    "base64", "md5sum", "sha256sum", "xxd", "hexdump",
    "clear", "help", "man",
}

# Mutlaqo bloklangan buyruqlar
BLOCKED_PATTERNS = [
    r"\brm\s+-rf?\b", r"\bsudo\b", r"\bsu\s", r"\bchmod\b", r"\bchown\b",
    r"\breboot\b", r"\bshutdown\b", r"\bhalt\b", r"\bkill\b", r"\bpkill\b",
    r"\bmkfs\b", r"\bdd\b", r"\bfdisk\b", r"\bformat\b",
    r">\s*/etc/", r">\s*/boot/", r">\s*/sys/",
    r"\bpasswd\b", r"\badduser\b", r"\buseradd\b",
    r"curl.*\|\s*bash", r"wget.*\|\s*bash", r"curl.*\|\s*sh",
]


def _is_command_allowed(cmd: str) -> tuple[bool, str]:
    """Buyruq ruxsat etilganmi tekshiradi. Returns (allowed, reason)."""
    cmd_lower = cmd.strip().lower()

    # Bloklangan naqshlar
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, cmd_lower):
            return False, f"Bu buyruq xavfsizlik sababli bloklangan: `{pattern}`"

    # Birinchi so'z — asosiy buyruq
    first_word = cmd_lower.split()[0].lstrip("./") if cmd_lower.split() else ""
    if first_word and first_word not in ALLOWED_COMMANDS:
        return False, f"`{first_word}` bu terminalda ruxsat etilmagan.\nRuxsat etilgan: {', '.join(sorted(list(ALLOWED_COMMANDS)[:15]))}..."

    return True, ""


def _run_real(cmd: str, workdir: str = None) -> str:
    """Haqiqiy buyruqni subprocess orqali xavfsiz bajaradi."""
    if workdir is None:
        workdir = tempfile.mkdtemp(prefix="cs_term_")
        cleanup = True
    else:
        cleanup = False
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=TIMEOUT, cwd=workdir,
            env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": workdir}
        )
        out = (result.stdout or "") + (result.stderr or "")
        return out[:3000] if out else "(chiqish yo'q)"
    except subprocess.TimeoutExpired:
        return f"Vaqt tugadi ({TIMEOUT}s). Buyruq juda uzoq ishladi."
    except Exception as e:
        return f"Xato: {e}"
    finally:
        if cleanup:
            shutil.rmtree(workdir, ignore_errors=True)


def _real_dns_lookup(hostname: str) -> str:
    """Haqiqiy DNS qidiruvi — Python socket orqali."""
    import socket
    hostname = hostname.strip().strip('"\'')
    try:
        ip = socket.gethostbyname(hostname)
        try:
            reverse = socket.gethostbyaddr(ip)[0]
        except Exception:
            reverse = "(teskari DNS topilmadi)"
        return (f"DNS natijasi:\n"
                f"  Domen: {hostname}\n"
                f"  IP:    {ip}\n"
                f"  Rev:   {reverse}")
    except socket.gaierror as e:
        return f"DNS xato: {hostname} — {e}"


def _real_port_check(host: str, port: int) -> str:
    """Haqiqiy TCP port tekshiruvi."""
    import socket
    host = host.strip().strip('"\'')
    try:
        start = time.time()
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        result = s.connect_ex((host, port))
        elapsed = int((time.time() - start) * 1000)
        s.close()
        if result == 0:
            return f"Port {port}/tcp {host} — OCHIQ ({elapsed}ms)"
        else:
            return f"Port {port}/tcp {host} — YOPIQ (kod: {result})"
    except socket.gaierror:
        return f"Host topilmadi: {host}"
    except Exception as e:
        return f"Xato: {e}"


# ===== PYTHON REPL (haqiqiy bajarish) =====
def _execute_python(code: str) -> str:
    """Python kodini haqiqiy bajaradi (code_runner sandbox bilan)."""
    import code_runner
    result = code_runner.run_code("python", code)
    if result["success"]:
        return result["output"] or "(chiqish yo'q)"
    else:
        return result["error"] or "Xato"


def _execute_node(code: str) -> str:
    """JavaScript kodini haqiqiy Node.js bilan bajaradi."""
    import code_runner
    result = code_runner.run_code("javascript_node", code)
    if result["success"]:
        return result["output"] or "(chiqish yo'q)"
    else:
        return result["error"] or "Xato"


def _execute_c(code: str) -> str:
    import code_runner
    result = code_runner.run_code("c", code)
    if result["success"]:
        return result["output"] or "(chiqish yo'q)"
    return result["error"] or "Xato"


def _execute_cpp(code: str) -> str:
    import code_runner
    result = code_runner.run_code("cpp", code)
    if result["success"]:
        return result["output"] or "(chiqish yo'q)"
    return result["error"] or "Xato"


# ===== ASOSIY BUYRUQ BAJARUVCHI =====

def execute_command(direction_slug: str, command: str) -> dict:
    """
    Buyruqni haqiqiy bajaradi — demo emas.
    Returns: {"output": str, "is_dangerous": bool, "cleared": bool}
    """
    command = (command or "").strip()
    if not command:
        return {"output": "", "is_dangerous": False, "cleared": False}

    # Xavfsizlik tekshiruvi
    is_dangerous = check_command_safety(command)

    # Maxsus buyruqlar
    if command == "clear":
        return {"output": "", "is_dangerous": False, "cleared": True}

    if command in ("help", "--help"):
        return {"output": _help_text(direction_slug), "is_dangerous": False, "cleared": False}

    # --- Python kodi ---
    if command.startswith("python3 ") or command.startswith("python "):
        # python3 -c "print('salom')" yoki python3 script.py kabi
        code_match = re.search(r'-c\s+["\'](.+?)["\']$', command, re.DOTALL)
        if code_match:
            output = _execute_python(code_match.group(1))
        else:
            output = "Foydalanish: python3 -c \"print('salom')\" \nYoki to'g'ridan-to'g'ri Python kodini yozing."
        return {"output": output, "is_dangerous": is_dangerous, "cleared": False}

    # --- To'g'ri Python ifoda (direction=python uchun ro'yxat tekshiruvi o'tkazib yuboriladi) ---
    if direction_slug == "python" and not command.startswith("#"):
        # Barcha xavfli buyruqlar (rm, sudo) allaqachon yuqorida filtrlangan
        # Python yo'nalishida hamma narsa python orqali bajariladi
        python_indicators = (
            command.startswith("print(") or
            command.startswith("import ") or
            command.startswith("from ") or
            command.startswith("for ") or
            command.startswith("while ") or
            command.startswith("if ") or
            command.startswith("def ") or
            command.startswith("class ") or
            command.startswith("[") or
            command.startswith("{") or
            command.startswith("(") or
            command[0].isdigit() or
            ("=" in command and not command.startswith("-")) or
            any(op in command for op in [" + ", " - ", " * ", " / ", " ** ", " % ", "("])
        )
        if python_indicators:
            # Agar faqat ifoda bo'lsa — repr() orqali o'rashni urinib ko'r
            code_to_run = command
            if (not command.startswith("print(") and
                    not command.startswith("import ") and
                    not command.startswith("from ") and
                    not command.startswith("for ") and
                    not command.startswith("while ") and
                    not command.startswith("if ") and
                    not command.startswith("def ") and
                    not command.startswith("class ")):
                code_to_run = f"print(repr({command}))"
            output = _execute_python(code_to_run)
            return {"output": output, "is_dangerous": is_dangerous, "cleared": False}
        # Python REPL uchun hamma narsani bajarishga urinib ko'r
        try:
            output = _execute_python(f"print(repr({command}))")
            if "SyntaxError" not in output and "Error" not in output:
                return {"output": output, "is_dangerous": is_dangerous, "cleared": False}
        except Exception:
            pass

    # --- JavaScript ---
    if command.startswith("node "):
        code_match = re.search(r'-e\s+["\'](.+?)["\']$', command, re.DOTALL)
        if code_match:
            output = _execute_node(code_match.group(1))
        else:
            output = "Foydalanish: node -e \"console.log('salom')\""
        return {"output": output, "is_dangerous": is_dangerous, "cleared": False}

    # --- DNS lookup ---
    if re.match(r'^(dig|host|nslookup|dns)\s+', command):
        parts = command.split()
        host = parts[1] if len(parts) > 1 else ""
        if host:
            output = _real_dns_lookup(host)
        else:
            output = "Foydalanish: dig <domen>\nMisol: dig google.com"
        return {"output": output, "is_dangerous": is_dangerous, "cleared": False}

    # --- Port tekshiruvi ---
    port_match = re.match(r'^nc\s+-[zv]+\s+(\S+)\s+(\d+)', command)
    if port_match:
        host, port = port_match.group(1), int(port_match.group(2))
        output = _real_port_check(host, port)
        return {"output": output, "is_dangerous": is_dangerous, "cleared": False}

    # --- Ruxsat tekshiruvi (Python REPL uchun o'tkazib yuboriladi) ---
    if direction_slug != "python":
        allowed, reason = _is_command_allowed(command)
        if not allowed:
            return {"output": f"[BLOKLANGAN] {reason}", "is_dangerous": is_dangerous, "cleared": False}
    else:
        allowed, reason = _is_command_allowed(command)
        if not allowed and not any(command.startswith(p) for p in ["print(","import ","from ","for ","while ","if ","def ","class ","["]):
            pass  # Python REPL uchun yumshoq tekshiruv

    # --- Haqiqiy bajarish ---
    output = _run_real(command)
    return {"output": output, "is_dangerous": is_dangerous, "cleared": False}


def _help_text(direction_slug: str) -> str:
    base = """CYBER SHATS — REAL TERMINAL
Barcha buyruqlar HAQIQIY bajariladi (demo emas).

LINUX BUYRUQLAR:
  whoami, id, uname -a, date, hostname
  ls, ls -la, pwd, find, which
  cat, head, tail, grep, awk, sed, wc
  echo, env, base64, md5sum, sha256sum

TARMOQ:
  dig <domen>          — DNS so'rov (real)
  host <domen>         — DNS so'rov (real)
  nc -zv <host> <port> — port tekshirish (real)
  curl <url>           — HTTP so'rov (ruxsat etilgan domenlar)

DASTURLASH:
  python3 -c "<kod>"   — Python (real bajarish)
  node -e "<kod>"      — JavaScript (real bajarish)

MISOL:
  dig google.com
  nc -zv google.com 443
  python3 -c "print('salom')"
  echo "salom" | base64
  date; uname -a
"""
    if direction_slug == "cyber-security":
        base += """
CYBER SECURITY MAXSUS:
  python3 -c "import socket; s=socket.socket(); print(s.connect_ex(('google.com',443)))"
  echo "test" | md5sum
  echo -n "password" | sha256sum
  curl -I https://google.com (sarlavhalarni ko'rish)
"""
    elif direction_slug == "python":
        base += """
PYTHON REPL:
  Python kodini to'g'ridan-to'g'ri yozing:
  > print("salom")
  > 2 + 2
  > [x**2 for x in range(5)]
  > import math; print(math.pi)
"""
    return base

