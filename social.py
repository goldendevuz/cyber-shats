"""
CYBER SHATS V1.3 — Ijtimoiy tarmoq moduli (Bosqich 5 — MVP)

GURUH (Group): ko'p kishilik suhbat — har qanday foydalanuvchi yarata oladi,
boshqalar qo'shiladi (ochiq) yoki taklif qilinadi (yopiq).

KANAL (Channel): bitta egasi/admin tomonidan boshqariladigan e'lon kanali —
a'zolar obuna bo'lib o'qiydi, izoh qoldiradi.
"""
from db import query_one, query_all, execute, log_action


# =================================================================
# GURUHLAR
# =================================================================

def create_group(owner_id: int, name: str, description: str = "", is_public: bool = True) -> tuple[bool, str, int]:
    name = (name or "").strip()
    if not name:
        return False, "Guruh nomi majburiy.", 0
    if len(name) > 100:
        return False, "Guruh nomi juda uzun.", 0
    gid = execute(
        "INSERT INTO groups (name, description, owner_id, is_public) VALUES (?,?,?,?)",
        (name, (description or "").strip(), owner_id, 1 if is_public else 0)
    )
    execute(
        "INSERT INTO group_members (group_id, user_id, role) VALUES (?,?,'owner')",
        (gid, owner_id)
    )
    log_action(owner_id, "group_created", details=f"group:{gid}")
    return True, "Guruh yaratildi!", gid


def get_group(group_id: int):
    return query_one("SELECT * FROM groups WHERE id=?", (group_id,))


def get_all_groups(limit: int = 50):
    return query_all(
        """SELECT g.*, u.ism as owner_ism, u.familiya as owner_familiya
           FROM groups g JOIN users u ON u.id = g.owner_id
           ORDER BY g.member_count DESC, g.id DESC LIMIT ?""",
        (limit,)
    )


def get_user_groups(user_id: int):
    return query_all(
        """SELECT g.*, gm.role FROM groups g
           JOIN group_members gm ON gm.group_id = g.id
           WHERE gm.user_id = ? ORDER BY g.id DESC""",
        (user_id,)
    )


def is_member(group_id: int, user_id: int) -> bool:
    row = query_one("SELECT id FROM group_members WHERE group_id=? AND user_id=?", (group_id, user_id))
    return bool(row)


def get_member_role(group_id: int, user_id: int):
    row = query_one("SELECT role FROM group_members WHERE group_id=? AND user_id=?", (group_id, user_id))
    return row["role"] if row else None


def join_group(group_id: int, user_id: int) -> tuple[bool, str]:
    group = get_group(group_id)
    if not group:
        return False, "Guruh topilmadi."
    if is_member(group_id, user_id):
        return False, "Siz allaqachon a'zosiz."
    if not group["is_public"]:
        return False, "Bu yopiq guruh — faqat taklif orqali qo'shilish mumkin."
    execute("INSERT INTO group_members (group_id, user_id, role) VALUES (?,?,'member')", (group_id, user_id))
    execute("UPDATE groups SET member_count = member_count + 1 WHERE id=?", (group_id,))
    log_action(user_id, "group_joined", details=f"group:{group_id}")
    return True, "Guruhga qo'shildingiz!"


def leave_group(group_id: int, user_id: int) -> tuple[bool, str]:
    role = get_member_role(group_id, user_id)
    if not role:
        return False, "Siz a'zo emassiz."
    if role == "owner":
        return False, "Guruh egasi chiqib keta olmaydi. Avval egalikni o'tkazing yoki guruhni o'chiring."
    execute("DELETE FROM group_members WHERE group_id=? AND user_id=?", (group_id, user_id))
    execute("UPDATE groups SET member_count = member_count - 1 WHERE id=?", (group_id,))
    return True, "Guruhdan chiqdingiz."


def get_group_members(group_id: int):
    return query_all(
        """SELECT gm.*, u.ism, u.familiya, u.avatar, u.plan
           FROM group_members gm JOIN users u ON u.id = gm.user_id
           WHERE gm.group_id = ? ORDER BY
               CASE gm.role WHEN 'owner' THEN 0 WHEN 'admin' THEN 1 ELSE 2 END, gm.joined_at ASC""",
        (group_id,)
    )


def get_group_messages(group_id: int, limit: int = 100):
    rows = query_all(
        """SELECT * FROM (
               SELECT m.*, u.ism, u.familiya, u.avatar
               FROM group_messages m JOIN users u ON u.id = m.user_id
               WHERE m.group_id = ? ORDER BY m.id DESC LIMIT ?
           ) sub ORDER BY id ASC""",
        (group_id, limit)
    )
    return rows


def send_group_message(group_id: int, user_id: int, body: str,
                       file_path: str = None, file_type: str = None) -> tuple[bool, str]:
    if not is_member(group_id, user_id):
        return False, "Siz bu guruh a'zosi emassiz."
    body = (body or "").strip()
    if not body and not file_path:
        return False, "Xabar bo'sh bo'lishi mumkin emas."
    execute(
        "INSERT INTO group_messages (group_id, user_id, body, file_path, file_type) VALUES (?,?,?,?,?)",
        (group_id, user_id, body, file_path, file_type)
    )
    return True, "OK"


def kick_member(group_id: int, actor_id: int, target_user_id: int) -> tuple[bool, str]:
    """Owner yoki admin a'zoni guruhdan chiqarib yuboradi."""
    actor_role = get_member_role(group_id, actor_id)
    if actor_role not in ("owner", "admin"):
        return False, "Sizda ruxsat yo'q."
    target_role = get_member_role(group_id, target_user_id)
    if target_role == "owner":
        return False, "Guruh egasini chiqarib bo'lmaydi."
    if not target_role:
        return False, "Foydalanuvchi a'zo emas."
    execute("DELETE FROM group_members WHERE group_id=? AND user_id=?", (group_id, target_user_id))
    execute("UPDATE groups SET member_count = member_count - 1 WHERE id=?", (group_id,))
    return True, "Foydalanuvchi guruhdan chiqarildi."


def delete_group(group_id: int, actor_id: int) -> tuple[bool, str]:
    group = get_group(group_id)
    if not group:
        return False, "Guruh topilmadi."
    if group["owner_id"] != actor_id:
        return False, "Faqat guruh egasi o'chira oladi."
    execute("DELETE FROM group_messages WHERE group_id=?", (group_id,))
    execute("DELETE FROM group_members WHERE group_id=?", (group_id,))
    execute("DELETE FROM groups WHERE id=?", (group_id,))
    return True, "Guruh o'chirildi."


# =================================================================
# KANALLAR
# =================================================================

def create_channel(owner_id: int, name: str, description: str = "") -> tuple[bool, str, int]:
    name = (name or "").strip()
    if not name:
        return False, "Kanal nomi majburiy.", 0
    if len(name) > 100:
        return False, "Kanal nomi juda uzun.", 0
    cid = execute(
        "INSERT INTO channels (name, description, owner_id) VALUES (?,?,?)",
        (name, (description or "").strip(), owner_id)
    )
    execute("INSERT INTO channel_subscribers (channel_id, user_id) VALUES (?,?)", (cid, owner_id))
    execute("UPDATE channels SET subscriber_count = 1 WHERE id=?", (cid,))
    log_action(owner_id, "channel_created", details=f"channel:{cid}")
    return True, "Kanal yaratildi!", cid


def get_channel(channel_id: int):
    return query_one("SELECT * FROM channels WHERE id=?", (channel_id,))


def get_all_channels(limit: int = 50):
    return query_all(
        """SELECT c.*, u.ism as owner_ism, u.familiya as owner_familiya
           FROM channels c JOIN users u ON u.id = c.owner_id
           ORDER BY c.subscriber_count DESC, c.id DESC LIMIT ?""",
        (limit,)
    )


def get_user_channels(user_id: int):
    """Foydalanuvchi obuna bo'lgan kanallar."""
    return query_all(
        """SELECT c.*, cs.subscribed_at FROM channels c
           JOIN channel_subscribers cs ON cs.channel_id = c.id
           WHERE cs.user_id = ? ORDER BY c.id DESC""",
        (user_id,)
    )


def is_subscribed(channel_id: int, user_id: int) -> bool:
    row = query_one("SELECT id FROM channel_subscribers WHERE channel_id=? AND user_id=?", (channel_id, user_id))
    return bool(row)


def is_channel_owner(channel_id: int, user_id: int) -> bool:
    ch = get_channel(channel_id)
    return bool(ch and ch["owner_id"] == user_id)


def subscribe_channel(channel_id: int, user_id: int) -> tuple[bool, str]:
    if not get_channel(channel_id):
        return False, "Kanal topilmadi."
    if is_subscribed(channel_id, user_id):
        return False, "Siz allaqachon obunasiz."
    execute("INSERT INTO channel_subscribers (channel_id, user_id) VALUES (?,?)", (channel_id, user_id))
    execute("UPDATE channels SET subscriber_count = subscriber_count + 1 WHERE id=?", (channel_id,))
    return True, "Obuna bo'ldingiz!"


def unsubscribe_channel(channel_id: int, user_id: int) -> tuple[bool, str]:
    if is_channel_owner(channel_id, user_id):
        return False, "Kanal egasi obunani bekor qila olmaydi."
    if not is_subscribed(channel_id, user_id):
        return False, "Siz obuna emassiz."
    execute("DELETE FROM channel_subscribers WHERE channel_id=? AND user_id=?", (channel_id, user_id))
    execute("UPDATE channels SET subscriber_count = subscriber_count - 1 WHERE id=?", (channel_id,))
    return True, "Obuna bekor qilindi."


def get_channel_posts(channel_id: int, limit: int = 50):
    return query_all(
        """SELECT p.*, u.ism, u.familiya, u.avatar,
                  (SELECT COUNT(*) FROM channel_post_comments cc WHERE cc.post_id=p.id) as comments_count
           FROM channel_posts p JOIN users u ON u.id = p.user_id
           WHERE p.channel_id = ? ORDER BY p.id DESC LIMIT ?""",
        (channel_id, limit)
    )


def get_channel_post(post_id: int):
    return query_one(
        """SELECT p.*, u.ism, u.familiya, u.avatar, c.name as channel_name, c.id as channel_id
           FROM channel_posts p
           JOIN users u ON u.id = p.user_id
           JOIN channels c ON c.id = p.channel_id
           WHERE p.id = ?""",
        (post_id,)
    )


def create_channel_post(channel_id: int, user_id: int, body: str,
                        file_path: str = None, file_type: str = None) -> tuple[bool, str]:
    if not is_channel_owner(channel_id, user_id):
        return False, "Faqat kanal egasi e'lon qila oladi."
    body = (body or "").strip()
    if not body and not file_path:
        return False, "E'lon matni bo'sh bo'lishi mumkin emas."
    execute(
        "INSERT INTO channel_posts (channel_id, user_id, body, file_path, file_type) VALUES (?,?,?,?,?)",
        (channel_id, user_id, body, file_path, file_type)
    )
    return True, "E'lon joylandi!"


def get_post_comments(post_id: int):
    return query_all(
        """SELECT cc.*, u.ism, u.familiya, u.avatar
           FROM channel_post_comments cc JOIN users u ON u.id = cc.user_id
           WHERE cc.post_id = ? ORDER BY cc.id ASC""",
        (post_id,)
    )


def add_post_comment(post_id: int, user_id: int, body: str) -> tuple[bool, str]:
    body = (body or "").strip()
    if not body:
        return False, "Izoh bo'sh bo'lishi mumkin emas."
    execute("INSERT INTO channel_post_comments (post_id, user_id, body) VALUES (?,?,?)", (post_id, user_id, body))
    return True, "Izoh qo'shildi."


def delete_channel(channel_id: int, actor_id: int) -> tuple[bool, str]:
    if not is_channel_owner(channel_id, actor_id):
        return False, "Faqat kanal egasi o'chira oladi."
    post_ids = [r["id"] for r in query_all("SELECT id FROM channel_posts WHERE channel_id=?", (channel_id,))]
    for pid in post_ids:
        execute("DELETE FROM channel_post_comments WHERE post_id=?", (pid,))
    execute("DELETE FROM channel_posts WHERE channel_id=?", (channel_id,))
    execute("DELETE FROM channel_subscribers WHERE channel_id=?", (channel_id,))
    execute("DELETE FROM channels WHERE id=?", (channel_id,))
    return True, "Kanal o'chirildi."


# =================================================================
# STORIES — Instagram uslubidagi 24 soatlik vaqtinchalik kontent
# =================================================================

def create_story(user_id: int, file_path: str, file_type: str, caption: str = "") -> tuple[bool, str, int]:
    if not file_path:
        return False, "Fayl majburiy.", 0
    import datetime
    expires_at = (datetime.datetime.now() + datetime.timedelta(hours=24)).isoformat()
    sid = execute(
        "INSERT INTO stories (user_id, file_path, file_type, caption, expires_at) VALUES (?,?,?,?,?)",
        (user_id, file_path, file_type, (caption or "").strip(), expires_at)
    )
    log_action(user_id, "story_created", details=f"story:{sid}")
    return True, "Hikoya joylandi!", sid


def get_active_stories_by_users():
    """Hozir faol (muddati o'tmagan) barcha hikoyalarni foydalanuvchi bo'yicha guruhlangan holda qaytaradi."""
    import datetime
    now = datetime.datetime.now().isoformat()
    rows = query_all(
        """SELECT s.*, u.ism, u.familiya, u.avatar
           FROM stories s JOIN users u ON u.id = s.user_id
           WHERE s.expires_at > ?
           ORDER BY s.user_id, s.created_at ASC""",
        (now,)
    )
    grouped = {}
    for r in rows:
        uid = r["user_id"]
        if uid not in grouped:
            grouped[uid] = {"user_id": uid, "ism": r["ism"], "familiya": r["familiya"],
                            "avatar": r["avatar"], "stories": []}
        grouped[uid]["stories"].append(r)
    return list(grouped.values())


def get_user_active_stories(user_id: int):
    import datetime
    now = datetime.datetime.now().isoformat()
    return query_all(
        "SELECT * FROM stories WHERE user_id=? AND expires_at > ? ORDER BY created_at ASC",
        (user_id, now)
    )


def get_story(story_id: int):
    import datetime
    now = datetime.datetime.now().isoformat()
    return query_one(
        """SELECT s.*, u.ism, u.familiya, u.avatar FROM stories s
           JOIN users u ON u.id = s.user_id
           WHERE s.id=? AND s.expires_at > ?""",
        (story_id, now)
    )


def mark_story_viewed(story_id: int, user_id: int):
    existing = query_one("SELECT id FROM story_views WHERE story_id=? AND user_id=?", (story_id, user_id))
    if existing:
        return
    execute("INSERT INTO story_views (story_id, user_id) VALUES (?,?)", (story_id, user_id))
    execute("UPDATE stories SET view_count = view_count + 1 WHERE id=?", (story_id,))


def delete_story(story_id: int, actor_id: int) -> tuple[bool, str]:
    story = query_one("SELECT user_id FROM stories WHERE id=?", (story_id,))
    if not story:
        return False, "Hikoya topilmadi."
    if story["user_id"] != actor_id:
        return False, "Faqat o'zingizning hikoyangizni o'chira olasiz."
    execute("DELETE FROM story_views WHERE story_id=?", (story_id,))
    execute("DELETE FROM stories WHERE id=?", (story_id,))
    return True, "Hikoya o'chirildi."


# =================================================================
# REELS — qisqa vertikal videolar tasmasi
# =================================================================

def create_reel(user_id: int, file_path: str, caption: str = "") -> tuple[bool, str, int]:
    if not file_path:
        return False, "Video fayl majburiy.", 0
    rid = execute(
        "INSERT INTO reels (user_id, file_path, caption) VALUES (?,?,?)",
        (user_id, file_path, (caption or "").strip())
    )
    log_action(user_id, "reel_created", details=f"reel:{rid}")
    return True, "Reel joylandi!", rid


def get_reels_feed(limit: int = 30, before_id: int = None):
    """Tasma — eng yangidan eskiga, ixtiyoriy 'before_id' bilan sahifalash (infinite scroll)."""
    if before_id:
        return query_all(
            """SELECT r.*, u.ism, u.familiya, u.avatar
               FROM reels r JOIN users u ON u.id = r.user_id
               WHERE r.id < ? ORDER BY r.id DESC LIMIT ?""",
            (before_id, limit)
        )
    return query_all(
        """SELECT r.*, u.ism, u.familiya, u.avatar
           FROM reels r JOIN users u ON u.id = r.user_id
           ORDER BY r.id DESC LIMIT ?""",
        (limit,)
    )


def get_reel(reel_id: int):
    return query_one(
        """SELECT r.*, u.ism, u.familiya, u.avatar FROM reels r
           JOIN users u ON u.id = r.user_id WHERE r.id=?""",
        (reel_id,)
    )


def increment_reel_view(reel_id: int):
    execute("UPDATE reels SET view_count = view_count + 1 WHERE id=?", (reel_id,))


def is_reel_liked(reel_id: int, user_id: int) -> bool:
    row = query_one("SELECT id FROM reel_likes WHERE reel_id=? AND user_id=?", (reel_id, user_id))
    return bool(row)


def toggle_reel_like(reel_id: int, user_id: int) -> tuple[bool, int]:
    """Like/unlike. Returns (liked_now, new_like_count)."""
    if is_reel_liked(reel_id, user_id):
        execute("DELETE FROM reel_likes WHERE reel_id=? AND user_id=?", (reel_id, user_id))
        execute("UPDATE reels SET like_count = like_count - 1 WHERE id=?", (reel_id,))
        liked = False
    else:
        execute("INSERT INTO reel_likes (reel_id, user_id) VALUES (?,?)", (reel_id, user_id))
        execute("UPDATE reels SET like_count = like_count + 1 WHERE id=?", (reel_id,))
        liked = True
    row = query_one("SELECT like_count FROM reels WHERE id=?", (reel_id,))
    return liked, row["like_count"] if row else 0


def get_reel_comments(reel_id: int):
    return query_all(
        """SELECT rc.*, u.ism, u.familiya, u.avatar
           FROM reel_comments rc JOIN users u ON u.id = rc.user_id
           WHERE rc.reel_id = ? ORDER BY rc.id ASC""",
        (reel_id,)
    )


def add_reel_comment(reel_id: int, user_id: int, body: str) -> tuple[bool, str]:
    body = (body or "").strip()
    if not body:
        return False, "Izoh bo'sh bo'lishi mumkin emas."
    execute("INSERT INTO reel_comments (reel_id, user_id, body) VALUES (?,?,?)", (reel_id, user_id, body))
    return True, "Izoh qo'shildi."


def delete_reel(reel_id: int, actor_id: int) -> tuple[bool, str]:
    reel = query_one("SELECT user_id FROM reels WHERE id=?", (reel_id,))
    if not reel:
        return False, "Reel topilmadi."
    if reel["user_id"] != actor_id:
        return False, "Faqat o'zingizning reelingizni o'chira olasiz."
    execute("DELETE FROM reel_comments WHERE reel_id=?", (reel_id,))
    execute("DELETE FROM reel_likes WHERE reel_id=?", (reel_id,))
    execute("DELETE FROM reels WHERE id=?", (reel_id,))
    return True, "Reel o'chirildi."
