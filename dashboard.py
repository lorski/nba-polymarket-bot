import polymarket_ws
import bot
import dash
from dash import dcc, html, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from datetime import datetime

bot.init_db()
polymarket_ws.start_background()

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.CYBORG],
    title="NBA Polymarket Agent",
    suppress_callback_exceptions=True
)
server = app.server

C = {
    "bg":     "#0d1117",
    "card":   "#161b22",
    "card2":  "#1c2128",
    "border": "#30363d",
    "green":  "#2ea043",
    "green2": "#3fb950",
    "red":    "#da3633",
    "blue":   "#58a6ff",
    "yellow": "#d29922",
    "purple": "#8b949e",
    "text":   "#e6edf3",
    "muted":  "#8b949e",
    "success":"#238636",
}

def mk_card(title, val_id, sub=""):
    return html.Div([
        html.P(title, style={"color":C["muted"],"fontSize":"11px","fontWeight":"600",
                             "letterSpacing":"0.5px","marginBottom":"6px","textTransform":"uppercase"}),
        html.H2("—", id=val_id, style={"color":C["text"],"fontWeight":"700",
                                        "fontSize":"26px","marginBottom":"2px","fontFamily":"monospace"}),
        html.P(sub, style={"color":C["muted"],"fontSize":"11px","marginBottom":"0"}),
    ], style={"background":C["card"],"border":f"1px solid {C['border']}",
              "borderRadius":"8px","padding":"16px 20px"})

app.layout = html.Div([

    # Header
    html.Div([
        html.Div([
            html.Span("●", id="run-dot", style={"color":C["green"],"fontSize":"10px","marginRight":"6px"}),
            html.Span("NBA", style={"color":C["text"],"fontWeight":"700","fontSize":"18px"}),
            html.Span(" Polymarket Agent", style={"color":C["blue"],"fontWeight":"700","fontSize":"18px"}),
            html.Span("PAPER MODE", id="mode-badge", style={
                "background":C["yellow"],"color":"#000","padding":"2px 10px",
                "borderRadius":"4px","fontSize":"11px","fontWeight":"700","marginLeft":"12px"
            }),
        ], style={"display":"flex","alignItems":"center","flex":"1"}),
        html.Div([
            html.Span("● Polymarket", id="poly-dot", style={"color":C["green"],"fontSize":"12px","marginRight":"16px"}),
            html.Span(id="pm-status", style={"color":C["muted"],"fontSize":"11px","marginRight":"16px"}),
            html.Span(id="refresh-time", style={"color":C["muted"],"fontSize":"12px"}),
        ], style={"display":"flex","alignItems":"center"}),
    ], style={"display":"flex","justifyContent":"space-between","alignItems":"center",
              "padding":"12px 24px","borderBottom":f"1px solid {C['border']}",
              "background":C["card"]}),

    html.Div([

        # Stat Cards
        html.Div([
            mk_card("TOTAL VALUE",    "s-bankroll", "current portfolio"),
            mk_card("DAILY P&L",      "s-dpnl",     "since midnight"),
            mk_card("TOTAL P&L",      "s-tpnl",     "all time"),
            mk_card("OPEN POSITIONS", "s-open",     "active"),
            mk_card("WIN RATE",       "s-wr",       "completed bets"),
            mk_card("DAILY TRADES",   "s-daily",    "today"),
        ], style={"display":"grid","gridTemplateColumns":"repeat(6,1fr)",
                  "gap":"12px","marginBottom":"16px"}),

        # Controls
        html.Div([
            html.Div([
                html.Button("▶ Run Analysis", id="btn-run",
                    style={"background":C["success"],"color":"#fff","border":"none",
                           "padding":"8px 18px","borderRadius":"6px","fontSize":"13px",
                           "fontWeight":"600","cursor":"pointer","marginRight":"8px"}),
                html.Button("⏸ Pause", id="btn-pause",
                    style={"background":"transparent","color":C["text"],
                           "border":f"1px solid {C['border']}","padding":"8px 16px",
                           "borderRadius":"6px","fontSize":"13px","cursor":"pointer","marginRight":"8px"}),
                html.Button("🔄 Refresh", id="btn-refresh",
                    style={"background":"transparent","color":C["blue"],
                           "border":f"1px solid {C['blue']}","padding":"8px 16px",
                           "borderRadius":"6px","fontSize":"13px","cursor":"pointer"}),
            ]),
            html.Div([
                html.Span("Paper", style={"color":C["muted"],"fontSize":"13px","marginRight":"8px"}),
                dbc.Switch(id="mode-switch", value=False),
                html.Span("Live", style={"color":C["muted"],"fontSize":"13px","marginLeft":"8px"}),
            ], style={"display":"flex","alignItems":"center"}),
        ], style={"display":"flex","justifyContent":"space-between",
                  "alignItems":"center","marginBottom":"16px"}),

        html.Div([

            # LEFT
            html.Div([

                # Polymarket Live Odds
                html.Div([
                    html.Div([
                        html.Span("Polymarket Live NBA Odds", style={"fontWeight":"600","fontSize":"14px"}),
                        html.Span(id="pm-count", style={
                            "background":C["blue"],"color":"#fff","padding":"1px 8px",
                            "borderRadius":"10px","fontSize":"11px","float":"right"
                        }),
                    ], style={"padding":"12px 16px","borderBottom":f"1px solid {C['border']}"}),
                    html.Div(id="pm-odds-list", style={"maxHeight":"280px","overflowY":"auto"}),
                ], style={"background":C["card"],"border":f"1px solid {C['border']}",
                          "borderRadius":"8px","marginBottom":"12px"}),

                # Open Positions
                html.Div([
                    html.Div([
                        html.Span("Open Positions", style={"fontWeight":"600","fontSize":"14px"}),
                        html.Span(id="open-count", style={
                            "background":C["green"],"color":"#fff","padding":"1px 8px",
                            "borderRadius":"10px","fontSize":"11px","float":"right"
                        }),
                    ], style={"padding":"12px 16px","borderBottom":f"1px solid {C['border']}"}),
                    html.Div(id="open-pos"),
                ], style={"background":C["card"],"border":f"1px solid {C['border']}",
                          "borderRadius":"8px","marginBottom":"12px"}),

                # Manual Bet
                html.Div([
                    html.Div("Manual Bet Input", style={
                        "padding":"12px 16px","fontWeight":"600","fontSize":"14px",
                        "borderBottom":f"1px solid {C['border']}"}),
                    html.Div([
                        dbc.Input(id="m-game", placeholder="Lakers vs Celtics", size="sm",
                            style={"marginBottom":"8px","background":C["card2"],
                                   "border":f"1px solid {C['border']}","color":C["text"]}),
                        dbc.Input(id="m-fav", placeholder="ფავი (Lakers)", size="sm",
                            style={"marginBottom":"8px","background":C["card2"],
                                   "border":f"1px solid {C['border']}","color":C["text"]}),
                        html.Div([
                            dbc.Input(id="m-odds", placeholder="კოეფი 1.65", type="number",
                                size="sm", style={"background":C["card2"],
                                "border":f"1px solid {C['border']}","color":C["text"]}),
                            dbc.Input(id="m-open", placeholder="Opening 1.72", type="number",
                                size="sm", style={"background":C["card2"],
                                "border":f"1px solid {C['border']}","color":C["text"]}),
                            dbc.Select(id="m-tier", size="sm", value="B",
                                options=[{"label":"Tier A","value":"A"},
                                         {"label":"Tier B","value":"B"},
                                         {"label":"Tier C","value":"C"}],
                                style={"background":C["card2"],"border":f"1px solid {C['border']}",
                                       "color":C["text"]}),
                            dbc.Select(id="m-sharp", size="sm", value="0",
                                options=[{"label":"Sharp: —","value":"0"},
                                         {"label":"🟡 Medium","value":"1"},
                                         {"label":"🔥 Strong","value":"2"}],
                                style={"background":C["card2"],"border":f"1px solid {C['border']}",
                                       "color":C["text"]}),
                        ], style={"display":"grid","gridTemplateColumns":"1fr 1fr 1fr 1fr",
                                  "gap":"8px","marginBottom":"8px"}),
                        html.P(id="m-calc", style={"color":C["green"],"fontSize":"12px","marginBottom":"8px"}),
                        html.Button("+ ბეთის დამატება", id="btn-add",
                            style={"background":C["success"],"color":"#fff","border":"none",
                                   "padding":"7px 16px","borderRadius":"6px","fontSize":"13px",
                                   "fontWeight":"600","cursor":"pointer","width":"100%"}),
                        html.Span(id="add-fb", style={"color":C["green"],"fontSize":"12px",
                                                       "display":"block","marginTop":"6px"}),
                    ], style={"padding":"12px 16px"}),
                ], style={"background":C["card"],"border":f"1px solid {C['border']}","borderRadius":"8px"}),

            ], style={"flex":"1","marginRight":"12px"}),

            # RIGHT
            html.Div([
                html.Div([
                    html.Div([
                        html.Span("Recent Trades", style={"fontWeight":"600","fontSize":"14px"}),
                        html.Span(id="trades-count", style={
                            "background":C["purple"],"color":"#fff","padding":"1px 8px",
                            "borderRadius":"10px","fontSize":"11px","float":"right"
                        }),
                    ], style={"padding":"12px 16px","borderBottom":f"1px solid {C['border']}"}),
                    html.Div(id="recent-trades",
                        style={"maxHeight":"500px","overflowY":"auto"}),
                ], style={"background":C["card"],"border":f"1px solid {C['border']}","borderRadius":"8px"}),
            ], style={"width":"380px"}),

        ], style={"display":"flex","marginBottom":"16px"}),

        # Portfolio Chart
        html.Div([
            html.Div("Portfolio Value", style={
                "padding":"12px 16px","fontWeight":"600","fontSize":"14px",
                "borderBottom":f"1px solid {C['border']}"}),
            dcc.Graph(id="chart", style={"height":"180px"}, config={"displayModeBar":False}),
        ], style={"background":C["card"],"border":f"1px solid {C['border']}","borderRadius":"8px"}),

    ], style={"padding":"16px 24px","background":C["bg"],"minHeight":"calc(100vh - 52px)"}),

    dcc.Interval(id="interval", interval=15*1000, n_intervals=0),

], style={"background":C["bg"],"fontFamily":"-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif",
          "color":C["text"]})


@app.callback(
    [Output("s-bankroll","children"), Output("s-dpnl","children"),
     Output("s-tpnl","children"), Output("s-open","children"),
     Output("s-wr","children"), Output("s-daily","children"),
     Output("pm-odds-list","children"), Output("pm-count","children"),
     Output("open-pos","children"), Output("open-count","children"),
     Output("recent-trades","children"), Output("trades-count","children"),
     Output("chart","figure"),
     Output("refresh-time","children"),
     Output("mode-badge","children"), Output("mode-badge","style"),
     Output("run-dot","style"),
     Output("pm-status","children"),
     Output("m-calc","children")],
    [Input("interval","n_intervals"),
     Input("btn-refresh","n_clicks"),
     Input("btn-run","n_clicks"),
     Input("btn-pause","n_clicks"),
     Input("mode-switch","value"),
     Input("m-odds","value"),
     Input("m-tier","value"),
     Input("m-sharp","value")],
    prevent_initial_call=False
)
def update(n, ref, run, pause, live, odds_v, tier, sharp):
    ctx = callback_context
    trig = ctx.triggered[0]["prop_id"] if ctx.triggered else ""

    if "mode-switch" in trig:
        bot.set_setting("mode","live" if live else "paper")
    if "btn-run" in trig:
        bot.set_setting("running","true")
        live_odds = polymarket_ws.get_live_odds()
        espn_games = bot.get_todays_games()
        # Polymarket odds merge
        merged = []
        for g in espn_games:
            pm = polymarket_ws.get_odds_for_game(g["home"],g["away"])
            if pm:
                g["h_odds"] = pm["h_odds"]
                g["a_odds"] = pm["a_odds"]
                g["source"] = "polymarket"
            else:
                g["source"] = "espn"
            merged.append(g)
        if not merged and live_odds:
            for mid, od in live_odds.items():
                merged.append({
                    "home": od["question"][:30],
                    "away": "",
                    "h_odds": od["h_odds"],
                    "a_odds": od["a_odds"],
                    "source": "polymarket"
                })
        trades, _ = bot.analyze_games(merged)
        for t in trades:
            bot.save_trade(t)
    if "btn-pause" in trig:
        bot.set_setting("running","false")

    stats   = bot.get_stats()
    trades  = bot.get_trades(100)
    history = bot.get_portfolio_history()
    bk      = stats["bankroll"]
    pm_st   = polymarket_ws.get_status()
    live_odds = polymarket_ws.get_live_odds()

    def pspan(v,positive_color):
        c = positive_color if v>=0 else C["red"]
        return html.Span(f"${v:+.2f}", style={"color":c,"fontFamily":"monospace",
                                               "fontSize":"26px","fontWeight":"700"})

    # Polymarket odds display
    if live_odds:
        pm_els = []
        for mid, od in live_odds.items():
            q = od["question"]
            h_o = od.get("h_odds")
            a_o = od.get("a_odds")
            h_p = od.get("h_price",0)
            a_p = od.get("a_price",0)
            upd = od.get("updated","—")
            fav_o = min(h_o,a_o) if h_o and a_o else None
            in_range = 1.22<=fav_o<=1.82 if fav_o else False
            pm_els.append(html.Div([
                html.Div([
                    html.Div(q[:45], style={"fontSize":"12px","marginBottom":"3px","fontWeight":"500"}),
                    html.Div([
                        html.Span(f"YES: {h_p:.3f} = ", style={"color":C["muted"],"fontSize":"11px"}),
                        html.Span(f"{h_o}x", style={"color":C["green2"],"fontFamily":"monospace",
                                                      "fontSize":"13px","fontWeight":"600"}),
                        html.Span(f"  NO: {a_p:.3f} = ", style={"color":C["muted"],"fontSize":"11px","marginLeft":"12px"}),
                        html.Span(f"{a_o}x", style={"color":C["blue"],"fontFamily":"monospace",
                                                      "fontSize":"13px","fontWeight":"600"}),
                    ]),
                ]),
                html.Div([
                    html.Span("✓" if in_range else "✗",
                        style={"color":C["green2"] if in_range else C["muted"],"fontSize":"14px","marginRight":"4px"}),
                    html.Span(upd, style={"color":C["muted"],"fontSize":"10px"}),
                ], style={"textAlign":"right"}),
            ], style={"display":"flex","justifyContent":"space-between","alignItems":"center",
                      "padding":"8px 12px","borderBottom":f"1px solid {C['border']}"}))
        pm_list = pm_els
        pm_cnt  = str(len(live_odds))
    else:
        pm_list = [html.Div([
            html.P("Polymarket NBA markets-ი ჯერ ცარიელია",
                style={"color":C["muted"],"textAlign":"center","padding":"20px 12px","fontSize":"13px"}),
            html.P("თამაშამდე 24-48 სთ. გამოჩნდება",
                style={"color":C["muted"],"textAlign":"center","fontSize":"11px","marginTop":"-12px"}),
        ])]
        pm_cnt = "0"

    # Open positions
    pending = [t for t in trades if t["result"]=="PENDING"]
    if pending:
        rows = []
        for t in pending:
            sh = {"Strong":"🔥","Medium":"🟡"}.get(t.get("sharp_label",""),"—")
            tc = {"A":C["green"],"B":C["blue"],"C":C["yellow"]}.get(t.get("tier",""),C["muted"])
            src = t.get("source","espn")
            src_badge = html.Span("PM" if src=="polymarket" else "ESPN",
                style={"background":C["blue"] if src=="polymarket" else C["purple"],
                       "color":"#fff","padding":"1px 5px","borderRadius":"3px","fontSize":"10px","marginLeft":"4px"})
            rows.append(html.Div([
                html.Div([
                    html.Div([t["game"][:30], src_badge], style={"fontSize":"12px","marginBottom":"2px","display":"flex","alignItems":"center","gap":"4px"}),
                    html.Div([
                        html.Span(t["fav"][:14], style={"fontWeight":"600","fontSize":"13px","marginRight":"6px"}),
                        html.Span(f"@{t['odds']}", style={"fontFamily":"monospace","color":C["blue"],"fontSize":"12px"}),
                        html.Span(f" {sh}", style={"marginLeft":"4px"}),
                    ]),
                ]),
                html.Div([
                    html.Span(f"Tier {t['tier']}", style={"background":tc,"color":"#fff",
                        "padding":"1px 6px","borderRadius":"4px","fontSize":"11px","marginRight":"6px"}),
                    html.Span(f"${t['stake']:.0f}", style={"color":C["muted"],"fontSize":"12px","marginRight":"8px"}),
                    html.Button("W", id={"type":"btn-w","index":t["id"]},
                        style={"background":C["success"],"color":"#fff","border":"none",
                               "padding":"2px 8px","borderRadius":"4px","fontSize":"11px",
                               "cursor":"pointer","marginRight":"4px"}),
                    html.Button("L", id={"type":"btn-l","index":t["id"]},
                        style={"background":C["red"],"color":"#fff","border":"none",
                               "padding":"2px 8px","borderRadius":"4px","fontSize":"11px","cursor":"pointer"}),
                ], style={"display":"flex","alignItems":"center"}),
            ], style={"display":"flex","justifyContent":"space-between","alignItems":"center",
                      "padding":"8px 12px","borderBottom":f"1px solid {C['border']}"}))
        open_el = rows
    else:
        open_el = [html.P("ღია პოზიცია არ არის",
            style={"color":C["muted"],"padding":"16px","textAlign":"center","fontSize":"13px"})]

    # Recent trades
    done = [t for t in trades if t["result"]!="PENDING"][:20]
    if done:
        rows = []
        for t in done:
            won = t["result"]=="WIN"
            rows.append(html.Div([
                html.Div([
                    html.Div(t["game"][:28], style={"fontSize":"11px","color":C["muted"]}),
                    html.Span(t["fav"][:14], style={"fontSize":"13px","fontWeight":"500"}),
                ]),
                html.Div([
                    html.Span(f"@{t['odds']} ", style={"fontFamily":"monospace","fontSize":"11px","color":C["muted"]}),
                    html.Span(f"${t.get('pnl',0):+.2f}", style={
                        "color":C["green2"] if won else C["red"],
                        "fontFamily":"monospace","fontSize":"13px","fontWeight":"600"
                    }),
                    html.Span(" ✅" if won else " ❌", style={"fontSize":"11px"}),
                ]),
            ], style={"display":"flex","justifyContent":"space-between","alignItems":"center",
                      "padding":"7px 12px","borderBottom":f"1px solid {C['border']}"}))
        recent_el = rows
    else:
        recent_el = [html.P("ბეთი ჯერ არ არის",
            style={"color":C["muted"],"padding":"16px","textAlign":"center","fontSize":"13px"})]

    # Chart
    if history and len(history)>1:
        times  = [h[0] for h in history]
        values = [h[1] for h in history]
    else:
        times  = [datetime.now().strftime("%H:%M")]
        values = [bk]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=times, y=values, mode="lines", fill="tozeroy",
        line=dict(color=C["blue"],width=2), fillcolor="rgba(88,166,255,0.08)"))
    fig.update_layout(
        plot_bgcolor=C["card"], paper_bgcolor=C["card"],
        font=dict(color=C["text"]),
        margin=dict(l=50,r=10,t=5,b=30),
        xaxis=dict(gridcolor=C["border"],showgrid=True,zeroline=False),
        yaxis=dict(gridcolor=C["border"],showgrid=True,zeroline=False,tickprefix="$"),
        showlegend=False
    )

    # Mode
    mode = bot.get_setting("mode") or "paper"
    is_paper = mode=="paper"
    mode_txt = "PAPER MODE" if is_paper else "⚡ LIVE MODE"
    mode_style = {"background":C["yellow"] if is_paper else C["red"],
                  "color":"#000" if is_paper else "#fff",
                  "padding":"2px 10px","borderRadius":"4px","fontSize":"11px",
                  "fontWeight":"700","marginLeft":"12px"}

    # Run dot
    is_running = bot.get_setting("running")=="true"
    dot_style = {"color":C["green2"] if is_running else C["red"],"fontSize":"10px","marginRight":"6px"}

    # PM status
    pm_status_txt = f"PM: {pm_st['live_odds']} markets | {pm_st['last_update']}"

    # Calc hint
    calc = ""
    if odds_v:
        try:
            sh_b=[0,6,14][int(sharp or 0)]
            mp=1/float(odds_v)
            p=min(0.95,mp+(5+sh_b*0.5)/100)
            k=max(0,((float(odds_v)-1)*p-(1-p))/(float(odds_v)-1))
            f={"A":0.25,"B":0.18,"C":0.10}.get(tier,0.18)
            st=round(max(12,min(bk*0.12,bk*k*f)),2)
            ev=round(p*(float(odds_v)-1)-(1-p),4)
            calc=f"Stake: ${st:.2f} | Model: {p:.1%} | EV: {ev:+.3f}"
        except: pass

    wr_txt = f"{stats['win_rate']:.1f}%" if stats['total_trades']>0 else "—"
    rt = f"Updated: {datetime.now().strftime('%H:%M:%S')}"

    return (
        f"${bk:.2f}",
        pspan(stats["daily_pnl"], C["green2"]),
        pspan(stats["pnl"], C["green2"]),
        str(stats["open_positions"]),
        wr_txt, str(stats["daily_trades"]),
        pm_list, pm_cnt,
        open_el, str(len(pending)),
        recent_el, str(len(done)),
        fig, rt,
        mode_txt, mode_style, dot_style,
        pm_status_txt, calc
    )


@app.callback(
    Output("add-fb","children"),
    Input("btn-add","n_clicks"),
    [State("m-game","value"), State("m-fav","value"),
     State("m-odds","value"), State("m-open","value"),
     State("m-tier","value"), State("m-sharp","value")],
    prevent_initial_call=True
)
def add_bet(n, game, fav, odds, open_o, tier, sharp):
    if not all([game, fav, odds]):
        return "⚠️ შეავსე ყველა ველი!"
    try:
        bk = bot.get_bankroll()
        odds = float(odds)
        open_o = float(open_o or odds)
        sh = int(sharp or 0)
        sh_b = [0,6,14][sh]
        mp = 1/odds
        p = min(0.95, mp+(5+sh_b*0.5)/100)
        k = max(0,((odds-1)*p-(1-p))/(odds-1))
        f = {"A":0.25,"B":0.18,"C":0.10}.get(tier,0.18)
        st = round(max(12,min(bk*0.12,bk*k*f)),2)
        bot.save_trade({
            "game":game,"fav":fav,"odds":odds,"open_odds":open_o,
            "sharp":sh,"sharp_label":["—","Medium","Strong"][sh],
            "tier":tier,"score":60.0,
            "edge":round(p-mp,4),"ev":round(p*(odds-1)-(1-p),4),
            "stake":st,"pot":round(st*(odds-1),2),"source":"manual"
        })
        return f"✅ ${st:.2f} შენახულია!"
    except Exception as e:
        return f"❌ {e}"


if __name__ == "__main__":
    print("\n🏀 NBA Polymarket Agent")
    print("→ http://localhost:8050\n")
    app.run(debug=False, host="0.0.0.0", port=8050)
