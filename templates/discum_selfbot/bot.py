import time
import json
import random
import logging
import requests
import sqlite3
import threading
import re
import warnings
from collections import deque, defaultdict
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any

import discum

# ====== Suppress noisy warnings (optional) ======
with warnings.catch_warnings():
    warnings.simplefilter("ignore")

# ====== Load config.toml ======
try:
    import tomllib  # Py3.11+
except ModuleNotFoundError:
    import tomli as tomllib  # pip install tomli

with open("config.toml", "rb") as f:
    CFG = tomllib.load(f)

TOKEN      = CFG["discord_user_token"]
GEM_KEY    = CFG["gemini_api_key"]
CHANNELS   = {int(x) for x in CFG["channel_ids"]}

PERSONA    = CFG["persona"]
REPLY_CFG  = CFG["reply"]
PUB_PROBS  = CFG["reply"]["public_probs"]
FRIENDCFG  = CFG["friendship"]
MEM_CFG    = CFG["memory"]
FACT_RULES = CFG.get("fact_rules", {})
MIRROR_CFG = CFG["mirror"]
FILTERS    = CFG["filters"]
EMOJI_CFG  = CFG["emoji"]
HOURS_CFG  = CFG["active_hours"]
SELF_CFG   = CFG["self_start"]
RLIM_CFG   = CFG["rate_limit"]
STORE      = CFG["storage"]

DEBUG_LOG  = STORE["debug_log_file"]
AI_LOG     = STORE["ai_log_file"]
DB_FILE    = STORE["db_file"]
MAX_HIST   = int(MEM_CFG["max_history_per_channel"])

# ====== Logging ======
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(DEBUG_LOG, encoding="utf-8")]
)
log = logging.getLogger("discum-bestfriend")

def log_ai(prompt, raw_response, final_reply):
    rec = {
        "ts": datetime.now().isoformat(),
        "prompt": prompt,
        "raw_gemini": raw_response,
        "final_reply": final_reply
    }
    with open(AI_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

# ====== SQLite (thread-safe) ======
db_lock = threading.Lock()
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cur  = conn.cursor()
with db_lock:
    cur.execute("""
        CREATE TABLE IF NOT EXISTS chat_history(
            channel_id INTEGER,
            message_id TEXT,
            author_id TEXT,
            author_name TEXT,
            content TEXT,
            ts TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_facts(
            user_id TEXT,
            username TEXT,
            fact_key TEXT,
            fact_value TEXT,
            confidence REAL,
            first_seen TEXT,
            last_seen TEXT,
            PRIMARY KEY(user_id, fact_key, fact_value)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS friendships(
            user_id TEXT PRIMARY KEY,
            username TEXT,
            score INTEGER,
            first_seen TEXT,
            last_seen TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_topics(
            user_id TEXT,
            topic TEXT,
            count INTEGER,
            last_seen TEXT,
            PRIMARY KEY(user_id, topic)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_style(
            user_id TEXT PRIMARY KEY,
            username TEXT,
            avg_msg_len REAL,
            lowercase_ratio REAL,
            emoji_ratio REAL,
            samples INTEGER
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS channel_counts(
            channel_id INTEGER,
            window_start TEXT,
            count INTEGER,
            PRIMARY KEY(channel_id, window_start)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS api_stats(
            date TEXT PRIMARY KEY,
            success_count INTEGER,
            error_count INTEGER,
            total_tokens INTEGER
        )
    """)
    conn.commit()

# ====== DB helpers ======
def save_message(cid, mid, uid, uname, content):
    with db_lock:
        cur.execute("INSERT INTO chat_history VALUES (?,?,?,?,?,?)",
                    (cid, mid, uid, uname, content, datetime.now().isoformat()))
        conn.commit()

def recent_messages_for_reactions(cid, within_seconds):
    cutoff = datetime.now() - timedelta(seconds=within_seconds)
    with db_lock:
        cur.execute("""
            SELECT message_id, content FROM chat_history
            WHERE channel_id=? AND ts >= ?
            ORDER BY ts DESC LIMIT 25
        """, (cid, cutoff.isoformat()))
        return cur.fetchall()

def load_history(cid, limit=MAX_HIST):
    with db_lock:
        cur.execute("""
            SELECT author_name, content FROM chat_history
            WHERE channel_id=?
            ORDER BY ts DESC LIMIT ?
        """, (cid, limit))
        rows = cur.fetchall()
    return [f"{a}: {m}" for a, m in reversed(rows)]

def upsert_fact(uid, uname, key, value, confidence=0.85):
    now = datetime.now().isoformat()
    with db_lock:
        cur.execute("""
            INSERT INTO user_facts(user_id, username, fact_key, fact_value, confidence, first_seen, last_seen)
            VALUES (?,?,?,?,?,?,?)
            ON CONFLICT(user_id, fact_key, fact_value)
            DO UPDATE SET username=excluded.username, confidence=max(confidence, excluded.confidence), last_seen=excluded.last_seen
        """, (uid, uname, key, value, confidence, now, now))
        conn.commit()

def get_user_facts(uid, limit=6):
    with db_lock:
        cur.execute("""
            SELECT fact_key, fact_value FROM user_facts
            WHERE user_id=?
            ORDER BY last_seen DESC LIMIT ?
        """, (uid, limit))
        return cur.fetchall()

def get_friend_score(uid, uname=None):
    with db_lock:
        cur.execute("SELECT score FROM friendships WHERE user_id=?", (uid,))
        row = cur.fetchone()
        if row:
            return int(row[0])
        cur.execute("INSERT OR IGNORE INTO friendships VALUES (?,?,?,?,?)",
                    (uid, uname or "", FRIENDCFG["start_score"], datetime.now().isoformat(), datetime.now().isoformat()))
        conn.commit()
        return int(FRIENDCFG["start_score"])

def adjust_friend_score(uid, uname, delta):
    if delta == 0:
        return
    delta = max(-FRIENDCFG["max_abs_score_change_per_day"], min(FRIENDCFG["max_abs_score_change_per_day"], delta))
    now = datetime.now().isoformat()
    with db_lock:
        cur.execute("SELECT score FROM friendships WHERE user_id=?", (uid,))
        row = cur.fetchone()
        if row:
            newscore = int(row[0]) + int(delta)
            cur.execute("UPDATE friendships SET username=?, score=?, last_seen=? WHERE user_id=?",
                        (uname, newscore, now, uid))
        else:
            cur.execute("INSERT INTO friendships(user_id, username, score, first_seen, last_seen) VALUES (?,?,?,?,?)",
                        (uid, uname, FRIENDCFG["start_score"] + int(delta), now, now))
        conn.commit()

def decay_friendships_weekly():
    while True:
        try:
            with db_lock:
                cur.execute("SELECT user_id, username, score, last_seen FROM friendships")
                rows = cur.fetchall()
                for uid, uname, score, last_seen in rows:
                    try:
                        last = datetime.fromisoformat(last_seen)
                        if (datetime.now() - last).days >= 7:
                            newscore = max(0, score + FRIENDCFG["weekly_decay"])
                            cur.execute("UPDATE friendships SET score=?, last_seen=? WHERE user_id=?",
                                        (newscore, datetime.now().isoformat(), uid))
                    except Exception:
                        pass
                conn.commit()
        except Exception as e:
            log.warning(f"[FriendDecay] {e}")
        time.sleep(24 * 3600)

def bump_channel_count(cid):
    start = datetime.now().replace(minute=0, second=0, microsecond=0).isoformat()
    with db_lock:
        cur.execute("""
            INSERT INTO channel_counts(channel_id, window_start, count) VALUES (?,?,1)
            ON CONFLICT(channel_id, window_start)
            DO UPDATE SET count = count + 1
        """, (cid, start))
        conn.commit()

def channel_count(cid):
    start = datetime.now().replace(minute=0, second=0, microsecond=0).isoformat()
    with db_lock:
        cur.execute("SELECT count FROM channel_counts WHERE channel_id=? AND window_start=?", (cid, start))
        row = cur.fetchone()
    return row[0] if row else 0

def upsert_style(uid, uname, content):
    if not content:
        return
    text = content
    emj = sum(c in "😂😅🔥😎🙌👍😊🙂😁😆😢😭😡😍❤️✨🥲😉🤔🤨😴😮🙄" for c in text)
    emojis_ratio = emj / max(1, len(text))
    lower_ratio  = (sum(1 for c in text if c.isalpha() and c.islower())
                    / max(1, sum(1 for c in text if c.isalpha())))
    avg_len      = len(text)
    with db_lock:
        cur.execute("SELECT avg_msg_len, lowercase_ratio, emoji_ratio, samples FROM user_style WHERE user_id=?", (uid,))
        row = cur.fetchone()
        if row:
            a, l, e, n = row
            n2 = n + 1
            a2 = (a*n + avg_len)/n2
            l2 = (l*n + lower_ratio)/n2
            e2 = (e*n + emojis_ratio)/n2
            cur.execute("UPDATE user_style SET username=?, avg_msg_len=?, lowercase_ratio=?, emoji_ratio=?, samples=? WHERE user_id=?",
                        (uname, a2, l2, e2, n2, uid))
        else:
            cur.execute("INSERT INTO user_style VALUES (?,?,?,?,?,?)", (uid, uname, avg_len, lower_ratio, emojis_ratio, 1))
        conn.commit()

def get_style(uid):
    with db_lock:
        cur.execute("SELECT avg_msg_len, lowercase_ratio, emoji_ratio FROM user_style WHERE user_id=?", (uid,))
        row = cur.fetchone()
    if not row:
        return (20.0, 0.6, 0.01)
    return row

def upsert_topic(uid, topic):
    now = datetime.now().isoformat()
    topic = (topic or "").strip().lower()
    if not topic:
        return
    with db_lock:
        cur.execute("""
            INSERT INTO user_topics(user_id, topic, count, last_seen) VALUES (?,?,1,?)
            ON CONFLICT(user_id, topic)
            DO UPDATE SET count = count + 1, last_seen = excluded.last_seen
        """, (uid, topic, now))
        conn.commit()

def get_top_friend():
    with db_lock:
        cur.execute("SELECT user_id, username, score FROM friendships ORDER BY score DESC LIMIT 1")
        row = cur.fetchone()
    return row if row else None

def update_api_stats(success: bool, tokens: int = 0):
    """Track API usage statistics"""
    date = datetime.now().strftime("%Y-%m-%d")
    with db_lock:
        cur.execute("SELECT success_count, error_count, total_tokens FROM api_stats WHERE date=?", (date,))
        row = cur.fetchone()
        if row:
            success_count, error_count, total_tokens = row
            if success:
                success_count += 1
            else:
                error_count += 1
            total_tokens += tokens
            cur.execute("UPDATE api_stats SET success_count=?, error_count=?, total_tokens=? WHERE date=?",
                        (success_count, error_count, total_tokens, date))
        else:
            success_count = 1 if success else 0
            error_count = 0 if success else 1
            total_tokens = tokens
            cur.execute("INSERT INTO api_stats VALUES (?,?,?,?)", (date, success_count, error_count, total_tokens))
        conn.commit()

# ====== Behavior helpers ======
def in_active_hours():
    start = int(HOURS_CFG["start_hour"]) % 24
    end   = int(HOURS_CFG["end_hour"]) % 24
    hour  = datetime.now().hour
    if start <= end:
        return start <= hour < end
    else:
        return hour >= start or hour < end

def should_reply_now():
    if in_active_hours():
        return True
    return random.random() < float(REPLY_CFG["outside_hours_reply_prob"])

def within_filters(uid, content):
    if uid in set(FILTERS["blocked_user_ids"]):
        return False
    text = (content or "").lower()
    if any(kw.lower() in text for kw in FILTERS["blocked_keywords"]):
        return False
    req = FILTERS.get("require_keyword_any", [])
    if req and not any(k.lower() in text for k in req):
        return False
    return True

def public_probability_for_score(score, mentioned=False, content=""):
    if score <= 10:
        base = float(PUB_PROBS["stranger"])
    elif score <= 50:
        base = float(PUB_PROBS["acquaintance"])
    elif score <= 100:
        base = float(PUB_PROBS["friend"])
    else:
        base = float(PUB_PROBS["bestfriend"])
    if mentioned or any(k in (content or "").lower() for k in FILTERS["keywords_priority"]):
        base = min(1.0, base + float(PUB_PROBS["mention_boost"]))
    return base

# ====== Mood & typing ======
CURRENT_MOOD = random.choice(PERSONA["moods"])
last_mood_drift_day = datetime.now().day

def daily_mood_drift():
    global CURRENT_MOOD, last_mood_drift_day
    while True:
        try:
            today = datetime.now().day
            if today != last_mood_drift_day and random.random() < float(PERSONA["mood_daily_drift"]):
                CURRENT_MOOD = random.choice(PERSONA["moods"])
                last_mood_drift_day = today
                log.info(f"[DailyMood] now {CURRENT_MOOD}")
        except Exception as e:
            log.warning(f"[DailyMood] {e}")
        time.sleep(3600)

def maybe_change_mood():
    global CURRENT_MOOD
    if random.random() < float(PERSONA["mood_change_probability"]):
        CURRENT_MOOD = random.choice(PERSONA["moods"])
        log.info(f"[Mood] now {CURRENT_MOOD}")

def typing_delay_for_text(text):
    wpm = max(40, int(REPLY_CFG["typing_speed_wpm"]))
    words = max(1, len(text.split()))
    seconds = (words / wpm) * 60
    return min(10, seconds + random.uniform(0.5, 1.8))

# ====== Enhanced Gemini API with retry logic ======
def ask_gemini_text(prompt: str, api_key: str = GEM_KEY, timeout: int = 30, max_retries: int = 3) -> Tuple[Optional[str], str]:
    """
    Enhanced Gemini API call with retry logic and better error handling
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    
    # Enhanced payload with better configuration
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 200,
            "topK": 40,
            "topP": 0.95
        },
        "safetySettings": [
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_ONLY_HIGH"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_ONLY_HIGH"
            },
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_ONLY_HIGH"
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_ONLY_HIGH"
            }
        ]
    }
    
    headers = {"Content-Type": "application/json"}
    
    # Log the outbound prompt (truncate to keep logs readable)
    log.info(f"[Gemini Request] {prompt[:500]}{'...' if len(prompt)>500 else ''}")
    
    last_exception = None
    last_response_text = ""
    
    for attempt in range(1, max_retries + 1):
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=timeout)
            last_response_text = r.text[:1200] + ("..." if len(r.text) > 1200 else "")
            
            # Log response status
            log.info(f"[Gemini Response] Attempt {attempt}/{max_retries} | Status {r.status_code} | Body: {last_response_text}")
            
            # Check for successful response
            if r.status_code == 200:
                # Check if response has content
                if not r.text:
                    log.warning(f"[Gemini API] Empty response on attempt {attempt}")
                    last_exception = "Empty response"
                    continue
                
                # Try to parse JSON
                try:
                    data = r.json()
                except json.JSONDecodeError as e:
                    log.warning(f"[Gemini API] JSON decode error on attempt {attempt}: {e}")
                    last_exception = f"JSON decode error: {e}"
                    continue
                
                # Check if we have valid content
                if "candidates" in data and len(data["candidates"]) > 0:
                    candidate = data["candidates"][0]
                    if "content" in candidate and "parts" in candidate["content"]:
                        text = candidate["content"]["parts"][0]["text"].strip()
                        if text:
                            # Update API stats
                            tokens = data.get("usageMetadata", {}).get("totalTokenCount", 0)
                            update_api_stats(True, tokens)
                            return text, r.text
                        else:
                            log.warning(f"[Gemini API] Empty text response on attempt {attempt}")
                            last_exception = "Empty text response"
                            continue
                    else:
                        log.warning(f"[Gemini API] Invalid response structure on attempt {attempt}")
                        last_exception = "Invalid response structure"
                        continue
                else:
                    log.warning(f"[Gemini API] No candidates in response on attempt {attempt}")
                    last_exception = "No candidates in response"
                    continue
            else:
                # Handle HTTP errors
                log.warning(f"[Gemini API] HTTP {r.status_code} on attempt {attempt}")
                last_exception = f"HTTP {r.status_code}"
                
                # If it's a client error (4xx), don't retry
                if 400 <= r.status_code < 500:
                    break
                    
        except requests.exceptions.Timeout:
            log.warning(f"[Gemini API] Timeout on attempt {attempt}")
            last_exception = "Timeout"
        except requests.exceptions.ConnectionError as e:
            log.warning(f"[Gemini API] Connection error on attempt {attempt}: {e}")
            last_exception = f"Connection error: {e}"
        except Exception as e:
            log.warning(f"[Gemini API] Unexpected error on attempt {attempt}: {e}")
            last_exception = f"Unexpected error: {e}"
            
        # If we've reached max retries, break
        if attempt >= max_retries:
            break
            
        # Wait before retrying (exponential backoff)
        wait_time = min(2 ** attempt, 10)  # Max 10 seconds
        log.info(f"[Gemini API] Waiting {wait_time}s before retry {attempt+1}")
        time.sleep(wait_time)
    
    # Update API stats for failure
    update_api_stats(False, 0)
    
    # Log final failure
    log.error(f"[Gemini API] All {max_retries} attempts failed. Last error: {last_exception}")
    return None, last_response_text

# ====== Enhanced Prompt builder ======
def build_prompt(cid, uid, uname):
    history   = load_history(cid)
    facts     = get_user_facts(uid)
    facts_txt = "; ".join([f"{k}:{v}" for k, v in facts]) if facts else ""
    avg_len, lower_ratio, emoji_ratio = get_style(uid)

    wL = MIRROR_CFG["weight_length"] if MIRROR_CFG["enable"] else 0.0
    wlc= MIRROR_CFG["weight_lowercase"] if MIRROR_CFG["enable"] else 0.0
    we = MIRROR_CFG["weight_emoji"] if MIRROR_CFG["enable"] else 0.0

    # Enhanced prompt with better structure
    head = (
        f"You are {PERSONA['name']}, a {CURRENT_MOOD} Bangladeshi friend.\n"
        f"Personality Style: {PERSONA['style']}\n"
        f"Communication Quirks: {PERSONA['quirks']}\n"
        f"Conversation Boundaries: {PERSONA['boundaries']}\n\n"
        f"User Facts (use sparingly): {facts_txt}\n"
        f"Style Mirroring Hints (weight_length={wL}, weight_lowercase={wlc}, weight_emoji={we}): "
        f"avg_len={avg_len:.1f}, lowercase_ratio={lower_ratio:.2f}, emoji_ratio={emoji_ratio:.3f}\n"
        f"Recent conversation context:\n"
    )
    
    # Add conversation context
    conversation_context = "\n".join(history) if history else "No previous messages."
    
    tail = (
        "\n\nRespond as a natural, engaging friend in Banglish (Bengali in Latin letters). "
        "Keep responses concise and conversational. Use 0-2 emojis max. "
        "Mirror the user's communication style subtly based on the style hints. "
        "Avoid markdown, formal language, or overly structured responses. "
        "Be authentic and friendly while respecting all boundaries."
    )
    
    return head + conversation_context + tail

# ====== Facts extraction ======
FACT_REGEXES = [(re.compile(p, re.IGNORECASE), key) for p, key in FACT_RULES.items()]

def extract_and_store_facts(uid, uname, content):
    if not MEM_CFG.get("enable_fact_learning", True):
        return False
    if not content:
        return False
    stored = False
    for rx, key in FACT_REGEXES:
        m = rx.search(content)
        if m:
            val = m.group(1).strip()
            val = re.sub(r"[^0-9A-Za-zঅ-হ\s\-_.]", "", val)
            if 1 <= len(val) <= 40:
                upsert_fact(uid, uname, key, val, confidence=0.88)
                stored = True
    return stored

# ====== Discum client ======
bot = discum.Client(token=TOKEN, log=False)

mem_cache = {cid: deque(maxlen=MAX_HIST) for cid in CHANNELS}
last_message_time_global = time.time()
last_reply_to_user = defaultdict(lambda: 0.0)

@bot.gateway.command
def on_ready(resp):
    if resp.event.ready_supplemental:
        log.info("Connected to Discord (Discum).")

@bot.gateway.command
def on_message(resp):
    global last_message_time_global
    if not resp.event.message:
        return
    m = resp.parsed.auto()
    cid = int(m["channel_id"])
    if cid not in CHANNELS:
        return

    me = bot.gateway.session.user
    if me and m["author"]["id"] == me["id"]:
        last_message_time_global = time.time()
        return

    uid   = m["author"]["id"]
    uname = m["author"]["username"]
    mid   = m["id"]
    content = m.get("content", "") or ""

    if not within_filters(uid, content):
        return

    log.info(f"[#{cid}] {uname}({uid}): {content}")
    save_message(cid, mid, uid, uname, content)
    mem_cache[cid].append(f"{uname}: {content}")
    upsert_style(uid, uname, content)
    stored_fact = extract_and_store_facts(uid, uname, content)

    # friendship adjustments
    score_before = get_friend_score(uid, uname)
    me_mentioned = (me and (str(me["id"]) in content or (PERSONA["name"].lower() in content.lower())))
    delta = 0
    if me_mentioned:
        delta += int(FRIENDCFG["direct_mention_boost"])
    if stored_fact:
        delta += int(FRIENDCFG["fact_share_boost"])

    low = content.lower()
    if any(x in low for x in ["😅","😂","😎","❤️","nice","thanks","valo","love","best","haha","lol","bro","vai","bhai"]):
        delta += int(FRIENDCFG["positive_boost"])
    if any(x in low for x in ["stupid","dumb","hate","bad","trash","idiot","cancel","f off"]):
        delta += int(FRIENDCFG["negative_penalty"])
    adjust_friend_score(uid, uname, delta)

    last_message_time_global = time.time()

    # React sometimes
    if random.random() < float(EMOJI_CFG["reaction_probability"]):
        try:
            recent = recent_messages_for_reactions(cid, int(EMOJI_CFG["reaction_window_seconds"]))
            if recent:
                msg_id, _ = random.choice(recent)
                emoji  = random.choice(EMOJI_CFG["reply_emojis"])
                bot.addReaction(str(cid), msg_id, emoji)
                log.info(f"[React #{cid}] {emoji} to {msg_id}")
        except Exception as e:
            log.warning(f"[React] failed: {e}")

    # Decide to reply now
    score_now = get_friend_score(uid, uname)
    base_prob = public_probability_for_score(score_now, mentioned=me_mentioned, content=content)
    if random.random() > base_prob:
        return
    if not should_reply_now():
        return

    # per-user cooldown
    now = time.time()
    cd  = float(RLIM_CFG["per_user_cooldown_s"])
    if now - last_reply_to_user[uid] < cd:
        log.info(f"[Cooldown] skipping reply to {uname}")
        return

    # channel hourly rate limit
    if channel_count(cid) >= int(RLIM_CFG["max_per_channel_per_hour"]):
        log.info(f"[RateLimit] channel #{cid} quota reached")
        return

    # Natural delay (configured 5–10 min typically)
    delay = random.randint(int(REPLY_CFG["min_delay_sec"]), int(REPLY_CFG["max_delay_sec"]))
    log.info(f"[#{cid}] waiting {delay}s before reply…")
    time.sleep(delay)

    maybe_change_mood()
    prompt = build_prompt(cid, uid, uname)
    reply_text, raw_json = ask_gemini_text(prompt)

    # fallback if Gemini fails
    if not reply_text:
        # Try a different fallback based on mood
        fallbacks = {
            "happy": ["hehe 🙂", "nice one bhai!", "cool cool 😎"],
            "chill": ["hmm bhai", "yeah yeah", "right right"],
            "tired": ["ugh tired asf", "zzz", "maybe later"],
            "playful": ["kek 😂", "really bro?", "seriously now?"],
            "annoyed": ["yeah whatever", "hmm bhai 🙂", "alright then"]
        }
        reply_text = random.choice(fallbacks.get(CURRENT_MOOD, ["hmm bhai 🙂"]))

    if len(reply_text) > int(REPLY_CFG["max_reply_chars"]):
        reply_text = reply_text[:int(REPLY_CFG["max_reply_chars"])].rstrip() + "..."

    # lightweight topic guess (single keywords)
    for t in re.findall(r"\b(\w{3,15})\b", content.lower()):
        if t.isalpha():
            upsert_topic(uid, t)

    # If positive-looking reply, nudge friendship
    if any(x in reply_text.lower() for x in ["🙂","😅","😂","😎","bhalo","valo","nice","ashchi","dosto","bro","bhai","vai"]):
        adjust_friend_score(uid, uname, FRIENDCFG["positive_boost"])

    # Typing simulation
    try:
        bot.typingAction(str(cid))
    except Exception:
        pass
    time.sleep(typing_delay_for_text(reply_text))

    # Multi-message split?
    to_send = [reply_text]
    if random.random() < float(REPLY_CFG["multi_msg_probability"]):
        parts = re.split(r'(?<=[.!?])\s+', reply_text)
        if len(parts) >= 2:
            to_send = [parts[0], " ".join(parts[1:])]

    # Send + log
    try:
        for i, chunk in enumerate(to_send):
            bot.sendMessage(str(cid), chunk)
            me_id = bot.gateway.session.user["id"] if bot.gateway.session.user else "me"
            save_message(cid, f"me-{int(time.time()*1000)}-{i}", me_id, PERSONA["name"], chunk)
            time.sleep(random.uniform(0.6, 1.6))
        bump_channel_count(cid)
        last_reply_to_user[uid] = time.time()
        last_message_time_global = time.time()
        log_ai(prompt, raw_json or "", reply_text)
        log.info(f"[BOT -> #{cid}] (score {score_before}->{get_friend_score(uid, uname)}): {reply_text}")
    except Exception as e:
        log.error(f"[Send] failed: {e}")

# ====== Self-start: mention a friend casually ======
def self_start_loop():
    global last_message_time_global
    while True:
        try:
            if SELF_CFG.get("enabled", True):
                idle = time.time() - last_message_time_global
                if idle > int(SELF_CFG["min_idle_seconds"]) and random.random() < float(SELF_CFG["chance"]):
                    cid = random.choice(list(CHANNELS))
                    opener = random.choice(SELF_CFG["openers"])
                    top = get_top_friend()
                    if top and top[2] >= FRIENDCFG["friend_threshold"]:
                        _, uname, _ = top
                        opener = f"{opener} {uname}"
                    try:
                        bot.typingAction(str(cid))
                    except Exception:
                        pass
                    time.sleep(random.uniform(1.0, 2.2))
                    bot.sendMessage(str(cid), opener)
                    save_message(cid, f"me-{int(time.time()*1000)}", "me", PERSONA["name"], opener)
                    log.info(f"[SELF-START -> #{cid}] {opener}")
                    last_message_time_global = time.time()
        except Exception as e:
            log.warning(f"[SelfStart] error: {e}")
        time.sleep(60)

# ====== Background threads ======
threading.Thread(target=decay_friendships_weekly, daemon=True).start()
threading.Thread(target=daily_mood_drift, daemon=True).start()
threading.Thread(target=self_start_loop, daemon=True).start()

log.info("Starting… (educational; selfbots violate Discord ToS)")
bot.gateway.run(auto_reconnect=True)