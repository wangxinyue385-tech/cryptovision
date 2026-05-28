from flask import Flask, request, jsonify, render_template_string
import requests
import os
import json

app = Flask(__name__)
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")

COIN_MAP = {
    "比特币": "BTC", "bitcoin": "BTC", "btc": "BTC",
    "以太坊": "ETH", "ethereum": "ETH", "eth": "ETH",
    "bnb": "BNB", "币安币": "BNB",
    "狗狗币": "DOGE", "dogecoin": "DOGE", "doge": "DOGE",
    "sol": "SOL", "solana": "SOL", "索拉纳": "SOL",
    "xrp": "XRP", "瑞波": "XRP", "ripple": "XRP",
    "ada": "ADA", "cardano": "ADA",
    "dot": "DOT", "polkadot": "DOT", "波卡": "DOT",
    "avax": "AVAX", "avalanche": "AVAX",
    "matic": "MATIC", "polygon": "MATIC",
    "link": "LINK", "chainlink": "LINK",
    "ltc": "LTC", "litecoin": "LTC", "莱特币": "LTC",
    "shib": "SHIB", "柴犬币": "SHIB",
    "trx": "TRX", "tron": "TRX",
    "uni": "UNI", "uniswap": "UNI",
}

def get_price(symbol):
    try:
        s = symbol.upper()
        if not s.endswith("-USDT"):
            s = s + "-USDT"
        res = requests.get(f"https://www.okx.com/api/v5/market/ticker?instId={s}", timeout=5)
        d = res.json()
        if d["code"] != "0":
            return None
        t = d["data"][0]
        price = float(t["last"])
        change = (float(t["last"]) - float(t["open24h"])) / float(t["open24h"]) * 100
        return {
            "symbol": symbol.upper(),
            "price": price,
            "change": round(change, 2),
            "high": float(t["high24h"]),
            "low": float(t["low24h"]),
            "volume": float(t["vol24h"])
        }
    except:
        return None

def get_kline(symbol, bar="1H", limit=24):
    try:
        s = symbol.upper()
        if not s.endswith("-USDT"):
            s = s + "-USDT"
        res = requests.get(
            f"https://www.okx.com/api/v5/market/candles?instId={s}&bar={bar}&limit={limit}",
            timeout=5
        )
        d = res.json()
        if d["code"] != "0":
            return None
        candles = d["data"]
        candles.reverse()
        return [{"time": c[0], "open": float(c[1]), "high": float(c[2]), "low": float(c[3]), "close": float(c[4])} for c in candles]
    except:
        return None

def get_top_prices():
    symbols = ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "AVAX"]
    result = []
    for s in symbols:
        p = get_price(s)
        if p:
            result.append(p)
    return result

HTML = '''<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CryptoVision</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #0a0a14; color: #e0e0e0; height: 100vh; display: flex; flex-direction: column; overflow: hidden; }

.header { padding: 12px 16px; display: flex; align-items: center; justify-content: space-between; border-bottom: 0.5px solid #1a1a2e; flex-shrink: 0; }
.logo { color: #F7931A; font-weight: 600; font-size: 16px; }
.live-dot { color: #4caf50; font-size: 11px; }

.content { flex: 1; overflow-y: auto; padding: 12px 16px; }

.top-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-bottom: 14px; }
.price-card { background: #1a1a2e; border-radius: 10px; padding: 12px; text-align: center; cursor: pointer; transition: all 0.2s; border: 0.5px solid transparent; }
.price-card:hover { border-color: #F7931A44; }
.price-card.active { border-color: #F7931A; }
.card-symbol { color: #666; font-size: 10px; margin-bottom: 4px; }
.card-price { font-size: 14px; font-weight: 600; margin-bottom: 2px; }
.card-change { font-size: 10px; }
.up { color: #4caf50; }
.down { color: #f44336; }

.chat-area { display: flex; flex-direction: column; gap: 12px; }

.msg-row { display: flex; gap: 8px; align-items: flex-start; }
.msg-row.user { flex-direction: row-reverse; }
.avatar { width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 12px; flex-shrink: 0; }
.ai-avatar { background: #F7931A; color: #0a0a14; font-weight: 600; font-size: 10px; }
.user-avatar { background: #2a2a3e; }
.bubble { max-width: 85%; padding: 10px 14px; border-radius: 16px; font-size: 13px; line-height: 1.6; }
.ai-bubble { background: #1a1a2e; color: #ddd; border-bottom-left-radius: 4px; }
.user-bubble { background: #F7931A; color: #0a0a14; border-bottom-right-radius: 4px; font-weight: 500; }
.chart-bubble { background: #1a1a2e; border-radius: 12px; padding: 14px; max-width: 95%; }
.chart-title { color: #aaa; font-size: 11px; margin-bottom: 10px; }
.chart-wrap { position: relative; height: 160px; }
.table-wrap { width: 100%; }
.data-table { width: 100%; border-collapse: collapse; font-size: 11px; }
.data-table th { color: #555; font-weight: normal; padding: 4px 6px; text-align: right; }
.data-table th:first-child { text-align: left; }
.data-table td { padding: 6px 6px; border-top: 0.5px solid #ffffff08; text-align: right; color: #ccc; }
.data-table td:first-child { text-align: left; color: #aaa; }

.bottom-nav { display: grid; grid-template-columns: repeat(4, 1fr); border-top: 0.5px solid #1a1a2e; flex-shrink: 0; }
.nav-item { padding: 10px 0; text-align: center; cursor: pointer; border-top: 2px solid transparent; transition: all 0.2s; }
.nav-item.active { border-top-color: #F7931A; }
.nav-item.active .nav-label { color: #F7931A; }
.nav-icon { font-size: 16px; margin-bottom: 2px; }
.nav-label { font-size: 9px; color: #444; }

.input-area { padding: 10px 16px; border-top: 0.5px solid #1a1a2e; flex-shrink: 0; }
.quick-chips { display: flex; gap: 6px; flex-wrap: nowrap; overflow-x: auto; margin-bottom: 8px; padding-bottom: 2px; scrollbar-width: none; }
.quick-chips::-webkit-scrollbar { display: none; }
.chip { background: #1a1a2e; border: 0.5px solid #2a2a3e; color: #888; border-radius: 14px; padding: 4px 10px; font-size: 11px; cursor: pointer; white-space: nowrap; transition: all 0.2s; flex-shrink: 0; }
.chip:hover:not(:disabled) { border-color: #F7931A; color: #F7931A; }
.chip:disabled { opacity: 0.4; cursor: not-allowed; }
.input-row { display: flex; gap: 8px; }
.input-row input { flex: 1; background: #1a1a2e; border: 0.5px solid #2a2a3e; border-radius: 20px; padding: 9px 14px; font-size: 13px; color: #e0e0e0; outline: none; }
.input-row input:focus { border-color: #F7931A44; }
.send-btn { background: #F7931A; border: none; border-radius: 50%; width: 36px; height: 36px; color: #0a0a14; font-size: 16px; cursor: pointer; flex-shrink: 0; transition: all 0.2s; }
.send-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.typing { color: #555; font-size: 12px; padding: 4px 0; }
</style>
</head>
<body>

<div class="header">
  <div class="logo">₿ CryptoVision</div>
  <div class="live-dot">● 实时</div>
</div>

<div class="content" id="content">
  <div class="top-cards" id="topCards">
    <div class="price-card" onclick="askCoin('BTC')">
      <div class="card-symbol">BTC</div>
      <div class="card-price" style="color:#F7931A" id="btc-price">--</div>
      <div class="card-change" id="btc-change">--</div>
    </div>
    <div class="price-card" onclick="askCoin('ETH')">
      <div class="card-symbol">ETH</div>
      <div class="card-price" style="color:#627EEA" id="eth-price">--</div>
      <div class="card-change" id="eth-change">--</div>
    </div>
    <div class="price-card" onclick="askCoin('SOL')">
      <div class="card-symbol">SOL</div>
      <div class="card-price" style="color:#9945FF" id="sol-price">--</div>
      <div class="card-change" id="sol-change">--</div>
    </div>
  </div>
  <div class="chat-area" id="chatArea">
    <div class="msg-row">
      <div class="avatar ai-avatar">AI</div>
      <div class="bubble ai-bubble">你好！我可以帮你查询实时行情、生成图表、分析市场数据。<br><br>试试问我：<br>• BTC今天走势怎么样？<br>• 哪些合约资金费率最高？<br>• ETH最近30天表现如何？</div>
    </div>
  </div>
</div>

<div class="input-area">
  <div class="quick-chips" id="chips">
    <button class="chip" onclick="sendMsg('BTC走势图')">📈 BTC走势</button>
    <button class="chip" onclick="sendMsg('ETH走势图')">📊 ETH走势</button>
    <button class="chip" onclick="sendMsg('主流币行情')">🔥 主流行情</button>
    <button class="chip" onclick="sendMsg('SOL走势图')">◎ SOL走势</button>
    <button class="chip" onclick="sendMsg('市场概况')">🌐 市场概况</button>
  </div>
  <div class="input-row">
    <input type="text" id="userInput" placeholder="问我任何市场问题..." onkeydown="if(event.key==='Enter'&&!sending)sendMsg()"/>
    <button class="send-btn" id="sendBtn" onclick="sendMsg()">➤</button>
  </div>
</div>

<script>
let history = [];
let sending = false;
let chartInstances = {};

function setLoading(on) {
  sending = on;
  document.getElementById("sendBtn").disabled = on;
  document.getElementById("userInput").disabled = on;
  document.querySelectorAll(".chip").forEach(c => c.disabled = on);
}

async function loadTopPrices() {
  try {
    const res = await fetch("/top_prices");
    const data = await res.json();
    const map = {};
    data.forEach(d => map[d.symbol] = d);
    ["BTC","ETH","SOL"].forEach(s => {
      if (map[s]) {
        const el = document.getElementById(s.toLowerCase()+"-price");
        const cel = document.getElementById(s.toLowerCase()+"-change");
        if (el) el.textContent = "$" + map[s].price.toLocaleString("en", {maximumFractionDigits:2});
        if (cel) {
          const up = map[s].change >= 0;
          cel.textContent = (up?"+":"") + map[s].change + "%";
          cel.className = "card-change " + (up?"up":"down");
        }
      }
    });
  } catch(e) {}
}

function askCoin(symbol) {
  sendMsg(symbol + "走势图");
}

async function sendMsg(text) {
  if (sending) return;
  const input = document.getElementById("userInput");
  const msg = text || input.value.trim();
  if (!msg) return;
  input.value = "";

  appendUserMsg(msg);
  history.push({role:"user", content:msg});
  setLoading(true);

  const typing = appendTyping();
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 20000);

  try {
    const res = await fetch("/chat", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({messages: history}),
      signal: controller.signal
    });
    clearTimeout(timeout);
    const data = await res.json();
    typing.remove();

    if (data.type === "chart") {
      appendChart(data);
    } else if (data.type === "table") {
      appendTable(data);
    } else {
      appendAIMsg(data.reply);
    }
    history.push({role:"assistant", content: data.reply || data.summary || ""});
  } catch(e) {
    clearTimeout(timeout);
    typing.remove();
    appendAIMsg("网络超时，请重试～");
    history.pop();
  } finally {
    setLoading(false);
  }
}

function appendUserMsg(text) {
  const area = document.getElementById("chatArea");
  const div = document.createElement("div");
  div.className = "msg-row user";
  div.innerHTML = `<div class="avatar user-avatar">👤</div><div class="bubble user-bubble">${text}</div>`;
  area.appendChild(div);
  scrollBottom();
}

function appendAIMsg(text) {
  const area = document.getElementById("chatArea");
  const div = document.createElement("div");
  div.className = "msg-row";
  div.innerHTML = `<div class="avatar ai-avatar">AI</div><div class="bubble ai-bubble">${text.replace(/\n/g,"<br>")}</div>`;
  area.appendChild(div);
  scrollBottom();
}

function appendTyping() {
  const area = document.getElementById("chatArea");
  const div = document.createElement("div");
  div.className = "msg-row";
  div.innerHTML = `<div class="avatar ai-avatar">AI</div><div class="bubble ai-bubble typing">正在获取数据...</div>`;
  area.appendChild(div);
  scrollBottom();
  return div;
}

function appendChart(data) {
  const area = document.getElementById("chatArea");
  const id = "chart_" + Date.now();
  const div = document.createElement("div");
  div.className = "msg-row";
  div.innerHTML = `
    <div class="avatar ai-avatar">AI</div>
    <div class="chart-bubble">
      <div class="chart-title">${data.title}</div>
      <div class="chart-wrap"><canvas id="${id}"></canvas></div>
      <div style="color:#666; font-size:10px; margin-top:8px;">${data.summary}</div>
    </div>`;
  area.appendChild(div);
  scrollBottom();

  const ctx = document.getElementById(id).getContext("2d");
  const labels = data.labels;
  const prices = data.prices;
  const up = prices[prices.length-1] >= prices[0];

  if (chartInstances[id]) chartInstances[id].destroy();
  chartInstances[id] = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [{
        data: prices,
        borderColor: up ? "#4caf50" : "#f44336",
        backgroundColor: up ? "rgba(76,175,80,0.1)" : "rgba(244,67,54,0.1)",
        borderWidth: 1.5,
        pointRadius: 0,
        tension: 0.3,
        fill: true
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { display: false },
        y: {
          grid: { color: "#ffffff08" },
          ticks: { color: "#555", font: { size: 10 }, maxTicksLimit: 4,
            callback: v => "$" + (v >= 1000 ? (v/1000).toFixed(1)+"k" : v.toFixed(2)) }
        }
      }
    }
  });
}

function appendTable(data) {
  const area = document.getElementById("chatArea");
  const div = document.createElement("div");
  div.className = "msg-row";
  let rows = data.rows.map(r => `
    <tr>
      <td>${r.symbol}</td>
      <td>$${r.price.toLocaleString("en",{maximumFractionDigits:4})}</td>
      <td class="${r.change>=0?'up':'down'}">${r.change>=0?'+':''}${r.change}%</td>
      <td style="color:#555;">$${(r.volume/1e9).toFixed(2)}B</td>
    </tr>`).join("");
  div.innerHTML = `
    <div class="avatar ai-avatar">AI</div>
    <div class="chart-bubble" style="max-width:95%;">
      <div class="chart-title">${data.title}</div>
      <div class="table-wrap">
        <table class="data-table">
          <tr><th>币种</th><th>价格</th><th>24h</th><th>成交量</th></tr>
          ${rows}
        </table>
      </div>
      <div style="color:#666; font-size:10px; margin-top:8px;">${data.summary}</div>
    </div>`;
  area.appendChild(div);
  scrollBottom();
}

function scrollBottom() {
  const c = document.getElementById("content");
  setTimeout(() => c.scrollTop = c.scrollHeight, 50);
}

loadTopPrices();
setInterval(loadTopPrices, 30000);
</script>
</body>
</html>'''

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/top_prices")
def top_prices():
    return jsonify(get_top_prices())

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    messages = data.get("messages", [])
    user_msg = messages[-1]["content"] if messages else ""
    msg_lower = user_msg.lower()

    # 检测是否是走势图请求
    chart_keywords = ["走势", "图", "chart", "趋势", "k线", "价格变化", "最近"]
    is_chart = any(k in msg_lower for k in chart_keywords)

    # 检测是否是行情表格请求
    table_keywords = ["行情", "排行", "主流币", "所有", "市场概况", "概况", "top"]
    is_table = any(k in msg_lower for k in table_keywords)

    # 找到币种
    found_symbol = None
    for name, symbol in COIN_MAP.items():
        if name in msg_lower:
            found_symbol = symbol
            break

    if is_chart and found_symbol:
        kline = get_kline(found_symbol, bar="1H", limit=24)
        price_data = get_price(found_symbol)
        if kline and price_data:
            labels = [str(i)+"h" for i in range(len(kline))]
            prices = [c["close"] for c in kline]
            change = price_data["change"]
            return jsonify({
                "type": "chart",
                "title": f"{found_symbol}/USDT · 24小时走势",
                "labels": labels,
                "prices": prices,
                "summary": f"当前价格 ${price_data['price']:,.4f} · 24h {'▲' if change>=0 else '▼'} {abs(change)}% · 最高 ${price_data['high']:,.2f} · 最低 ${price_data['low']:,.2f}",
                "reply": f"{found_symbol} 24小时走势图"
            })

    if is_table:
        top = get_top_prices()
        if top:
            return jsonify({
                "type": "table",
                "title": "主流币实时行情",
                "rows": top,
                "summary": f"数据来自 OKX · 共 {len(top)} 个币种",
                "reply": "主流币行情表格"
            })

    # 普通AI对话
    price_context = ""
    if found_symbol:
        p = get_price(found_symbol)
        if p:
            price_context = f"\n\n[实时数据] {found_symbol}: 价格=${p['price']}, 24h变化={p['change']}%, 最高=${p['high']}, 最低=${p['low']}"

    system = """你是CryptoVision的AI助手，专业分析加密货币市场。
支持中英文。回复简洁专业，3-5句话为宜。
如果有实时数据，直接引用。
不给具体买卖建议，但可以分析市场情况。
投资有风险，适时提醒用户。"""

    api_msgs = [{"role": "system", "content": system}]
    for h in messages[:-1]:
        api_msgs.append(h)
    api_msgs.append({"role": "user", "content": user_msg + price_context})

    try:
        res = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
            json={"model": "deepseek-chat", "messages": api_msgs, "max_tokens": 500, "temperature": 0.4},
            timeout=12
        )
        reply = res.json()["choices"][0]["message"]["content"]
    except:
        reply = "网络超时，请重试～"

    return jsonify({"type": "text", "reply": reply})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
