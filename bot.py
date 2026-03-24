import math, time, json, os, requests
from datetime import datetime
import sqlite3

DB = "trades.db"

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT, game TEXT, fav TEXT,
        odds REAL, open_odds REAL, sharp INTEGER,
        sharp_label TEXT, tier TEXT, score REAL,
        edge REAL, ev REAL, stake REAL, pot REAL,
        result TEXT DEFAULT 'PENDING', pnl REAL DEFAULT 0,
        mode TEXT DEFAULT 'paper', source TEXT DEFAULT 'odds_api'
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS portfolio (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT, bankroll REAL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY, value TEXT
    )""")
    c.execute("INSERT OR IGNORE INTO settings VALUES ('bankroll','1000.0')")
    c.execute("INSERT OR IGNORE INTO settings VALUES ('mode','paper')")
    c.execute("INSERT OR IGNORE INTO settings VALUES ('running','false')")
    conn.commit()
    conn.close()

def get_setting(key):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def set_setting(key, value):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO settings VALUES (?,?)", (key, str(value)))
    conn.commit()
    conn.close()

def get_bankroll():
    return float(get_setting('bankroll') or 1000.0)

def save_trade(trade):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""INSERT INTO trades
        (timestamp,game,fav,odds,open_odds,sharp,sharp_label,
         tier,score,edge,ev,stake,pot,mode,source)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        trade['game'], trade['fav'], trade['odds'], trade['open_odds'],
        trade['sharp'], trade['sharp_label'], trade['tier'],
        trade['score'], trade['edge'], trade['ev'],
        trade['stake'], trade['pot'],
        get_setting('mode'), trade.get('source','odds_api')
    ))
    tid = c.lastrowid
    conn.commit()
    conn.close()
    return tid

def update_result(trade_id, won):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT stake,odds FROM trades WHERE id=?", (trade_id,))
    row = c.fetchone()
    if row:
        stake, odds = row
        pnl = round(stake*(odds-1),2) if won else -stake
        c.execute("UPDATE trades SET result=?,pnl=? WHERE id=?",
                  ('WIN' if won else 'LOSS', pnl, trade_id))
        bk = round(get_bankroll()+pnl, 2)
        set_setting('bankroll', bk)
        c.execute("INSERT INTO portfolio (timestamp,bankroll) VALUES (?,?)",
                  (datetime.now().strftime("%Y-%m-%d %H:%M"), bk))
        conn.commit()
    conn.close()

def get_trades(limit=50):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM trades ORDER BY id DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    cols = ['id','timestamp','game','fav','odds','open_odds','sharp',
            'sharp_label','tier','score','edge','ev','stake','pot',
            'result','pnl','mode','source']
    return [dict(zip(cols,r)) for r in rows]

def get_portfolio_history():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT timestamp,bankroll FROM portfolio ORDER BY id")
    rows = c.fetchall()
    conn.close()
    return rows

def get_stats():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM trades WHERE result='PENDING'")
    open_pos = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM trades WHERE result!='PENDING'")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM trades WHERE result='WIN'")
    wins = c.fetchone()[0]
    c.execute("SELECT SUM(pnl) FROM trades WHERE result!='PENDING'")
    tpnl = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM trades WHERE DATE(timestamp)=DATE('now')")
    daily = c.fetchone()[0]
    c.execute("SELECT SUM(pnl) FROM trades WHERE DATE(timestamp)=DATE('now') AND result!='PENDING'")
    dpnl = c.fetchone()[0] or 0
    conn.close()
    bk = get_bankroll()
    return {
        'bankroll': bk, 'pnl': round(tpnl,2),
        'daily_pnl': round(dpnl,2), 'open_positions': open_pos,
        'daily_trades': daily, 'total_trades': total,
        'win_rate': round(wins/total*100,1) if total>0 else 0,
        'wins': wins, 'losses': total-wins,
        'mode': get_setting('mode'),
        'running': get_setting('running')=='true'
    }

# ════════════════════════════════════════
# THE ODDS API — NBA Games + Odds
# ════════════════════════════════════════

ODDS_CACHE_FILE = "/tmp/odds_cache.json"
OPENING_CACHE_FILE = "/tmp/opening_odds.json"

def get_nba_odds_from_api():
    """
    The Odds API-დან NBA odds ამოღება
    Polymarket bookmaker-ის კოეფიციენტები
    """
    api_key = os.environ.get("ODDS_API_KEY", "")
    if not api_key:
        print("[ODDS] No API key found")
        return []

    url = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds"
    params = {
        "apiKey":      api_key,
        "regions":     "us",
        "markets":     "h2h",
        "oddsFormat":  "decimal",
        "dateFormat":  "iso",
        "bookmakers":  "draftkings,fanduel,betmgm,pointsbet"
    }

    try:
        r = requests.get(url, params=params, timeout=15)
        print(f"[ODDS] Status: {r.status_code}")
        remaining = r.headers.get("x-requests-remaining","?")
        print(f"[ODDS] Requests remaining: {remaining}")

        if r.status_code != 200:
            print(f"[ODDS] Error: {r.text[:200]}")
            return []

        games = []
        for event in r.json():
            home = event.get("home_team","")
            away = event.get("away_team","")
            commence = event.get("commence_time","")

            # odds-ების ამოღება
            best_h = best_a = None
            bookmakers = event.get("bookmakers",[])
            if bookmakers:
                bm = bookmakers[0]
                for market in bm.get("markets",[]):
                    if market["key"] == "h2h":
                        outcomes = market.get("outcomes",[])
                        for o in outcomes:
                            if o["name"] == home:
                                best_h = round(o["price"],2)
                            elif o["name"] == away:
                                best_a = round(o["price"],2)

            if best_h and best_a:
                games.append({
                    "home":    home,
                    "away":    away,
                    "h_odds":  best_h,
                    "a_odds":  best_a,
                    "time":    commence,
                    "source":  "odds_api"
                })

        # Cache-ში შენახვა
        with open(ODDS_CACHE_FILE,"w") as f:
            json.dump({
                "time": datetime.now().isoformat(),
                "games": games
            }, f)

        # Opening odds შენახვა (პირველი გაშვება)
        if not os.path.exists(OPENING_CACHE_FILE):
            opening = {g["home"]+"|"+g["away"]: {
                "h": g["h_odds"], "a": g["a_odds"]
            } for g in games}
            with open(OPENING_CACHE_FILE,"w") as f:
                json.dump({
                    "time": datetime.now().isoformat(),
                    "odds": opening
                }, f)
            print(f"[ODDS] Opening odds saved: {len(opening)} games")

        print(f"[ODDS] Games loaded: {len(games)}")
        return games

    except Exception as e:
        print(f"[ODDS] Exception: {e}")
        return []


def get_opening_odds():
    """Opening odds ჩატვირთვა"""
    if not os.path.exists(OPENING_CACHE_FILE):
        return {}
    try:
        d = json.load(open(OPENING_CACHE_FILE))
        hours = (datetime.now()-datetime.fromisoformat(d["time"])).total_seconds()/3600
        if hours > 24:
            os.remove(OPENING_CACHE_FILE)
            return {}
        return d["odds"]
    except:
        return {}


def reset_opening_odds():
    """Opening odds გადაყენება (ახალი დღე)"""
    if os.path.exists(OPENING_CACHE_FILE):
        os.remove(OPENING_CACHE_FILE)
    print("[ODDS] Opening odds reset")


def get_cached_games():
    """Cache-დან games"""
    if not os.path.exists(ODDS_CACHE_FILE):
        return []
    try:
        d = json.load(open(ODDS_CACHE_FILE))
        mins = (datetime.now()-datetime.fromisoformat(d["time"])).total_seconds()/60
        if mins > 30:
            return []
        return d["games"]
    except:
        return []


def get_todays_games():
    """ESPN-დან games (fallback)"""
    today = datetime.now().strftime("%Y%m%d")
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={today}"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        games = []
        for event in data.get("events",[]):
            comp = event["competitions"][0]
            if comp["status"]["type"]["name"]=="STATUS_FINAL": continue
            competitors = comp["competitors"]
            home = next((c for c in competitors if c["homeAway"]=="home"), competitors[0])
            away = next((c for c in competitors if c["homeAway"]=="away"), competitors[1])
            odds_list = comp.get("odds",[])
            o = odds_list[0] if odds_list else {}
            def ml(x):
                if x is None: return None
                x=float(x)
                return round(1+x/100,2) if x>0 else round(1+100/abs(x),2)
            h = ml(o.get("homeTeamOdds",{}).get("moneyLine"))
            a = ml(o.get("awayTeamOdds",{}).get("moneyLine"))
            if h and a:
                games.append({
                    "home": home["team"]["displayName"],
                    "away": away["team"]["displayName"],
                    "h_odds": h, "a_odds": a,
                    "source": "espn"
                })
        return games
    except:
        return []


# ════════════════════════════════════════
# V1 BOT LOGIC
# ════════════════════════════════════════

STATS = {
    "Detroit Pistons":        {"elo":1720,"net":12.4,"def":107.2,"off":119.6,"vol":7.4,"h2h_h":0.72,"h2h_a":0.62},
    "Oklahoma City Thunder":  {"elo":1710,"net":13.2,"def":107.4,"off":120.6,"vol":7.2,"h2h_h":0.70,"h2h_a":0.62},
    "Boston Celtics":         {"elo":1680,"net":11.8,"def":107.8,"off":119.4,"vol":7.6,"h2h_h":0.70,"h2h_a":0.60},
    "San Antonio Spurs":      {"elo":1670,"net":10.8,"def":108.4,"off":118.2,"vol":7.8,"h2h_h":0.68,"h2h_a":0.58},
    "Los Angeles Lakers":     {"elo":1630,"net":8.6, "def":109.8,"off":117.4,"vol":8.4,"h2h_h":0.64,"h2h_a":0.54},
    "Minnesota Timberwolves": {"elo":1600,"net":7.4, "def":110.4,"off":116.2,"vol":8.6,"h2h_h":0.62,"h2h_a":0.52},
    "New York Knicks":        {"elo":1640,"net":7.2, "def":110.2,"off":116.8,"vol":8.8,"h2h_h":0.62,"h2h_a":0.54},
    "Cleveland Cavaliers":    {"elo":1620,"net":9.4, "def":109.2,"off":118.2,"vol":8.2,"h2h_h":0.64,"h2h_a":0.54},
    "Houston Rockets":        {"elo":1580,"net":6.8, "def":110.8,"off":116.0,"vol":8.8,"h2h_h":0.60,"h2h_a":0.50},
    "Denver Nuggets":         {"elo":1560,"net":5.4, "def":111.2,"off":115.4,"vol":9.0,"h2h_h":0.58,"h2h_a":0.48},
    "Toronto Raptors":        {"elo":1560,"net":4.8, "def":111.8,"off":114.6,"vol":9.2,"h2h_h":0.55,"h2h_a":0.46},
    "Atlanta Hawks":          {"elo":1540,"net":3.2, "def":112.4,"off":113.8,"vol":9.4,"h2h_h":0.54,"h2h_a":0.44},
    "Sacramento Kings":       {"elo":1490,"net":1.2, "def":113.8,"off":113.4,"vol":9.6,"h2h_h":0.50,"h2h_a":0.42},
    "Dallas Mavericks":       {"elo":1520,"net":3.8, "def":112.6,"off":114.2,"vol":9.2,"h2h_h":0.54,"h2h_a":0.44},
    "Indiana Pacers":         {"elo":1490,"net":1.6, "def":113.6,"off":115.2,"vol":9.8,"h2h_h":0.50,"h2h_a":0.42},
    "Philadelphia 76ers":     {"elo":1500,"net":1.4, "def":113.4,"off":113.2,"vol":10.2,"h2h_h":0.50,"h2h_a":0.40},
    "Miami Heat":             {"elo":1510,"net":2.8, "def":112.6,"off":113.2,"vol":9.6,"h2h_h":0.52,"h2h_a":0.42},
    "Phoenix Suns":           {"elo":1480,"net":-1.2,"def":114.6,"off":111.8,"vol":11.0,"h2h_h":0.44,"h2h_a":0.36},
    "LA Clippers":            {"elo":1470,"net":-1.8,"def":114.8,"off":111.4,"vol":11.2,"h2h_h":0.43,"h2h_a":0.35},
    "Portland Trail Blazers": {"elo":1450,"net":-2.4,"def":115.2,"off":110.8,"vol":10.4,"h2h_h":0.42,"h2h_a":0.34},
    "Golden State Warriors":  {"elo":1440,"net":-2.8,"def":115.4,"off":110.6,"vol":10.6,"h2h_h":0.41,"h2h_a":0.33},
    "Charlotte Hornets":      {"elo":1480,"net":0.8, "def":114.2,"off":113.6,"vol":10.8,"h2h_h":0.48,"h2h_a":0.38},
    "Orlando Magic":          {"elo":1460,"net":-0.8,"def":112.8,"off":111.2,"vol":9.2,"h2h_h":0.46,"h2h_a":0.38},
    "New Orleans Pelicans":   {"elo":1430,"net":-0.4,"def":113.6,"off":112.8,"vol":9.8,"h2h_h":0.46,"h2h_a":0.38},
    "Milwaukee Bucks":        {"elo":1420,"net":-3.2,"def":115.8,"off":110.6,"vol":11.2,"h2h_h":0.42,"h2h_a":0.34},
    "Chicago Bulls":          {"elo":1370,"net":-6.2,"def":116.4,"off":109.4,"vol":10.4,"h2h_h":0.40,"h2h_a":0.32},
    "Utah Jazz":              {"elo":1340,"net":-8.4,"def":118.6,"off":109.2,"vol":11.4,"h2h_h":0.36,"h2h_a":0.28},
    "Memphis Grizzlies":      {"elo":1360,"net":-4.8,"def":116.8,"off":110.4,"vol":10.8,"h2h_h":0.38,"h2h_a":0.30},
    "Brooklyn Nets":          {"elo":1380,"net":-16.2,"def":121.4,"off":103.8,"vol":13.2,"h2h_h":0.32,"h2h_a":0.26},
    "Washington Wizards":     {"elo":1280,"net":-22.4,"def":124.2,"off":100.2,"vol":15.2,"h2h_h":0.24,"h2h_a":0.18},
}

def ip(o): return 1.0/o if o>1 else 0.0
def sigmoid(x): return 1.0/(1.0+math.exp(-x))
def kelly(p,o): return max(0.0,((o-1)*p-(1-p))/(o-1)) if o>1 else 0.0
def ev_f(p,o): return p*(o-1)-(1-p)

def snap(team, is_home):
    s = STATS.get(team,{})
    if not s:
        return {"elo":1500,"net":0,"defr":112,"off":112,"vol":9,
                "h2h":0.5,"rest":3,"b2b":False,"is_home":is_home}
    return {"elo":s["elo"],"net":s["net"],"defr":s["def"],"off":s["off"],
            "vol":s["vol"],"h2h":s["h2h_h"] if is_home else s["h2h_a"],
            "rest":3,"b2b":False,"is_home":is_home}

def sharp_sig(oph, odds):
    if not oph or abs(oph-odds)<0.001:
        return {"lv":0,"bonus":0,"drop":0,"lbl":"—"}
    dr=(oph-odds)/oph; ipd=ip(odds)-ip(oph)
    if dr>=0.025 and ipd>=0.012:
        return {"lv":2,"bonus":14,"drop":round(dr,4),"lbl":"Strong"}
    if dr>=0.012 and ipd>=0.007:
        return {"lv":1,"bonus":6,"drop":round(dr,4),"lbl":"Medium"}
    return {"lv":0,"bonus":0,"drop":round(dr,4),"lbl":"—"}

def model_prob(f,d,sh):
    raw=(f["elo"]-d["elo"])*0.012+(f["net"]-d["net"])*0.165
    raw+=(f["rest"]-d["rest"])*0.62+(f["h2h"]-0.5)*100*0.022
    raw+=(d["vol"]-f["vol"])*0.175
    raw+=(3.0 if f["is_home"] else -1.2)+sh["bonus"]*0.28
    return round(sigmoid(raw/10.4),4)

def comp_score(f,d,odds,p,mp,sh,side):
    e=p-mp; s=50.0
    s+=max(-14,min(24,e*295))
    s+=max(-10,min(14,(f["elo"]-d["elo"])/14.5))
    s+=max(-12,min(14,(f["net"]-d["net"])*1.55))
    s+=sh["bonus"]
    if f["b2b"]: s-=14
    if d["b2b"]: s+=7
    rg=f["rest"]-d["rest"]
    if rg>=2: s+=4
    elif rg<=-2: s-=5
    if f["defr"]<=109: s+=8
    elif f["defr"]<=113: s+=3
    elif f["defr"]>=118: s-=7
    if f["off"]>=118: s+=4
    elif f["off"]<=108: s-=4
    if f["h2h"]>=0.70: s+=3
    elif f["h2h"]<=0.30: s-=3
    if f["vol"]>14: s-=6
    elif f["vol"]<7: s+=3
    if side=="AWAY": s-=6
    if 1.30<=odds<=1.62: s+=4
    elif odds>1.72: s-=4
    return round(max(0,min(100,s)),1)

def get_tier(sc,e):
    if sc>=76 and e>=0.028: return "A"
    if sc>=66 and e>=0.018: return "B"
    if sc>=56 and e>=0.010: return "C"
    return "-"

def get_stake(t,p,odds,bk):
    f={"A":0.25,"B":0.18,"C":0.10}.get(t,0)
    if not f: return 0.0
    return round(max(12,min(bk*0.12,bk*kelly(p,odds)*f)),2)


def analyze_games(games_override=None):
    bk = get_bankroll()

    # Odds ამოღება
    if games_override:
        games = games_override
    else:
        games = get_cached_games()
        if not games:
            games = get_nba_odds_from_api()
        if not games:
            games = get_todays_games()

    opening = get_opening_odds()
    approved = []
    log = []

    for g in games:
        home, away = g["home"], g["away"]
        h_c = g.get("h_odds")
        a_c = g.get("a_odds")
        if not h_c or not a_c: continue

        key = f"{home}|{away}"
        h_o = opening.get(key,{}).get("h", h_c)
        a_o = opening.get(key,{}).get("a", a_c)

        if h_c<=a_c:
            fav,dog,odds,opf,side,ih=home,away,h_c,h_o,"HOME",True
        else:
            fav,dog,odds,opf,side,ih=away,home,a_c,a_o,"AWAY",False

        if not(1.22<=odds<=1.82):
            log.append(f"SKIP {fav} ({odds}) range")
            continue
        if side=="AWAY" and odds<1.28:
            log.append(f"SKIP {fav} away<1.28")
            continue

        fs=snap(fav,ih); ds=snap(dog,not ih)
        sh=sharp_sig(opf,odds)
        mp=ip(odds); p=model_prob(fs,ds,sh)
        e=round(p-mp,4); ev=round(ev_f(p,odds),4)
        sc=comp_score(fs,ds,odds,p,mp,sh,side)
        t=get_tier(sc,e)

        if ev<0.003 or e<0.008 or sc<55 or t=="-":
            log.append(f"SKIP {fav} EV={ev:+.3f} sc={sc}")
            continue

        st=get_stake(t,p,odds,bk)
        if st==0: continue

        approved.append({
            "game": f"{home} vs {away}",
            "fav": fav, "dog": dog,
            "odds": odds, "open_odds": opf,
            "side": side, "tier": t,
            "score": sc, "edge": e, "ev": ev,
            "prob": p, "mp": mp,
            "stake": st, "pot": round(st*(odds-1),2),
            "sharp": sh["lv"], "sharp_label": sh["lbl"],
            "source": g.get("source","odds_api")
        })
        log.append(f"BET {fav}@{odds} T{t} ${st:.0f}")

    if approved:
        exp=sum(r["stake"] for r in approved)
        mx=bk*0.25
        if exp>mx:
            ratio=mx/exp
            for r in approved:
                r["stake"]=round(r["stake"]*ratio,2)
                r["pot"]=round(r["stake"]*(r["odds"]-1),2)

    return approved, "\n".join(log)
