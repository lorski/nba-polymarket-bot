python3 << 'SETUP'
import os

# ══════════════════════════════════════
# bot.py — სრული ვერსია
# ══════════════════════════════════════
bot_code = '''
import math, time, json, os, requests
from datetime import datetime
import sqlite3

DB = "trades.db"
PRICE_HISTORY_FILE = "/tmp/price_history.json"
ODDS_CACHE_FILE = "/tmp/odds_cache.json"
OPENING_CACHE_FILE = "/tmp/opening_odds.json"

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT, game TEXT, fav TEXT,
        odds REAL, open_odds REAL, sharp INTEGER,
        sharp_label TEXT, tier TEXT, score REAL,
        edge REAL, ev REAL, stake REAL, pot REAL,
        result TEXT DEFAULT "PENDING", pnl REAL DEFAULT 0,
        mode TEXT DEFAULT "paper", source TEXT DEFAULT "polymarket",
        reasons TEXT DEFAULT ""
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS portfolio (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT, bankroll REAL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY, value TEXT
    )""")
    c.execute("INSERT OR IGNORE INTO settings VALUES (\"bankroll\",\"1000.0\")")
    c.execute("INSERT OR IGNORE INTO settings VALUES (\"mode\",\"paper\")")
    c.execute("INSERT OR IGNORE INTO settings VALUES (\"running\",\"false\")")
    conn.commit(); conn.close()

def get_setting(key):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = c.fetchone(); conn.close()
    return row[0] if row else None

def set_setting(key, value):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO settings VALUES (?,?)", (key, str(value)))
    conn.commit(); conn.close()

def get_bankroll():
    return float(get_setting("bankroll") or 1000.0)

def save_trade(trade):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    reasons = json.dumps(trade.get("reasons", []), ensure_ascii=False)
    c.execute("""INSERT INTO trades
        (timestamp,game,fav,odds,open_odds,sharp,sharp_label,
         tier,score,edge,ev,stake,pot,mode,source,reasons)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        trade["game"], trade["fav"], trade["odds"], trade["open_odds"],
        trade["sharp"], trade["sharp_label"], trade["tier"],
        trade["score"], trade["edge"], trade["ev"],
        trade["stake"], trade["pot"],
        get_setting("mode"), trade.get("source","polymarket"), reasons
    ))
    tid = c.lastrowid; conn.commit(); conn.close()
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
                  ("WIN" if won else "LOSS", pnl, trade_id))
        bk = round(get_bankroll()+pnl, 2)
        set_setting("bankroll", bk)
        c.execute("INSERT INTO portfolio (timestamp,bankroll) VALUES (?,?)",
                  (datetime.now().strftime("%Y-%m-%d %H:%M"), bk))
        conn.commit()
    conn.close()

def get_trades(limit=50):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM trades ORDER BY id DESC LIMIT ?", (limit,))
    rows = c.fetchall(); conn.close()
    cols = ["id","timestamp","game","fav","odds","open_odds","sharp",
            "sharp_label","tier","score","edge","ev","stake","pot",
            "result","pnl","mode","source","reasons"]
    result = []
    for r in rows:
        d = dict(zip(cols, r))
        try: d["reasons"] = json.loads(d.get("reasons","[]"))
        except: d["reasons"] = []
        result.append(d)
    return result

def get_portfolio_history():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT timestamp,bankroll FROM portfolio ORDER BY id")
    rows = c.fetchall(); conn.close()
    return rows

def get_stats():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM trades WHERE result=\\"PENDING\\""); op = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM trades WHERE result!=\\"PENDING\\""); total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM trades WHERE result=\\"WIN\\""); wins = c.fetchone()[0]
    c.execute("SELECT SUM(pnl) FROM trades WHERE result!=\\"PENDING\\""); tpnl = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM trades WHERE DATE(timestamp)=DATE(\\"now\\")"); daily = c.fetchone()[0]
    c.execute("SELECT SUM(pnl) FROM trades WHERE DATE(timestamp)=DATE(\\"now\\") AND result!=\\"PENDING\\""); dpnl = c.fetchone()[0] or 0
    conn.close()
    bk = get_bankroll()
    return {"bankroll":bk,"pnl":round(tpnl,2),"daily_pnl":round(dpnl,2),
            "open_positions":op,"daily_trades":daily,"total_trades":total,
            "win_rate":round(wins/total*100,1) if total>0 else 0,
            "wins":wins,"losses":total-wins,
            "mode":get_setting("mode"),"running":get_setting("running")=="true"}

# Price History
def save_price_history(games):
    try:
        try: hist = json.load(open(PRICE_HISTORY_FILE))
        except: hist = {}
        t = datetime.now().strftime("%H:%M")
        for g in games:
            key = g["home"] + "|" + g["away"]
            if key not in hist: hist[key] = []
            hist[key].append({
                "time": t,
                "h_pct": g.get("h_cents", int(g.get("h_price",0.5)*100)),
                "a_pct": g.get("a_cents", int(g.get("a_price",0.5)*100)),
                "home": g["home"], "away": g["away"]
            })
            if len(hist[key]) > 100: hist[key] = hist[key][-100:]
        with open(PRICE_HISTORY_FILE,"w") as f: json.dump(hist, f)
    except Exception as e: print(f"[HIST] {e}")

def get_price_history():
    try: return json.load(open(PRICE_HISTORY_FILE))
    except: return {}

def reset_opening_odds():
    if os.path.exists(OPENING_CACHE_FILE): os.remove(OPENING_CACHE_FILE)

def get_opening_odds():
    if not os.path.exists(OPENING_CACHE_FILE): return {}
    try:
        d = json.load(open(OPENING_CACHE_FILE))
        hours = (datetime.now()-datetime.fromisoformat(d["time"])).total_seconds()/3600
        if hours > 24: os.remove(OPENING_CACHE_FILE); return {}
        return d["odds"]
    except: return {}

def save_opening_odds(games):
    if os.path.exists(OPENING_CACHE_FILE): return
    data = {}
    for g in games:
        key = g["home"]+"|"+g["away"]
        data[key] = {"h": g.get("h_odds"), "a": g.get("a_odds")}
    with open(OPENING_CACHE_FILE,"w") as f:
        json.dump({"time": datetime.now().isoformat(), "odds": data}, f)

def get_cached_games():
    if not os.path.exists(ODDS_CACHE_FILE): return []
    try:
        d = json.load(open(ODDS_CACHE_FILE))
        mins = (datetime.now()-datetime.fromisoformat(d["time"])).total_seconds()/60
        return d["games"] if mins < 30 else []
    except: return []

def get_todays_games():
    today = datetime.now().strftime("%Y%m%d")
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={today}"
    try:
        r = requests.get(url, timeout=10)
        games = []
        for event in r.json().get("events",[]):
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
                games.append({"home":home["team"]["displayName"],
                             "away":away["team"]["displayName"],
                             "h_odds":h,"a_odds":a,"source":"espn"})
        return games
    except: return []

# V1 Bot Logic
STATS = {
    "Detroit Pistons":        {"elo":1720,"net":12.4,"def":107.2,"off":119.6,"vol":7.4,"h2h_h":0.72,"h2h_a":0.62},
    "Oklahoma City Thunder":  {"elo":1710,"net":13.2,"def":107.4,"off":120.6,"vol":7.2,"h2h_h":0.70,"h2h_a":0.62},
    "Boston Celtics":         {"elo":1680,"net":11.8,"def":107.8,"off":119.4,"vol":7.6,"h2h_h":0.70,"h2h_a":0.60},
    "Cleveland Cavaliers":    {"elo":1620,"net":9.4, "def":109.2,"off":118.2,"vol":8.2,"h2h_h":0.64,"h2h_a":0.54},
    "Los Angeles Lakers":     {"elo":1630,"net":8.6, "def":109.8,"off":117.4,"vol":8.4,"h2h_h":0.64,"h2h_a":0.54},
    "New York Knicks":        {"elo":1640,"net":7.2, "def":110.2,"off":116.8,"vol":8.8,"h2h_h":0.62,"h2h_a":0.54},
    "Minnesota Timberwolves": {"elo":1600,"net":7.4, "def":110.4,"off":116.2,"vol":8.6,"h2h_h":0.62,"h2h_a":0.52},
    "Houston Rockets":        {"elo":1580,"net":6.8, "def":110.8,"off":116.0,"vol":8.8,"h2h_h":0.60,"h2h_a":0.50},
    "Denver Nuggets":         {"elo":1560,"net":5.4, "def":111.2,"off":115.4,"vol":9.0,"h2h_h":0.58,"h2h_a":0.48},
    "Toronto Raptors":        {"elo":1560,"net":4.8, "def":111.8,"off":114.6,"vol":9.2,"h2h_h":0.55,"h2h_a":0.46},
    "Atlanta Hawks":          {"elo":1540,"net":3.2, "def":112.4,"off":113.8,"vol":9.4,"h2h_h":0.54,"h2h_a":0.44},
    "Dallas Mavericks":       {"elo":1520,"net":3.8, "def":112.6,"off":114.2,"vol":9.2,"h2h_h":0.54,"h2h_a":0.44},
    "Miami Heat":             {"elo":1510,"net":2.8, "def":112.6,"off":113.2,"vol":9.6,"h2h_h":0.52,"h2h_a":0.42},
    "Philadelphia 76ers":     {"elo":1500,"net":1.4, "def":113.4,"off":113.2,"vol":10.2,"h2h_h":0.50,"h2h_a":0.40},
    "Indiana Pacers":         {"elo":1490,"net":1.6, "def":113.6,"off":115.2,"vol":9.8,"h2h_h":0.50,"h2h_a":0.42},
    "Sacramento Kings":       {"elo":1490,"net":1.2, "def":113.8,"off":113.4,"vol":9.6,"h2h_h":0.50,"h2h_a":0.42},
    "Charlotte Hornets":      {"elo":1480,"net":0.8, "def":114.2,"off":113.6,"vol":10.8,"h2h_h":0.48,"h2h_a":0.38},
    "Phoenix Suns":           {"elo":1480,"net":-1.2,"def":114.6,"off":111.8,"vol":11.0,"h2h_h":0.44,"h2h_a":0.36},
    "Orlando Magic":          {"elo":1460,"net":-0.8,"def":112.8,"off":111.2,"vol":9.2,"h2h_h":0.46,"h2h_a":0.38},
    "LA Clippers":            {"elo":1470,"net":-1.8,"def":114.8,"off":111.4,"vol":11.2,"h2h_h":0.43,"h2h_a":0.35},
    "Portland Trail Blazers": {"elo":1450,"net":-2.4,"def":115.2,"off":110.8,"vol":10.4,"h2h_h":0.42,"h2h_a":0.34},
    "Golden State Warriors":  {"elo":1440,"net":-2.8,"def":115.4,"off":110.6,"vol":10.6,"h2h_h":0.41,"h2h_a":0.33},
    "New Orleans Pelicans":   {"elo":1430,"net":-0.4,"def":113.6,"off":112.8,"vol":9.8,"h2h_h":0.46,"h2h_a":0.38},
    "Milwaukee Bucks":        {"elo":1420,"net":-3.2,"def":115.8,"off":110.6,"vol":11.2,"h2h_h":0.42,"h2h_a":0.34},
    "Chicago Bulls":          {"elo":1370,"net":-6.2,"def":116.4,"off":109.4,"vol":10.4,"h2h_h":0.40,"h2h_a":0.32},
    "Memphis Grizzlies":      {"elo":1360,"net":-4.8,"def":116.8,"off":110.4,"vol":10.8,"h2h_h":0.38,"h2h_a":0.30},
    "Brooklyn Nets":          {"elo":1380,"net":-16.2,"def":121.4,"off":103.8,"vol":13.2,"h2h_h":0.32,"h2h_a":0.26},
    "Utah Jazz":              {"elo":1340,"net":-8.4,"def":118.6,"off":109.2,"vol":11.4,"h2h_h":0.36,"h2h_a":0.28},
    "Washington Wizards":     {"elo":1280,"net":-22.4,"def":124.2,"off":100.2,"vol":15.2,"h2h_h":0.24,"h2h_a":0.18},
    "San Antonio Spurs":      {"elo":1670,"net":10.8,"def":108.4,"off":118.2,"vol":7.8,"h2h_h":0.68,"h2h_a":0.58},
}

def ip(o): return 1.0/o if o>1 else 0.0
def sigmoid(x): return 1.0/(1.0+math.exp(-x))
def kelly(p,o): return max(0.0,((o-1)*p-(1-p))/(o-1)) if o>1 else 0.0
def ev_f(p,o): return p*(o-1)-(1-p)

def snap(team, is_home):
    s = STATS.get(team,{})
    if not s: return {"elo":1500,"net":0,"defr":112,"off":112,"vol":9,"h2h":0.5,"rest":3,"b2b":False,"is_home":is_home}
    return {"elo":s["elo"],"net":s["net"],"defr":s["def"],"off":s["off"],
            "vol":s["vol"],"h2h":s["h2h_h"] if is_home else s["h2h_a"],
            "rest":3,"b2b":False,"is_home":is_home}

def sharp_sig(oph, odds):
    if not oph or abs(oph-odds)<0.001:
        return {"lv":0,"bonus":0,"drop":0,"lbl":"—"}
    dr=(oph-odds)/oph; ipd=ip(odds)-ip(oph)
    if dr>=0.025 and ipd>=0.012: return {"lv":2,"bonus":14,"drop":round(dr,4),"lbl":"Strong"}
    if dr>=0.012 and ipd>=0.007: return {"lv":1,"bonus":6,"drop":round(dr,4),"lbl":"Medium"}
    return {"lv":0,"bonus":0,"drop":round(dr,4),"lbl":"—"}

def model_prob(f,d,sh):
    raw=(f["elo"]-d["elo"])*0.012+(f["net"]-d["net"])*0.165
    raw+=(f["rest"]-d["rest"])*0.62+(f["h2h"]-0.5)*100*0.022
    raw+=(d["vol"]-f["vol"])*0.175+(3.0 if f["is_home"] else -1.2)+sh["bonus"]*0.28
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

def analyze_games_with_reason(games_override=None):
    bk = get_bankroll()
    games = games_override or get_cached_games() or get_todays_games()
    opening = get_opening_odds()
    if games: save_opening_odds(games)
    approved = []
    skipped = []

    for g in games:
        home,away = g["home"],g["away"]
        h_c = g.get("h_odds"); a_c = g.get("a_odds")
        if not h_c or not a_c: continue
        key = home+"|"+away
        h_o = opening.get(key,{}).get("h", h_c)
        a_o = opening.get(key,{}).get("a", a_c)
        if h_c<=a_c: fav,dog,odds,opf,side,ih=home,away,h_c,h_o,"HOME",True
        else: fav,dog,odds,opf,side,ih=away,home,a_c,a_o,"AWAY",False

        fs=snap(fav,ih); ds=snap(dog,not ih)
        sh=sharp_sig(opf,odds)
        mp=ip(odds); p=model_prob(fs,ds,sh)
        e=round(p-mp,4); ev=round(ev_f(p,odds),4)
        sc=comp_score(fs,ds,odds,p,mp,sh,side)
        t=get_tier(sc,e)

        skip_reasons=[]
        bet_reasons=[]

        if not(1.22<=odds<=1.82): skip_reasons.append(f"კოეფი {odds} არ არის 1.22-1.82 შუალედში")
        if side=="AWAY" and odds<1.28: skip_reasons.append(f"სტუმარი {fav} @ {odds} < 1.28")
        if ev<0.003: skip_reasons.append(f"EV {ev:+.3f} — ძალიან დაბალი (მინ. 0.003)")
        if e<0.008: skip_reasons.append(f"Edge {e:+.1%} — ძალიან პატარა (მინ. 0.8%)")
        if sc<55: skip_reasons.append(f"Score {sc}/100 — ნიშნულს ვერ აღწევს (მინ. 55)")
        if t=="-": skip_reasons.append("Tier ვერ მიენიჭა — edge/score ძალიან დაბალია")

        elo_gap = fs["elo"]-ds["elo"]
        if elo_gap>50: bet_reasons.append(f"ELO უპირატესობა +{elo_gap:.0f} ქულა")
        if sh["lv"]==2: bet_reasons.append(f"🔥 Strong Sharp — კოეფი {sh['drop']:.1%} დაეცა (მსხვილი ფული)")
        elif sh["lv"]==1: bet_reasons.append(f"🟡 Medium Sharp — კოეფი {sh['drop']:.1%} დაეცა")
        net_gap = fs["net"]-ds["net"]
        if net_gap>3: bet_reasons.append(f"Net Rating +{net_gap:.1f} (ბოლო 10 თამაში)")
        if fs["defr"]<=109: bet_reasons.append(f"ელიტა დაცვა {fs['defr']:.1f} — Top 5 NBA")
        if e>0.015: bet_reasons.append(f"Edge {e:+.1%} — ძლიერი უპირატესობა ბაზარზე")
        bet_reasons.append(f"მოდელი: {p:.1%} vs ბაზარი: {mp:.1%} (+{e:.1%} edge)")
        if t=="A": bet_reasons.append(f"Tier A — ყველაზე ძლიერი სიგნალი (Score {sc})")
        elif t=="B": bet_reasons.append(f"Tier B — ძლიერი სიგნალი (Score {sc})")
        elif t=="C": bet_reasons.append(f"Tier C — საშუალო სიგნალი (Score {sc})")

        if skip_reasons:
            skipped.append({"game":home+" vs "+away,"fav":fav,"odds":odds,
                           "score":sc,"ev":ev,"edge":e,"reasons":skip_reasons})
            continue

        st=get_stake(t,p,odds,bk)
        if st==0: continue

        approved.append({
            "game":home+" vs "+away,"fav":fav,"dog":dog,
            "odds":odds,"open_odds":opf,"side":side,"tier":t,
            "score":sc,"edge":e,"ev":ev,"prob":p,"mp":mp,
            "stake":st,"pot":round(st*(odds-1),2),
            "sharp":sh["lv"],"sharp_label":sh["lbl"],
            "source":g.get("source","polymarket"),
            "reasons":bet_reasons
        })

    if approved:
        exp=sum(r["stake"] for r in approved); mx=bk*0.25
        if exp>mx:
            ratio=mx/exp
            for r in approved:
                r["stake"]=round(r["stake"]*ratio,2)
                r["pot"]=round(r["stake"]*(r["odds"]-1),2)

    return approved, skipped

def analyze_games(games_override=None):
    r,_ = analyze_games_with_reason(games_override)
    return r, ""
'''

# ══════════════════════════════════════
# polymarket_scraper.py
# ══════════════════════════════════════
scraper_code = '''
import json, time, re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from datetime import datetime

CACHE_FILE = "/tmp/polymarket_odds.json"

TEAMS = {
    "76ers":"Philadelphia 76ers","heat":"Miami Heat","celtics":"Boston Celtics",
    "hawks":"Atlanta Hawks","bulls":"Chicago Bulls","spurs":"San Antonio Spurs",
    "suns":"Phoenix Suns","grizzlies":"Memphis Grizzlies",
    "timberwolves":"Minnesota Timberwolves","mavericks":"Dallas Mavericks",
    "lakers":"Los Angeles Lakers","warriors":"Golden State Warriors",
    "knicks":"New York Knicks","nets":"Brooklyn Nets",
    "cavaliers":"Cleveland Cavaliers","bucks":"Milwaukee Bucks",
    "nuggets":"Denver Nuggets","clippers":"LA Clippers",
    "rockets":"Houston Rockets","jazz":"Utah Jazz",
    "thunder":"Oklahoma City Thunder","blazers":"Portland Trail Blazers",
    "kings":"Sacramento Kings","hornets":"Charlotte Hornets",
    "pistons":"Detroit Pistons","pacers":"Indiana Pacers",
    "raptors":"Toronto Raptors","pelicans":"New Orleans Pelicans",
    "wizards":"Washington Wizards","magic":"Orlando Magic",
}

def find_team(text):
    t = text.lower().strip()
    for key, name in TEAMS.items():
        if key in t: return name
    return None

def scrape_polymarket():
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.binary_location = "/usr/bin/chromium"
    driver = webdriver.Chrome(options=opts)
    games = []
    try:
        driver.get("https://polymarket.com/sports/nba/games")
        time.sleep(10)
        body = driver.find_element(By.TAG_NAME, "body").text
        lines = [l.strip() for l in body.split("\\n") if l.strip()]
        cents_p = re.compile(r"^([A-Z]{2,4})?(\\d+)¢$")
        i = 0
        while i < len(lines):
            m = cents_p.match(lines[i])
            if m:
                c1 = int(m.group(2))
                if i+1 < len(lines):
                    m2 = cents_p.match(lines[i+1])
                    if m2:
                        c2 = int(m2.group(2))
                        ctx = lines[max(0,i-8):i]
                        teams = []
                        for l in ctx:
                            t = find_team(l)
                            if t and t not in teams: teams.append(t)
                        if len(teams)>=2 and 1<c1<99:
                            p1=c1/100; p2=c2/100
                            games.append({
                                "home":teams[0],"away":teams[1],
                                "h_price":round(p1,3),"a_price":round(p2,3),
                                "h_odds":round(1/p1,2),"a_odds":round(1/p2,2),
                                "h_cents":c1,"a_cents":c2,
                                "source":"polymarket",
                                "updated":datetime.now().strftime("%H:%M:%S")
                            })
                        i+=2; continue
            i+=1
        seen=set(); unique=[]
        for g in games:
            key=tuple(sorted([g["home"],g["away"]]))
            if key not in seen: seen.add(key); unique.append(g)
        with open(CACHE_FILE,"w") as f:
            json.dump({"time":datetime.now().isoformat(),"games":unique},f)
        print(f"[PM] {len(unique)} games")
        for g in unique:
            print(f"  {g[\'home\']} {g[\'h_cents\']}¢ vs {g[\'away\']} {g[\'a_cents\']}¢  ({g[\'h_odds\']}x/{g[\'a_odds\']}x)")
        return unique
    except Exception as e:
        print(f"[PM] Error: {e}"); return []
    finally:
        driver.quit()

def get_cached():
    try:
        d = json.load(open(CACHE_FILE))
        mins = (datetime.now()-datetime.fromisoformat(d["time"])).total_seconds()/60
        return d["games"] if mins < 25 else []
    except: return []
'''

# ══════════════════════════════════════
# dashboard.py
# ══════════════════════════════════════
dashboard_code = '''
import bot, polymarket_scraper, threading, time
import dash
from dash import dcc, html, Input, Output, callback_context
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from datetime import datetime

bot.init_db()

def bg():
    while True:
        try:
            games = polymarket_scraper.scrape_polymarket()
            if games: bot.save_price_history(games)
        except Exception as e: print(f"[BG] {e}")
        time.sleep(60)

threading.Thread(target=bg, daemon=True).start()

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CYBORG],
    title="NBA Polymarket Agent", suppress_callback_exceptions=True)
server = app.server

C = {"bg":"#080c18","card":"#0d1425","card2":"#0a1020","border":"#1a2840",
     "green":"#00e5a0","red":"#ff3d5a","blue":"#4facfe","yellow":"#ffd32a",
     "text":"#e8f4ff","muted":"#4a6080","orange":"#ff6b35","purple":"#9b59b6"}

def mk(title, vid, sub=""):
    return html.Div([
        html.P(title,style={"color":C["muted"],"fontSize":"9px","fontWeight":"700","letterSpacing":"1.5px","marginBottom":"6px","textTransform":"uppercase"}),
        html.H2("—",id=vid,style={"color":C["text"],"fontWeight":"800","fontSize":"22px","marginBottom":"2px","fontFamily":"monospace"}),
        html.P(sub,style={"color":C["muted"],"fontSize":"9px","marginBottom":"0"}),
    ],style={"background":C["card"],"border":f"1px solid {C[\'border\']}","borderRadius":"12px","padding":"14px 16px"})

app.layout = html.Div([
    # Header
    html.Div([
        html.Div([
            html.Span("◉ ",id="dot",style={"color":C["green"],"fontSize":"14px"}),
            html.Span("NBA",style={"color":C["text"],"fontWeight":"900","fontSize":"20px","letterSpacing":"3px"}),
            html.Span(" POLYMARKET",style={"color":C["blue"],"fontWeight":"900","fontSize":"20px","letterSpacing":"3px"}),
            html.Span(" AGENT",style={"color":C["muted"],"fontSize":"14px"}),
            html.Span("PAPER",id="mbadge",style={"background":C["yellow"],"color":"#000","padding":"2px 10px","borderRadius":"20px","fontSize":"9px","fontWeight":"900","marginLeft":"14px","letterSpacing":"2px"}),
        ],style={"display":"flex","alignItems":"center","flex":"1","gap":"4px"}),
        html.Div([
            html.Span("⬤ AUTO-REFRESH",style={"color":C["green"],"fontSize":"10px","fontWeight":"700","marginRight":"16px"}),
            html.Span(id="rtime",style={"color":C["muted"],"fontSize":"11px","fontFamily":"monospace"}),
        ],style={"display":"flex","alignItems":"center"}),
    ],style={"display":"flex","justifyContent":"space-between","alignItems":"center","padding":"14px 28px","borderBottom":f"1px solid {C[\'border\']}","background":C["card"]}),

    html.Div([
        # Stats Row
        html.Div([mk("BANKROLL","s-bk","total"),mk("DAILY P&L","s-dp","today"),
                  mk("TOTAL P&L","s-tp","all time"),mk("OPEN","s-op","positions"),
                  mk("WIN RATE","s-wr","completed"),mk("TODAY","s-td","trades")],
            style={"display":"grid","gridTemplateColumns":"repeat(6,1fr)","gap":"10px","marginBottom":"14px"}),

        # Controls
        html.Div([
            html.Div([
                html.Button("▶ RUN",id="btn-run",style={"background":C["green"],"color":"#000","border":"none","padding":"9px 20px","borderRadius":"8px","fontSize":"11px","fontWeight":"900","cursor":"pointer","marginRight":"8px"}),
                html.Button("⟳ REFRESH",id="btn-ref",style={"background":"transparent","color":C["blue"],"border":f"1px solid {C[\'blue\']}","padding":"9px 16px","borderRadius":"8px","fontSize":"11px","cursor":"pointer","marginRight":"8px"}),
                html.Button("↺ RESET",id="btn-rst",style={"background":"transparent","color":C["muted"],"border":f"1px solid {C[\'border\']}","padding":"9px 16px","borderRadius":"8px","fontSize":"11px","cursor":"pointer"}),
            ]),
            html.Div([
                html.Span("PAPER",style={"color":C["muted"],"fontSize":"10px","marginRight":"8px","fontWeight":"700"}),
                dbc.Switch(id="msw",value=False),
                html.Span("LIVE",style={"color":C["muted"],"fontSize":"10px","marginLeft":"8px","fontWeight":"700"}),
            ],style={"display":"flex","alignItems":"center"}),
        ],style={"display":"flex","justifyContent":"space-between","alignItems":"center","marginBottom":"14px"}),

        html.Div([
            # LEFT COLUMN
            html.Div([
                # Polymarket Live Odds
                html.Div([
                    html.Div([
                        html.Div([html.Span("⬤ ",style={"color":C["green"],"fontSize":"8px"}),
                                  html.Span("POLYMARKET LIVE",style={"fontWeight":"700","fontSize":"11px","letterSpacing":"1.5px"})]),
                        html.Span(id="pm-cnt",style={"background":C["blue"],"color":"#000","padding":"2px 10px","borderRadius":"10px","fontSize":"9px","fontWeight":"900"}),
                    ],style={"display":"flex","justifyContent":"space-between","alignItems":"center","padding":"12px 16px","borderBottom":f"1px solid {C[\'border\']}"}),
                    html.Div(id="pm-list",style={"maxHeight":"250px","overflowY":"auto"}),
                ],style={"background":C["card"],"border":f"1px solid {C[\'border\']}","borderRadius":"12px","marginBottom":"12px"}),

                # Polymarket Charts
                html.Div([
                    html.Div([html.Span("PROBABILITY CHARTS",style={"fontWeight":"700","fontSize":"11px","letterSpacing":"1.5px"})],
                             style={"padding":"12px 16px","borderBottom":f"1px solid {C[\'border\']}"}),
                    html.Div(id="pm-charts",style={"padding":"8px"}),
                ],style={"background":C["card"],"border":f"1px solid {C[\'border\']}","borderRadius":"12px","marginBottom":"12px"}),

                # Bot Analysis
                html.Div([
                    html.Div([
                        html.Div([html.Span("✦ ",style={"color":C["yellow"],"fontSize":"12px"}),
                                  html.Span("BOT ANALYSIS",style={"fontWeight":"700","fontSize":"11px","letterSpacing":"1.5px"})]),
                        html.Span(id="rec-cnt",style={"background":C["green"],"color":"#000","padding":"2px 10px","borderRadius":"10px","fontSize":"9px","fontWeight":"900"}),
                    ],style={"display":"flex","justifyContent":"space-between","alignItems":"center","padding":"12px 16px","borderBottom":f"1px solid {C[\'border\']}"}),
                    html.Div(id="rec-list"),
                ],style={"background":C["card"],"border":f"1px solid {C[\'border\']}","borderRadius":"12px","marginBottom":"12px"}),

                # Open Positions
                html.Div([
                    html.Div([
                        html.Span("OPEN POSITIONS",style={"fontWeight":"700","fontSize":"11px","letterSpacing":"1.5px"}),
                        html.Span(id="op-cnt",style={"background":C["orange"],"color":"#fff","padding":"2px 10px","borderRadius":"10px","fontSize":"9px","fontWeight":"900"}),
                    ],style={"display":"flex","justifyContent":"space-between","alignItems":"center","padding":"12px 16px","borderBottom":f"1px solid {C[\'border\']}"}),
                    html.Div(id="op-list"),
                ],style={"background":C["card"],"border":f"1px solid {C[\'border\']}","borderRadius":"12px"}),
            ],style={"flex":"1","marginRight":"12px"}),

            # RIGHT COLUMN
            html.Div([
                html.Div([
                    html.Div([
                        html.Span("RECENT TRADES",style={"fontWeight":"700","fontSize":"11px","letterSpacing":"1.5px"}),
                        html.Span(id="tr-cnt",style={"background":C["muted"],"color":"#fff","padding":"2px 10px","borderRadius":"10px","fontSize":"9px","fontWeight":"900"}),
                    ],style={"display":"flex","justifyContent":"space-between","alignItems":"center","padding":"12px 16px","borderBottom":f"1px solid {C[\'border\']}"}),
                    html.Div(id="tr-list",style={"maxHeight":"300px","overflowY":"auto"}),
                ],style={"background":C["card"],"border":f"1px solid {C[\'border\']}","borderRadius":"12px","marginBottom":"12px"}),

                html.Div([
                    html.Div("STATISTICS",style={"padding":"12px 16px","fontWeight":"700","fontSize":"11px","letterSpacing":"1.5px","borderBottom":f"1px solid {C[\'border\']}"}),
                    html.Div(id="stats",style={"padding":"14px 16px"}),
                ],style={"background":C["card"],"border":f"1px solid {C[\'border\']}","borderRadius":"12px","marginBottom":"12px"}),

                html.Div([
                    html.Div("PORTFOLIO GROWTH",style={"padding":"12px 16px","fontWeight":"700","fontSize":"11px","letterSpacing":"1.5px","borderBottom":f"1px solid {C[\'border\']}"}),
                    dcc.Graph(id="port-chart",style={"height":"160px"},config={"displayModeBar":False}),
                ],style={"background":C["card"],"border":f"1px solid {C[\'border\']}","borderRadius":"12px"}),
            ],style={"width":"380px"}),
        ],style={"display":"flex"}),
    ],style={"padding":"16px 28px","background":C["bg"],"minHeight":"calc(100vh - 54px)"}),

    dcc.Interval(id="iv",interval=10*1000,n_intervals=0),
],style={"background":C["bg"],"fontFamily":"-apple-system,BlinkMacSystemFont,\'Segoe UI\',sans-serif","color":C["text"]})


@app.callback(
    [Output("s-bk","children"),Output("s-dp","children"),Output("s-tp","children"),
     Output("s-op","children"),Output("s-wr","children"),Output("s-td","children"),
     Output("pm-list","children"),Output("pm-cnt","children"),
     Output("pm-charts","children"),
     Output("rec-list","children"),Output("rec-cnt","children"),
     Output("op-list","children"),Output("op-cnt","children"),
     Output("tr-list","children"),Output("tr-cnt","children"),
     Output("port-chart","figure"),Output("stats","children"),
     Output("rtime","children"),Output("mbadge","children"),Output("mbadge","style"),Output("dot","style")],
    [Input("iv","n_intervals"),Input("btn-ref","n_clicks"),
     Input("btn-run","n_clicks"),Input("btn-rst","n_clicks"),Input("msw","value")],
    prevent_initial_call=False
)
def upd(n,ref,run,rst,live):
    ctx = callback_context
    trig = ctx.triggered[0]["prop_id"] if ctx.triggered else ""
    if "msw" in trig: bot.set_setting("mode","live" if live else "paper")
    if "btn-rst" in trig: bot.reset_opening_odds()
    if "btn-ref" in trig:
        def do_ref():
            games = polymarket_scraper.scrape_polymarket()
            if games: bot.save_price_history(games)
        threading.Thread(target=do_ref,daemon=True).start()
    if "btn-run" in trig:
        bot.set_setting("running","true")
        pm = polymarket_scraper.get_cached()
        results,_ = bot.analyze_games_with_reason(pm if pm else None)
        for r in results:
            ex=[t for t in bot.get_trades(50) if t["game"]==r["game"] and t["result"]=="PENDING"]
            if not ex: bot.save_trade(r)

    st = bot.get_stats()
    trades = bot.get_trades(100)
    hist_data = bot.get_portfolio_history()
    bk = st["bankroll"]
    pm = polymarket_scraper.get_cached()
    _,skipped = bot.analyze_games_with_reason(pm if pm else None)

    def ps(v):
        c=C["green"] if v>=0 else C["red"]
        return html.Span(f"${v:+.2f}",style={"color":c,"fontFamily":"monospace","fontSize":"22px","fontWeight":"800"})

    # Polymarket Live Odds
    if pm:
        pm_els=[]
        for g in pm:
            hc=g.get("h_cents",0); ac=g.get("a_cents",0)
            ho=g.get("h_odds",0); ao=g.get("a_odds",0)
            fh=ho<=ao; fo=min(ho,ao); ir=1.22<=fo<=1.82
            pm_els.append(html.Div([
                html.Div([
                    html.Span(g["home"][:16],style={"fontWeight":"800" if fh else "400","fontSize":"13px","color":C["green"] if fh else C["text"]}),
                    html.Span(" vs ",style={"color":C["muted"],"fontSize":"11px","margin":"0 8px"}),
                    html.Span(g["away"][:16],style={"fontWeight":"800" if not fh else "400","fontSize":"13px","color":C["green"] if not fh else C["text"]}),
                ]),
                html.Div([
                    html.Span(f"{hc}¢",style={"fontFamily":"monospace","fontSize":"16px","fontWeight":"900","color":C["green"] if fh else C["muted"],"marginRight":"2px"}),
                    html.Span(f"({ho}x)",style={"fontSize":"9px","color":C["muted"],"marginRight":"10px"}),
                    html.Span(f"{ac}¢",style={"fontFamily":"monospace","fontSize":"16px","fontWeight":"900","color":C["green"] if not fh else C["muted"],"marginRight":"2px"}),
                    html.Span(f"({ao}x)",style={"fontSize":"9px","color":C["muted"],"marginRight":"8px"}),
                    html.Span("✓" if ir else "✗",style={"color":C["green"] if ir else C["red"],"fontSize":"12px"}),
                ]),
            ],style={"display":"flex","justifyContent":"space-between","alignItems":"center","padding":"10px 16px","borderBottom":f"1px solid {C[\'border\']}"}))
        pm_list=pm_els; pm_cnt=str(len(pm))
    else:
        pm_list=[html.P("⟳ Polymarket-ს უკავშირდება...",style={"color":C["muted"],"textAlign":"center","padding":"20px","fontSize":"12px"})]
        pm_cnt="0"

    # Probability Charts (Polymarket style)
    ph = bot.get_price_history()
    if ph and len(ph)>0:
        charts=[]
        for key,data in list(ph.items())[:6]:
            if len(data)<2: continue
            teams=key.split("|")
            home=teams[0] if len(teams)>0 else "?"
            away=teams[1] if len(teams)>1 else "?"
            times=[d["time"] for d in data]
            hv=[d["h_pct"] for d in data]
            av=[d["a_pct"] for d in data]
            lh=hv[-1]; la=av[-1]
            ph2=hv[-2] if len(hv)>1 else lh
            hcol=C["green"] if lh>=ph2 else C["red"]
            fig=go.Figure()
            # Home team line
            fig.add_trace(go.Scatter(
                x=times, y=hv, name=home.split()[-1][:8],
                mode="lines",
                line=dict(color=C["green"],width=2.5),
                fill="tozeroy",
                fillcolor="rgba(0,229,160,0.06)"
            ))
            # Away team line
            fig.add_trace(go.Scatter(
                x=times, y=av, name=away.split()[-1][:8],
                mode="lines",
                line=dict(color=C["blue"],width=2.5)
            ))
            # Last value annotations
            fig.add_annotation(x=times[-1],y=lh,text=f"{lh}%",
                showarrow=False,xanchor="left",font=dict(color=hcol,size=11,family="monospace"),
                xshift=5)
            fig.add_annotation(x=times[-1],y=la,text=f"{la}%",
                showarrow=False,xanchor="left",font=dict(color=C["blue"],size=11,family="monospace"),
                xshift=5)
            fig.update_layout(
                plot_bgcolor=C["card2"],paper_bgcolor=C["card2"],
                font=dict(color=C["text"],size=9),
                margin=dict(l=30,r=50,t=5,b=25),height=130,
                xaxis=dict(gridcolor=C["border"],showgrid=True,zeroline=False,
                          tickfont=dict(size=8),showticklabels=True),
                yaxis=dict(gridcolor=C["border"],showgrid=True,zeroline=False,
                          ticksuffix="%",tickfont=dict(size=8),range=[0,100]),
                legend=dict(font=dict(size=9),bgcolor="rgba(0,0,0,0)",
                           x=0,y=1.1,orientation="h"),
            )
            # Change indicator
            change = lh - ph2
            change_color = C["green"] if change>=0 else C["red"]
            change_sym = "▲" if change>=0 else "▼"
            charts.append(html.Div([
                html.Div([
                    html.Div([
                        html.Span(home.split()[-1][:10],style={"fontWeight":"800","fontSize":"13px","color":C["green"]}),
                        html.Span(" vs ",style={"color":C["muted"],"fontSize":"10px","margin":"0 6px"}),
                        html.Span(away.split()[-1][:10],style={"fontWeight":"800","fontSize":"13px","color":C["blue"]}),
                    ]),
                    html.Div([
                        html.Span(f"{lh}%",style={"fontFamily":"monospace","fontSize":"16px","fontWeight":"900","color":hcol,"marginRight":"6px"}),
                        html.Span(f"{la}%",style={"fontFamily":"monospace","fontSize":"16px","fontWeight":"900","color":C["blue"],"marginRight":"8px"}),
                        html.Span(f"{change_sym}{abs(change):.0f}",style={"fontSize":"11px","color":change_color,"fontFamily":"monospace"}),
                    ]),
                ],style={"display":"flex","justifyContent":"space-between","padding":"8px 12px","alignItems":"center"}),
                dcc.Graph(figure=fig,config={"displayModeBar":False},style={"height":"130px"}),
            ],style={"background":C["card2"],"border":f"1px solid {C[\'border\']}","borderRadius":"8px","marginBottom":"8px","overflow":"hidden"}))
        pm_charts = charts if charts else [html.P("⟳ Refresh → ჩარტები",style={"color":C["muted"],"padding":"16px","textAlign":"center","fontSize":"11px"})]
    else:
        pm_charts=[html.Div([
            html.P("⟳ Refresh Odds → ჩარტები გამოჩნდება",style={"color":C["muted"],"padding":"16px","textAlign":"center","fontSize":"11px"}),
            html.P("(ყოველ 60 წამში ავტომატური განახლება)",style={"color":C["muted"],"padding":"0","textAlign":"center","fontSize":"10px","marginTop":"-8px"}),
        ])]

    # Bot Analysis
    pending=[t for t in trades if t["result"]=="PENDING"]
    rec_els=[]
    if pending:
        for t in pending:
            tc={"A":C["green"],"B":C["blue"],"C":C["yellow"]}.get(t.get("tier",""),C["muted"])
            sh={"Strong":"🔥","Medium":"🟡"}.get(t.get("sharp_label",""),"")
            reasons=t.get("reasons",[])
            rec_els.append(html.Div([
                html.Div([
                    html.Div([html.Span("✅ ",style={"fontSize":"13px"}),html.Span(t["fav"],style={"fontWeight":"900","fontSize":"14px","color":C["green"]})]),
                    html.Div(t["game"][:40],style={"fontSize":"10px","color":C["muted"],"marginTop":"2px"}),
                    html.Div([
                        html.Div("მიზეზები:",style={"fontSize":"9px","color":C["muted"],"fontWeight":"700","marginTop":"6px","marginBottom":"3px","letterSpacing":"1px"}),
                        *[html.Div(f"  ↳ {r}",style={"fontSize":"10px","color":C["blue"],"marginBottom":"2px"}) for r in reasons[:5]]
                    ]),
                ],style={"flex":"1"}),
                html.Div([
                    html.Div(f"@{t[\'odds\']}x",style={"fontFamily":"monospace","color":C["blue"],"fontWeight":"900","fontSize":"18px"}),
                    html.Div(f"{sh} Tier {t[\'tier\']}",style={"fontSize":"10px","color":C["yellow"],"marginBottom":"3px"}),
                    html.Span(f"EV {t[\'ev\']:+.3f} | Score {t[\'score\']}",style={"color":C["muted"],"fontSize":"9px","display":"block"}),
                    html.Div(f"💵${t[\'stake\']:.2f}→+${t[\'pot\']:.2f}",style={"color":C["green"],"fontWeight":"700","fontSize":"12px","fontFamily":"monospace","marginTop":"4px"}),
                ],style={"textAlign":"right","minWidth":"130px"}),
            ],style={"display":"flex","justifyContent":"space-between","alignItems":"flex-start","padding":"12px 16px","borderBottom":f"1px solid {C[\'border\']}","borderLeft":f"3px solid {C[\'green\']}"}))

    if skipped:
        rec_els.append(html.Div("გამოტოვებული",style={"padding":"6px 16px","fontSize":"9px","color":C["muted"],"fontWeight":"700","letterSpacing":"1.5px","background":C["card2"]}))
        for s in skipped[:6]:
            rec_els.append(html.Div([
                html.Div([
                    html.Span("✗ SKIP → ",style={"color":C["red"],"fontSize":"9px","fontWeight":"700"}),
                    html.Span(s["fav"],style={"fontSize":"12px","fontWeight":"700"}),
                    html.Span(f" @{s[\'odds\']}x",style={"fontFamily":"monospace","fontSize":"11px","color":C["muted"],"marginLeft":"4px"}),
                ]),
                *[html.Div(f"  ↳ {r}",style={"fontSize":"10px","color":C["red"],"marginTop":"2px"}) for r in s.get("reasons",[])[:2]],
            ],style={"padding":"8px 16px","borderBottom":f"1px solid {C[\'border\']}"}))

    if not rec_els:
        rec_els=[html.P("▶ RUN დააჭირე ანალიზისთვის",style={"color":C["muted"],"padding":"20px","textAlign":"center","fontSize":"12px","letterSpacing":"1px"})]

    # Open Positions
    if pending:
        rows=[]
        for t in pending:
            tc={"A":C["green"],"B":C["blue"],"C":C["yellow"]}.get(t.get("tier",""),C["muted"])
            sh={"Strong":"🔥","Medium":"🟡"}.get(t.get("sharp_label",""),"")
            rows.append(html.Div([
                html.Div([
                    html.Div(t["game"][:28],style={"fontSize":"9px","color":C["muted"]}),
                    html.Div([html.Span(t["fav"][:14],style={"fontWeight":"700","fontSize":"12px","marginRight":"6px"}),
                              html.Span(f"@{t[\'odds\']}x",style={"fontFamily":"monospace","color":C["blue"],"fontSize":"11px"}),html.Span(f" {sh}")]),
                ]),
                html.Div([
                    html.Span(f"T{t[\'tier\']}",style={"background":tc,"color":"#000","padding":"1px 6px","borderRadius":"4px","fontSize":"9px","fontWeight":"900","marginRight":"6px"}),
                    html.Span(f"${t[\'stake\']:.0f}→+${t[\'pot\']:.0f}",style={"color":C["muted"],"fontSize":"10px","fontFamily":"monospace","marginRight":"8px"}),
                    html.Button("W",id={"type":"bw","index":t["id"]},style={"background":C["green"],"color":"#000","border":"none","padding":"2px 10px","borderRadius":"4px","fontSize":"10px","fontWeight":"900","cursor":"pointer","marginRight":"4px"}),
                    html.Button("L",id={"type":"bl","index":t["id"]},style={"background":C["red"],"color":"#fff","border":"none","padding":"2px 10px","borderRadius":"4px","fontSize":"10px","fontWeight":"900","cursor":"pointer"}),
                ],style={"display":"flex","alignItems":"center"}),
            ],style={"display":"flex","justifyContent":"space-between","alignItems":"center","padding":"8px 14px","borderBottom":f"1px solid {C[\'border\']}"}))
        op_list=rows
    else:
        op_list=[html.P("ღია პოზიცია არ არის",style={"color":C["muted"],"padding":"14px","textAlign":"center","fontSize":"11px"})]

    # Recent Trades
    done=[t for t in trades if t["result"]!="PENDING"][:20]
    if done:
        rows=[]
        for t in done:
            won=t["result"]=="WIN"
            rows.append(html.Div([
                html.Div([html.Div(t["game"][:26],style={"fontSize":"9px","color":C["muted"]}),html.Span(t["fav"][:14],style={"fontSize":"12px","fontWeight":"600"})]),
                html.Div([
                    html.Span(f"@{t[\'odds\']}x ",style={"fontFamily":"monospace","fontSize":"9px","color":C["muted"]}),
                    html.Span(f"${t.get(\'pnl\',0):+.2f}",style={"color":C["green"] if won else C["red"],"fontFamily":"monospace","fontSize":"13px","fontWeight":"800"}),
                    html.Span(" ✅" if won else " ❌"),
                ]),
            ],style={"display":"flex","justifyContent":"space-between","alignItems":"center","padding":"7px 14px","borderBottom":f"1px solid {C[\'border\']}"}))
        tr_list=rows
    else:
        tr_list=[html.P("ბეთი ჯერ არ არის",style={"color":C["muted"],"padding":"14px","textAlign":"center","fontSize":"11px"})]

    # Portfolio Chart
    if hist_data and len(hist_data)>1:
        ptimes=[h[0] for h in hist_data]; pvals=[h[1] for h in hist_data]
    else:
        ptimes=[datetime.now().strftime("%H:%M")]; pvals=[bk]
    pfig=go.Figure()
    pfig.add_trace(go.Scatter(x=ptimes,y=pvals,mode="lines",fill="tozeroy",
        line=dict(color=C["green"],width=2),fillcolor="rgba(0,229,160,0.06)"))
    pfig.update_layout(
        plot_bgcolor=C["card"],paper_bgcolor=C["card"],font=dict(color=C["text"]),
        margin=dict(l=50,r=10,t=5,b=30),
        xaxis=dict(gridcolor=C["border"],showgrid=True,zeroline=False,tickfont=dict(size=9)),
        yaxis=dict(gridcolor=C["border"],showgrid=True,zeroline=False,tickprefix="$",tickfont=dict(size=9)),
        showlegend=False
    )

    # Stats
    td=len(done); wins=sum(1 for t in done if t["result"]=="WIN")
    wr=f"{wins/td*100:.1f}%" if td else "—"
    ao=sum(t["odds"] for t in done)/td if td else 0
    stats_el=html.Div([html.Div([
        html.Div([html.P("WIN RATE",style={"color":C["muted"],"fontSize":"8px","fontWeight":"700","letterSpacing":"1.5px","marginBottom":"4px"}),html.P(wr,style={"color":C["green"],"fontWeight":"900","fontSize":"20px","fontFamily":"monospace"})]),
        html.Div([html.P("W / L",style={"color":C["muted"],"fontSize":"8px","fontWeight":"700","letterSpacing":"1.5px","marginBottom":"4px"}),html.P(f"{wins}/{td-wins}",style={"color":C["text"],"fontWeight":"900","fontSize":"20px","fontFamily":"monospace"})]),
        html.Div([html.P("AVG ODDS",style={"color":C["muted"],"fontSize":"8px","fontWeight":"700","letterSpacing":"1.5px","marginBottom":"4px"}),html.P(f"{ao:.2f}x" if ao else "—",style={"color":C["blue"],"fontWeight":"900","fontSize":"20px","fontFamily":"monospace"})]),
        html.Div([html.P("TOTAL",style={"color":C["muted"],"fontSize":"8px","fontWeight":"700","letterSpacing":"1.5px","marginBottom":"4px"}),html.P(str(td),style={"color":C["text"],"fontWeight":"900","fontSize":"20px","fontFamily":"monospace"})]),
    ],style={"display":"grid","gridTemplateColumns":"repeat(4,1fr)","gap":"8px"})])

    mode=bot.get_setting("mode") or "paper"; ip=mode=="paper"
    mt="PAPER" if ip else "⚡ LIVE"
    ms={"background":C["yellow"] if ip else C["red"],"color":"#000","padding":"2px 10px","borderRadius":"20px","fontSize":"9px","fontWeight":"900","marginLeft":"14px","letterSpacing":"2px"}
    ir=bot.get_setting("running")=="true"
    ds={"color":C["green"] if ir else C["red"],"fontSize":"14px"}
    wr2=f"{st[\'win_rate\']:.1f}%" if st["total_trades"]>0 else "—"

    return (f"${bk:,.2f}",ps(st["daily_pnl"]),ps(st["pnl"]),
            str(st["open_positions"]),wr2,str(st["daily_trades"]),
            pm_list,pm_cnt,pm_charts,rec_els,str(len(pending)),
            op_list,str(len(pending)),tr_list,str(len(done)),
            pfig,stats_el,datetime.now().strftime("%H:%M:%S"),mt,ms,ds)

if __name__=="__main__":
    print("\\n🏀 NBA Polymarket Agent")
    print("→ http://localhost:8050\\n")
    app.run(debug=False,host="0.0.0.0",port=8050)
'''

open('bot.py','w').write(bot_code)
open('polymarket_scraper.py','w').write(scraper_code)
open('dashboard.py','w').write(dashboard_code)

import importlib, sys
for m in ['bot','polymarket_scraper']:
    if m in sys.modules: del sys.modules[m]

import bot
print("✅ bot.py:", hasattr(bot,'analyze_games_with_reason'), hasattr(bot,'save_price_history'))
import polymarket_scraper
print("✅ polymarket_scraper.py OK")
print("✅ dashboard.py OK")
print("\\n🚀 ყველაფერი მზადაა!")
SETUP
