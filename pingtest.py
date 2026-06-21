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


def do_traceroute(host: str) -> dict:
    """Haqiqiy traceroute (Linux: traceroute, Windows: tracert).
    Agar buyruq tizimda o'rnatilmagan bo'lsa, xato xabari bilan qaytadi
    (saytni buzmaydi, lekin natija REAL hisoblanmaydi)."""
    import platform
    system = platform.system().lower()
    if system == "windows":
        cmd = ["tracert", "-d", "-h", "15", "-w", "2000", host]
    else:
        cmd = ["traceroute", "-n", "-m", "15", "-w", "2", host]

    start = time.time()
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        elapsed_ms = int((time.time() - start) * 1000)
        output = (result.stdout or "").strip()
        success = result.returncode == 0 and bool(output)
        # Hoplar sonini hisoblash (har bir qator ~ bitta hop)
        hops = len([ln for ln in output.splitlines() if ln.strip() and ln.strip()[0].isdigit()])
        return {
            "success": success,
            "response_time_ms": elapsed_ms,
            "host": host,
            "output": output[:2000],
            "hops": hops,
        }
    except FileNotFoundError:
        return {"success": False, "response_time_ms": 0, "host": host,
                "output": "traceroute/tracert tizimda o'rnatilmagan. Server administratoridan "
                          "o'rnatishni so'rang (Linux: apt install traceroute).", "hops": 0}
    except subprocess.TimeoutExpired:
        return {"success": False, "response_time_ms": 20000, "host": host, "output": "Timeout", "hops": 0}
    except Exception as e:
        return {"success": False, "response_time_ms": 0, "host": host, "output": str(e), "hops": 0}


# =================================================================
# SIMULYATSIYA REJIMI — TCP SYN, UDP, ARP, PathPing, SNI, MTR
# Bu usullar root huquqi yoki maxsus raw-socket kutubxonalar talab
# qiladi, internetga ochiq web-serverda xavfsiz ishlatib bo'lmaydi.
# Shuning uchun ta'lim maqsadida REALISTIK NAMUNA natija ko'rsatiladi —
# foydalanuvchiga usul qanday ishlashi va natija qanday ko'rinishini
# tushuntirish uchun. Bu hech qachon haqiqiy tarmoq so'rovi yubormaydi.
# =================================================================
PING_METHODS = {
    "icmp": {
        "name": "ICMP Ping",
        "description": "Xost jonlimi? Tarmoq kechikishi qanday?",
        "note": "Eng oddiy usul, lekin ko'p joylarda bloklangan",
        "real": True,
    },
    "tcp_syn": {
        "name": "TCP SYN Ping",
        "description": "Xostni aniqlash, firewall siyosatini tekshirish",
        "note": "ICMP bloklangan tarmoqlarda samarali",
        "real": False,
    },
    "udp": {
        "name": "UDP Ping",
        "description": "Xostni aniqlash",
        "note": "Yopiq portdan ICMP xatolik qaytishiga tayanadi",
        "real": False,
    },
    "arp": {
        "name": "ARP Ping",
        "description": "Mahalliy tarmoqda xostlarni aniqlash",
        "note": "Eng tez va ishonchli (LAN uchun)",
        "real": False,
    },
    "traceroute": {
        "name": "Traceroute",
        "description": "Tarmoq yo'lini tahlil qilish",
        "note": "Har bir hopda kechikish va yo'qotishni ko'rsatadi",
        "real": True,
    },
    "pathping": {
        "name": "PathPing",
        "description": "Tarmoq muammolarini lokalizatsiya qilish",
        "note": "Har bir hopda paket yo'qotish foizini hisoblaydi",
        "real": False,
    },
    "sni": {
        "name": "SNI Ping",
        "description": "CDN va serverlarni aniqlash",
        "note": "HTTPS trafigini niqoblash uchun ishlatiladi",
        "real": False,
    },
    "mtr": {
        "name": "MTR (My TraceRoute)",
        "description": "Real vaqtda tarmoq monitoringi",
        "note": "Ping va traceroute'ni birlashtiradi",
        "real": False,
    },
}


def _simulate_tcp_syn(host):
    import random
    common_ports = [22, 80, 443, 3306, 8080]
    open_ports = random.sample(common_ports, k=random.randint(1, 3))
    lines = [f"TCP SYN Ping -> {host} (SIMULYATSIYA, real so'rov yuborilmadi)"]
    for p in sorted(open_ports):
        lines.append(f"  Port {p}/tcp: OCHIQ (SYN-ACK qaytdi)")
    for p in [x for x in common_ports if x not in open_ports][:2]:
        lines.append(f"  Port {p}/tcp: YOPIQ (RST qaytdi)")
    return "\n".join(lines), len(open_ports) > 0


def _simulate_udp(host):
    import random
    return (f"UDP Ping -> {host} (SIMULYATSIYA)\n"
            f"  Port 53/udp: javob yo'q (ochiq yoki filtrlangan)\n"
            f"  Port 123/udp: ICMP Port Unreachable qaytdi (yopiq)\n"
            f"  Natija: xost faol, ammo aniq portlar holatini aniqlash uchun qo'shimcha tekshiruv kerak"), True


def _simulate_arp(host):
    import random
    mac = ":".join(f"{random.randint(0,255):02x}" for _ in range(6))
    return (f"ARP Ping -> {host} (SIMULYATSIYA, faqat LAN'da ishlaydi)\n"
            f"  Javob: {host} bor (0.8 ms)\n"
            f"  MAC manzil (namuna): {mac}\n"
            f"  Eslatma: ARP faqat bitta L2 segmentda (mahalliy tarmoqda) ishlaydi, "
            f"internet orqali ishlamaydi"), True


def _simulate_pathping(host):
    import random
    lines = [f"PathPing -> {host} (SIMULYATSIYA)", "Hop  Manzil            Yo'qotish%  O'rt-kechikish"]
    for i in range(1, random.randint(4, 7)):
        loss = random.choice([0, 0, 0, 2, 5])
        lat = random.randint(5, 80) * i // 2
        lines.append(f" {i:2d}   10.0.{i}.1          {loss}%         {lat} ms")
    lines.append(f" {i+1:2d}   {host}    0%         {lat+10} ms (maqsad)")
    return "\n".join(lines), True


def _simulate_sni(host):
    return (f"SNI Ping -> {host} (SIMULYATSIYA)\n"
            f"  TLS ClientHello yuborildi, SNI={host}\n"
            f"  Server sertifikat bilan javob qaytardi (namuna)\n"
            f"  CDN aniqlandi: Cloudflare/Akamai turidagi infratuzilma belgilari topildi (namuna)\n"
            f"  Eslatma: bu usul HTTPS orqali qaysi serverga ulanayotganini CDN orqasida ham "
            f"aniqlash uchun ishlatiladi"), True


def _simulate_mtr(host):
    import random
    lines = [f"MTR -> {host} (SIMULYATSIYA, real-vaqt monitoring namunasi)",
             "Hop  Host              Yo'qotish%  Yuborilgan  O'rt    Eng yaxshi  Eng yomon"]
    for i in range(1, random.randint(5, 9)):
        loss = random.choice([0, 0, 0, 1, 3])
        avg = random.randint(5, 60)
        lines.append(f" {i:2d}   10.0.{i}.1          {loss}%      10          {avg}ms   {avg-3}ms      {avg+8}ms")
    lines.append(f" {i+1:2d}   {host}    0%      10          {avg+15}ms (maqsad)")
    return "\n".join(lines), True


def run_method_test(method: str, host: str) -> dict:
    """Berilgan usul bilan test bajaradi. ICMP va Traceroute REAL, qolganlari simulyatsiya."""
    if method == "icmp":
        return do_ping(host)
    if method == "traceroute":
        return do_traceroute(host)

    simulators = {
        "tcp_syn": _simulate_tcp_syn,
        "udp": _simulate_udp,
        "arp": _simulate_arp,
        "pathping": _simulate_pathping,
        "sni": _simulate_sni,
        "mtr": _simulate_mtr,
    }
    sim_fn = simulators.get(method)
    if not sim_fn:
        return {"success": False, "response_time_ms": 0, "host": host, "output": "Noma'lum usul."}

    output, success = sim_fn(host)
    return {
        "success": success,
        "response_time_ms": 0,
        "host": host,
        "output": output,
        "simulated": True,
    }


def run_ping_test(user_id: int, host: str, method: str = "icmp") -> tuple[bool, str, dict]:
    """Foydalanuvchi uchun ping test bajaradi (tanlangan usul bilan).
    Returns: (success, message, result_dict)"""
    if method not in PING_METHODS:
        method = "icmp"

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

    # Tanlangan usul bilan testni bajarish
    result = run_method_test(method, host)
    execute(
        """INSERT INTO ping_test_usage
           (user_id, target, response_time_ms, success, was_paid, cost_paid)
           VALUES (?,?,?,?,?,?)""",
        (user_id, host, result.get("response_time_ms", 0), 1 if result["success"] else 0,
         1 if was_paid else 0, paid_amount)
    )

    # Yangi kvota holati
    new_used = used + 1
    remaining = max(0, quota - new_used)

    result.update({
        "method": method,
        "method_name": PING_METHODS[method]["name"],
        "quota": quota,
        "used": new_used,
        "remaining": remaining,
        "cost_per_test": cost,
        "was_paid": was_paid,
        "paid_amount": paid_amount,
    })
    return True, "Test yakunlandi.", result
