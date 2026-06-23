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
import math
import datetime
from db import query_one, query_all, execute


# =================================================================
# NARX GENERATSIYASI — matematik model
# =================================================================

BASE_PRICE = 1.0        # Boshlang'ich narx
MIN_PRICE = 0.5         # Minimal narx
MAX_PRICE = 3.0         # Maksimal narx
VOLATILITY = 0.015      # Narx o'zgaruvchanlik koeffitsienti (0.1 sekunddagi)


def _get_active_trend() -> dict:
    """Admin belgilagan haftalik trend sozlamalarini qaytaradi."""
    try:
        row = query_one("SELECT * FROM trading_trend WHERE active=1 ORDER BY id DESC LIMIT 1")
        if row:
            return dict(row)
    except Exception:
        pass
    return {"direction": "neutral", "target_change_pct": 0, "duration_days": 7, "volatility": VOLATILITY}


def generate_next_price(current_price: float) -> tuple[float, float, int]:
    """
    GBM asosida keyingi narxni hisoblaydi.
    Admin haftalik trend belgilagan bo'lsa (up/down/neutral), shu tomonga moyil bo'ladi.

    Drift hisoblash: volatility × trend_strength
    Trend kuchi: target_pct / 100 / duration_days ni volatility ga nisbat sifatida
    Bu usul real bozor tendensiyasini aks ettiradi — kichik, lekin sezilarli moyillik.
    """
    trend = _get_active_trend()
    volatility = float(trend.get("volatility") or VOLATILITY)
    duration_days = max(1, int(trend.get("duration_days") or 7))
    target_pct = float(trend.get("target_change_pct") or 0)
    direction_str = trend.get("direction", "neutral")

    if direction_str == "neutral" or target_pct == 0:
        drift = 0.0
    else:
        # Drift = volatility × (target_pct_per_day / 100)
        # Bu real vaqtda sezilarli trend beradi
        # 8% / 7 kun = 1.14% / kun = kunlik trend kuchi
        daily_target = target_pct / duration_days / 100
        # Drift = volatility × daily_target × 0.1 (yumshatish)
        # Bu trend bor ekanini ko'rsatadi, lekin narx hali ham ikki tomonlama harakat qiladi
        drift = volatility * daily_target * 0.08
        sign = 1 if direction_str == "up" else -1
        drift = sign * abs(drift)

    random_component = random.gauss(drift, volatility)
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
    """Grafik uchun narx tarixi — sham (candlestick) formatda."""
    rows = query_all(
        "SELECT price, change_pct, direction, created_at FROM trading_prices ORDER BY id DESC LIMIT ?",
        (limit,)
    )
    return list(reversed(rows))


def get_ohlc_history(candle_count: int = 60) -> list:
    """
    OHLC (Open, High, Low, Close) sham grafigi uchun.
    Har 10 ta tick = 1 ta sham (1 saniya = 10 tick × 0.1s).
    """
    rows = query_all(
        "SELECT price, created_at FROM trading_prices ORDER BY id DESC LIMIT ?",
        (candle_count * 10,)
    )
    if not rows:
        return []
    rows = list(reversed(rows))
    candles = []
    step = 10
    for i in range(0, len(rows), step):
        chunk = rows[i:i+step]
        if not chunk:
            continue
        prices = [r["price"] for r in chunk]
        candles.append({
            "t": chunk[-1]["created_at"],
            "o": prices[0],
            "h": max(prices),
            "l": min(prices),
            "c": prices[-1],
            "up": prices[-1] >= prices[0],
        })
    return candles[-candle_count:]


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
    """
    Pozitsiyani yopadi va foyda/zarar hisoblaydi.

    MANTIQ (margin trading uslubi):
    - Narx entry dan exit gacha N% ko'tarilgan/tushgan bo'lsa,
      foydalanuvchi tiklov miqdorining N% ini yutadi yoki yo'qotadi.
    - To'g'ri yo'nalish: tiklov + (tiklov × N%)  qo'shiladi
    - Noto'g'ri yo'nalish: tiklov - (tiklov × N%) yechildi (ya'ni yo'nalish teskari bo'lsa)
    - Komisyon: 2% (sof foyda yoki zarar miqdoridan)
    """
    from coins import add_coins, _treasury_fund_in

    current = get_current_price()
    exit_price = current["price"]
    entry_price = pos["entry_price"]
    amount = pos["amount"]

    if entry_price == 0:
        entry_price = 1.0

    # Narx o'zgarish foizi (mutlaq qiymat)
    price_change_pct = abs((exit_price - entry_price) / entry_price) * 100

    # Agar narx o'zgarmagan bo'lsa — hamma pul qaytariladi
    if price_change_pct < 0.001:
        execute(
            "UPDATE trading_positions SET status='cancelled', exit_price=?, "
            "closed_at=datetime('now'), profit_loss=0, profit_pct=0 WHERE id=?",
            (exit_price, pos["id"])
        )
        add_coins(pos["user_id"], amount, "trading_return")
        _notify_trade_result(pos["user_id"], "cancelled", 0, 0, exit_price, entry_price)
        return

    # Haqiqiy narx yo'nalishi
    actual_up = exit_price > entry_price  # True = narx ko'tarildi

    # Foydalanuvchi to'g'ri topganmi?
    user_up = pos["direction"] == "up"
    correct = (user_up and actual_up) or (not user_up and not actual_up)

    # Foyda/zarar miqdori: tiklov × o'zgarish%
    pnl_raw = int(amount * price_change_pct / 100)
    commission_pct = 2  # 2%

    if correct:
        # G'alaba — tiklov qaytariladi + foyda qo'shiladi
        commission = max(1, int(pnl_raw * commission_pct / 100))
        net_profit = pnl_raw - commission
        payout = amount + net_profit  # tiklov + foyda
        profit_pct = round(price_change_pct * (1 - commission_pct/100), 3)

        add_coins(pos["user_id"], payout, "trading_win")
        _treasury_fund_in(commission, "trading_commission", pos["user_id"])

        execute(
            "UPDATE trading_positions SET status='won', exit_price=?, "
            "closed_at=datetime('now'), profit_loss=?, profit_pct=? WHERE id=?",
            (exit_price, net_profit, profit_pct, pos["id"])
        )
        execute(
            "UPDATE trading_stats SET total_volume=total_volume+?, total_trades=total_trades+1, "
            "total_won=total_won+1, platform_commission=platform_commission+? WHERE id=1",
            (amount, commission)
        )
        _notify_trade_result(pos["user_id"], "won", net_profit, profit_pct, exit_price, entry_price)

    else:
        # Zarar — tiklov narx o'zgarish foiziga ko'ra yechiladi
        commission = max(1, int(pnl_raw * commission_pct / 100))
        loss = pnl_raw + commission  # zarar + komisyon
        loss = min(loss, amount)     # ko'pi bilan tiklov miqdoricha yo'qoladi
        # Tiklovning qolgan qismi qaytariladi
        returned = amount - loss
        if returned > 0:
            add_coins(pos["user_id"], returned, "trading_partial_return")
        _treasury_fund_in(loss, "trading_loss", pos["user_id"])

        loss_pct = round(price_change_pct * (1 + commission_pct/100), 3)
        execute(
            "UPDATE trading_positions SET status='lost', exit_price=?, "
            "closed_at=datetime('now'), profit_loss=?, profit_pct=? WHERE id=?",
            (exit_price, -loss, -loss_pct, pos["id"])
        )
        execute(
            "UPDATE trading_stats SET total_volume=total_volume+?, total_trades=total_trades+1, "
            "platform_commission=platform_commission+? WHERE id=1",
            (amount, loss)
        )
        _notify_trade_result(pos["user_id"], "lost", -loss, -loss_pct, exit_price, entry_price)


def _notify_trade_result(user_id, status, profit_loss, profit_pct, exit_price, entry_price):
    """Natija haqida bildirishnoma yuboradi."""
    change_pct = abs(round(((exit_price - entry_price) / max(entry_price, 0.0001)) * 100, 3))
    if status == "won":
        title = "Trading: G'alaba! 🎉"
        body = (f"Narx {change_pct}% o'zgardi — to'g'ri topdingiz! "
                f"+{profit_loss:,} CODE (+{profit_pct}%) foyda.")
        ntype = "success"
    elif status == "lost":
        title = "Trading: Zarar"
        body = (f"Narx {change_pct}% o'zgardi — noto'g'ri yo'nalish. "
                f"{profit_loss:,} CODE ({profit_pct}%) zarar.")
        ntype = "error"
    else:
        title = "Trading: Tiklov bekor"
        body = "Narx o'zgarmadi — tiklovingiz qaytarildi."
        ntype = "info"

    execute(
        "INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
        (user_id, title, body, ntype)
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
