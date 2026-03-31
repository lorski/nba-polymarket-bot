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
            if games:
                bot.save_price_history(games)
        except Exception as e:
            print(f"[BG] {e}")
        time.sleep(60)

threading.Thread(target=bg, daemon=True).start()

app = dash.Dash(__name__,
    external_stylesheets=[dbc.themes.CYBORG],
    title="NBA Polymarket Agent",
    suppress_callback_exceptions=True)
server = app.server

BG    = "#111827"
CARD  = "#1f2937"
BORD  = "#374151"
GREEN = "#10b981"
RED   = "#ef4444"
BLUE  = "#3b82f6"
TEXT  = "#f9fafb"
MUTED = "#6b7280"
YEL   = "#f59e0b"

def stat(title, vid, sub=""):
    return html.Div([
        html.P(title, style={"color":MUTED,"fontSize":"10px","fontWeight":"600",
                             "letterSpacing":"1px","textTransform":"uppercase","marginBottom":"4px"}),
        html.H3("--", id=vid, style={"color":TEXT,"fontWeight":"700","fontSize":"20px",
                                     "fontFamily":"monospace","marginBottom":"0"}),
        html.P(sub, style={"color":MUTED,"fontSize":"9px","marginBottom":"0","marginTop":"2px"}),
    ], style={"background":CARD,"border":f"1px solid {BORD}","borderRadius":"10px","padding":"14px 16px"})

app.layout = html.Div([

    html.Div([
        html.Div([
            html.Span("●", id="dot", style={"color":GREEN,"fontSize":"12px","marginRight":"8px"}),
            html.Span("NBA", style={"color":TEXT,"fontWeight":"800","fontSize":"18px","letterSpacing":"2px"}),
            html.Span(" POLYMARKET", style={"color":BLUE,"fontWeight":"800","fontSize":"18px","letterSpacing":"2px"}),
            html.Span(" AGENT", style={"color":MUTED,"fontSize":"14px","marginLeft":"6px"}),
            html.Span("PAPER", id="mbadge", style={
                "background":YEL,"color":"#000","padding":"2px 10px",
                "borderRadius":"12px","fontSize":"9px","fontWeight":"800","marginLeft":"12px"
            }),
        ], style={"display":"flex","alignItems":"center","flex":"1"}),
        html.Span(id="rtime", style={"color":MUTED,"fontSize":"11px","fontFamily":"monospace"}),
    ], style={"display":"flex","justifyContent":"space-between","alignItems":"center",
              "padding":"12px 24px","borderBottom":f"1px solid {BORD}","background":CARD}),

    html.Div([

        html.Div([
            stat("BANKROLL","s-bk","total"),
            stat("DAILY P&L","s-dp","today"),
            stat("TOTAL P&L","s-tp","all time"),
            stat("OPEN","s-op","positions"),
            stat("WIN RATE","s-wr","completed"),
            stat("TODAY","s-td","trades"),
        ], style={"display":"grid","gridTemplateColumns":"repeat(6,1fr)","gap":"10px","marginBottom":"14px"}),

        html.Div([
            html.Div([
                html.Button("RUN", id="btn-run", style={
                    "background":GREEN,"color":"#000","border":"none",
                    "padding":"8px 18px","borderRadius":"8px","fontSize":"12px",
                    "fontWeight":"700","cursor":"pointer","marginRight":"8px"}),
                html.Button("REFRESH", id="btn-ref", style={
                    "background":"transparent","color":BLUE,"border":f"1px solid {BLUE}",
                    "padding":"8px 14px","borderRadius":"8px","fontSize":"12px",
                    "cursor":"pointer","marginRight":"8px"}),
                html.Button("RESET", id="btn-rst", style={
                    "background":"transparent","color":MUTED,"border":f"1px solid {BORD}",
                    "padding":"8px 14px","borderRadius":"8px","fontSize":"12px","cursor":"pointer"}),
            ]),
            html.Div([
                html.Span("Paper", style={"color":MUTED,"fontSize":"11px","marginRight":"8px"}),
                dbc.Switch(id="msw", value=False),
                html.Span("Live", style={"color":MUTED,"fontSize":"11px","marginLeft":"8px"}),
            ], style={"display":"flex","alignItems":"center"}),
        ], style={"display":"flex","justifyContent":"space-between","alignItems":"center","marginBottom":"14px"}),

        html.Div([

            html.Div([

                html.Div([
                    html.Div([
                        html.Span("● ", style={"color":GREEN,"fontSize":"8px"}),
                        html.Span("WIN PROBABILITY — POLYMARKET",
                            style={"fontWeight":"700","fontSize":"11px","letterSpacing":"1.5px"}),
                    ], style={"padding":"12px 16px","borderBottom":f"1px solid {BORD}"}),
                    html.Div(id="pm-charts", style={"padding":"8px"}),
                ], style={"background":CARD,"border":f"1px solid {BORD}","borderRadius":"10px","marginBottom":"12px"}),

                html.Div([
                    html.Div([
                        html.Span("BOT ANALYSIS",
                            style={"fontWeight":"700","fontSize":"11px","letterSpacing":"1.5px"}),
                        html.Span(id="rec-cnt", style={
                            "background":GREEN,"color":"#000","padding":"1px 10px",
                            "borderRadius":"10px","fontSize":"9px","fontWeight":"800","float":"right"}),
                    ], style={"padding":"12px 16px","borderBottom":f"1px solid {BORD}"}),
                    html.Div(id="rec-list"),
                ], style={"background":CARD,"border":f"1px solid {BORD}","borderRadius":"10px","marginBottom":"12px"}),

                html.Div([
                    html.Div([
                        html.Span("OPEN POSITIONS",
                            style={"fontWeight":"700","fontSize":"11px","letterSpacing":"1.5px"}),
                        html.Span(id="op-cnt", style={
                            "background":YEL,"color":"#000","padding":"1px 10px",
                            "borderRadius":"10px","fontSize":"9px","fontWeight":"800","float":"right"}),
                    ], style={"padding":"12px 16px","borderBottom":f"1px solid {BORD}"}),
                    html.Div(id="op-list"),
                ], style={"background":CARD,"border":f"1px solid {BORD}","borderRadius":"10px"}),

            ], style={"flex":"1","marginRight":"12px"}),

            html.Div([

                html.Div([
                    html.Div([
                        html.Span("RECENT TRADES",
                            style={"fontWeight":"700","fontSize":"11px","letterSpacing":"1.5px"}),
                        html.Span(id="tr-cnt", style={
                            "background":MUTED,"color":"#fff","padding":"1px 10px",
                            "borderRadius":"10px","fontSize":"9px","fontWeight":"800","float":"right"}),
                    ], style={"padding":"12px 16px","borderBottom":f"1px solid {BORD}"}),
                    html.Div(id="tr-list", style={"maxHeight":"300px","overflowY":"auto"}),
                ], style={"background":CARD,"border":f"1px solid {BORD}","borderRadius":"10px","marginBottom":"12px"}),

                html.Div([
                    html.Div("STATISTICS", style={"padding":"12px 16px","fontWeight":"700",
                             "fontSize":"11px","letterSpacing":"1.5px","borderBottom":f"1px solid {BORD}"}),
                    html.Div(id="stats-box", style={"padding":"14px 16px"}),
                ], style={"background":CARD,"border":f"1px solid {BORD}","borderRadius":"10px","marginBottom":"12px"}),

                html.Div([
                    html.Div("PORTFOLIO GROWTH", style={"padding":"12px 16px","fontWeight":"700",
                             "fontSize":"11px","letterSpacing":"1.5px","borderBottom":f"1px solid {BORD}"}),
                    dcc.Graph(id="port-chart", style={"height":"160px"}, config={"displayModeBar":False}),
                ], style={"background":CARD,"border":f"1px solid {BORD}","borderRadius":"10px"}),

            ], style={"width":"380px"}),

        ], style={"display":"flex"}),

    ], style={"padding":"16px 24px","background":BG,"minHeight":"calc(100vh - 52px)"}),

    dcc.Interval(id="iv", interval=10*1000, n_intervals=0),

], style={"background":BG,"fontFamily":"-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif","color":TEXT})


def make_chart(key, data):
    teams = key.split("|")
    home = teams[0] if len(teams)>0 else "?"
    away = teams[1] if len(teams)>1 else "?"

    def abbr(name):
        parts = name.split()
        return parts[-1][:3].upper() if len(parts)>=2 else name[:3].upper()

    h_abbr = abbr(home)
    a_abbr = abbr(away)

    times = [d["time"] for d in data]
    hv = [d["h_pct"] for d in data]
    av = [d["a_pct"] for d in data]

    lh = hv[-1]; la = av[-1]
    ph = hv[-2] if len(hv)>1 else lh
    h_up = lh >= ph
    h_col = GREEN if h_up else RED

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=times, y=hv, name=h_abbr,
        mode="lines",
        line=dict(color=GREEN, width=2.5),
        fill="tozeroy",
        fillcolor="rgba(16,185,129,0.05)"
    ))

    fig.add_trace(go.Scatter(
        x=times, y=av, name=a_abbr,
        mode="lines",
        line=dict(color=BLUE, width=2.5),
    ))

    if times:
        fig.add_trace(go.Scatter(
            x=[times[-1]], y=[lh],
            mode="markers+text",
            marker=dict(color=h_col, size=8),
            text=[f"  {h_abbr} {lh}%"],
            textposition="middle right",
            textfont=dict(color=h_col, size=10),
            showlegend=False
        ))
        fig.add_trace(go.Scatter(
            x=[times[-1]], y=[la],
            mode="markers+text",
            marker=dict(color=BLUE, size=8),
            text=[f"  {a_abbr} {la}%"],
            textposition="middle right",
            textfont=dict(color=BLUE, size=10),
            showlegend=False
        ))

    mn = max(0, min(hv+av) - 10)
    mx = min(100, max(hv+av) + 10)

    fig.update_layout(
        plot_bgcolor="#111827",
        paper_bgcolor="#111827",
        font=dict(color=TEXT, size=9),
        margin=dict(l=35, r=80, t=10, b=25),
        height=180,
        xaxis=dict(gridcolor="#1f2937",showgrid=True,zeroline=False,tickfont=dict(size=9,color=MUTED)),
        yaxis=dict(gridcolor="#1f2937",showgrid=True,zeroline=False,
                  ticksuffix="%",tickfont=dict(size=9,color=MUTED),range=[mn,mx]),
        legend=dict(font=dict(size=10,color=TEXT),bgcolor="rgba(0,0,0,0)",x=0,y=1,orientation="h"),
    )

    change = lh - ph
    ch_sym = "▲" if change>=0 else "▼"
    ch_col = GREEN if change>=0 else RED

    return html.Div([
        html.Div([
            html.Div([
                html.Span(h_abbr, style={"background":GREEN,"color":"#000","padding":"3px 10px",
                          "borderRadius":"6px","fontSize":"12px","fontWeight":"800",
                          "fontFamily":"monospace","marginRight":"6px"}),
                html.Span("vs", style={"color":MUTED,"fontSize":"10px","marginRight":"6px"}),
                html.Span(a_abbr, style={"background":BLUE,"color":"#fff","padding":"3px 10px",
                          "borderRadius":"6px","fontSize":"12px","fontWeight":"800","fontFamily":"monospace"}),
            ]),
            html.Div([
                html.Span(f"{lh}%", style={"fontFamily":"monospace","fontSize":"20px",
                          "fontWeight":"900","color":h_col,"marginRight":"12px"}),
                html.Span(f"{la}%", style={"fontFamily":"monospace","fontSize":"20px",
                          "fontWeight":"900","color":BLUE,"marginRight":"10px"}),
                html.Span(f"{ch_sym}{abs(change):.0f}", style={"fontSize":"13px",
                          "color":ch_col,"fontFamily":"monospace","fontWeight":"700"}),
            ]),
        ], style={"display":"flex","justifyContent":"space-between","alignItems":"center","padding":"10px 14px"}),
        dcc.Graph(figure=fig, config={"displayModeBar":False}, style={"height":"180px"}),
    ], style={"background":"#111827","border":f"1px solid {BORD}","borderRadius":"10px",
              "marginBottom":"8px","overflow":"hidden"})


@app.callback(
    [Output("s-bk","children"), Output("s-dp","children"),
     Output("s-tp","children"), Output("s-op","children"),
     Output("s-wr","children"), Output("s-td","children"),
     Output("pm-charts","children"),
     Output("rec-list","children"), Output("rec-cnt","children"),
     Output("op-list","children"), Output("op-cnt","children"),
     Output("tr-list","children"), Output("tr-cnt","children"),
     Output("port-chart","figure"), Output("stats-box","children"),
     Output("rtime","children"),
     Output("mbadge","children"), Output("mbadge","style"),
     Output("dot","style")],
    [Input("iv","n_intervals"),
     Input("btn-ref","n_clicks"),
     Input("btn-run","n_clicks"),
     Input("btn-rst","n_clicks"),
     Input("msw","value")],
    prevent_initial_call=False
)
def upd(n, ref, run, rst, live):
    ctx = callback_context
    trig = ctx.triggered[0]["prop_id"] if ctx.triggered else ""

    if "msw" in trig: bot.set_setting("mode","live" if live else "paper")
    if "btn-rst" in trig: bot.reset_opening_odds()
    if "btn-ref" in trig:
        def do_ref():
            g = polymarket_scraper.scrape_polymarket()
            if g: bot.save_price_history(g)
        threading.Thread(target=do_ref, daemon=True).start()
    if "btn-run" in trig:
        bot.set_setting("running","true")
        pm = polymarket_scraper.get_cached()
        results, _ = bot.analyze_games_with_reason(pm if pm else None)
        for r in results:
            ex = [t for t in bot.get_trades(50) if t["game"]==r["game"] and t["result"]=="PENDING"]
            if not ex: bot.save_trade(r)

    st = bot.get_stats()
    trades = bot.get_trades(100)
    hist_data = bot.get_portfolio_history()
    bk = st["bankroll"]
    pm = polymarket_scraper.get_cached()
    _, skipped = bot.analyze_games_with_reason(pm if pm else None)

    def ps(v):
        c = GREEN if v>=0 else RED
        return html.Span(f"${v:+.2f}", style={"color":c,"fontFamily":"monospace","fontSize":"20px","fontWeight":"700"})

    # Probability Charts
    ph = bot.get_price_history()
    if ph:
        charts = []
        for key, data in list(ph.items())[:8]:
            if len(data) < 2: continue
            charts.append(make_chart(key, data))
        pm_charts = charts if charts else [
            html.P("REFRESH → ჩარტები გამოჩნდება",
                style={"color":MUTED,"padding":"20px","textAlign":"center","fontSize":"12px"})
        ]
    else:
        pm_charts = [html.P("REFRESH ODDS დააჭირე → ჩარტები გამოჩნდება",
            style={"color":MUTED,"padding":"20px","textAlign":"center","fontSize":"12px"})]

    # Bot Analysis
    pending = [t for t in trades if t["result"]=="PENDING"]
    rec_els = []

    if pending:
        for t in pending:
            tc = {"A":GREEN,"B":BLUE,"C":YEL}.get(t.get("tier",""), MUTED)
            sh = {"Strong":"🔥","Medium":"🟡"}.get(t.get("sharp_label",""), "")
            reasons = t.get("reasons", [])
            rec_els.append(html.Div([
                html.Div([
                    html.Div([
                        html.Span("✅ "),
                        html.Span(t["fav"], style={"fontWeight":"800","fontSize":"14px","color":GREEN}),
                    ]),
                    html.Div(t["game"][:40], style={"fontSize":"10px","color":MUTED,"marginTop":"2px"}),
                    html.Div([
                        html.Div("მიზეზები:", style={"fontSize":"9px","color":MUTED,"fontWeight":"700",
                                 "marginTop":"6px","marginBottom":"3px","letterSpacing":"1px"}),
                        *[html.Div(f"↳ {r}", style={"fontSize":"10px","color":BLUE,"marginBottom":"2px"})
                          for r in reasons[:5]]
                    ]),
                ], style={"flex":"1"}),
                html.Div([
                    html.Div(f"@{t['odds']}x", style={"fontFamily":"monospace","color":BLUE,
                             "fontWeight":"900","fontSize":"18px"}),
                    html.Div(f"{sh} Tier {t['tier']}", style={"fontSize":"10px","color":YEL,"marginBottom":"3px"}),
                    html.Div(f"EV {t['ev']:+.3f}", style={"color":MUTED,"fontSize":"9px"}),
                    html.Div(f"${t['stake']:.2f} -> +${t['pot']:.2f}",
                        style={"color":GREEN,"fontWeight":"700","fontSize":"12px",
                               "fontFamily":"monospace","marginTop":"4px"}),
                ], style={"textAlign":"right","minWidth":"120px"}),
            ], style={"display":"flex","justifyContent":"space-between","alignItems":"flex-start",
                      "padding":"12px 16px","borderBottom":f"1px solid {BORD}",
                      "borderLeft":f"3px solid {GREEN}"}))

    if skipped:
        rec_els.append(html.Div("SKIP -- მიზეზები", style={
            "padding":"6px 16px","fontSize":"9px","color":MUTED,
            "fontWeight":"700","letterSpacing":"1.5px","background":BG}))
        for s in skipped[:6]:
            rec_els.append(html.Div([
                html.Div([
                    html.Span("X ", style={"color":RED,"fontWeight":"700"}),
                    html.Span(s["fav"], style={"fontSize":"12px","fontWeight":"700"}),
                    html.Span(f" @{s['odds']}x", style={"fontFamily":"monospace","fontSize":"11px","color":MUTED,"marginLeft":"4px"}),
                ]),
                *[html.Div(f"  -> {r}", style={"fontSize":"10px","color":RED,"marginTop":"2px","paddingLeft":"12px"})
                  for r in s.get("reasons",[])[:2]],
            ], style={"padding":"8px 16px","borderBottom":f"1px solid {BORD}"}))

    if not rec_els:
        rec_els = [html.P("RUN დააჭირე ანალიზისთვის",
            style={"color":MUTED,"padding":"20px","textAlign":"center","fontSize":"12px"})]

    # Open Positions
    if pending:
        rows = []
        for t in pending:
            tc = {"A":GREEN,"B":BLUE,"C":YEL}.get(t.get("tier",""), MUTED)
            sh = {"Strong":"🔥","Medium":"🟡"}.get(t.get("sharp_label",""), "")
            rows.append(html.Div([
                html.Div([
                    html.Div(t["game"][:28], style={"fontSize":"9px","color":MUTED}),
                    html.Div([
                        html.Span(t["fav"][:14], style={"fontWeight":"700","fontSize":"13px","marginRight":"6px"}),
                        html.Span(f"@{t['odds']}x", style={"fontFamily":"monospace","color":BLUE,"fontSize":"12px"}),
                        html.Span(f" {sh}"),
                    ]),
                ]),
                html.Div([
                    html.Span(f"T{t['tier']}", style={"background":tc,"color":"#000","padding":"1px 8px",
                              "borderRadius":"4px","fontSize":"9px","fontWeight":"800","marginRight":"6px"}),
                    html.Span(f"${t['stake']:.0f}->+${t['pot']:.0f}", style={"color":MUTED,
                              "fontSize":"11px","fontFamily":"monospace","marginRight":"8px"}),
                    html.Button("W", id={"type":"bw","index":t["id"]}, style={
                        "background":GREEN,"color":"#000","border":"none","padding":"2px 10px",
                        "borderRadius":"4px","fontSize":"11px","fontWeight":"700","cursor":"pointer","marginRight":"4px"}),
                    html.Button("L", id={"type":"bl","index":t["id"]}, style={
                        "background":RED,"color":"#fff","border":"none","padding":"2px 10px",
                        "borderRadius":"4px","fontSize":"11px","fontWeight":"700","cursor":"pointer"}),
                ], style={"display":"flex","alignItems":"center"}),
            ], style={"display":"flex","justifyContent":"space-between","alignItems":"center",
                      "padding":"8px 14px","borderBottom":f"1px solid {BORD}"}))
        op_list = rows
    else:
        op_list = [html.P("ღია პოზიცია არ არის",
            style={"color":MUTED,"padding":"14px","textAlign":"center","fontSize":"12px"})]

    # Recent Trades
    done = [t for t in trades if t["result"]!="PENDING"][:20]
    if done:
        rows = []
        for t in done:
            won = t["result"]=="WIN"
            rows.append(html.Div([
                html.Div([
                    html.Div(t["game"][:26], style={"fontSize":"9px","color":MUTED}),
                    html.Span(t["fav"][:14], style={"fontSize":"12px","fontWeight":"600"}),
                ]),
                html.Div([
                    html.Span(f"@{t['odds']}x ", style={"fontFamily":"monospace","fontSize":"9px","color":MUTED}),
                    html.Span(f"${t.get('pnl',0):+.2f}", style={"color":GREEN if won else RED,
                              "fontFamily":"monospace","fontSize":"13px","fontWeight":"800"}),
                    html.Span(" V" if won else " X"),
                ]),
            ], style={"display":"flex","justifyContent":"space-between","alignItems":"center",
                      "padding":"7px 14px","borderBottom":f"1px solid {BORD}"}))
        tr_list = rows
    else:
        tr_list = [html.P("ბეთი ჯერ არ არის",
            style={"color":MUTED,"padding":"14px","textAlign":"center","fontSize":"12px"})]

    # Portfolio Chart
    if hist_data and len(hist_data)>1:
        ptimes = [h[0] for h in hist_data]
        pvals  = [h[1] for h in hist_data]
    else:
        ptimes = [datetime.now().strftime("%H:%M")]
        pvals  = [bk]
    pfig = go.Figure()
    pfig.add_trace(go.Scatter(x=ptimes, y=pvals, mode="lines", fill="tozeroy",
        line=dict(color=GREEN, width=2), fillcolor="rgba(16,185,129,0.06)"))
    pfig.update_layout(
        plot_bgcolor=CARD, paper_bgcolor=CARD, font=dict(color=TEXT),
        margin=dict(l=50,r=10,t=5,b=30),
        xaxis=dict(gridcolor=BORD,showgrid=True,zeroline=False,tickfont=dict(size=9,color=MUTED)),
        yaxis=dict(gridcolor=BORD,showgrid=True,zeroline=False,tickprefix="$",tickfont=dict(size=9,color=MUTED)),
        showlegend=False
    )

    # Stats
    td   = len(done)
    wins = sum(1 for t in done if t["result"]=="WIN")
    wr   = f"{wins/td*100:.1f}%" if td else "--"
    ao   = sum(t["odds"] for t in done)/td if td else 0
    stats_el = html.Div([html.Div([
        html.Div([html.P("WIN RATE",style={"color":MUTED,"fontSize":"8px","fontWeight":"700","letterSpacing":"1.5px","marginBottom":"4px"}),
                  html.P(wr,style={"color":GREEN,"fontWeight":"800","fontSize":"20px","fontFamily":"monospace"})]),
        html.Div([html.P("W / L",style={"color":MUTED,"fontSize":"8px","fontWeight":"700","letterSpacing":"1.5px","marginBottom":"4px"}),
                  html.P(f"{wins}/{td-wins}",style={"color":TEXT,"fontWeight":"800","fontSize":"20px","fontFamily":"monospace"})]),
        html.Div([html.P("AVG ODDS",style={"color":MUTED,"fontSize":"8px","fontWeight":"700","letterSpacing":"1.5px","marginBottom":"4px"}),
                  html.P(f"{ao:.2f}x" if ao else "--",style={"color":BLUE,"fontWeight":"800","fontSize":"20px","fontFamily":"monospace"})]),
        html.Div([html.P("TOTAL",style={"color":MUTED,"fontSize":"8px","fontWeight":"700","letterSpacing":"1.5px","marginBottom":"4px"}),
                  html.P(str(td),style={"color":TEXT,"fontWeight":"800","fontSize":"20px","fontFamily":"monospace"})]),
    ], style={"display":"grid","gridTemplateColumns":"repeat(4,1fr)","gap":"8px"})])

    mode = bot.get_setting("mode") or "paper"
    ip   = mode=="paper"
    mt   = "PAPER" if ip else "LIVE"
    ms   = {"background":YEL if ip else RED,"color":"#000","padding":"2px 10px",
            "borderRadius":"12px","fontSize":"9px","fontWeight":"800","marginLeft":"12px"}
    ir   = bot.get_setting("running")=="true"
    ds   = {"color":GREEN if ir else RED,"fontSize":"12px","marginRight":"8px"}
    wr2  = f"{st['win_rate']:.1f}%" if st['total_trades']>0 else "--"

    return (
        f"${bk:,.2f}", ps(st["daily_pnl"]), ps(st["pnl"]),
        str(st["open_positions"]), wr2, str(st["daily_trades"]),
        pm_charts,
        rec_els, str(len(pending)),
        op_list, str(len(pending)),
        tr_list, str(len(done)),
        pfig, stats_el,
        datetime.now().strftime("%H:%M:%S"),
        mt, ms, ds
    )


if __name__ == "__main__":
    print("\n NBA Polymarket Agent")
    print("-> http://localhost:8050\n")
    app.run(debug=False, host="0.0.0.0", port=8050)
