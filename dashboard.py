# ════════════════════════════════════════════════════
# dashboard.py — Polymarket NBA Agent Dashboard
# pip install dash dash-bootstrap-components plotly
# python dashboard.py → localhost:8050
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
    external_stylesheets=[dbc.themes.DARKLY],
    title="NBA Polymarket Agent"
)

# ── Colors ────────────────────────────────────────
C = {
    "bg":     "#0d1117",
    "card":   "#161b22",
    "border": "#30363d",
    "green":  "#2ea043",
    "red":    "#da3633",
    "blue":   "#58a6ff",
    "yellow": "#d29922",
    "text":   "#c9d1d9",
    "muted":  "#8b949e",
}

def badge(text, color):
    return html.Span(text, style={
        "background": color,
        "color": "#fff",
        "padding": "2px 8px",
        "borderRadius": "4px",
        "fontSize": "11px",
        "fontWeight": "600",
    })

def stat_card(title, value_id, subtitle=""):
    return dbc.Card([
        dbc.CardBody([
            html.P(title, style={"color": C["muted"], "fontSize": "12px", "marginBottom": "4px"}),
            html.H3("—", id=value_id, style={"color": C["text"], "fontWeight": "600", "marginBottom": "2px"}),
            html.P(subtitle, style={"color": C["muted"], "fontSize": "11px", "marginBottom": "0"}),
        ])
    ], style={"background": C["card"], "border": f"1px solid {C['border']}"})

# ── Layout ────────────────────────────────────────
app.layout = dbc.Container([

    # Header
    dbc.Row([
        dbc.Col([
            html.Div([
                html.H4("Polymarket", style={"color": C["text"], "display": "inline", "marginRight": "4px"}),
                html.H4("NBA Agent", style={"color": C["blue"], "display": "inline"}),
                html.Span("  "),
                html.Span("● RUNNING", id="status-badge", style={
                    "color": "#fff", "background": C["green"],
                    "padding": "3px 10px", "borderRadius": "12px",
                    "fontSize": "12px", "fontWeight": "600",
                }),
            ])
        ], width=6),
        dbc.Col([
            html.Div([
                html.Span("PAPER MODE", id="mode-badge", style={
                    "color": "#000", "background": C["yellow"],
                    "padding": "3px 10px", "borderRadius": "4px",
                    "fontSize": "12px", "fontWeight": "700",
                    "marginRight": "12px",
                }),
                html.Span(id="last-refresh", style={"color": C["muted"], "fontSize": "12px"}),
            ], style={"textAlign": "right", "paddingTop": "8px"})
        ], width=6),
    ], style={"padding": "16px 0 8px 0", "borderBottom": f"1px solid {C['border']}"}),

    html.Br(),

    # Stat Cards
    dbc.Row([
        dbc.Col(stat_card("TOTAL VALUE", "stat-bankroll", "current portfolio"), width=2),
        dbc.Col(stat_card("CASH BALANCE", "stat-cash", "available"), width=2),
        dbc.Col(stat_card("DAILY P&L", "stat-daily-pnl", "today"), width=2),
        dbc.Col(stat_card("TOTAL P&L", "stat-total-pnl", "all time"), width=2),
        dbc.Col(stat_card("OPEN POSITIONS", "stat-open", "active markets"), width=2),
        dbc.Col(stat_card("DAILY TRADES", "stat-daily", "today"), width=2),
    ], className="mb-3"),

    # Controls
    dbc.Row([
        dbc.Col([
            dbc.Button("▶ Run Analysis", id="btn-run", color="success", size="sm", className="me-2"),
            dbc.Button("⏸ Pause", id="btn-pause", color="secondary", size="sm", className="me-2"),
            dbc.Button("🔄 Refresh", id="btn-refresh", color="primary", size="sm"),
        ], width=6),
        dbc.Col([
            dbc.Switch(id="mode-switch", label="Live Mode", value=False, style={"color": C["muted"]}),
        ], width=6, style={"textAlign": "right"}),
    ], className="mb-3"),

    # Main Content
    dbc.Row([
        # Left — Open Positions + Manual Bet
        dbc.Col([
            # Open Positions
            dbc.Card([
                dbc.CardHeader([
                    html.Span("Open Positions", style={"fontWeight": "600"}),
                    html.Span(id="open-count", style={
                        "float": "right", "background": C["blue"],
                        "color": "#fff", "padding": "1px 8px",
                        "borderRadius": "10px", "fontSize": "12px"
                    })
                ], style={"background": C["card"], "borderColor": C["border"]}),
                dbc.CardBody([
                    html.Div(id="open-positions-table")
                ], style={"padding": "0"})
            ], style={"background": C["card"], "border": f"1px solid {C['border']}"}),

            html.Br(),

            # Manual Bet Input
            dbc.Card([
                dbc.CardHeader("Manual Bet Input", style={
                    "background": C["card"], "borderColor": C["border"], "fontWeight": "600"
                }),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([dbc.Input(id="inp-game", placeholder="Lakers vs Celtics", size="sm")], width=6),
                        dbc.Col([dbc.Input(id="inp-fav", placeholder="ფავი (Lakers)", size="sm")], width=6),
                    ], className="mb-2"),
                    dbc.Row([
                        dbc.Col([dbc.Input(id="inp-odds", placeholder="კოეფი 1.65", type="number", size="sm")], width=3),
                        dbc.Col([dbc.Input(id="inp-open", placeholder="Opening 1.72", type="number", size="sm")], width=3),
                        dbc.Col([dbc.Select(id="inp-tier", options=[
                            {"label":"Tier A","value":"A"},
                            {"label":"Tier B","value":"B"},
                            {"label":"Tier C","value":"C"},
                        ], value="B", size="sm")], width=3),
                        dbc.Col([dbc.Select(id="inp-sharp", options=[
                            {"label":"Sharp: —","value":"0"},
                            {"label":"Medium 🟡","value":"1"},
                            {"label":"Strong 🔥","value":"2"},
                        ], value="0", size="sm")], width=3),
                    ], className="mb-2"),
                    dbc.Row([
                        dbc.Col([
                            html.P(id="calc-stake", style={"color": C["green"], "fontSize": "13px", "marginBottom": "8px"}),
                        ]),
                    ]),
                    dbc.Button("+ ბეთის დამატება", id="btn-add-bet", color="success", size="sm"),
                    html.Span(id="bet-feedback", style={"color": C["green"], "fontSize": "12px", "marginLeft": "12px"}),
                ])
            ], style={"background": C["card"], "border": f"1px solid {C['border']}"}),

        ], width=7),

        # Right — Recent Trades
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.Span("Recent Trades", style={"fontWeight": "600"}),
                    html.Span(id="trades-count", style={
                        "float": "right", "background": C["muted"],
                        "color": "#fff", "padding": "1px 8px",
                        "borderRadius": "10px", "fontSize": "12px"
                    })
                ], style={"background": C["card"], "borderColor": C["border"]}),
                dbc.CardBody([
                    html.Div(id="recent-trades-table")
                ], style={"padding": "0"})
            ], style={"background": C["card"], "border": f"1px solid {C['border']}"})
        ], width=5),
    ]),

    html.Br(),

    # Portfolio Chart
    dbc.Card([
        dbc.CardHeader("Portfolio Value", style={
            "background": C["card"], "borderColor": C["border"], "fontWeight": "600"
        }),
        dbc.CardBody([
            dcc.Graph(id="portfolio-chart", style={"height": "200px"})
        ])
    ], style={"background": C["card"], "border": f"1px solid {C['border']}"}),

    # Auto-refresh
    dcc.Interval(id="interval", interval=30*1000, n_intervals=0),
    dcc.Store(id="store"),

], fluid=True, style={"background": C["bg"], "minHeight": "100vh", "color": C["text"]})


# ── Callbacks ─────────────────────────────────────

@app.callback(
    [Output("stat-bankroll","children"), Output("stat-cash","children"),
     Output("stat-daily-pnl","children"), Output("stat-total-pnl","children"),
     Output("stat-open","children"), Output("stat-daily","children"),
     Output("open-positions-table","children"),
     Output("recent-trades-table","children"),
     Output("portfolio-chart","figure"),
     Output("last-refresh","children"),
     Output("open-count","children"),
     Output("trades-count","children"),
     Output("status-badge","children"),
     Output("mode-badge","children"),
     Output("mode-badge","style"),
     Output("calc-stake","children")],
    [Input("interval","n_intervals"),
     Input("btn-refresh","n_clicks"),
     Input("btn-run","n_clicks"),
     Input("btn-pause","n_clicks"),
     Input("inp-odds","value"),
     Input("inp-tier","value"),
     Input("inp-sharp","value"),
     Input("mode-switch","value")],
    prevent_initial_call=False
)
def update_all(n, ref, run, pause, odds_val, tier, sharp, live_mode):
    ctx = callback_context
    triggered = ctx.triggered[0]["prop_id"] if ctx.triggered else ""

    # Mode switch
    if "mode-switch" in triggered:
        bot.set_setting("mode", "live" if live_mode else "paper")

    # Run analysis
    if "btn-run" in triggered:
        bot.set_setting("running", "true")
        trades, log = bot.analyze_games()
        for t in trades:
            bot.save_trade(t)

    # Pause
    if "btn-pause" in triggered:
        bot.set_setting("running", "false")

    stats = bot.get_stats()
    trades = bot.get_trades(50)
    history = bot.get_portfolio_history()

    # Stat cards
    pnl_color = C["green"] if stats["pnl"] >= 0 else C["red"]
    dpnl_color = C["green"] if stats["daily_pnl"] >= 0 else C["red"]

    bk_str = f"${stats['bankroll']:.2f}"
    cash_str = f"${stats['bankroll']:.2f}"
    dpnl_str = html.Span(f"{stats['daily_pnl']:+.2f}", style={"color": dpnl_color})
    tpnl_str = html.Span(f"{stats['pnl']:+.2f}", style={"color": pnl_color})
    open_str = str(stats["open_positions"])
    daily_str = str(stats["daily_trades"])

    # Open positions
    pending = [t for t in trades if t["result"] == "PENDING"]
    if pending:
        rows = []
        for t in pending:
            sharp_badge = {"Strong": "🔥", "Medium": "🟡"}.get(t["sharp_label"], "—")
            rows.append(html.Tr([
                html.Td(t["game"][:35], style={"fontSize":"12px","padding":"6px 8px"}),
                html.Td(t["fav"][:16], style={"fontWeight":"500","padding":"6px 8px"}),
                html.Td(sharp_badge, style={"padding":"6px 8px"}),
                html.Td(html.Span(t["tier"], style={
                    "background": {"A":C["green"],"B":C["blue"],"C":C["yellow"]}.get(t["tier"],C["muted"]),
                    "color":"#fff","padding":"1px 6px","borderRadius":"4px","fontSize":"11px"
                }), style={"padding":"6px 8px"}),
                html.Td(f"${t['stake']:.2f}", style={"padding":"6px 8px"}),
                html.Td(f"+${t['pot']:.2f}", style={"color":C["green"],"padding":"6px 8px"}),
                html.Td([
                    dbc.Button("W", id={"type":"btn-win","index":t["id"]}, color="success", size="sm", style={"padding":"1px 8px","fontSize":"11px","marginRight":"4px"}),
                    dbc.Button("L", id={"type":"btn-loss","index":t["id"]}, color="danger", size="sm", style={"padding":"1px 8px","fontSize":"11px"}),
                ], style={"padding":"6px 8px"}),
            ]))
        open_table = html.Table([
            html.Thead(html.Tr([
                html.Th("თამაში",style={"padding":"6px 8px","fontSize":"11px","color":C["muted"],"fontWeight":"500"}),
                html.Th("ფავი",style={"padding":"6px 8px","fontSize":"11px","color":C["muted"],"fontWeight":"500"}),
                html.Th("Sharp",style={"padding":"6px 8px","fontSize":"11px","color":C["muted"],"fontWeight":"500"}),
                html.Th("Tier",style={"padding":"6px 8px","fontSize":"11px","color":C["muted"],"fontWeight":"500"}),
                html.Th("Stake",style={"padding":"6px 8px","fontSize":"11px","color":C["muted"],"fontWeight":"500"}),
                html.Th("პოტ.",style={"padding":"6px 8px","fontSize":"11px","color":C["muted"],"fontWeight":"500"}),
                html.Th("შედ.",style={"padding":"6px 8px","fontSize":"11px","color":C["muted"],"fontWeight":"500"}),
            ]), style={"borderBottom":f"1px solid {C['border']}"}),
            html.Tbody(rows)
        ], style={"width":"100%","borderCollapse":"collapse"})
    else:
        open_table = html.P("ღია პოზიცია არ არის", style={"color":C["muted"],"padding":"16px","textAlign":"center","fontSize":"13px"})

    # Recent trades
    done = [t for t in trades if t["result"] != "PENDING"][:20]
    if done:
        rows = []
        for t in done:
            pnl_c = C["green"] if t["pnl"] > 0 else C["red"]
            status_bg = C["green"] if t["result"]=="WIN" else C["red"]
            sharp_badge = {"Strong": "🔥", "Medium": "🟡"}.get(t["sharp_label"], "—")
            rows.append(html.Tr([
                html.Td(t["timestamp"], style={"fontSize":"11px","color":C["muted"],"padding":"5px 8px"}),
                html.Td(t["game"][:28], style={"fontSize":"12px","padding":"5px 8px"}),
                html.Td(sharp_badge, style={"padding":"5px 8px"}),
                html.Td(f"{t['edge']:+.1%}", style={"fontSize":"12px","padding":"5px 8px","color":C["blue"]}),
                html.Td(html.Span(t["result"], style={
                    "background":status_bg,"color":"#fff",
                    "padding":"1px 6px","borderRadius":"4px","fontSize":"11px"
                }), style={"padding":"5px 8px"}),
            ]))
        recent_table = html.Table([
            html.Thead(html.Tr([
                html.Th("დრო",style={"padding":"5px 8px","fontSize":"11px","color":C["muted"],"fontWeight":"500"}),
                html.Th("თამაში",style={"padding":"5px 8px","fontSize":"11px","color":C["muted"],"fontWeight":"500"}),
                html.Th("Sharp",style={"padding":"5px 8px","fontSize":"11px","color":C["muted"],"fontWeight":"500"}),
                html.Th("Edge",style={"padding":"5px 8px","fontSize":"11px","color":C["muted"],"fontWeight":"500"}),
                html.Th("Status",style={"padding":"5px 8px","fontSize":"11px","color":C["muted"],"fontWeight":"500"}),
            ]), style={"borderBottom":f"1px solid {C['border']}"}),
            html.Tbody(rows)
        ], style={"width":"100%","borderCollapse":"collapse"})
    else:
        recent_table = html.P("ბეთი ჯერ არ არის", style={"color":C["muted"],"padding":"16px","textAlign":"center","fontSize":"13px"})

    # Portfolio chart
    if history:
        times = [h[0] for h in history]
        values = [h[1] for h in history]
    else:
        times = [datetime.now().strftime("%H:%M")]
        values = [stats["bankroll"]]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=times, y=values,
        mode="lines", fill="tozeroy",
        line=dict(color=C["blue"], width=2),
        fillcolor="rgba(88,166,255,0.1)"
    ))
    fig.update_layout(
        plot_bgcolor=C["card"], paper_bgcolor=C["card"],
        font=dict(color=C["text"]),
        margin=dict(l=40,r=10,t=10,b=30),
        xaxis=dict(gridcolor=C["border"], showgrid=True),
        yaxis=dict(gridcolor=C["border"], showgrid=True),
        showlegend=False
    )

    # Status + Mode badges
    is_running = stats["running"]
    status_text = "● RUNNING" if is_running else "■ PAUSED"
    status_style = {
        "color":"#fff", "background": C["green"] if is_running else C["muted"],
        "padding":"3px 10px","borderRadius":"12px","fontSize":"12px","fontWeight":"600"
    }

    mode = bot.get_setting("mode")
    mode_text = "PAPER MODE" if mode=="paper" else "LIVE MODE"
    mode_style = {
        "color":"#000", "background": C["yellow"] if mode=="paper" else C["red"],
        "padding":"3px 10px","borderRadius":"4px","fontSize":"12px","fontWeight":"700","marginRight":"12px"
    }

    # Calc stake hint
    calc_hint = ""
    if odds_val:
        try:
            bk = stats["bankroll"]
            sh_bonus = [0,6,14][int(sharp or 0)]
            mp = 1/float(odds_val)
            edge_est = (5+sh_bonus*0.5)/100
            p = min(0.95, mp+edge_est)
            k = max(0,((float(odds_val)-1)*p-(1-p))/(float(odds_val)-1))
            f = {"A":0.25,"B":0.18,"C":0.10}.get(tier,0.18)
            st = round(max(12,min(bk*0.12,bk*k*f)),2)
            calc_hint = f"Kelly Stake: ${st:.2f} | Model: {p:.1%} | Market: {mp:.1%}"
        except:
            pass

    refresh_str = f"Last refresh: {datetime.now().strftime('%H:%M:%S')}"

    return (bk_str, cash_str, dpnl_str, tpnl_str, open_str, daily_str,
            open_table, recent_table, fig,
            refresh_str, str(len(pending)), str(len(done)),
            status_text, mode_text, mode_style, calc_hint)


@app.callback(
    Output("bet-feedback","children"),
    Input("btn-add-bet","n_clicks"),
    [State("inp-game","value"), State("inp-fav","value"),
     State("inp-odds","value"), State("inp-open","value"),
     State("inp-tier","value"), State("inp-sharp","value")],
    prevent_initial_call=True
)
def add_manual_bet(n, game, fav, odds, open_odds, tier, sharp):
    if not all([game, fav, odds]):
        return "შეავსე ყველა ველი!"
    try:
        bk = bot.get_bankroll()
        odds = float(odds)
        open_odds = float(open_odds or odds)
        sh = int(sharp or 0)
        sh_bonus = [0,6,14][sh]
        mp = 1/odds
        p = min(0.95, mp + (5+sh_bonus*0.5)/100)
        k = max(0,((odds-1)*p-(1-p))/(odds-1))
        f = {"A":0.25,"B":0.18,"C":0.10}.get(tier,0.18)
        st = round(max(12,min(bk*0.12,bk*k*f)),2)

        trade = {
            "game": game, "fav": fav,
            "odds": odds, "open_odds": open_odds,
            "sharp": sh, "sharp_label": ["—","Medium","Strong"][sh],
            "tier": tier, "score": 60.0,
            "edge": round(p-mp,4), "ev": round(p*(odds-1)-(1-p),4),
            "stake": st, "pot": round(st*(odds-1),2)
        }
        bot.save_trade(trade)
        return f"✓ ბეთი შენახულია! ${st:.2f}"
    except Exception as e:
        return f"Error: {e}"


if __name__ == "__main__":
    print("\n🏀 NBA Polymarket Agent Dashboard")
    print("━" * 40)
    print("→ გადადი: http://localhost:8050")
    print("━" * 40 + "\n")
    app.run(debug=False, host="0.0.0.0", port=8050)
