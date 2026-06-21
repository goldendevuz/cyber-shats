"""
CYBER SHATS V1.3 — Ping Test moduli (Pentesting bo'limi)

Plan bo'yicha kvota:
- Free:      10 ta tekin, keyin 2,000 CODE/test
- Pro:       20 ta tekin, keyin 1,000 CODE/test
- Cyber Pro: 30 ta tekin, keyin   500 CODE/test

Xavfsizlik chegaralari:
- Faqat ommaviy host'larga ruxsat (ip whitelist emas, blacklist)
- Lokalho'st (127.0.0.1, localhost, 0.0.0.0) va ichki tarmoq IP'lari rad etiladi
- Har bir ping uchun 3 soniyalik timeout
- Bitta foydalanuvchi minutida maksimal 30 ta ping (rate limit)
"""
import time
import socket
import ipaddress
import subprocess
from db import query_one, execute
from pricing import get_price


# Bloklangan host'lar/maxsus IP oraliqlari
BLOCKED_HOSTS = {"localhost", "0.0.0.0"}


def get_quota_and_cost(plan: str) -> tuple[int, int]:
    """Plan bo'yicha tekin kvota va keyin har bir testning narxi."""
    if plan == "vip":
        return get_price("ping_test_vip_quota"), get_price("ping_test_cost_vip")
    elif plan == "cyber_pro":
        return get_price("ping_test_cyber_pro_quota"), get_price("ping_test_cost_cyber_pro")
    elif plan in ("pro", "enterprise"):
        return get_price("ping_test_pro_quota"), get_price("ping_test_cost_pro")
    else:
        return get_price("ping_test_free_quota"), get_price("ping_test_cost_free")


def get_used_count(user_id: int) -> int:
    """Foydalanuvchining shu kungacha (umuman) ishlatgan ping testlar soni."""
    row = query_one("SELECT COUNT(*) c FROM ping_test_usage WHERE user_id=?", (user_id,))
    return row["c"] if row else 0


def get_minute_count(user_id: int) -> int:
    """So'nggi 60 soniya ichidagi ping testlar soni (rate limit)."""
    row = query_one(
        "SELECT COUNT(*) c FROM ping_test_usage WHERE user_id=? AND created_at > datetime('now','-60 seconds')",
        (user_id,)
    )
    return row["c"] if row else 0


def is_host_allowed(host: str) -> tuple[bool, str]:
    """Host xavfsizmi tekshirish."""
    host = (host or "").strip().lower()
    if not host:
        return False, "Host bo'sh."
    if len(host) > 100:
        return False, "Host juda uzun."
    if host in BLOCKED_HOSTS:
        return False, "Bu host bloklangan."

    # Faqat ascii belgilar
    try:
        host.encode("ascii")
    except UnicodeEncodeError:
        return False, "Host'da ruxsatsiz belgilar bor."

    # Belgi cheklovi (faqat harf, raqam, nuqta, defis)
    import re
    if not re.match(r"^[a-z0-9.\-]+$", host):
        return False, "Host formati noto'g'ri."

    # IP manzilini olishga harakat
    try:
        addr_info = socket.getaddrinfo(host, None)
        ip_str = addr_info[0][4][0]
        ip = ipaddress.ip_address(ip_str)
        if ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_multicast or ip.is_reserved:
            return False, "Ichki yoki maxsus IP'larga ping qilib bo'lmaydi."
    except (socket.gaierror, ValueError) as e:
        return False, f"Host topilmadi: {e}"

    return True, "OK"


def do_ping(host: str) -> dict:
    """Bitta ping testini bajaradi va natija qaytaradi.
    Linux/Mac'da `ping -c 1 -W 3`, Windows'da `ping -n 1 -w 3000`."""
    import platform
    system = platform.system().lower()
    if system == "windows":
        cmd = ["ping", "-n", "1", "-w", "3000", host]
    else:
        cmd = ["ping", "-c", "1", "-W", "3", host]

    start = time.time()
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        elapsed_ms = int((time.time() - start) * 1000)
        success = result.returncode == 0

        # Javob vaqtini chiqarish ehtimoli
        response_time = elapsed_ms
        output = result.stdout or ""
        # Linux: "time=12.345 ms" / Windows: "time=12ms"
        import re
        m = re.search(r"time[=<]([\d.]+)\s*ms", output)
        if m:
            try:
                response_time = int(float(m.group(1)))
            except ValueError:
                pass

        return {
            "success": success,
            "response_time_ms": response_time,
            "host": host,
            "output": (output[:500] if output else "").strip(),
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "response_time_ms": 5000, "host": host, "output": "Timeout"}
    except Exception as e:
        return {"success": False, "response_time_ms": 0, "host": host, "output": str(e)}


def run_ping_test(user_id: int, host: str) -> tuple[bool, str, dict]:
    """Foydalanuvchi uchun ping test bajaradi.
    Returns: (success, message, result_dict)"""
    # Rate limit
    if get_minute_count(user_id) >= 30:
        return False, "Tezlik chegarasi: minutida maksimal 30 ta ping. Birozdan keyin urinib ko'ring.", {}

    # Host validatsiyasi
    allowed, msg = is_host_allowed(host)
    if not allowed:
        return False, msg, {}

    # Kvota va plan
    user = query_one("SELECT plan, code_balance FROM users WHERE id=?", (user_id,))
    if not user:
        return False, "Foydalanuvchi topilmadi.", {}
    quota, cost = get_quota_and_cost(user["plan"])
    used = get_used_count(user_id)

    was_paid = False
    paid_amount = 0

    # Kvota tugagan bo'lsa, code yechib olamiz
    if used >= quota:
        balance = user["code_balance"] or 0
        if balance < cost:
            return False, f"Tekin kvota tugadi ({quota}/{quota}). Yana 1 ta test {cost:,} CODE. Sizda mavjud: {balance:,}.", {}
        from coins import spend_coins, _treasury_fund_in
        ok, msg = spend_coins(user_id, cost, "ping_test")
        if not ok:
            return False, msg, {}
        _treasury_fund_in(cost, "ping_test", user_id)
        was_paid = True
        paid_amount = cost

    # Pingni bajarish
    result = do_ping(host)
    execute(
        """INSERT INTO ping_test_usage
           (user_id, target, response_time_ms, success, was_paid, cost_paid)
           VALUES (?,?,?,?,?,?)""",
        (user_id, host, result["response_time_ms"], 1 if result["success"] else 0,
         1 if was_paid else 0, paid_amount)
    )

    # Yangi kvota holati
    new_used = used + 1
    remaining = max(0, quota - new_used)

    result.update({
        "quota": quota,
        "used": new_used,
        "remaining": remaining,
        "cost_per_test": cost,
        "was_paid": was_paid,
        "paid_amount": paid_amount,
    })
    return True, "Ping yakunlandi.", result
