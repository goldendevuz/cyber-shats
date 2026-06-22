"""
CYBER SHATS V1.3 — Trading bo'limi (CODE tangalari treding simulyatori)

Narx generatsiyasi: matematik stokastik model (Geometric Brownian Motion
soddalashtirilgan versiyasi) — real bozor kabi ko'tarilish/tushish, lekin
simulyatsiya. Sahifaga yangilanish berilmasa ham narx o'zgarib turadi —
server API endpoint'i orqali, JavaScript har 100ms'da so'raydi.

Tiklov mantig'i:
- Foydalanuvchi "UP" (ko'tariladi) yoki "DOWN" (tushadi) deb tiklov qo'yadi
- Belgilangan vaqt o'tgach (30 soniya default) narx tekshiriladi
- To'g'ri taxmin: tiklov × win_multiplier% (masalan 195% = +95% foyda)
- Noto'g'ri taxmin: tiklov × loss_pct% (masalan -100% = to'liq yo'qoladi)
- G'azna komisyasi: 2% (g'alaba va zarar summasidan)
"""
import random
import datetime
import math
from db import query_one, query_all, execute


# =================================================================
# NARX GENERATSIYASI — matematik model
# =================================================================

BASE_PRICE = 1.0        # Boshlang'ich narx
MIN_PRICE = 0.5         # Minimal narx
MAX_PRICE = 3.0         # Maksimal narx
VOLATILITY = 0.015      # Narx o'zgaruvchanlik koeffitsienti (0.1 sekunddagi)


def generate_next_price(current_price: float) -> tuple[float, float, int]:
    """
    Geometric Brownian Motion (GBM) asosida keyingi narxni hisoblaydi.
    Soddalashtirilgan, lekin haqiqiy bozordagi kabi ko'rinadi.
    Returns: (yangi_narx, o'zgarish_%, yo'nalish)
    """
    # Random komponent (normal taqsimlangan)
    drift = 0  # Trend yo'q — neytr
    random_component = random.gauss(drift, VOLATILITY)

    new_price = current_price * math.exp(random_component)
    new_price = max(MIN_PRICE, min(MAX_PRICE, round(new_price, 4)))

    change_pct = round(((new_price - current_price) / current_price) * 100, 3)
    direction = 1 if new_price > current_price else (-1 if new_price < current_price else 0)

    return new_price, change_pct, direction


def get_current_price() -> dict:
    """Eng so'nggi narxni qaytaradi."""
    row = query_one(
        "SELECT * FROM trading_prices ORDER BY id DESC LIMIT 1"
    )
    if row:
        return dict(row)
    return {"price": BASE_PRICE, "change_pct": 0, "direction": 0, "id": 0, "created_at": ""}


def tick_price() -> dict:
    """
    Yangi narx yaratadi va bazaga yozadi. Server-side event (SSE) yoki
    JavaScript polling tomonidan chaqiriladi.
    """
    current = get_current_price()
    new_price, change_pct, direction = generate_next_price(current["price"])

    execute(
        "INSERT INTO trading_prices (price, change_pct, direction) VALUES (?,?,?)",
        (new_price, change_pct, direction)
    )

    # Eski narxlarni tozalash (1000 ta saqlanamiz — grafik uchun)
    execute("DELETE FROM trading_prices WHERE id <= (SELECT id FROM trading_prices ORDER BY id DESC LIMIT 1 OFFSET 1000)")

    # Ochiq pozitsiyalarni tekshirish (muddati tugagan)
    _check_expired_positions()

    return {
        "price": new_price,
        "change_pct": change_pct,
        "direction": direction,
        "formatted": f"{new_price:.4f}",
        "change_str": f"{'+' if change_pct >= 0 else ''}{change_pct:.3f}%",
    }


def get_price_history(limit: int = 200) -> list:
    """Grafik uchun narx tarixi."""
    rows = query_all(
        "SELECT price, change_pct, direction, created_at FROM trading_prices ORDER BY id DESC LIMIT ?",
        (limit,)
    )
    return list(reversed(rows))


# =================================================================
# TIKLOV MANTIG'I
# =================================================================

def open_position(user_id: int, direction: str, amount: int,
                  duration_seconds: int = 30) -> tuple[bool, str, int]:
    """
    Yangi tiklov ochadi.
    direction: 'up' yoki 'down'
    amount: CODE miqdori (tiklov)
    duration_seconds: pozitsiya muddati (default 30 soniya)
    """
    from pricing import get_price
    min_bet = get_price("trading_min_bet")
    max_bet = get_price("trading_max_bet")

    if direction not in ("up", "down"):
        return False, "Yo'nalish noto'g'ri ('up' yoki 'down').", 0

    if amount < min_bet:
        return False, f"Minimal tiklov: {min_bet:,} CODE.", 0
    if amount > max_bet:
        return False, f"Maksimal tiklov: {max_bet:,} CODE.", 0

    # Foydalanuvchining ochiq pozitsiyasi bormi?
    existing = query_one(
        "SELECT id FROM trading_positions WHERE user_id=? AND status='open'", (user_id,)
    )
    if existing:
        return False, "Avvalgi tiklovingiz hali ochiq. Uning natijasini kuting.", 0

    from coins import spend_coins, get_balance
    if get_balance(user_id) < amount:
        return False, "Balansingizda yetarli CODE yo'q.", 0

    ok, msg = spend_coins(user_id, amount, "trading_bet")
    if not ok:
        return False, msg, 0

    current = get_current_price()
    pos_id = execute(
        """INSERT INTO trading_positions
           (user_id, direction, amount, entry_price, duration_seconds, status)
           VALUES (?,?,?,?,?,'open')""",
        (user_id, direction, amount, current["price"], duration_seconds)
    )
    return True, f"Tiklov qo'yildi: {amount:,} CODE {'⬆ UP' if direction=='up' else '⬇ DOWN'}", pos_id


def _check_expired_positions():
    """Muddati o'tgan ochiq pozitsiyalarni yopadi. tick_price() chaqirganda avtomatik ishlaydi."""
    now = datetime.datetime.now().isoformat()
    expired = query_all(
        """SELECT * FROM trading_positions WHERE status='open'
           AND datetime(opened_at, '+' || duration_seconds || ' seconds') <= datetime(?)""",
        (now,)
    )
    for pos in expired:
        _close_position(pos)


def _close_position(pos: dict):
    """Pozitsiyani yopadi va foyda/zarar hisoblaydi."""
    from pricing import get_price
    from coins import add_coins, _treasury_fund_in

    current = get_current_price()
    exit_price = current["price"]
    entry_price = pos["entry_price"]

    # Narx yo'nalishini aniqlash
    actual_direction = "up" if exit_price > entry_price else ("down" if exit_price < entry_price else None)

    if actual_direction is None:
        # Narx o'zgarmagan — pul qaytariladi, commission yo'q
        execute(
            "UPDATE trading_positions SET status='cancelled', exit_price=?, closed_at=datetime('now'), profit_loss=0, profit_pct=0 WHERE id=?",
            (exit_price, pos["id"])
        )
        add_coins(pos["user_id"], pos["amount"], "trading_return")
        return

    win_multiplier = get_price("trading_win_multiplier") / 100  # 1.95
    commission_pct = get_price("trading_commission_pct") / 100  # 0.02
    amount = pos["amount"]

    if pos["direction"] == actual_direction:
        # G'alaba: tiklov × multiplier - commission
        gross_payout = int(amount * win_multiplier)
        commission = int(gross_payout * commission_pct)
        net_payout = gross_payout - commission
        profit = net_payout - amount  # sof foyda
        profit_pct = round((profit / amount) * 100, 2)

        add_coins(pos["user_id"], net_payout, "trading_win")
        _treasury_fund_in(commission, "trading_commission", pos["user_id"])

        execute(
            "UPDATE trading_positions SET status='won', exit_price=?, closed_at=datetime('now'), profit_loss=?, profit_pct=? WHERE id=?",
            (exit_price, profit, profit_pct, pos["id"])
        )
        execute(
            "INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
            (pos["user_id"], "Trading: G'alaba! 🎉",
             f"Tiklovingiz to'g'ri! +{profit:,} CODE foyda (+{profit_pct}%)", "success")
        )
        execute(
            "UPDATE trading_stats SET total_volume=total_volume+?, total_trades=total_trades+1, total_won=total_won+1, platform_commission=platform_commission+? WHERE id=1",
            (amount, commission)
        )
    else:
        # Zarar: tiklov to'liq yo'qoladi, commission saqlanadi g'aznada
        loss = amount
        loss_pct = -100.0
        commission = int(amount * commission_pct)
        _treasury_fund_in(amount, "trading_loss", pos["user_id"])

        execute(
            "UPDATE trading_positions SET status='lost', exit_price=?, closed_at=datetime('now'), profit_loss=?, profit_pct=? WHERE id=?",
            (exit_price, -loss, loss_pct, pos["id"])
        )
        execute(
            "INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
            (pos["user_id"], "Trading: Zarar",
             f"Tiklovingiz noto'g'ri bo'ldi. -{loss:,} CODE zarar.", "error")
        )
        execute(
            "UPDATE trading_stats SET total_volume=total_volume+?, total_trades=total_trades+1, platform_commission=platform_commission+? WHERE id=1",
            (amount, amount)
        )


def get_user_open_position(user_id: int):
    """Foydalanuvchining ochiq pozitsiyasi."""
    return query_one(
        "SELECT * FROM trading_positions WHERE user_id=? AND status='open' ORDER BY id DESC LIMIT 1",
        (user_id,)
    )


def get_user_history(user_id: int, limit: int = 20):
    return query_all(
        "SELECT * FROM trading_positions WHERE user_id=? ORDER BY id DESC LIMIT ?",
        (user_id, limit)
    )


def get_trading_stats():
    return query_one("SELECT * FROM trading_stats WHERE id=1")
