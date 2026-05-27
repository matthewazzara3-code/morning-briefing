#!/usr/bin/env python3
"""
Daily Morning Briefing Bot — FREE VERSION (uses Google Gemini)
Sends a personalized email digest every morning at 7am
To: matthewazzara3@gmail.com
100% FREE — no credit card needed
"""

import smtplib
import json
import urllib.request
import urllib.parse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

# ============================================================
# CONFIGURATION
# ============================================================

RECIPIENT_EMAIL   = "matthewazzara3@gmail.com"
SENDER_EMAIL      = "matthewazzara3@gmail.com"
SENDER_PASSWORD   = "qsvi jvgy nuex gmbp"
GEMINI_API_KEY    = "AIzaSyB8uqA-a7HC9WJ_ch9HtPxeS1g6zK_jp1A"
NEWS_API_KEY      = "679ecf883a054496bc78ccd41003d649"
ALPHA_VANTAGE_KEY = "LAI0292XFDZWGMR2"

# ============================================================
# TEAMS & STOCKS TO TRACK
# ============================================================

TEAMS = [
    "Chicago Bulls", "Manchester City",
    "Cincinnati Reds", "Cincinnati Bengals", "Baltimore Ravens",
    "University of Louisville Mens Basketball",
    "University of Cincinnati Mens Basketball",
    "University of Louisville Mens Football"
]

STOCKS = [
    "SPY", "QQQ", "DIA", "IWM",
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "BRK-B",
    "VNQ", "JPM", "BAC",
]

# ============================================================
# DATA FETCHERS
# ============================================================

def fetch_news(query, api_key, num_articles=5):
    params = urllib.parse.urlencode({
        "q": query,
        "sortBy": "publishedAt",
        "pageSize": num_articles,
        "language": "en",
        "apiKey": api_key
    })
    url = f"https://newsapi.org/v2/everything?{params}"
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())
            articles = data.get("articles", [])
            return [
                {
                    "title": a.get("title", ""),
                    "source": a.get("source", {}).get("name", ""),
                    "description": a.get("description", ""),
                    "url": a.get("url", ""),
                    "publishedAt": a.get("publishedAt", "")
                }
                for a in articles if a.get("title")
            ]
    except Exception as e:
        print(f"News fetch error for '{query}': {e}")
        return []


def fetch_stock_price(symbol, api_key):
    url = (
        f"https://www.alphavantage.co/query"
        f"?function=GLOBAL_QUOTE&symbol={symbol}&apikey={api_key}"
    )
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())
            quote = data.get("Global Quote", {})
            if not quote:
                return None
            return {
                "symbol": symbol,
                "price": float(quote.get("05. price", 0)),
                "change": float(quote.get("09. change", 0)),
                "change_pct": quote.get("10. change percent", "0%").replace("%", ""),
                "volume": quote.get("06. volume", "N/A"),
                "prev_close": float(quote.get("08. previous close", 0))
            }
    except Exception as e:
        print(f"Stock fetch error for {symbol}: {e}")
        return None


def fetch_all_stocks(symbols, api_key):
    import time
    results = []
    for i, symbol in enumerate(symbols):
        if i > 0 and i % 5 == 0:
            time.sleep(61)
        data = fetch_stock_price(symbol, api_key)
        if data:
            results.append(data)
    return results


# ============================================================
# AI DIGEST GENERATOR — Using FREE Google Gemini
# ============================================================

def generate_digest(news_data, stock_data, today_str):
    prompt = f"""
Today is {today_str}. You are creating a polished, insightful morning briefing email for Matthew.

Here is the raw data to synthesize:

=== SPORTS NEWS ===
{json.dumps(news_data['sports'], indent=2)}

=== COMMERCIAL REAL ESTATE NEWS ===
{json.dumps(news_data['cre'], indent=2)}

=== FINANCIAL & WORLD NEWS ===
{json.dumps(news_data['financial'], indent=2)}

=== GENERAL NEWS ===
{json.dumps(news_data['general'], indent=2)}

=== STOCK/FUND PRICES ===
{json.dumps(stock_data, indent=2)}

Write a morning briefing in clean HTML sections. For each section:
- Lead with the most important insight, not just a summary
- For stocks: highlight big movers (>1.5% change), note trends, flag anything unusual
- For sports: focus on Matthew's teams first (Bulls, Man City, Reds, Bengals, Ravens, Louisville, UC), then general sports
- For CRE: focus on market trends, cap rates, any major deals or shifts
- For world/political news: be factual and balanced
- Keep each section punchy — this is a morning read, not an essay

Return ONLY a JSON object with these exact keys (no markdown, no code fences, pure JSON only):
{{
  "sports_html": "...",
  "cre_html": "...",
  "financial_news_html": "...",
  "stocks_html": "...",
  "world_news_html": "...",
  "top_headline": "One sentence summary of the single most important thing happening today"
}}
"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 4000}
    }).encode("utf-8")

    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())
            raw = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            return json.loads(raw)
    except Exception as e:
        print(f"Gemini API error: {e}")
        return {
            "sports_html": "<p>" + "<br>".join([a['title'] for a in news_data['sports'][:5]]) + "</p>",
            "cre_html": "<p>" + "<br>".join([a['title'] for a in news_data['cre'][:4]]) + "</p>",
            "financial_news_html": "<p>" + "<br>".join([a['title'] for a in news_data['financial'][:4]]) + "</p>",
            "stocks_html": "<p>See stock table above.</p>",
            "world_news_html": "<p>" + "<br>".join([a['title'] for a in news_data['general'][:4]]) + "</p>",
            "top_headline": "Your morning briefing is ready."
        }


# ============================================================
# EMAIL TEMPLATE
# ============================================================

def build_email_html(digest, today_str, stock_data):
    gainers = [s for s in stock_data if s['change'] > 0]
    losers  = [s for s in stock_data if s['change'] < 0]
    market_mood = "📈 Markets Up" if len(gainers) > len(losers) else "📉 Markets Mixed"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Morning Briefing - {today_str}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=Source+Sans+3:wght@300;400;600&display=swap');
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:'Source Sans 3',Arial,sans-serif; background:#0f0f0f; color:#e8e4dc; font-size:15px; line-height:1.6; }}
  .wrapper {{ max-width:680px; margin:0 auto; background:#141414; }}
  .header {{ background:linear-gradient(135deg,#1a1a2e 0%,#0f0f1a 60%,#1a0f0f 100%); padding:40px 40px 32px; border-bottom:1px solid #2a2a2a; }}
  .header-label {{ font-size:10px; font-weight:600; letter-spacing:4px; text-transform:uppercase; color:#c4a460; margin-bottom:10px; }}
  .header-date {{ font-family:'Playfair Display',serif; font-size:32px; font-weight:900; color:#f0ebe0; margin-bottom:16px; }}
  .header-headline {{ font-size:14px; color:#9a9080; font-style:italic; line-height:1.5; }}
  .market-badge {{ display:inline-block; background:rgba(196,164,96,0.12); border:1px solid rgba(196,164,96,0.3); color:#c4a460; font-size:11px; font-weight:600; padding:4px 12px; border-radius:20px; margin-top:14px; }}
  .section {{ padding:32px 40px; border-bottom:1px solid #1e1e1e; }}
  .section-label {{ font-size:9px; font-weight:600; letter-spacing:4px; text-transform:uppercase; color:#c4a460; margin-bottom:6px; }}
  .section-title {{ font-family:'Playfair Display',serif; font-size:20px; font-weight:700; color:#f0ebe0; margin-bottom:20px; padding-bottom:12px; border-bottom:1px solid #222; }}
  .stock-up {{ color:#4caf7d; font-weight:600; text-align:right; }}
  .stock-down {{ color:#e05252; font-weight:600; text-align:right; }}
  .stock-flat {{ color:#888; font-weight:600; text-align:right; }}
  .stock-symbol {{ font-weight:700; color:#f0ebe0; font-size:13px; }}
  .stock-price {{ color:#c8c0b0; text-align:right; }}
  .stock-cell {{ padding:8px 10px; font-size:13px; vertical-align:middle; }}
  .section p {{ margin-bottom:12px; color:#b8b0a0; font-size:14px; }}
  .section h3 {{ color:#e8e0cc; font-size:15px; font-weight:600; margin:16px 0 6px; }}
  .section h4 {{ color:#c4a460; font-size:13px; font-weight:600; margin:14px 0 4px; }}
  .section ul {{ padding-left:18px; color:#b8b0a0; font-size:14px; }}
  .section li {{ margin-bottom:6px; }}
  .section strong {{ color:#e0d8c8; }}
  .team-tag {{ display:inline-block; background:rgba(196,164,96,0.1); border-left:2px solid #c4a460; padding:2px 8px; margin-bottom:8px; font-size:12px; color:#c4a460; font-weight:600; text-transform:uppercase; }}
  .footer {{ background:#0f0f0f; padding:24px 40px; text-align:center; font-size:11px; color:#444; }}
</style>
</head>
<body>
<div class="wrapper">
  <div class="header">
    <div class="header-label">Morning Briefing</div>
    <div class="header-date">{today_str}</div>
    <div class="header-headline">{digest.get('top_headline','Your daily intelligence digest.')}</div>
    <div class="market-badge">{market_mood}</div>
  </div>

  <div class="section">
    <div class="section-label">Markets</div>
    <div class="section-title">Stocks &amp; Funds</div>
    <table cellpadding="0" cellspacing="0" width="100%" style="border-collapse:collapse;">
      <tr style="border-bottom:1px solid #222;">
        <td style="padding:6px 10px;font-size:10px;letter-spacing:2px;color:#555;text-transform:uppercase;">Symbol</td>
        <td style="padding:6px 10px;font-size:10px;letter-spacing:2px;color:#555;text-transform:uppercase;text-align:right;">Price</td>
        <td style="padding:6px 10px;font-size:10px;letter-spacing:2px;color:#555;text-transform:uppercase;text-align:right;">Change</td>
        <td style="padding:6px 10px;font-size:10px;letter-spacing:2px;color:#555;text-transform:uppercase;text-align:right;">%</td>
      </tr>
"""

    for s in stock_data:
        pct = float(s.get('change_pct', 0))
        chg = s.get('change', 0)
        if chg > 0:
            cls, arrow = "stock-up", "▲"
        elif chg < 0:
            cls, arrow = "stock-down", "▼"
        else:
            cls, arrow = "stock-flat", "-"
        html += f"""      <tr style="border-bottom:1px solid #1a1a1a;">
        <td class="stock-cell stock-symbol">{s['symbol']}</td>
        <td class="stock-cell stock-price">${s['price']:.2f}</td>
        <td class="stock-cell {cls}">{arrow} {abs(chg):.2f}</td>
        <td class="stock-cell {cls}">{abs(pct):.2f}%</td>
      </tr>\n"""

    html += f"""    </table>
    <div style="margin-top:20px;">{digest.get('stocks_html','')}</div>
  </div>

  <div class="section">
    <div class="section-label">Sports</div>
    <div class="section-title">Your Teams &amp; Around the League</div>
    <div style="margin-bottom:14px;">{''.join([f'<span class="team-tag">{t.split()[-1]}</span>&nbsp;' for t in TEAMS])}</div>
    {digest.get('sports_html','<p>No sports data available today.</p>')}
  </div>

  <div class="section">
    <div class="section-label">Real Estate</div>
    <div class="section-title">Commercial Real Estate Markets</div>
    {digest.get('cre_html','<p>No CRE data available today.</p>')}
  </div>

  <div class="section">
    <div class="section-label">Finance</div>
    <div class="section-title">Financial &amp; Economic News</div>
    {digest.get('financial_news_html','<p>No financial news available today.</p>')}
  </div>

  <div class="section">
    <div class="section-label">World</div>
    <div class="section-title">Politics &amp; World News</div>
    {digest.get('world_news_html','<p>No world news available today.</p>')}
  </div>

  <div class="footer">
    <p>MORNING BRIEFING &nbsp;·&nbsp; Delivered daily at 7:00 AM &nbsp;·&nbsp; {today_str}</p>
    <p style="margin-top:6px;">matthewazzara3@gmail.com</p>
  </div>
</div>
</body>
</html>"""
    return html


# ============================================================
# EMAIL SENDER
# ============================================================

def send_email(html_content, today_str):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Morning Briefing - {today_str}"
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = RECIPIENT_EMAIL
    msg.attach(MIMEText(html_content, "html"))
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())
        print(f"Email sent to {RECIPIENT_EMAIL}")
    except Exception as e:
        print(f"Email failed: {e}")
        raise


# ============================================================
# MAIN
# ============================================================

def main():
    today_str = datetime.now().strftime("%A, %B %d, %Y")
    print(f"Generating Morning Briefing for {today_str}...")

    print("Fetching news...")
    sports_query = "Chicago Bulls OR Manchester City OR Cincinnati Reds OR Cincinnati Bengals OR Baltimore Ravens OR Louisville Cardinals OR Cincinnati Bearcats OR NBA OR NFL OR Premier League OR MLB"
    news_data = {
        "sports":    fetch_news(sports_query, NEWS_API_KEY, 8),
        "cre":       fetch_news("commercial real estate market cap rates office retail industrial", NEWS_API_KEY, 6),
        "financial": fetch_news("stock market Federal Reserve economy inflation earnings Wall Street", NEWS_API_KEY, 6),
        "general":   fetch_news("US politics world news breaking today", NEWS_API_KEY, 6),
    }

    print("Fetching stock prices (this takes 3-5 minutes)...")
    stock_data = fetch_all_stocks(STOCKS, ALPHA_VANTAGE_KEY)
    if not stock_data:
        stock_data = [{"symbol": s, "price": 0, "change": 0, "change_pct": "0"} for s in STOCKS]

    print("Generating AI digest with Gemini...")
    digest = generate_digest(news_data, stock_data, today_str)

    print("Sending email...")
    html = build_email_html(digest, today_str, stock_data)
    send_email(html, today_str)
    print("Done! Check your inbox at matthewazzara3@gmail.com")


if __name__ == "__main__":
    main()
