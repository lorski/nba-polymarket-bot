# ════════════════════════════════════════════════════
# dashboard.py v2.0 — NBA Polymarket Agent
# pip install dash dash-bootstrap-components plotly
# ════════════════════════════════════════════════════

import dash
from dash import dcc, html, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from datetime import datetime
import bot

bot.init_db()

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.CYBORG],
    title="NBA Polymarket Agent",
    suppress_callback_exceptions=True
)
server = app.server

C = {
    "bg":      "#0d1117",
    "card":    "#161b22",
    "card2":   "#1c2128",
    "border":  "#30363d",
    "green":   "#2ea043",
    "green2":  "#3fb950",
    "red":     "#da3633",
    "blue":    "#58a6ff",
    "yellow":  "#d29922",
    "purple":  "#8b949e",
    "text":    "#e6edf3",
    "muted":   "#8b949e",
    "success": "#238636",
}

def mk_card(title, val_id, sub="", color=None):
    return html.Div([
        html.P(title, style={"color":C["muted"],"fontSize":"11px","fontWeight":"600",
                             "letterSpacing":"0.5px","marginBottom":"6px","textTransform":"uppercase"}),
        html.H2("—", id=val_id, style={"color": color or C["text"],"fontWeight":"700",
                                        "fontSize":"28px","marginBottom":"2px","fontFamily":"monospace"}),
        html.P(sub, style={"color":C["muted"],"fontSize":"11px","marginBottom":"0"}),
    ], style={"background":C["card"],"border":f"1px solid {C['border']}",
              "borderRadius":"8px","padding":"16px 20px"})

app.layout = html.Div([

    # ── Header ──────────────────────────────────────
    html.Div([
        html.Div([
            html.Div([
                html.Span("●", id="run-dot", style={"color":C["green"],"fontSize":"10px","marginRight":"6px"}),
                html.Span("NBA", style={"color":C["text"],"fontWeight":"700","fontSize":"18px"}),
                html.Span(" Polymarket Agent", style={"color":C["blue"],"fontWeight":"700","fontSize":"18px"}),
                html.Span("  "),
                html.Span("PAPER MODE", id="mode-badge-top", style={
                    "background":C["yellow"],"color":"#000","padding":"2px 10px",
                    "borderRadius":"4px","fontSize":"11px","fontWeight":"700","marginLeft":"8px"
                }),
            ], style={"display":"flex","alignItems":"center"}),
        ], style={"flex":"1"}),
        html.Div([
            html.Span("● Polymarket", id="poly-status", style={"color":C["green"],"fontSize":"12px","marginRight":"16px"}),
            html.Span(id="refresh-time", style={"color":C["muted"],"fontSize":"12px"}),
        ], style={"display":"flex","alignItems":"center"}),
    ], style={"display":"flex","justifyContent":"space-between","alignItems":"center",
              "padding":"14px 24px","borderBottom":f"1px solid {C['border']}",
              "background":C["card"]}),

    # ── Main Content ─────────────────────────────────
    html.Div([

        # Stat Cards Row
        html.Div([
            mk_card("TOTAL VALUE",     "s-bankroll",  "current portfolio"),
            mk_card("CASH BALANCE",    "s-cash",      "available to trade"),
            mk_card("DAILY P&L",       "s-dpnl",      "since midnight"),
            mk_card("TOTAL P&L",       "s-tpnl",      "all time"),
            mk_card("OPEN POSITIONS",  "s-open",      "active markets"),
            mk_card("DAILY TRADES",    "s-daily",     "settled today"),
        ], style={"display":"grid","gridTemplateColumns":"repeat(6,1fr)",
                  "gap":"12px","marginBottom":"16px"}),

        # Controls Row
        html.Div([
            html.Div([
                html.Button([html.Span("▶ "), "Run Analysis"], id="btn-run",
                    style={"background":C["success"],"color":"#fff","border":"none",
                           "padding":"8px 18px","borderRadius":"6px","fontSize":"13px",
                           "fontWeight":"600","cursor":"pointer","marginRight":"8px"}),
                html.Button([html.Span("⏸ "), "Pause"], id="btn-pause",
                    style={"background":"transparent","color":C["text"],
                           "border":f"1px solid {C['border']}","padding":"8px 16px",
                           "borderRadius":"6px","fontSize":"13px","cursor":"pointer","marginRight":"8px"}),
                html.Button([html.Span("🔄 "), "Refresh"], id="btn-refresh",
                    style={"background":"transparent","color":C["blue"],
                           "border":f"1px solid {C['blue']}","padding":"8px 16px",
                           "borderRadius":"6px","fontSize":"13px","cursor":"pointer"}),
            ]),
            html.Div([
                html.Span("Paper", style={"color":C["muted"],"fontSize":"13px","marginRight":"8px"}),
                dbc.Switch(id="mode-switch", value=False, style={"display":"inline-block"}),
                html.Span("Live", style={"color":C["muted"],"fontSize":"13px","marginLeft":"8px"}),
            ], style={"display":"flex","alignItems":"center"}),
        ], style={"display":"flex","justifyContent":"space-between",
                  "alignItems":"center","marginBottom":"16px"}),

        # Main Grid
        html.Div([

            # LEFT COLUMN
            html.Div([

                # Today's Games
                html.Div([
                    html.Div([
                        html.Span("Today's Games", style={"fontWeight":"600","fontSize":"14px"}),
                        html.Span(id="games-count", style={
                            "background":C["blue"],"color":"#fff","padding":"1px 8px",
                            "borderRadius":"10px","fontSize":"11px","float":"right"
                        }),
                    ], style={"padding":"12px 16px","borderBottom":f"1px solid {C['border']}"}),
                    html.Div(id="games-list", style={"padding":"8px"}),
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
                    html.Div(id="open-pos", style={"padding":"4px"}),
                ], style={"background":C["card"],"border":f"1px solid {C['border']}",
                          "borderRadius":"8px","marginBottom":"12px"}),

                # Manual Bet
                html.Div([
                    html.Div("Manual Bet Input",
                        style={"padding":"12px 16px","fontWeight":"600","fontSize":"14px",
                               "borderBottom":f"1px solid {C['border']}"}),
                    html.Div([
                        html.Div([
                            dbc.Input(id="m-game", placeholder="Lakers vs Celtics", size="sm",
                                style={"marginBottom":"8px","background":C["card2"],
                                       "border":f"1px solid {C['border']}","color":C["text"]}),
                            dbc.Input(id="m-fav", placeholder="ფავი (Lakers)", size="sm",
                                style={"marginBottom":"8px","background":C["card2"],
                                       "border":f"1px solid {C['border']}","color":C["text"]}),
                        ]),
                        html.Div([
                            dbc.Input(id="m-odds", placeholder="კოეფი 1.65", type="number",
                                size="sm", style={"marginBottom":"8px","background":C["card2"],
                                "border":f"1px solid {C['border']}","color":C["text"]}),
                            dbc.Input(id="m-open", placeholder="Opening 1.72", type="number",
                                size="sm", style={"marginBottom":"8px","background":C["card2"],
                                "border":f"1px solid {C['border']}","color":C["text"]}),
                            dbc.Select(id="m-tier", size="sm",
                                options=[{"label":"Tier A","value":"A"},
                                         {"label":"Tier B","value":"B"},
                                         {"label":"Tier C","value":"C"}],
                                value="B",
                                style={"marginBottom":"8px","background":C["card2"],
                                       "border":f"1px solid {C['border']}","color":C["text"]}),
                            dbc.Select(id="m-sharp", size="sm",
                                options=[{"label":"Sharp: —","value":"0"},
                                         {"label":"🟡 Medium","value":"1"},
                                         {"label":"🔥 Strong","value":"2"}],
                                value="0",
                                style={"marginBottom":"8px","background":C["card2"],
                                       "border":f"1px solid {C['border']}","color":C["text"]}),
                        ]),
                        html.P(id="m-calc", style={"color":C["green"],"fontSize":"12px","marginBottom":"8px"}),
                        html.Button("+ ბეთის დამატება", id="btn-add",
                            style={"background":C["success"],"color":"#fff","border":"none",
                                   "padding":"7px 16px","borderRadius":"6px","fontSize":"13px",
                                   "fontWeight":"600","cursor":"pointer","width":"100%"}),
                        html.Span(id="add-fb", style={"color":C["green"],"fontSize":"12px",
                                                       "display":"block","marginTop":"6px"}),
                    ], style={"padding":"12px 16px"}),
                ], style={"background":C["card"],"border":f"1px solid {C['border']}",
                          "borderRadius":"8px"}),

            ], style={"flex":"1","marginRight":"12px"}),

            # RIGHT COLUMN
            html.Div([

                # Recent Trades
                html.Div([
                    html.Div([
                        html.Span("Recent Trades", style={"fontWeight":"600","fontSize":"14px"}),
                        html.Span(id="trades-count", style={
                            "background":C["purple"],"color":"#fff","padding":"1px 8px",
                            "borderRadius":"10px","fontSize":"11px","float":"right"
                        }),
                    ], style={"padding":"12px 16px","borderBottom":f"1px solid {C['border']}"}),
                    html.Div(id="recent-trades", style={"padding":"4px","maxHeight":"400px","overflowY":"auto"}),
                ], style={"background":C["card"],"border":f"1px solid {C['border']}",
                          "borderRadius":"8px","marginBottom":"12px"}),

                # Win Rate
                html.Div([
                    html.Div("Statistics",
                        style={"padding":"12px 16px","fontWeight":"600","fontSize":"14px",
                               "borderBottom":f"1px solid {C['border']}"}),
                    html.Div(id="stats-detail", style={"padding":"12px 16px"}),
                ], style={"background":C["card"],"border":f"1px solid {C['border']}",
                          "borderRadius":"8px"}),

            ], style={"width":"380px"}),

        ], style={"display":"flex","marginBottom":"16px"}),

        # Portfolio Chart
        html.Div([
            html.Div("Portfolio Value",
                style={"padding":"12px 16px","fontWeight":"600","fontSize":"14px",
                       "borderBottom":f"1px solid {C['border']}"}),
            html.Div([dcc.Graph(id="portfolio-chart", style={"height":"180px"},
                config={"displayModeBar": False})],
                style={"padding":"8px 16px"}),
        ], style={"background":C["card"],"border":f"1px solid {C['border']}","borderRadius":"8px"}),

    ], style={"padding":"16px 24px","background":C["bg"],"minHeight":"calc(100vh - 52px)"}),

    dcc.Interval(id="interval", interval=30*1000, n_intervals=0),

], style={"background":C["bg"],"fontFamily":"-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif",
          "color":C["text"]})


# ── Main Callback ─────────────────────────────────

@app.callback(
    [Output("s-bankroll","children"), Output("s-cash","children"),
     Output("s-dpnl","children"), Output("s-tpnl","children"),
     Output("s-open","children"), Output("s-daily","children"),
     Output("games-list","children"), Output("games-count","children"),
     Output("open-pos","children"), Output("open-count","children"),
     Output("recent-trades","children"), Output("trades-count","children"),
     Output("portfolio-chart","figure"),
     Output("stats-detail","children"),
     Output("refresh-time","children"),
     Output("mode-badge-top","children"),
     Output("mode-badge-top","style"),
     Output("run-dot","style"),
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
        bot.set_setting("mode", "live" if live else "paper")
    if "btn-run" in trig:
        bot.set_setting("running","true")
        trades, _ = bot.analyze_games()
        for t in trades:
            bot.save_trade(t)
    if "btn-pause" in trig:
        bot.set_setting("running","false")

    stats   = bot.get_stats()
    trades  = bot.get_trades(100)
    history = bot.get_portfolio_history()

    # Stat cards
    bk = stats["bankroll"]
    pnl_c = C["green2"] if stats["pnl"]>=0 else C["red"]
    dpnl_c = C["green2"] if stats["daily_pnl"]>=0 else C["red"]

    def pnl_span(v,c): return html.Span(f"${v:+.2f}", style={"color":c,"fontFamily":"monospace","fontSize":"28px","fontWeight":"700"})

    # Games from ESPN
    games = bot.get_todays_games()
    if games:
        game_els = []
        for g in games:
            h_odds = g.get("h_odds","—")
            a_odds = g.get("a_odds","—")
            fav = g["home"] if (h_odds and a_odds and h_odds<=a_odds) else g["away"]
            fav_odds = min(h_odds,a_odds) if h_odds and a_odds else "—"
            in_range = 1.22 <= fav_odds <= 1.82 if isinstance(fav_odds, float) else False
            game_els.append(html.Div([
                html.Div([
                    html.Span(g["home"][:18], style={"fontWeight":"500","fontSize":"13px"}),
                    html.Span(" vs ", style={"color":C["muted"],"fontSize":"12px"}),
                    html.Span(g["away"][:18], style={"fontWeight":"500","fontSize":"13px"}),
                ]),
                html.Div([
                    html.Span(f"Fav: {fav_odds}", style={
                        "color":C["green2"] if in_range else C["muted"],
                        "fontSize":"12px","fontFamily":"monospace"
                    }),
                    html.Span("✓ In range" if in_range else "✗ Skip", style={
                        "color":C["green2"] if in_range else C["red"],
                        "fontSize":"11px","marginLeft":"8px"
                    }),
                ]),
            ], style={"padding":"8px 12px","borderBottom":f"1px solid {C['border']}",
                      "display":"flex","justifyContent":"space-between","alignItems":"center"}))
        games_el = game_els if game_els else [html.P("ESPN: თამაშები ვერ ჩამოიტვირთა",
            style={"color":C["muted"],"padding":"12px","textAlign":"center","fontSize":"13px"})]
        games_count = str(len(games))
    else:
        games_el = [html.P("ESPN-დან თამაშები ვერ ჩამოიტვირთა",
            style={"color":C["muted"],"padding":"12px","textAlign":"center","fontSize":"13px"})]
        games_count = "0"

    # Open positions
    pending = [t for t in trades if t["result"]=="PENDING"]
    if pending:
        rows = []
        for t in pending:
            sh_icon = {"Strong":"🔥","Medium":"🟡"}.get(t.get("sharp_label",""),"—")
            tier_colors = {"A":C["green"],"B":C["blue"],"C":C["yellow"]}
            rows.append(html.Div([
                html.Div([
                    html.Div(t["game"][:32], style={"fontSize":"12px","color":C["text"],"marginBottom":"2px"}),
                    html.Div([
                        html.Span(t["fav"][:16], style={"fontWeight":"600","fontSize":"13px","marginRight":"8px"}),
                        html.Span(f"@{t['odds']}", style={"fontFamily":"monospace","color":C["blue"],"fontSize":"12px"}),
                        html.Span(f" {sh_icon}", style={"marginLeft":"6px"}),
                    ]),
                ]),
                html.Div([
                    html.Span(f"Tier {t['tier']}", style={
                        "background":tier_colors.get(t['tier'],C["muted"]),
                        "color":"#fff","padding":"1px 6px","borderRadius":"4px",
                        "fontSize":"11px","marginRight":"6px"
                    }),
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
                    html.Span(t["fav"][:16], style={"fontSize":"13px","fontWeight":"500"}),
                ]),
                html.Div([
                    html.Span(f"@{t['odds']}", style={"fontFamily":"monospace","fontSize":"12px",
                                                        "color":C["muted"],"marginRight":"8px"}),
                    html.Span(f"${t['pnl']:+.2f}" if t['pnl'] else "—", style={
                        "color":C["green2"] if won else C["red"],
                        "fontFamily":"monospace","fontSize":"13px","fontWeight":"600"
                    }),
                    html.Span("✅" if won else "❌", style={"marginLeft":"6px","fontSize":"11px"}),
                ]),
            ], style={"display":"flex","justifyContent":"space-between","alignItems":"center",
                      "padding":"7px 12px","borderBottom":f"1px solid {C['border']}"}))
        recent_el = rows
    else:
        recent_el = [html.P("ბეთი ჯერ არ არის",
            style={"color":C["muted"],"padding":"16px","textAlign":"center","fontSize":"13px"})]

    # Portfolio chart
    if history and len(history)>1:
        times  = [h[0] for h in history]
        values = [h[1] for h in history]
    else:
        times  = [datetime.now().strftime("%H:%M")]
        values = [bk]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=times, y=values, mode="lines", fill="tozeroy",
        line=dict(color=C["blue"],width=2),
        fillcolor="rgba(88,166,255,0.08)"
    ))
    fig.update_layout(
        plot_bgcolor=C["card"], paper_bgcolor=C["card"],
        font=dict(color=C["text"],family="-apple-system,sans-serif"),
        margin=dict(l=50,r=10,t=5,b=30),
        xaxis=dict(gridcolor=C["border"],showgrid=True,zeroline=False),
        yaxis=dict(gridcolor=C["border"],showgrid=True,zeroline=False,tickprefix="$"),
        showlegend=False
    )

    # Stats detail
    total_done = len(done)
    wins = sum(1 for t in done if t["result"]=="WIN")
    wr = f"{wins/total_done*100:.1f}%" if total_done else "—"
    avg_odds = sum(t["odds"] for t in done)/total_done if total_done else 0
    stats_el = html.Div([
        html.Div([
            html.Div([html.P("Win Rate",style={"color":C["muted"],"fontSize":"11px","marginBottom":"2px"}),
                      html.P(wr,style={"color":C["green2"],"fontWeight":"700","fontSize":"18px","fontFamily":"monospace"})]),
            html.Div([html.P("Total Bets",style={"color":C["muted"],"fontSize":"11px","marginBottom":"2px"}),
                      html.P(str(total_done),style={"color":C["text"],"fontWeight":"700","fontSize":"18px","fontFamily":"monospace"})]),
            html.Div([html.P("Avg Odds",style={"color":C["muted"],"fontSize":"11px","marginBottom":"2px"}),
                      html.P(f"{avg_odds:.2f}" if avg_odds else "—",
                             style={"color":C["blue"],"fontWeight":"700","fontSize":"18px","fontFamily":"monospace"})]),
            html.Div([html.P("W/L",style={"color":C["muted"],"fontSize":"11px","marginBottom":"2px"}),
                      html.P(f"{wins}/{total_done-wins}",
                             style={"color":C["text"],"fontWeight":"700","fontSize":"18px","fontFamily":"monospace"})]),
        ], style={"display":"grid","gridTemplateColumns":"repeat(4,1fr)","gap":"8px"}),
    ])

    # Mode badge
    mode = bot.get_setting("mode") or "paper"
    is_paper = mode == "paper"
    mode_txt = "PAPER MODE" if is_paper else "⚡ LIVE MODE"
    mode_style = {
        "background":C["yellow"] if is_paper else C["red"],
        "color":"#000" if is_paper else "#fff",
        "padding":"2px 10px","borderRadius":"4px","fontSize":"11px","fontWeight":"700","marginLeft":"8px"
    }

    # Run dot
    is_running = bot.get_setting("running") == "true"
    dot_style = {"color":C["green2"] if is_running else C["red"],"fontSize":"10px","marginRight":"6px"}

    # Calc hint
    calc_hint = ""
    if odds_v:
        try:
            bk_v = bk
            sh_b = [0,6,14][int(sharp or 0)]
            mp = 1/float(odds_v)
            p = min(0.95, mp+(5+sh_b*0.5)/100)
            k = max(0,((float(odds_v)-1)*p-(1-p))/(float(odds_v)-1))
            f = {"A":0.25,"B":0.18,"C":0.10}.get(tier,0.18)
            st = round(max(12,min(bk_v*0.12,bk_v*k*f)),2)
            ev = round(p*(float(odds_v)-1)-(1-p),4)
            calc_hint = f"Stake: ${st:.2f} | Model: {p:.1%} | EV: {ev:+.3f}"
        except: pass

    rt = f"Last refresh: {datetime.now().strftime('%H:%M:%S')}"

    return (
        f"${bk:.2f}", f"${bk:.2f}",
        pnl_span(stats["daily_pnl"], dpnl_c),
        pnl_span(stats["pnl"], pnl_c),
        str(stats["open_positions"]),
        str(stats["daily_trades"]),
        games_el, games_count,
        open_el, str(len(pending)),
        recent_el, str(len(done)),
        fig, stats_el, rt,
        mode_txt, mode_style, dot_style, calc_hint
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
        trade = {
            "game":game,"fav":fav,"odds":odds,"open_odds":open_o,
            "sharp":sh,"sharp_label":["—","Medium","Strong"][sh],
            "tier":tier,"score":60.0,
            "edge":round(p-mp,4),"ev":round(p*(odds-1)-(1-p),4),
            "stake":st,"pot":round(st*(odds-1),2)
        }
        bot.save_trade(trade)
        return f"✅ ბეთი შენახულია! ${st:.2f}"
    except Exception as e:
        return f"❌ Error: {e}"


if __name__ == "__main__":
    print("\n🏀 NBA Polymarket Agent v2.0")
    print("━"*40)
    print("→ http://localhost:8050")
    print("━"*40+"\n")
    app.run(debug=False, host="0.0.0.0", port=8050)
