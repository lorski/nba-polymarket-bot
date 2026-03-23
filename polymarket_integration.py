# ═══════════════════════════════════════════════════
# ეს კოდი bot.py-ს ᲑᲝᲚᲝᲨᲘ დაამატე
# (import requests უკვე გაქვს ზევით)
# ═══════════════════════════════════════════════════

import os

POLY_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "POLY-API-KEY": os.environ.get("POLY_API_KEY", ""),
}

TEAM_SLUGS = {
    "Los Angeles Lakers":     ["lakers", "los-angeles-lakers"],
    "Boston Celtics":         ["celtics", "boston-celtics"],
    "Golden State Warriors":  ["warriors", "golden-state-warriors"],
    "Miami Heat":             ["heat", "miami-heat"],
    "Chicago Bulls":          ["bulls", "chicago-bulls"],
    "New York Knicks":        ["knicks", "new-york-knicks"],
    "Brooklyn Nets":          ["nets", "brooklyn-nets"],
    "Cleveland Cavaliers":    ["cavaliers", "cleveland-cavaliers"],
    "Philadelphia 76ers":     ["76ers", "philadelphia-76ers", "sixers"],
    "Milwaukee Bucks":        ["bucks", "milwaukee-bucks"],
    "Denver Nuggets":         ["nuggets", "denver-nuggets"],
    "Phoenix Suns":           ["suns", "phoenix-suns"],
    "LA Clippers":            ["clippers", "la-clippers", "los-angeles-clippers"],
    "Dallas Mavericks":       ["mavericks", "dallas-mavericks"],
    "San Antonio Spurs":      ["spurs", "san-antonio-spurs"],
    "Houston Rockets":        ["rockets", "houston-rockets"],
    "Utah Jazz":              ["jazz", "utah-jazz"],
    "Oklahoma City Thunder":  ["thunder", "oklahoma-city-thunder"],
    "Portland Trail Blazers": ["trail-blazers", "portland-trail-blazers"],
    "Sacramento Kings":       ["kings", "sacramento-kings"],
    "Atlanta Hawks":          ["hawks", "atlanta-hawks"],
    "Charlotte Hornets":      ["hornets", "charlotte-hornets"],
    "Detroit Pistons":        ["pistons", "detroit-pistons"],
    "Indiana Pacers":         ["pacers", "indiana-pacers"],
    "Toronto Raptors":        ["raptors", "toronto-raptors"],
    "New Orleans Pelicans":   ["pelicans", "new-orleans-pelicans"],
    "Memphis Grizzlies":      ["grizzlies", "memphis-grizzlies"],
    "Minnesota Timberwolves": ["timberwolves", "minnesota-timberwolves"],
    "Washington Wizards":     ["wizards", "washington-wizards"],
    "Orlando Magic":          ["magic", "orlando-magic"],
}

def get_team_keywords(team):
    slugs = TEAM_SLUGS.get(team, [])
    short = team.split()[-1].lower()
    return slugs + [short]


def fetch_polymarket_nba():
    """
    Polymarket-იდან NBA markets ამოღება
    3 endpoint სცადე
    """
    markets = []

    # ── Endpoint 1: Gamma Events API ──────────────
    try:
        url = "https://gamma-api.polymarket.com/events"
        params = {"limit": 100, "active": "true"}
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            events = r.json()
            for ev in events:
                slug = ev.get("slug", "").lower()
                title = ev.get("title", "").lower()
                if "nba" in slug or "nba" in title:
                    for market in ev.get("markets", []):
                        q = market.get("question", "").lower()
                        prices = market.get("outcomePrices", "")
                        if prices:
                            try:
                                ps = [float(x.strip()) for x in prices.strip("[]").split(",")]
                                if len(ps) >= 2 and 0.01 < ps[0] < 0.99:
                                    markets.append({
                                        "question": market.get("question",""),
                                        "h_prob": ps[0],
                                        "a_prob": ps[1],
                                        "h_odds": round(1/ps[0], 2),
                                        "a_odds": round(1/ps[1], 2),
                                        "slug": ev.get("slug",""),
                                        "source": "gamma"
                                    })
                            except:
                                pass
    except Exception as e:
        print(f"Gamma events error: {e}")

    # ── Endpoint 2: Gamma Markets search ──────────
    if not markets:
        try:
            for keyword in ["nba", "basketball"]:
                url = "https://gamma-api.polymarket.com/markets"
                params = {
                    "limit": 100,
                    "active": "true",
                    "closed": "false",
                    "q": keyword
                }
                r = requests.get(url, params=params, timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    for m in data:
                        q = m.get("question", "").lower()
                        if any(t in q for t in ["nba","lakers","celtics","knicks",
                                                 "warriors","bucks","cavaliers"]):
                            prices = m.get("outcomePrices","")
                            if prices:
                                try:
                                    ps = [float(x.strip()) for x in prices.strip("[]").split(",")]
                                    if len(ps) >= 2 and 0.01 < ps[0] < 0.99:
                                        markets.append({
                                            "question": m.get("question",""),
                                            "h_prob": ps[0],
                                            "a_prob": ps[1],
                                            "h_odds": round(1/ps[0], 2),
                                            "a_odds": round(1/ps[1], 2),
                                            "slug": m.get("slug",""),
                                            "source": "gamma_search"
                                        })
                                except:
                                    pass
        except Exception as e:
            print(f"Gamma markets error: {e}")

    # ── Endpoint 3: CLOB ──────────────────────────
    if not markets:
        try:
            url = "https://clob.polymarket.com/markets"
            r = requests.get(url, params={"limit":100,"active":"true"}, timeout=10)
            if r.status_code == 200:
                data = r.json().get("data", [])
                for m in data:
                    q = m.get("question","").lower()
                    if any(t in q for t in ["nba","lakers","celtics","warriors",
                                             "knicks","cavaliers","bucks"]):
                        tokens = m.get("tokens", [])
                        if len(tokens) >= 2:
                            try:
                                p1 = float(tokens[0].get("price", 0.5))
                                p2 = float(tokens[1].get("price", 0.5))
                                if 0.01 < p1 < 0.99:
                                    markets.append({
                                        "question": m.get("question",""),
                                        "h_prob": p1,
                                        "a_prob": p2,
                                        "h_odds": round(1/p1, 2),
                                        "a_odds": round(1/p2, 2),
                                        "slug": m.get("condition_id",""),
                                        "source": "clob"
                                    })
                            except:
                                pass
        except Exception as e:
            print(f"CLOB error: {e}")

    return markets


def match_game_to_polymarket(home, away, poly_markets):
    """
    ESPN გუნდები → Polymarket market მოძებნა
    """
    h_keys = get_team_keywords(home)
    a_keys = get_team_keywords(away)

    for m in poly_markets:
        q = m["question"].lower()
        h_match = any(k in q for k in h_keys)
        a_match = any(k in q for k in a_keys)
        if h_match and a_match:
            return m

    # ერთი გუნდი მაინც
    for m in poly_markets:
        q = m["question"].lower()
        if any(k in q for k in h_keys) or any(k in q for k in a_keys):
            return m

    return None


def get_games_with_polymarket_odds():
    """
    ESPN თამაშები + Polymarket odds
    """
    espn_games = get_todays_games()
    poly_markets = fetch_polymarket_nba()

    print(f"ESPN games: {len(espn_games)}")
    print(f"Polymarket NBA markets: {len(poly_markets)}")

    result = []

    for g in espn_games:
        home, away = g["home"], g["away"]
        pm = match_game_to_polymarket(home, away, poly_markets)

        if pm:
            h_o = pm["h_odds"]
            a_o = pm["a_odds"]
            source = "polymarket"
        else:
            h_o = g.get("h_odds")
            a_o = g.get("a_odds")
            source = "espn"

        result.append({
            "home": home,
            "away": away,
            "h_odds": h_o,
            "a_odds": a_o,
            "h_open": h_o,
            "a_open": a_o,
            "source": source,
            "poly_question": pm["question"] if pm else None
        })

    # Polymarket-ის markets რომ ESPN-ში არ არის
    for pm in poly_markets:
        q = pm["question"]
        already = any(
            match_game_to_polymarket(g["home"], g["away"], [pm])
            for g in espn_games
        )
        if not already:
            result.append({
                "home": q[:40],
                "away": "",
                "h_odds": pm["h_odds"],
                "a_odds": pm["a_odds"],
                "h_open": pm["h_odds"],
                "a_open": pm["a_odds"],
                "source": "polymarket_only",
                "poly_question": q
            })

    return result, poly_markets


def analyze_games_polymarket():
    """
    ბოტის ანალიზი Polymarket odds-ებზე
    """
    bk = get_bankroll()
    games, poly_raw = get_games_with_polymarket_odds()

    # Morning odds cache
    morning = load_morning_odds()
    if not morning:
        cache = {}
        for g in games:
            key = f"{g['home']}|{g['away']}"
            cache[key] = {"h": g["h_odds"], "a": g["a_odds"]}
        save_morning_odds(games)
        morning = cache

    approved = []
    log = []

    for g in games:
        home, away = g["home"], g["away"]
        h_c, a_c = g["h_odds"], g["a_odds"]
        if not h_c or not a_c:
            continue

        key = f"{home}|{away}"
        h_o = morning.get(key, {}).get("h", h_c)
        a_o = morning.get(key, {}).get("a", a_c)

        if h_c <= a_c:
            fav,dog,odds,opf,side,ih = home,away,h_c,h_o,"HOME",True
        else:
            fav,dog,odds,opf,side,ih = away,home,a_c,a_o,"AWAY",False

        if not(1.22<=odds<=1.82):
            log.append(f"SKIP {fav} ({odds}) out of range")
            continue
        if side=="AWAY" and odds<1.28:
            log.append(f"SKIP {fav} ({odds}) away<1.28")
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

        trade = {
            "game": f"{home} vs {away}",
            "fav": fav, "dog": dog,
            "odds": odds, "open_odds": opf,
            "side": side, "tier": t,
            "score": sc, "edge": e, "ev": ev,
            "prob": p, "mp": mp,
            "stake": st, "pot": round(st*(odds-1),2),
            "sharp": sh["lv"],
            "sharp_label": sh["lbl"],
            "source": g.get("source","espn")
        }
        approved.append(trade)
        log.append(f"BET {fav} @ {odds} Tier {t} ${st:.2f} [{g.get('source','')}]")

    # Daily cap
    if approved:
        exp = sum(r["stake"] for r in approved)
        mx = bk * 0.25
        if exp > mx:
            ratio = mx/exp
            for r in approved:
                r["stake"] = round(r["stake"]*ratio,2)
                r["pot"] = round(r["stake"]*(r["odds"]-1),2)

    return approved, "\n".join(log), poly_raw
