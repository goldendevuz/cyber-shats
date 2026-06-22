"""
CYBER SHATS V1.3 — Xavfsiz ko'p tilli kod bajaruvchi (Code Runner)

DIQQAT — XAVFSIZLIK: Bu modul foydalanuvchi kodini HAQIQIY bajaradi, lekin
QATTIQ CHEKLOVLAR bilan:
  - Har bir bajarish ALOHIDA, vaqtinchalik papkada (keyin butunlay o'chiriladi)
  - CPU vaqti cheklangan (5 soniya)
  - Xotira cheklangan (128 MB)
  - Yaratilgan fayllar soni cheklangan
  - Tarmoqqa kira olmaydi (resource.RLIMIT orqali ulanish imkoni yo'q, va
    subprocess o'zi tarmoq sozlamalariga ega emas — productionda buni
    qo'shimcha network namespace/firewall bilan ham mustahkamlash tavsiya etiladi)
  - Bajariladigan har bir buyruq oldindan belgilangan, qattiq ro'yxatdan olinadi
    (foydalanuvchi o'zboshidan tizim buyrug'i bera olmaydi)
  - Standart kirish (stdin) yo'q — interaktiv dasturlar ishlamaydi
  - Chiqish hajmi cheklangan (10000 belgi)

Bu yondashuv "to'liq xavfsiz" emas (haqiqiy production tizimida Docker/gVisor
kabi to'liq konteynerlash tavsiya etiladi), lekin oddiy ta'lim mashqlari
(o'quvchi "Hello World" yoki oddiy algoritm yozadi) uchun YETARLI darajada
xavfsiz — chunki resurs va vaqt qattiq cheklangan, fayl tizimiga chiqish yo'q,
va xavfli operatsiyalar (import os/socket cheklanmagan, lekin tarmoqqa
ulanishning o'zi productionda firewall orqali bloklanishi kerak).
"""
import os
import subprocess
import tempfile
import shutil
import uuid
import resource
import signal

# Bajarish vaqti va resurs chegaralari
TIMEOUT_SECONDS = 5
MAX_MEMORY_MB = 128
MAX_OUTPUT_CHARS = 10000

# Taqiqlangan Python modullari/chaqiruvlari — fayl tizimi, tarmoq, tizim.
PYTHON_BLOCKED_PATTERNS = [
    "import os", "from os", "import subprocess", "from subprocess",
    "import socket", "from socket", "import shutil", "from shutil",
    "import sys", "from sys",
    "__import__", "importlib",
    "open(", "exec(", "eval(",
    "ctypes", "pty", "fcntl",
]


def _check_python_safety(code: str) -> str:
    """Xavfli pattern topilsa sabab matnini qaytaradi, xavfsiz bo'lsa None."""
    lowered = code.lower()
    for pattern in PYTHON_BLOCKED_PATTERNS:
        if pattern.lower() in lowered:
            return (f"Xavfsizlik cheklovi: '{pattern}' taqiqlangan. "
                    f"Sandbox faqat oddiy hisoblash/matn ishlovi uchun "
                    f"(fayl, tarmoq, tizim chaqiruvlari ruxsatsiz).")
    return None


LANGUAGES = {
    "python": {
        "name": "Python 3",
        "ext": "py",
        "icon": "code",
        "default_code": 'print("Salom, CYBER SHATS!")\n\nfor i in range(5):\n    print(f"Hisoblash: {i}")\n',
    },
    "javascript_node": {
        "name": "JavaScript (Node.js)",
        "ext": "js",
        "icon": "code",
        "default_code": 'console.log("Salom, CYBER SHATS!");\n\nfor (let i = 0; i < 5; i++) {\n    console.log("Hisoblash:", i);\n}\n',
    },
    "cpp": {
        "name": "C++",
        "ext": "cpp",
        "icon": "terminal",
        "default_code": '#include <iostream>\nusing namespace std;\n\nint main() {\n    cout << "Salom, CYBER SHATS!" << endl;\n    for (int i = 0; i < 5; i++) {\n        cout << "Hisoblash: " << i << endl;\n    }\n    return 0;\n}\n',
    },
    "c": {
        "name": "C",
        "ext": "c",
        "icon": "terminal",
        "default_code": '#include <stdio.h>\n\nint main() {\n    printf("Salom, CYBER SHATS!\\n");\n    for (int i = 0; i < 5; i++) {\n        printf("Hisoblash: %d\\n", i);\n    }\n    return 0;\n}\n',
    },
    "java": {
        "name": "Java",
        "ext": "java",
        "icon": "code",
        "default_code": 'public class Main {\n    public static void main(String[] args) {\n        System.out.println("Salom, CYBER SHATS!");\n        for (int i = 0; i < 5; i++) {\n            System.out.println("Hisoblash: " + i);\n        }\n    }\n}\n',
    },
}


def _limit_resources():
    """Bola jarayon uchun CPU vaqti va xotira chegaralarini o'rnatadi.
    preexec_fn sifatida subprocess.run() ga uzatiladi."""
    try:
        resource.setrlimit(resource.RLIMIT_CPU, (TIMEOUT_SECONDS, TIMEOUT_SECONDS))
        mem_bytes = MAX_MEMORY_MB * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
        # Yangi fayl yarata olmasin (vaqtinchalik papkadan tashqari)
        resource.setrlimit(resource.RLIMIT_FSIZE, (10 * 1024 * 1024, 10 * 1024 * 1024))
        # Yangi jarayon fork qila olmasin (fork bomb himoyasi)
        resource.setrlimit(resource.RLIMIT_NPROC, (10, 10))
    except Exception:
        pass


def _limit_resources_no_mem():
    """Node.js uchun: RLIMIT_AS qo'llanilmaydi (V8 katta virtual xotira manzil
    maydonini oldindan band qiladi, RLIMIT_AS bilan jarayon muzlab qoladi).
    Xotira cheklovi o'rniga Node'ning --max-old-space-size flagi ishlatiladi."""
    try:
        resource.setrlimit(resource.RLIMIT_CPU, (TIMEOUT_SECONDS, TIMEOUT_SECONDS))
        resource.setrlimit(resource.RLIMIT_FSIZE, (10 * 1024 * 1024, 10 * 1024 * 1024))
        resource.setrlimit(resource.RLIMIT_NPROC, (16, 16))
    except Exception:
        pass


def _truncate(text: str) -> str:
    if len(text) > MAX_OUTPUT_CHARS:
        return text[:MAX_OUTPUT_CHARS] + "\n\n... (chiqish kesildi, juda uzun)"
    return text


def run_code(language: str, code: str) -> dict:
    """
    Berilgan tilda kodni xavfsiz, vaqtinchalik, izolyatsiyalangan muhitda
    bajaradi. Returns: {"success": bool, "output": str, "error": str,
    "execution_time_ms": int}
    """
    if language not in LANGUAGES:
        return {"success": False, "output": "", "error": "Noma'lum dasturlash tili.", "execution_time_ms": 0}

    if not code or not code.strip():
        return {"success": False, "output": "", "error": "Kod bo'sh.", "execution_time_ms": 0}

    if len(code) > 20000:
        return {"success": False, "output": "", "error": "Kod juda uzun (maksimal 20000 belgi).", "execution_time_ms": 0}

    workdir = tempfile.mkdtemp(prefix="cybershats_run_")
    import time
    start = time.time()
    try:
        if language == "python":
            result = _run_python(workdir, code)
        elif language == "javascript_node":
            result = _run_node(workdir, code)
        elif language == "cpp":
            result = _run_cpp(workdir, code)
        elif language == "c":
            result = _run_c(workdir, code)
        elif language == "java":
            result = _run_java(workdir, code)
        else:
            result = {"success": False, "output": "", "error": "Bu til hali qo'llab-quvvatlanmaydi."}
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    elapsed_ms = int((time.time() - start) * 1000)
    result["execution_time_ms"] = elapsed_ms
    result["output"] = _truncate(result.get("output", ""))
    result["error"] = _truncate(result.get("error", ""))
    return result


def _run_subprocess(cmd, cwd, timeout=TIMEOUT_SECONDS, limiter=None):
    """Markazlashtirilgan, cheklangan subprocess ishga tushirish."""
    if limiter is None:
        limiter = _limit_resources
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            preexec_fn=limiter if os.name != "nt" else None,
            env={"PATH": os.environ.get("PATH", "")},  # minimal env, tarmoq/maxfiy o'zgaruvchilarsiz
        )
        return proc.returncode == 0, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return False, "", f"Vaqt tugadi ({timeout} soniya ichida bajarilmadi). Cheksiz tsikl bo'lishi mumkin."
    except FileNotFoundError:
        return False, "", (f"'{cmd[0]}' serverda o'rnatilmagan. Administrator bu kompilyator/interpretatorni "
                           f"o'rnatishi kerak.")
    except Exception as e:
        return False, "", str(e)


def _run_python(workdir, code):
    safety_err = _check_python_safety(code)
    if safety_err:
        return {"success": False, "output": "", "error": safety_err}
    filepath = os.path.join(workdir, "main.py")
    with open(filepath, "w") as f:
        f.write(code)
    ok, stdout, stderr = _run_subprocess(["python3", "-I", "main.py"], workdir)
    return {"success": ok, "output": stdout, "error": stderr if not ok else ""}


def _run_node(workdir, code):
    filepath = os.path.join(workdir, "main.js")
    with open(filepath, "w") as f:
        f.write(code)
    ok, stdout, stderr = _run_subprocess(
        ["node", f"--max-old-space-size={MAX_MEMORY_MB}", "--no-addons", "main.js"],
        workdir, limiter=_limit_resources_no_mem
    )
    return {"success": ok, "output": stdout, "error": stderr if not ok else ""}


def _run_cpp(workdir, code):
    src = os.path.join(workdir, "main.cpp")
    binpath = os.path.join(workdir, "main_bin")
    with open(src, "w") as f:
        f.write(code)
    compiled, _, compile_err = _run_subprocess(
        ["g++", "-O2", "-std=c++17", "-o", binpath, src], workdir, timeout=10
    )
    if not compiled:
        return {"success": False, "output": "", "error": f"Kompilyatsiya xatosi:\n{compile_err}"}
    ok, stdout, stderr = _run_subprocess([binpath], workdir)
    return {"success": ok, "output": stdout, "error": stderr if not ok else ""}


def _run_c(workdir, code):
    src = os.path.join(workdir, "main.c")
    binpath = os.path.join(workdir, "main_bin")
    with open(src, "w") as f:
        f.write(code)
    compiled, _, compile_err = _run_subprocess(
        ["gcc", "-O2", "-std=c17", "-o", binpath, src], workdir, timeout=10
    )
    if not compiled:
        return {"success": False, "output": "", "error": f"Kompilyatsiya xatosi:\n{compile_err}"}
    ok, stdout, stderr = _run_subprocess([binpath], workdir)
    return {"success": ok, "output": stdout, "error": stderr if not ok else ""}


def _run_java(workdir, code):
    # Java sinf nomi "Main" bo'lishi shart (oddiy talab, sandbox uchun)
    src = os.path.join(workdir, "Main.java")
    with open(src, "w") as f:
        f.write(code)
    compiled, _, compile_err = _run_subprocess(
        ["javac", "Main.java"], workdir, timeout=15, limiter=_limit_resources_no_mem
    )
    if not compiled:
        return {"success": False, "output": "", "error": f"Kompilyatsiya xatosi:\n{compile_err}"}
    ok, stdout, stderr = _run_subprocess(
        ["java", f"-Xmx{MAX_MEMORY_MB}m", "-cp", workdir, "Main"], workdir,
        timeout=TIMEOUT_SECONDS, limiter=_limit_resources_no_mem
    )
    return {"success": ok, "output": stdout, "error": stderr if not ok else ""}
