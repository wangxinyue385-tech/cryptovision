from flask import Flask, request, jsonify, render_template_string
import requests
import os
import datetime

app = Flask(__name__)
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
HTTP_TIMEOUT = 8
LLM_TIMEOUT = 20

COIN_MAP = {
    "bitcoin": "bitcoin", "btc": "bitcoin",
    "ethereum": "ethereum", "eth": "ethereum",
    "solana": "solana", "sol": "solana",
    "bnb": "binancecoin",
    "doge": "dogecoin", "dogecoin": "dogecoin",
    "xrp": "ripple", "ripple": "ripple",
    "ada": "cardano", "cardano": "cardano",
    "avax": "avalanche-2",
    "dot": "polkadot",
    "shib": "shiba-inu",
    "ltc": "litecoin",
    "link": "chainlink",
    "uni": "uniswap",
    "trx": "tron",
    "matic": "matic-network",
}

SYMBOL_MAP = {
    "bitcoin": "BTC", "ethereum": "ETH", "binancecoin": "BNB",
    "dogecoin": "DOGE", "solana": "SOL", "ripple": "XRP",
    "cardano": "ADA", "avalanche-2": "AVAX", "polkadot": "DOT",
    "shiba-inu": "SHIB", "litecoin": "LTC", "chainlink": "LINK",
    "uniswap": "UNI", "tron": "TRX", "matic-network": "MATIC",
}

def get_top_prices():
    try:
        ids = "bitcoin,ethereum,solana,binancecoin,ripple,cardano,dogecoin,avalanche-2"
        res = requests.get(
            "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=" + ids + "&order=market_cap_desc&sparkline=false",
            timeout=HTTP_TIMEOUT
        )
        res.raise_for_status()
        data = res.json()
        if not isinstance(data, list):
            return []
        result = []
        for d in data:
            result.append({
                "symbol": SYMBOL_MAP.get(d["id"], d["symbol"].upper()),
                "name": d["name"],
                "price": d["current_price"],
                "change": round(d["price_change_percentage_24h"] or 0, 2),
                "volume": d["total_volume"],
            })
        return result
    except:
        return []

def get_kline(coin_id, days=1):
    try:
        res = requests.get(
            "https://api.coingecko.com/api/v3/coins/" + coin_id + "/market_chart?vs_currency=usd&days=" + str(days),
            timeout=HTTP_TIMEOUT
        )
        res.raise_for_status()
        data = res.json()
        prices = data.get("prices", [])
        if not prices:
            return [], []
        step = max(1, len(prices) // 72)
        sampled = prices[::step][-72:]
        labels = []
        vals = []
        for p in sampled:
            t = datetime.datetime.fromtimestamp(p[0] / 1000)
            labels.append(t.strftime("%H:%M"))
            vals.append(round(p[1], 4))
        return labels, vals
    except:
        return [], []

HTML = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CryptoVision</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #f0f2f5; color: #1a1a2e; height: 100vh; display: flex; flex-direction: column; overflow: hidden; }
.header { background: white; padding: 14px 24px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #eee; flex-shrink: 0; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }
.logo { color: #F7931A; font-weight: 700; font-size: 18px; }
.live { color: #4caf50; font-size: 11px; background: #f0fff4; padding: 3px 10px; border-radius: 10px; border: 1px solid #c6f6d5; }
.content { flex: 1; overflow-y: auto; padding: 16px 24px; }
.top-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 16px; max-width: 600px; }
.price-card { background: white; border-radius: 14px; padding: 16px; text-align: center; cursor: pointer; transition: all 0.2s; border: 1.5px solid #eee; box-shadow: 0 1px 4px rgba(0,0,0,0.04); }
.price-card:hover { border-color: #F7931A88; transform: translateY(-2px); box-shadow: 0 4px 12px rgba(247,147,26,0.15); }
.card-sym { color: #999; font-size: 10px; margin-bottom: 6px; font-weight: 600; letter-spacing: 1px; }
.card-price { font-size: 16px; font-weight: 700; margin-bottom: 4px; }
.card-change { font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 6px; display: inline-block; }
.up { color: #16a34a; background: #f0fdf4; }
.down { color: #dc2626; background: #fef2f2; }
.chat-area { display: flex; flex-direction: column; gap: 16px; }
.msg-row { display: flex; gap: 10px; align-items: flex-start; width: 100%; }
.msg-row.user { flex-direction: row-reverse; }
.av { width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 12px; flex-shrink: 0; font-weight: 700; }
.ai-av { background: linear-gradient(135deg, #F7931A, #FFD700); color: white; }
.u-av { background: #e8eaf6; color: #5c6bc0; }
.bubble { max-width: 600px; padding: 12px 16px; border-radius: 16px; font-size: 13px; line-height: 1.7; }
.ai-b { background: white; color: #333; border-bottom-left-radius: 4px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); border: 1px solid #f0f0f0; }
.u-b { background: linear-gradient(135deg, #F7931A, #FFB347); color: white; border-bottom-right-radius: 4px; }
.chart-box { background: white; border-radius: 16px; padding: 20px; width: 100%; max-width: 700px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); border: 1px solid #f0f0f0; }
.chart-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.chart-title { color: #333; font-size: 14px; font-weight: 700; }
.chart-badge { font-size: 11px; font-weight: 600; padding: 3px 10px; border-radius: 8px; }
.chart-wrap { position: relative; height: 220px; }
.chart-sum { color: #999; font-size: 11px; margin-top: 12px; padding-top: 10px; border-top: 1px solid #f5f5f5; display: flex; gap: 16px; }
.chart-sum span { display: flex; gap: 4px; align-items: center; }
.table-box { background: white; border-radius: 16px; padding: 20px; width: 100%; max-width: 700px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); border: 1px solid #f0f0f0; }
.table-header { color: #333; font-size: 14px; font-weight: 700; margin-bottom: 14px; }
.dtable { width: 100%; border-collapse: collapse; font-size: 13px; }
.dtable th { color: #aaa; font-weight: 500; padding: 6px 10px; text-align: right; font-size: 11px; border-bottom: 1px solid #f5f5f5; }
.dtable th:first-child { text-align: left; }
.dtable td { padding: 10px 10px; border-top: 1px solid #f9f9f9; text-align: right; color: #333; }
.dtable td:first-child { text-align: left; }
.dtable tr:hover td { background: #fafafa; }
.coin-name { font-weight: 600; color: #222; }
.coin-sub { color: #bbb; font-size: 11px; }
.input-area { background: white; padding: 12px 24px; border-top: 1px solid #eee; flex-shrink: 0; box-shadow: 0 -1px 4px rgba(0,0,0,0.04); }
.chips { display: flex; gap: 8px; overflow-x: auto; margin-bottom: 10px; scrollbar-width: none; }
.chips::-webkit-scrollbar { display: none; }
.chip { background: #f8f9fa; border: 1px solid #eee; color: #666; border-radius: 16px; padding: 6px 14px; font-size: 12px; cursor: pointer; white-space: nowrap; transition: all 0.2s; }
.chip:hover { background: #fff3e0; border-color: #F7931A; color: #F7931A; }
.chip:disabled { opacity: 0.4; cursor: not-allowed; }
.irow { display: flex; gap: 10px; align-items: center; max-width: 700px; }
.irow input { flex: 1; background: #f8f9fa; border: 1.5px solid #eee; border-radius: 24px; padding: 10px 18px; font-size: 13px; color: #333; outline: none; transition: all 0.2s; }
.irow input:focus { border-color: #F7931A88; background: white; box-shadow: 0 0 0 3px rgba(247,147,26,0.08); }
.sbtn { background: linear-gradient(135deg, #F7931A, #FFB347); border: none; border-radius: 50%; width: 42px; height: 42px; color: white; font-size: 18px; cursor: pointer; flex-shrink: 0; box-shadow: 0 2px 8px rgba(247,147,26,0.4); transition: all 0.2s; }
.sbtn:hover:not(:disabled) { transform: scale(1.05); }
.sbtn:disabled { opacity: 0.4; cursor: not-allowed; transform: none; }
.dots span { display: inline-block; width: 6px; height: 6px; background: #F7931A; border-radius: 50%; animation: bonce 1.2s infinite; margin: 0 2px; }
.dots span:nth-child(2) { animation-delay: 0.2s; }
.dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes bonce { 0%,60%,100%{transform:translateY(0)} 30%{transform:translateY(-5px)} }
</style>
</head>
<body>
<div class="header">
  <div class="logo">&#8383; CryptoVision</div>
  <div class="live">&#9679; Live</div>
</div>
<div class="content" id="content">
  <div class="top-cards">
    <div class="price-card" onclick="doSend('BTC chart')"><div class="card-sym">BITCOIN</div><div class="card-price" style="color:#F7931A" id="p-btc">...</div><div class="card-change" id="c-btc">--</div></div>
    <div class="price-card" onclick="doSend('ETH chart')"><div class="card-sym">ETHEREUM</div><div class="card-price" style="color:#627EEA" id="p-eth">...</div><div class="card-change" id="c-eth">--</div></div>
    <div class="price-card" onclick="doSend('SOL chart')"><div class="card-sym">SOLANA</div><div class="card-price" style="color:#9945FF" id="p-sol">...</div><div class="card-change" id="c-sol">--</div></div>
  </div>
  <div class="chat-area" id="chatArea">
    <div class="msg-row">
      <div class="av ai-av">AI</div>
      <div class="bubble ai-b">Hello! I am CryptoVision AI.<br><br>I can help you:<br>- Check real-time prices<br>- Generate price charts<br>- Analyze market data<br>- Answer crypto questions<br><br>Try clicking a price card above!</div>
    </div>
  </div>
</div>
<div class="input-area">
  <div class="chips">
    <button class="chip" onclick="doSend('BTC chart')">&#128200; BTC Chart</button>
    <button class="chip" onclick="doSend('ETH chart')">&#128201; ETH Chart</button>
    <button class="chip" onclick="doSend('market overview')">&#128293; Market</button>
    <button class="chip" onclick="doSend('SOL chart')">&#9900; SOL Chart</button>
    <button class="chip" onclick="doSend('top coins')">&#127942; Top Coins</button>
  </div>
  <div class="irow">
    <input type="text" id="inp" placeholder="Ask me anything about crypto..." />
    <button class="sbtn" id="sbtn" onclick="doSend()">&#9658;</button>
  </div>
</div>
<script>
var chatHistory = [];
var busy = false;

function escapeHtml(value) {
  return String(value == null ? '' : value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function nl2br(value) {
  return escapeHtml(value).replace(/\n/g, '<br>');
}

function setBusy(v) {
  busy = v;
  document.getElementById('sbtn').disabled = v;
  document.getElementById('inp').disabled = v;
  var chips = document.querySelectorAll('.chip');
  for (var i = 0; i < chips.length; i++) { chips[i].disabled = v; }
}

function loadPrices() {
  fetch('/top_prices').then(function(r) { return r.json(); }).then(function(data) {
    var map = {};
    for (var i = 0; i < data.length; i++) { map[data[i].symbol] = data[i]; }
    var pairs = [['BTC','btc'],['ETH','eth'],['SOL','sol']];
    for (var j = 0; j < pairs.length; j++) {
      var s = pairs[j][0]; var id = pairs[j][1];
      if (map[s]) {
        var pe = document.getElementById('p-' + id);
        var ce = document.getElementById('c-' + id);
        if (pe) pe.textContent = '$' + map[s].price.toLocaleString('en-US', {maximumFractionDigits:2});
        if (ce) {
          var up = map[s].change >= 0;
          ce.textContent = (up ? '+' : '') + map[s].change + '%';
          ce.className = 'card-change ' + (up ? 'up' : 'down');
        }
      }
    }
  }).catch(function() {});
}

function doSend(text) {
  if (busy) return;
  var inp = document.getElementById('inp');
  var msg = text || inp.value.trim();
  if (!msg) return;
  inp.value = '';
  addUserMsg(msg);
  chatHistory.push({role:'user', content:msg});
  setBusy(true);
  var typing = addTyping();
  fetch('/chat', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({messages: chatHistory})
  }).then(function(r) {
    if (!r.ok) throw new Error('HTTP ' + r.status);
    return r.json();
  }).then(function(data) {
    typing.remove();
    if (data.type === 'chart') { addChart(data); }
    else if (data.type === 'table') { addTable(data); }
    else { addAIMsg(data.reply || 'No response received. Please retry.'); }
    chatHistory.push({role:'assistant', content: data.reply || data.summary || ''});
    setBusy(false);
  }).catch(function() {
    typing.remove();
    addAIMsg('Network error, please retry.');
    chatHistory.pop();
    setBusy(false);
  });
}

document.getElementById('inp').addEventListener('keydown', function(e) {
  if (e.key === 'Enter' && !busy) doSend();
});

function addUserMsg(text) {
  var area = document.getElementById('chatArea');
  var d = document.createElement('div');
  d.className = 'msg-row user';
  d.innerHTML = '<div class="av u-av">U</div><div class="bubble u-b">' + nl2br(text) + '</div>';
  area.appendChild(d);
  scrollDown();
}

function addAIMsg(text) {
  var area = document.getElementById('chatArea');
  var d = document.createElement('div');
  d.className = 'msg-row';
  d.innerHTML = '<div class="av ai-av">AI</div><div class="bubble ai-b">' + nl2br(text) + '</div>';
  area.appendChild(d);
  scrollDown();
}

function addTyping() {
  var area = document.getElementById('chatArea');
  var d = document.createElement('div');
  d.className = 'msg-row';
  d.innerHTML = '<div class="av ai-av">AI</div><div class="bubble ai-b"><div class="dots"><span></span><span></span><span></span></div></div>';
  area.appendChild(d);
  scrollDown();
  return d;
}

function addChart(data) {
  var area = document.getElementById('chatArea');
  var id = 'ch' + Date.now();
  var prices = data.prices;
  if (!prices || !prices.length) {
    addAIMsg(data.reply || 'Chart data is unavailable right now.');
    return;
  }
  var up = prices[prices.length-1] >= prices[0];
  var color = up ? '#16a34a' : '#dc2626';
  var badge = up ? '<span class="chart-badge up">+' + data.change + '%</span>' : '<span class="chart-badge down">' + data.change + '%</span>';
  var d = document.createElement('div');
  d.className = 'msg-row';
  d.innerHTML = '<div class="av ai-av">AI</div><div class="chart-box"><div class="chart-header"><div class="chart-title">' + escapeHtml(data.title) + '</div>' + badge + '</div><div class="chart-wrap"><canvas id="' + id + '"></canvas></div><div class="chart-sum"><span>Current: <b>$' + parseFloat(prices[prices.length-1]).toLocaleString('en-US',{maximumFractionDigits:4}) + '</b></span><span>High: <b>$' + data.high + '</b></span><span>Low: <b>$' + data.low + '</b></span><span style="margin-left:auto;color:#ccc">CoinGecko</span></div></div>';
  area.appendChild(d);
  scrollDown();
  setTimeout(function() {
    var ctx = document.getElementById(id);
    if (!ctx) return;
    new Chart(ctx.getContext('2d'), {
      type: 'line',
      data: {
        labels: data.labels,
        datasets: [{
          data: prices,
          borderColor: color,
          backgroundColor: up ? 'rgba(22,163,74,0.06)' : 'rgba(220,38,38,0.06)',
          borderWidth: 2,
          pointRadius: 0,
          tension: 0.4,
          fill: true
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function(ctx) { return '$' + ctx.parsed.y.toLocaleString('en-US',{maximumFractionDigits:4}); }
            }
          }
        },
        scales: {
          x: { display: true, grid: { display: false }, ticks: { color: '#ddd', font: { size: 10 }, maxTicksLimit: 6 } },
          y: {
            grid: { color: '#f8f8f8' },
            ticks: {
              color: '#bbb',
              font: { size: 10 },
              maxTicksLimit: 5,
              callback: function(v) { return '$' + (v >= 1000 ? (v/1000).toFixed(1)+'k' : v.toFixed(2)); }
            }
          }
        }
      }
    });
  }, 100);
}

function addTable(data) {
  var area = document.getElementById('chatArea');
  var d = document.createElement('div');
  d.className = 'msg-row';
  var rows = '';
  for (var i = 0; i < data.rows.length; i++) {
    var r = data.rows[i];
    var up = r.change >= 0;
    rows += '<tr><td><div class="coin-name">' + escapeHtml(r.symbol) + '</div><div class="coin-sub">' + escapeHtml(r.name) + '</div></td><td>$' + r.price.toLocaleString('en-US',{maximumFractionDigits:4}) + '</td><td><span class="' + (up?'up':'down') + '" style="padding:3px 8px;border-radius:6px;">' + (up?'+':'') + r.change + '%</span></td><td style="color:#999">$' + (r.volume/1e9).toFixed(1) + 'B</td></tr>';
  }
  d.innerHTML = '<div class="av ai-av">AI</div><div class="table-box"><div class="table-header">Top Coins - Live Market</div><table class="dtable"><tr><th>Coin</th><th>Price</th><th>24h</th><th>Volume</th></tr>' + rows + '</table><div style="color:#ccc;font-size:11px;margin-top:10px;padding-top:8px;border-top:1px solid #f5f5f5;">' + escapeHtml(data.summary) + '</div></div>';
  area.appendChild(d);
  scrollDown();
}

function scrollDown() {
  var c = document.getElementById('content');
  setTimeout(function() { c.scrollTop = c.scrollHeight; }, 80);
}

loadPrices();
setInterval(loadPrices, 60000);
</script>
</body>
</html>"""

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/top_prices")
def top_prices():
    return jsonify(get_top_prices())

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    messages = data.get("messages", [])
    if not isinstance(messages, list):
        messages = []

    user_msg = messages[-1].get("content", "") if messages and isinstance(messages[-1], dict) else ""
    if not isinstance(user_msg, str):
        user_msg = str(user_msg or "")
    user_msg = user_msg.strip()

    if not user_msg:
        return jsonify({
            "type": "text",
            "reply": "Please enter a question about crypto, a coin symbol, or a chart request."
        })

    msg_lower = user_msg.lower()

    chart_kw = ["chart", "trend", "btc", "eth", "sol", "bnb", "doge", "xrp", "ada", "avax", "dot", "shib", "ltc", "link"]
    table_kw = ["market", "top", "overview", "all", "coins", "list"]

    is_chart = any(k in msg_lower for k in chart_kw)
    is_table = any(k in msg_lower for k in table_kw)

    found_id = None
    found_symbol = None
    for name, cid in COIN_MAP.items():
        if name in msg_lower:
            found_id = cid
            found_symbol = SYMBOL_MAP.get(cid, cid.upper())
            break

    if is_chart and found_id:
        days = 30 if any(k in msg_lower for k in ["30", "month"]) else 7 if any(k in msg_lower for k in ["7", "week"]) else 1
        labels, prices = get_kline(found_id, days=days)
        if labels and prices:
            change = round((prices[-1] - prices[0]) / prices[0] * 100, 2) if prices[0] else 0
            high = max(prices)
            low = min(prices)
            period = "30D" if days == 30 else "7D" if days == 7 else "24H"
            return jsonify({
                "type": "chart",
                "title": found_symbol + "/USDT  " + period,
                "labels": labels,
                "prices": prices,
                "change": change,
                "high": round(high, 2),
                "low": round(low, 2),
                "summary": "Current $" + str(round(prices[-1], 4)) + " | " + ("+" if change >= 0 else "") + str(change) + "%",
                "reply": found_symbol + " chart"
            })

        return jsonify({
            "type": "text",
            "reply": "I could not load chart data right now. Please try again in a moment."
        })

    if is_table:
        top = get_top_prices()
        if top:
            return jsonify({
                "type": "table",
                "title": "Top Coins",
                "rows": top,
                "summary": str(len(top)) + " coins | Updated " + datetime.datetime.now().strftime("%H:%M"),
                "reply": "Market overview"
            })

    price_context = ""
    if found_id:
        top = get_top_prices()
        for t in top:
            if t["symbol"] == found_symbol:
                price_context = " [Live] " + found_symbol + ": $" + str(t["price"]) + ", 24h=" + str(t["change"]) + "%"
                break

    if not DEEPSEEK_API_KEY:
        return jsonify({
            "type": "text",
            "reply": "CryptoVision is running, but the AI chat is not configured yet. Please add DEEPSEEK_API_KEY in Render Environment settings, then redeploy. Crypto investing involves risk."
        })

    system = "You are CryptoVision AI. Answer in the same language the user writes in. Be concise and professional. No specific buy/sell advice. Always remind users crypto investing involves risk."

    api_msgs = [{"role": "system", "content": system}]
    for h in messages[:-1]:
        if isinstance(h, dict) and h.get("role") in ["user", "assistant"] and isinstance(h.get("content"), str):
            api_msgs.append({"role": h["role"], "content": h["content"][:2000]})
    api_msgs.append({"role": "user", "content": user_msg + price_context})

    try:
        res = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": "Bearer " + DEEPSEEK_API_KEY, "Content-Type": "application/json"},
            json={"model": "deepseek-chat", "messages": api_msgs, "max_tokens": 500, "temperature": 0.4},
            timeout=LLM_TIMEOUT
        )
        res.raise_for_status()
        payload = res.json()
        reply = payload["choices"][0]["message"]["content"]
    except requests.exceptions.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "unknown"
        reply = "AI service returned an error (" + str(status) + "). Please check the DeepSeek API key and billing/status in Render settings."
    except requests.exceptions.Timeout:
        reply = "AI service timed out. Please retry in a moment."
    except Exception:
        reply = "AI service is temporarily unavailable. Please retry in a moment."

    return jsonify({"type": "text", "reply": reply})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
