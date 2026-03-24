import bot
import dash
from dash import dcc, html, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from datetime import datetime

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

def mk_card(title, val_id, sub=""):
    return html.Div([
        html.P(title, style={
            "color":C["muted"],"fontSize":"11px","fontWeight":"600",
            "letterSpacing":"0.5px","marginBottom":"6px","textTransform":"uppercase"
        }),
        html.H2("—", id=val_id, style={
            "color":C["text"],"fontWeight":"700",
            "fontSize":"24px","marginBottom":"2px","fontFamily":"monospace"
        }),
        html.P(sub, style={"color":C["muted"],"fontSize":"11px","marginBottom":"0"}),
    ], style={
        "background":C["card"],"border":f"1px solid {C['border']}",
        "borderRadius":"8px","padding":"14px 18px"
    })

app.layout = html.Div([

    # Header
    html.Div([
        html.Div([
            html.Span("●", id="run-dot",
                style={"color":C["green"],"fontSize":"10px","marginRight":"6px"}),
            html.Span("NBA", style={"color":C["text"],"fontWeight":"700","fontSize":"18px"}),
            html.Span(" Polymarket Agent",
                style={"color":C["blue"],"fontWeight":"700","fontSize":"18px"}),
            html.Span("PAPER MODE", id="mode-badge", style={
                "background":C["yellow"],"color":"#000","padding":"2px 10px",
                "borderRadius":"4px","fontSize":"11px","fontWeight":"700","marginLeft":"12px"
            }),
        ], style={"display":"flex","alignItems":"center","flex":"1"}),
        html.Div([
            html.Span(id="api-status",
                style={"color":C["muted"],"fontSize":"11px","marginRight":"16px"}),
            html.Span(id="refresh-time",
                style={"color":C["muted"],"fontSize":"12px"}),
        ], style={"display":"flex","alignItems":"center"}),
    ], style={
        "display":"flex","justifyContent":"space-between","alignItems":"center",
        "padding":"12px 24px","borderBottom":f"1px solid {C['border']}",
        "background":C["card"]
    }),

    html.Div([

        # Stat Cards
        html.Div([
            mk_card("TOTAL VALUE",    "s-bankroll",  "portfolio"),
            mk_card("DAILY P&L",      "s-dpnl",      "today"),
            mk_card("TOTAL P&L",      "s-tpnl",      "all time"),
            mk_card("OPEN POSITIONS", "s-open",      "active"),
            mk_card("WIN RATE",       "s-wr",        "completed"),
            mk_card("DAILY TRADES",   "s-daily",     "today"),
        ], style={
            "display":"grid","gridTemplateColumns":"repeat(6,1fr)",
            "gap":"10px","marginBottom":"14px"
        }),

        # Controls
        html.Div([
            html.Div([
                html.Button("▶ Run Analysis", id="btn-run", style={
                    "background":C["success"],"color":"#fff","border":"none",
                    "padding":"8px 18px","borderRadius":"6px","fontSize":"13px",
                    "fontWeight":"600","cursor":"pointer","marginRight":"8px"
                }),
                html.Button("⏸ Pause", id="btn-pause", style={
                    "background":"transparent","color":C["text"],
                    "border":f"1px solid {C['border']}","padding":"8px 16px",
                    "borderRadius":"6px","fontSize":"13px","cursor":"pointer","marginRight":"8px"
                }),
                html.Button("🔄 Refresh Odds", id="btn-refresh", style={
                    "background":"transparent","color":C["blue"],
                    "border":f"1px solid {C['blue']}","padding":"8px 16px",
                    "borderRadius":"6px","fontSize":"13px","cursor":"pointer","marginRight":"8px"
                }),
                html.Button("🗑 Reset Opening", id="btn-reset", style={
                    "background":"transparent","color":C["yellow"],
                    "border":f"1px solid {C['yellow']}","padding":"8px 16px",
                    "borderRadius":"6px","fontSize":"13px","cursor":"pointer"
                }),
            ]),
            html.Div([
                html.Span("Paper", style={"color":C["muted"],"fontSize":"13px","marginRight":"8px"}),
                dbc.Switch(id="mode-switch", value=False),
                html.Span("Live", style={"color":C["muted"],"fontSize":"13px","marginLeft":"8px"}),
            ], style={"display":"flex","alignItems":"center"}),
        ], style={
            "display":"flex","justifyContent":"space-between",
            "alignItems":"center","marginBottom":"14px"
        }),

        html.Div([

            # LEFT COLUMN
            html.Div([

                # Today's NBA Games + Odds
                html.Div([
                    html.Div([
                        html.Span("Today's NBA Games", style={"fontWeight":"600","fontSize":"14px"}),
                        html.Span(id="games-count", style={
                            "background":C["blue"],"color":"#fff","padding":"1px 8px",
                            "borderRadius":"10px","fontSize":"11px","float":"right"
                        }),
                    ], style={"padding":"12px 16px","borderBottom":f"1px solid {C['border']}"}),
                    html.Div(id="games-list", style={"maxHeight":"320px","overflowY":"auto"}),
                ], style={
                    "background":C["card"],"border":f"1px solid {C['border']}",
                    "borderRadius":"8px","marginBottom":"12px"
                }),

                # Bot Recommendations
                html.Div([
                    html.Div([
                        html.Span("Bot Recommendations", style={"fontWeight":"600","fontSize":"14px"}),
                        html.Span(id="rec-count", style={
                            "background":C["green"],"color":"#fff","padding":"1px 8px",
                            "borderRadius":"10px","fontSize":"11px","float":"right"
                        }),
                    ], style={"padding":"12px 16px","borderBottom":f"1px solid {C['border']}"}),
                    html.Div(id="rec-list"),
                ], style={
                    "background":C["card"],"border":f"1px solid {C['border']}",
                    "borderRadius":"8px","marginBottom":"12px"
                }),

                # Open Positions
                html.Div([
                    html.Div([
                        html.Span("Open Positions", style={"fontWeight":"600","fontSize":"14px"}),
                        html.Span(id="open-count", style={
                            "background":C["yellow"],"color":"#000","padding":"1px 8px",
                            "borderRadius":"10px","fontSize":"11px","float":"right"
                        }),
                    ], style={"padding":"12px 16px","borderBottom":f"1px solid {C['border']}"}),
                    html.Div(id="open-pos"),
                ], style={
                    "background":C["card"],"border":f"1px solid {C['border']}",
                    "borderRadius":"8px"
                }),

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
                    html.Div(id="recent-trades",
                        style={"maxHeight":"380px","overflowY":"auto"}),
                ], style={
                    "background":C["card"],"border":f"1px solid {C['border']}",
                    "borderRadius":"8px","marginBottom":"12px"
                }),

                # Stats
                html.Div([
                    html.Div("Statistics", style={
                        "padding":"12px 16px","fontWeight":"600","fontSize":"14px",
                        "borderBottom":f"1px solid {C['border']}"
                    }),
                    html.Div(id="stats-box", style={"padding":"12px 16px"}),
                ], style={
                    "background":C["card"],"border":f"1px solid {C['border']}",
                    "borderRadius":"8px"
                }),

            ], style={"width":"380px"}),

        ], style={"display":"flex","marginBottom":"14px"}),

        # Portfolio Chart
        html.Div([
            html.Div("Portfolio Value", style={
                "padding":"12px 16px","fontWeight":"600","fontSize":"14px",
                "borderBottom":f"1px solid {C['border']}"
            }),
            dcc.Graph(id="chart", style={"height":"160px"},
                config={"displayModeBar":False}),
        ], style={
            "background":C["card"],"border":f"1px solid {C['border']}",
            "borderRadius":"8px"
        }),

    ], style={"padding":"16px 24px","background":C["bg"],"minHeight":"calc(100vh - 52px)"}),

    dcc.Interval(id="interval", interval=60*1000, n_intervals=0),
    dcc.Store(id="bot-results", data=[]),

], style={
    "background":C["bg"],
    "fontFamily":"-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif",
    "color":C["text"]
})


@app.callback(
    [Output("s-bankroll","children"), Output("s-dpnl","children"),
     Output("s-tpnl","children"), Output("s-open","children"),
     Output("s-wr","children"), Output("s-daily","children"),
     Output("games-list","children"), Output("games-count","children"),
     Output("rec-list","children"), Output("rec-count","children"),
     Output("open-pos","children"), Output("open-count","children"),
     Output("recent-trades","children"), Output("trades-count","children"),
     Output("chart","figure"),
     Output("stats-box","children"),
     Output("refresh-time","children"),
     Output("api-status","children"),
     Output("mode-badge","children"), Output("mode-badge","style"),
     Output("run-dot","style"),
     Output("bot-results","data")],
    [Input("interval","n_intervals"),
     Input("btn-refresh","n_clicks"),
     Input("btn-run","n_clicks"),
     Input("btn-pause","n_clicks"),
     Input("btn-reset","n_clicks"),
     Input("mode-switch","value")],
    prevent_initial_call=False
)
def update(n, ref, run, pause, reset, live):
    ctx = callback_context
    trig = ctx.triggered[0]["prop_id"] if ctx.triggered else ""

    if "mode-switch" in trig:
        bot.set_setting("mode","live" if live else "paper")
    if "btn-reset" in trig:
        bot.reset_opening_odds()
    if "btn-refresh" in trig:
        bot.get_nba_odds_from_api()

    bot_results = []
    if "btn-run" in trig:
        bot.set_setting("running","true")
        results, log = bot.analyze_games()
        print(f"[RUN] {log}")
        for t in results:
            bot.save_trade(t)
        bot_results = results
    if "btn-pause" in trig:
        bot.set_setting("running","false")

    stats   = bot.get_stats()
    trades  = bot.get_trades(100)
    history = bot.get_portfolio_history()
    bk      = stats["bankroll"]

    def pspan(v):
        c = C["green2"] if v>=0 else C["red"]
        return html.Span(f"${v:+.2f}", style={"color":c,"fontFamily":"monospace",
                                               "fontSize":"24px","fontWeight":"700"})

    # Games list
    games = bot.get_cached_games() or bot.get_todays_games()
    opening = bot.get_opening_odds()

    if games:
        game_els = []
        for g in games:
            h_o = g.get("h_odds")
            a_o = g.get("a_odds")
            if not h_o or not a_o: continue
            fav = g["home"] if h_o<=a_o else g["away"]
            fav_odds = min(h_o,a_o)
            key = f"{g['home']}|{g['away']}"
            h_op = opening.get(key,{}).get("h")
            sharp = ""
            sharp_c = C["muted"]
            if h_op and h_o < h_op:
                drop = (h_op-h_o)/h_op
                if drop >= 0.025:
                    sharp = f" 🔥 {drop:.1%}"
                    sharp_c = C["red"]
                elif drop >= 0.012:
                    sharp = f" 🟡 {drop:.1%}"
                    sharp_c = C["yellow"]
            in_range = 1.22<=fav_odds<=1.82
            game_els.append(html.Div([
                html.Div([
                    html.Span(g["home"][:16],
                        style={"fontWeight":"600" if h_o<=a_o else "400","fontSize":"13px"}),
                    html.Span(" vs ", style={"color":C["muted"],"fontSize":"12px","margin":"0 4px"}),
                    html.Span(g["away"][:16],
                        style={"fontWeight":"600" if a_o<h_o else "400","fontSize":"13px"}),
                ]),
                html.Div([
                    html.Span(f"{h_o}", style={
                        "fontFamily":"monospace","fontSize":"13px",
                        "color":C["green2"] if h_o<=a_o else C["muted"],
                        "marginRight":"8px","fontWeight":"600" if h_o<=a_o else "400"
                    }),
                    html.Span(f"{a_o}", style={
                        "fontFamily":"monospace","fontSize":"13px",
                        "color":C["green2"] if a_o<h_o else C["muted"],
                        "fontWeight":"600" if a_o<h_o else "400"
                    }),
                    html.Span(sharp, style={"color":sharp_c,"fontSize":"12px","marginLeft":"8px"}),
                    html.Span("✓" if in_range else "✗", style={
                        "color":C["green2"] if in_range else C["red"],
                        "fontSize":"12px","marginLeft":"8px"
                    }),
                ]),
            ], style={
                "display":"flex","justifyContent":"space-between","alignItems":"center",
                "padding":"9px 14px","borderBottom":f"1px solid {C['border']}"
            }))
        games_el = game_els
        games_cnt = str(len(games))
    else:
        games_el = [html.P("Odds ჩამოტვირთვა... Run Analysis დააჭირე",
            style={"color":C["muted"],"padding":"16px","textAlign":"center","fontSize":"13px"})]
        games_cnt = "0"

    # Recommendations (ბოტის შედეგები)
    pending_new = [t for t in trades if t["result"]=="PENDING"]
    if pending_new:
        rec_els = []
        for t in pending_new:
            sh = {"Strong":"🔥 Strong","Medium":"🟡 Medium"}.get(t.get("sharp_label",""),"—")
            tc = {"A":C["green"],"B":C["blue"],"C":C["yellow"]}.get(t.get("tier",""),C["muted"])
            rec_els.append(html.Div([
                html.Div([
                    html.Div(f"✅ {t['fav']}", style={"fontWeight":"600","fontSize":"14px","color":C["green2"],"marginBottom":"2px"}),
                    html.Div(t["game"][:40], style={"fontSize":"11px","color":C["muted"]}),
                ]),
                html.Div([
                    html.Div([
                        html.Span(f"@{t['odds']}", style={"fontFamily":"monospace","color":C["blue"],"fontWeight":"700","fontSize":"15px"}),
                        html.Span(f" {sh}", style={"fontSize":"12px","marginLeft":"8px"}),
                    ]),
                    html.Div([
                        html.Span(f"Tier {t['tier']}", style={
                            "background":tc,"color":"#fff","padding":"1px 6px",
                            "borderRadius":"4px","fontSize":"11px","marginRight":"6px"
                        }),
                        html.Span(f"Edge:{t['edge']:+.1%}", style={"color":C["muted"],"fontSize":"11px","marginRight":"6px"}),
                        html.Span(f"EV:{t['ev']:+.3f}", style={"color":C["muted"],"fontSize":"11px"}),
                    ]),
                    html.Div([
                        html.Span(f"💵 ${t['stake']:.2f}", style={"color":C["text"],"fontWeight":"600","fontSize":"13px","marginRight":"8px"}),
                        html.Span(f"→ +${t['pot']:.2f}", style={"color":C["green2"],"fontSize":"13px"}),
                    ]),
                ]),
            ], style={
                "display":"flex","justifyContent":"space-between","alignItems":"flex-start",
                "padding":"10px 14px","borderBottom":f"1px solid {C['border']}"
            }))
        rec_el = rec_els
        rec_cnt = str(len(pending_new))
    else:
        rec_el = [html.P("Run Analysis → ბოტი გაანალიზებს",
            style={"color":C["muted"],"padding":"16px","textAlign":"center","fontSize":"13px"})]
        rec_cnt = "0"

    # Open positions (W/L buttons)
    pending = [t for t in trades if t["result"]=="PENDING"]
    if pending:
        rows = []
        for t in pending:
            sh = {"Strong":"🔥","Medium":"🟡"}.get(t.get("sharp_label",""),"—")
            tc = {"A":C["green"],"B":C["blue"],"C":C["yellow"]}.get(t.get("tier",""),C["muted"])
            rows.append(html.Div([
                html.Div([
                    html.Div(t["game"][:28], style={"fontSize":"11px","color":C["muted"]}),
                    html.Div([
                        html.Span(t["fav"][:14], style={"fontWeight":"600","fontSize":"13px","marginRight":"6px"}),
                        html.Span(f"@{t['odds']}", style={"fontFamily":"monospace","color":C["blue"],"fontSize":"12px"}),
                        html.Span(f" {sh}", style={"marginLeft":"4px"}),
                    ]),
                ]),
                html.Div([
                    html.Span(f"Tier {t['tier']}", style={
                        "background":tc,"color":"#fff","padding":"1px 6px",
                        "borderRadius":"4px","fontSize":"11px","marginRight":"6px"
                    }),
                    html.Span(f"${t['stake']:.0f}→+${t['pot']:.0f}",
                        style={"color":C["muted"],"fontSize":"12px","marginRight":"8px"}),
                    html.Button("W", id={"type":"btn-w","index":t["id"]}, style={
                        "background":C["success"],"color":"#fff","border":"none",
                        "padding":"2px 8px","borderRadius":"4px","fontSize":"11px",
                        "cursor":"pointer","marginRight":"4px"
                    }),
                    html.Button("L", id={"type":"btn-l","index":t["id"]}, style={
                        "background":C["red"],"color":"#fff","border":"none",
                        "padding":"2px 8px","borderRadius":"4px","fontSize":"11px","cursor":"pointer"
                    }),
                ], style={"display":"flex","alignItems":"center"}),
            ], style={
                "display":"flex","justifyContent":"space-between","alignItems":"center",
                "padding":"8px 14px","borderBottom":f"1px solid {C['border']}"
            }))
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
                    html.Span(f"@{t['odds']}", style={"fontFamily":"monospace","fontSize":"11px","color":C["muted"],"marginRight":"8px"}),
                    html.Span(f"${t.get('pnl',0):+.2f}", style={
                        "color":C["green2"] if won else C["red"],
                        "fontFamily":"monospace","fontSize":"13px","fontWeight":"600"
                    }),
                    html.Span(" ✅" if won else " ❌", style={"fontSize":"11px"}),
                ]),
            ], style={
                "display":"flex","justifyContent":"space-between","alignItems":"center",
                "padding":"7px 12px","borderBottom":f"1px solid {C['border']}"
            }))
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

    # Stats box
    total_done = len(done)
    wins = sum(1 for t in done if t["result"]=="WIN")
    wr = f"{wins/total_done*100:.1f}%" if total_done else "—"
    avg_o = sum(t["odds"] for t in done)/total_done if total_done else 0
    stats_el = html.Div([
        html.Div([
            html.Div([
                html.P("Win Rate",style={"color":C["muted"],"fontSize":"11px","marginBottom":"2px"}),
                html.P(wr,style={"color":C["green2"],"fontWeight":"700","fontSize":"18px","fontFamily":"monospace"})
            ]),
            html.Div([
                html.P("W / L",style={"color":C["muted"],"fontSize":"11px","marginBottom":"2px"}),
                html.P(f"{wins}/{total_done-wins}",style={"color":C["text"],"fontWeight":"700","fontSize":"18px","fontFamily":"monospace"})
            ]),
            html.Div([
                html.P("Avg Odds",style={"color":C["muted"],"fontSize":"11px","marginBottom":"2px"}),
                html.P(f"{avg_o:.2f}" if avg_o else "—",style={"color":C["blue"],"fontWeight":"700","fontSize":"18px","fontFamily":"monospace"})
            ]),
            html.Div([
                html.P("Total Bets",style={"color":C["muted"],"fontSize":"11px","marginBottom":"2px"}),
                html.P(str(total_done),style={"color":C["text"],"fontWeight":"700","fontSize":"18px","fontFamily":"monospace"})
            ]),
        ], style={"display":"grid","gridTemplateColumns":"repeat(4,1fr)","gap":"8px"})
    ])

    # Mode
    mode = bot.get_setting("mode") or "paper"
    is_paper = mode=="paper"
    mode_txt = "PAPER MODE" if is_paper else "⚡ LIVE MODE"
    mode_style = {
        "background":C["yellow"] if is_paper else C["red"],
        "color":"#000" if is_paper else "#fff",
        "padding":"2px 10px","borderRadius":"4px","fontSize":"11px",
        "fontWeight":"700","marginLeft":"12px"
    }

    is_running = bot.get_setting("running")=="true"
    dot_style = {"color":C["green2"] if is_running else C["red"],"fontSize":"10px","marginRight":"6px"}

    import os
    has_key = bool(os.environ.get("ODDS_API_KEY",""))
    api_txt = f"✅ Odds API connected | {len(games)} games" if has_key else "❌ No API key"

    rt = f"Updated: {datetime.now().strftime('%H:%M:%S')}"

    wr_txt = f"{stats['win_rate']:.1f}%" if stats['total_trades']>0 else "—"

    return (
        f"${bk:.2f}", pspan(stats["daily_pnl"]), pspan(stats["pnl"]),
        str(stats["open_positions"]), wr_txt, str(stats["daily_trades"]),
        games_el, games_cnt,
        rec_el, rec_cnt,
        open_el, str(len(pending)),
        recent_el, str(len(done)),
        fig, stats_el, rt, api_txt,
        mode_txt, mode_style, dot_style,
        bot_results
    )


@app.callback(
    Output("open-pos","children", allow_duplicate=True),
    [Input({"type":"btn-w","index":dash.ALL},"n_clicks"),
     Input({"type":"btn-l","index":dash.ALL},"n_clicks")],
    prevent_initial_call=True
)
def resolve_bet(w_clicks, l_clicks):
    ctx = callback_context
    if not ctx.triggered: return dash.no_update
    trig = ctx.triggered[0]
    prop = trig["prop_id"]
    if not trig["value"]: return dash.no_update
    import json as js
    try:
        id_part = prop.split(".")[0]
        id_dict = js.loads(id_part)
        trade_id = id_dict["index"]
        won = id_dict["type"] == "btn-w"
        bot.update_result(trade_id, won)
    except: pass
    return dash.no_update


if __name__ == "__main__":
    print("\n🏀 NBA Polymarket Agent v3.0")
    print("→ http://localhost:8050\n")
    app.run(debug=False, host="0.0.0.0", port=8050)
