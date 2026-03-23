import json, time, threading, os, requests
from datetime import datetime

LIVE_ODDS = {}
NBA_MARKETS = {}
_running = False

TEAM_KEYS = {
    "Los Angeles Lakers":     ["lakers"],
    "Boston Celtics":         ["celtics"],
    "Golden State Warriors":  ["warriors"],
    "Miami Heat":             ["heat"],
    "Chicago Bulls":          ["bulls"],
    "New York Knicks":        ["knicks"],
    "Brooklyn Nets":          ["nets"],
    "Cleveland Cavaliers":    ["cavaliers"],
    "Philadelphia 76ers":     ["76ers","sixers"],
    "Milwaukee Bucks":        ["bucks"],
    "Denver Nuggets":         ["nuggets"],
    "Phoenix Suns":           ["suns"],
    "LA Clippers":            ["clippers"],
    "Dallas Mavericks":       ["mavericks"],
    "San Antonio Spurs":      ["spurs"],
    "Houston Rockets":        ["rockets"],
    "Utah Jazz":              ["jazz"],
    "Oklahoma City Thunder":  ["thunder","oklahoma"],
    "Portland Trail Blazers": ["trail blazers","portland"],
    "Sacramento Kings":       ["kings","sacramento"],
    "Atlanta Hawks":          ["hawks"],
    "Charlotte Hornets":      ["hornets"],
    "Detroit Pistons":        ["pistons"],
    "Indiana Pacers":         ["pacers"],
    "Toronto Raptors":        ["raptors"],
    "New Orleans Pelicans":   ["pelicans"],
    "Memphis Grizzlies":      ["grizzlies"],
    "Minnesota Timberwolves": ["timberwolves","minnesota"],
    "Washington Wizards":     ["wizards"],
    "Orlando Magic":          ["magic","orlando"],
}

def fetch_nba_markets():
    global NBA_MARKETS
    found = {}
    try:
        r = requests.get(
            "https://gamma-api.polymarket.com/events",
            params={"limit":200,"active":"true"},
            timeout=10
        )
        if r.status_code == 200:
            for ev in r.json():
                slug  = ev.get("slug","").lower()
                title = ev.get("title","").lower()
                if "nba" in slug or "nba" in title:
                    for m in ev.get("markets",[]):
                        mid = m.get("id","")
                        q   = m.get("question","")
                        tok = m.get("clobTokenIds","[]")
                        if isinstance(tok, str):
                            try: tok = json.loads(tok)
                            except: tok = []
                        prices = m.get("outcomePrices","")
                        h_p = a_p = None
                        if prices:
                            try:
                                ps = [float(x.strip()) for x in prices.strip("[]").split(",")]
                                if len(ps)>=2 and 0.01<ps[0]<0.99:
                                    h_p = round(ps[0],4)
                                    a_p = round(ps[1],4)
                            except: pass
                        if mid:
                            found[mid] = {
                                "question": q,
                                "token_ids": tok,
                                "h_price": h_p,
                                "a_price": a_p,
                                "h_odds": round(1/h_p,2) if h_p else None,
                                "a_odds": round(1/a_p,2) if a_p else None,
                                "updated": datetime.now().strftime("%H:%M:%S"),
                                "source": "polymarket"
                            }
    except Exception as e:
        print(f"[PM] Gamma error: {e}")

    if not found:
        try:
            r = requests.get(
                "https://clob.polymarket.com/markets",
                params={"limit":100,"active":"true"},
                timeout=10
            )
            if r.status_code == 200:
                for m in r.json().get("data",[]):
                    q = m.get("question","").lower()
                    if any(t in q for t in ["nba","lakers","celtics","warriors",
                                             "knicks","cavaliers","bucks","nuggets"]):
                        mid = m.get("condition_id","")
                        tokens = m.get("tokens",[])
                        if mid and len(tokens)>=2:
                            p1 = float(tokens[0].get("price",0.5))
                            p2 = float(tokens[1].get("price",0.5))
                            if 0.01<p1<0.99:
                                found[mid] = {
                                    "question": m.get("question",""),
                                    "token_ids": [t.get("token_id","") for t in tokens],
                                    "h_price": round(p1,4),
                                    "a_price": round(p2,4),
                                    "h_odds": round(1/p1,2),
                                    "a_odds": round(1/p2,2),
                                    "updated": datetime.now().strftime("%H:%M:%S"),
                                    "source": "polymarket"
                                }
        except Exception as e:
            print(f"[PM] CLOB error: {e}")

    NBA_MARKETS = found
    LIVE_ODDS.update(found)
    print(f"[PM] Markets loaded: {len(found)}")
    return found

def refresh_prices():
    global LIVE_ODDS
    if not NBA_MARKETS:
        fetch_nba_markets()
        return
    for mid, info in NBA_MARKETS.items():
        try:
            r = requests.get(
                f"https://gamma-api.polymarket.com/markets/{mid}",
                timeout=5
            )
            if r.status_code == 200:
                m = r.json()
                prices = m.get("outcomePrices","")
                if prices:
                    ps = [float(x.strip()) for x in prices.strip("[]").split(",")]
                    if len(ps)>=2 and 0.01<ps[0]<0.99:
                        LIVE_ODDS[mid] = {
                            "question": info["question"],
                            "h_price": round(ps[0],4),
                            "a_price": round(ps[1],4),
                            "h_odds": round(1/ps[0],2),
                            "a_odds": round(1/ps[1],2),
                            "updated": datetime.now().strftime("%H:%M:%S"),
                            "source": "polymarket"
                        }
        except: pass
        time.sleep(0.1)

def start_background():
    global _running
    _running = True
    def loop():
        fetch_nba_markets()
        while _running:
            try:
                refresh_prices()
            except Exception as e:
                print(f"[PM] Refresh error: {e}")
            time.sleep(30)
    t = threading.Thread(target=loop, daemon=True)
    t.start()
    print("[PM] Background started")

def get_live_odds():
    return dict(LIVE_ODDS)

def get_odds_for_game(home, away):
    h_keys = TEAM_KEYS.get(home, [home.split()[-1].lower()])
    a_keys = TEAM_KEYS.get(away, [away.split()[-1].lower()])
    for mid, odds in LIVE_ODDS.items():
        q = odds["question"].lower()
        if any(k in q for k in h_keys) and any(k in q for k in a_keys):
            return odds
    return None

def get_status():
    return {
        "markets": len(NBA_MARKETS),
        "live_odds": len(LIVE_ODDS),
        "running": _running,
        "last_update": max((v["updated"] for v in LIVE_ODDS.values()), default="—")
    }
