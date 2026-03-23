# ════════════════════════════════════════════════════
# polymarket_ws.py — Real-time Polymarket NBA Odds
# WebSocket კავშირი — მომენტალური განახლება
# ════════════════════════════════════════════════════

import json, time, threading, os, requests
import websocket
from datetime import datetime

# ── Live Odds Store (memory) ──────────────────────
LIVE_ODDS = {}   # {market_id: {question, h_price, a_price, h_odds, a_odds, updated}}
NBA_MARKETS = {} # {market_id: {question, token_ids}}
_ws = None
_running = False

# ── Polymarket Auth ───────────────────────────────
def get_auth_headers():
    import hmac, hashlib
    api_key    = os.environ.get("POLY_API_KEY", "")
    api_secret = os.environ.get("POLY_SECRET", "")
    api_pass   = os.environ.get("POLY_PASSPHRASE", "")
    ts = str(int(time.time() * 1000))
    msg = ts + "GET" + "/"
    sig = hmac.new(api_secret.encode(), msg.encode(), hashlib.sha256).hexdigest()
    return {
        "POLY-API-KEY":        api_key,
        "POLY-SIGNATURE":      sig,
        "POLY-TIMESTAMP":      ts,
        "POLY-PASSPHRASE":     api_pass,
        "Content-Type":        "application/json",
    }


# ── Fetch NBA Markets ─────────────────────────────
def fetch_nba_markets():
    """
    Polymarket-იდან NBA markets-ის ჩამოტვირთვა
    """
    global NBA_MARKETS
    found = {}

    # Gamma API
    try:
        r = requests.get(
            "https://gamma-api.polymarket.com/events",
            params={"limit": 200, "active": "true"},
            timeout=10
        )
        if r.status_code == 200:
            for ev in r.json():
                slug  = ev.get("slug","").lower()
                title = ev.get("title","").lower()
                if "nba" in slug or "nba" in title:
                    for m in ev.get("markets", []):
                        mid = m.get("id","")
                        q   = m.get("question","")
                        tok = m.get("clobTokenIds","[]")
                        if isinstance(tok, str):
                            tok = json.loads(tok)
                        if mid:
                            found[mid] = {"question": q, "token_ids": tok, "slug": slug}
    except Exception as e:
        print(f"Gamma fetch error: {e}")

    # CLOB API fallback
    if not found:
        try:
            r = requests.get(
                "https://clob.polymarket.com/markets",
                params={"limit": 100, "active": "true"},
                timeout=10
            )
            if r.status_code == 200:
                for m in r.json().get("data", []):
                    q = m.get("question","").lower()
                    if any(t in q for t in ["nba","lakers","celtics","warriors",
                                             "knicks","cavaliers","bucks","nuggets",
                                             "heat","suns","clippers","spurs","rockets"]):
                        mid = m.get("condition_id","")
                        tokens = [t.get("token_id","") for t in m.get("tokens",[])]
                        if mid:
                            found[mid] = {
                                "question": m.get("question",""),
                                "token_ids": tokens,
                                "slug": m.get("market_slug","")
                            }
        except Exception as e:
            print(f"CLOB fetch error: {e}")

    NBA_MARKETS = found
    print(f"[WS] NBA markets found: {len(found)}")
    return found


# ── Fetch Current Prices (REST) ───────────────────
def fetch_current_prices():
    """
    REST API-დან ახლანდელი prices
    (WebSocket-ის backup)
    """
    global LIVE_ODDS
    if not NBA_MARKETS:
        fetch_nba_markets()

    for mid, info in NBA_MARKETS.items():
        try:
            # Gamma outcomePrices
            r = requests.get(
                f"https://gamma-api.polymarket.com/markets/{mid}",
                timeout=8
            )
            if r.status_code == 200:
                m = r.json()
                prices_str = m.get("outcomePrices","")
                if prices_str:
                    ps = [float(x.strip()) for x in prices_str.strip("[]").split(",")]
                    if len(ps) >= 2 and 0.01 < ps[0] < 0.99:
                        LIVE_ODDS[mid] = {
                            "question": info["question"],
                            "h_price":  round(ps[0], 4),
                            "a_price":  round(ps[1], 4),
                            "h_odds":   round(1/ps[0], 2),
                            "a_odds":   round(1/ps[1], 2),
                            "updated":  datetime.now().strftime("%H:%M:%S"),
                            "source":   "rest"
                        }
        except:
            pass
        time.sleep(0.1)

    print(f"[REST] Live prices: {len(LIVE_ODDS)}")
    return LIVE_ODDS


# ── WebSocket ─────────────────────────────────────
def on_message(ws, message):
    global LIVE_ODDS
    try:
        data = json.loads(message)
        event_type = data.get("event_type","")
        asset_id   = data.get("asset_id","")

        # Price update
        if event_type in ["price_change","book"] and asset_id:
            price = float(data.get("price", 0))
            if 0.01 < price < 0.99:
                # ვეძებთ market_id-ს ამ token-ისთვის
                for mid, info in NBA_MARKETS.items():
                    tokens = info.get("token_ids",[])
                    if asset_id in tokens:
                        idx = tokens.index(asset_id)
                        if mid not in LIVE_ODDS:
                            LIVE_ODDS[mid] = {
                                "question": info["question"],
                                "h_price": 0.5, "a_price": 0.5,
                                "h_odds": 2.0,  "a_odds": 2.0,
                                "updated": "—", "source": "ws"
                            }
                        if idx == 0:
                            LIVE_ODDS[mid]["h_price"] = round(price,4)
                            LIVE_ODDS[mid]["h_odds"]  = round(1/price,2)
                        else:
                            LIVE_ODDS[mid]["a_price"] = round(price,4)
                            LIVE_ODDS[mid]["a_odds"]  = round(1/price,2)
                        LIVE_ODDS[mid]["updated"] = datetime.now().strftime("%H:%M:%S")
                        LIVE_ODDS[mid]["source"]  = "websocket"
                        break
    except Exception as e:
        pass


def on_error(ws, error):
    print(f"[WS] Error: {error}")


def on_close(ws, code, msg):
    global _running
    print(f"[WS] Closed: {code}")
    if _running:
        print("[WS] Reconnecting in 5s...")
        time.sleep(5)
        start_websocket()


def on_open(ws):
    print("[WS] Connected to Polymarket!")
    # Subscribe to all NBA market tokens
    token_ids = []
    for info in NBA_MARKETS.values():
        token_ids.extend(info.get("token_ids",[]))

    if token_ids:
        sub_msg = json.dumps({
            "type":    "subscribe",
            "channel": "live_activity",
            "assets_ids": token_ids[:50]  # max 50 per message
        })
        ws.send(sub_msg)
        print(f"[WS] Subscribed to {len(token_ids)} tokens")


def start_websocket():
    global _ws, _running
    _running = True

    if not NBA_MARKETS:
        fetch_nba_markets()

    websocket.enableTrace(False)
    _ws = websocket.WebSocketApp(
        "wss://ws-live-data.polymarket.com",
        header=get_auth_headers(),
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
    )
    _ws.run_forever(ping_interval=30, ping_timeout=10)


def stop_websocket():
    global _running, _ws
    _running = False
    if _ws:
        _ws.close()


# ── Background Thread ─────────────────────────────
def start_background():
    """
    Background-ში გაუშვი:
    1. NBA markets ჩამოტვირთე
    2. REST prices ამოიღე
    3. WebSocket დაიწყე
    4. ყოველ 30 წამს REST refresh
    """
    print("[BG] Starting Polymarket background service...")

    # ჯერ markets ჩამოტვირთე
    fetch_nba_markets()

    # REST prices (სწრაფი პირველი ჩატვირთვა)
    fetch_current_prices()

    # WebSocket thread
    ws_thread = threading.Thread(target=start_websocket, daemon=True)
    ws_thread.start()

    # REST refresh ყოველ 30 წამს (WebSocket backup)
    def rest_refresh():
        while True:
            time.sleep(30)
            try:
                fetch_current_prices()
            except:
                pass

    rest_thread = threading.Thread(target=rest_refresh, daemon=True)
    rest_thread.start()

    print("[BG] Background service started!")


# ── Public API ────────────────────────────────────
def get_live_odds():
    """
    Dashboard-ისთვის — ყველა NBA live odds
    """
    return dict(LIVE_ODDS)


def get_odds_for_game(home, away):
    """
    კონკრეტული თამაშის odds
    """
    h_keys = [home.split()[-1].lower(), home.lower()]
    a_keys = [away.split()[-1].lower(), away.lower()]

    for mid, odds in LIVE_ODDS.items():
        q = odds["question"].lower()
        h_match = any(k in q for k in h_keys)
        a_match = any(k in q for k in a_keys)
        if h_match and a_match:
            return odds

    return None


def get_status():
    return {
        "markets":    len(NBA_MARKETS),
        "live_odds":  len(LIVE_ODDS),
        "ws_running": _running,
        "last_update": max((v["updated"] for v in LIVE_ODDS.values()), default="—")
    }


# ── Test ──────────────────────────────────────────
if __name__ == "__main__":
    print("Testing Polymarket connection...")
    fetch_nba_markets()
    print(f"Markets: {len(NBA_MARKETS)}")
    for mid, info in list(NBA_MARKETS.items())[:5]:
        print(f"  {info['question']}")

    print("\nFetching prices...")
    fetch_current_prices()
    for mid, odds in list(LIVE_ODDS.items())[:5]:
        print(f"  {odds['question'][:50]}")
        print(f"    Home: {odds['h_price']} ({odds['h_odds']}x)")
        print(f"    Away: {odds['a_price']} ({odds['a_odds']}x)")
