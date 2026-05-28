from flask import Flask, request, jsonify, render_template_string
import requests
import os

app = Flask(__name__)
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")

COIN_MAP = {
    "比特币": "bitcoin", "bitcoin": "bitcoin", "btc": "bitcoin",
    "以太坊": "ethereum", "ethereum": "ethereum", "eth": "ethereum",
    "bnb": "binancecoin", "币安币": "binancecoin",
    "狗狗币": "dogecoin", "doge": "dogecoin",
    "sol": "solana", "solana": "solana", "索拉纳": "solana",
    "xrp": "ripple", "瑞波": "ripple",
    "ada": "cardano", "cardano": "cardano",
    "avax": "avalanche-2", "avalanche": "avalanche-2",
    "dot": "polkadot", "polkadot": "polkadot",
    "shib": "shiba-inu", "柴犬": "shiba-inu",
    "ltc": "litecoin", "litecoin": "litecoin",
    "link": "chainlink", "chainlink": "chainlink",
    "uni": "uniswap", "uniswap": "uniswap",
    "atom": "cosmos", "cosmos": "cosmos",
    "trx": "tron", "tron": "tron",
    "matic": "matic-network", "polygon": "matic-network",
}

SYMBOL_MAP = {
    "bitcoin": "BTC", "ethereum": "ETH", "binancecoin": "BNB",
    "dogecoin": "DOGE", "solana": "SOL", "ripple": "XRP",
    "cardano": "ADA", "avalanche-2": "AVAX", "polkadot": "DOT",
    "shiba-inu": "SHIB", "litecoin": "LTC", "chainlink": "LINK",
    "uniswap": "UNI", "cosmos": "ATOM", "tron": "TRX",
    "matic-network": "MATIC",
}

def get_top_prices():
    try:
        ids = "bitcoin,ethereum,solana,binancecoin,ripple,cardano,dogecoin,avalanche-2"
        res = requests.get(
            f"https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids={ids}&order=market_cap_desc&sparkline=false",
            timeout=8
        )
        data = res.json()
        result = []
        for d in data:
            result.append({
                "symbol": SYMBOL_MAP.get(d["id"], d["symbol"].upper()),
                "name": d["name"],
                "price": d["current_price"],
                "change": round(d["price_change_percentage_24h"] or 0, 2),
                "volume": d["total_volume"],
                "market_cap": d["market_cap"]
            })
        return result
    except Exception as e:
        return []

def get_kline(coin_id, days=1):
    try:
        res = requests.get(
            f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days={days}",
            timeout=8
        )
        data = res.json()
        prices = data.get("prices", [])
        step = max(1, len(prices) // 48)
        sampled = prices[::step][-48:]
        labels = []
        vals = []
        for p in sampled:
            import datetime
            t = datetime.datetime.fromtimestamp(p[0]/1000)
            labels.append(t.strftime("%H:%M"))
            vals.append(round(p[1], 4))
        return labels, vals
    except:
        return [], []

HTML = '''<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CryptoVision</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f0f2f5; color: #1a1a2e; height: 100vh; display: flex; flex-direction: column; overflow: hidden; }

.header { background: white; padding: 12px 16px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #eee; flex-shrink: 0; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }
.logo { color: #F7931A; font-weight: 700; font-size: 17px; }
.live-dot { color: #4caf50; font-size: 11px; background: #f0fff4; padding: 3px 8px; border-radius: 10px; border: 1px solid #c6f6d5; }

.content { flex: 1; overflow-y: auto; padding: 12px 16px; }

.top-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-bottom: 14px; }
.price-card { background: white; border-radius: 12px; padding: 12px; text-align: center; cursor: pointer; transition: all 0.2s; border: 1.5px solid #eee; box-shadow: 0 1px 4px rgba(0,0,0,0.04); }
.price-card:hover { border-color: #F7931A88; box-shadow: 0 2px 8px rgba(247,147,26,0.15); transform: translateY(-1px); }
.card-symbol { color: #999; font-size: 10px; margin-bottom: 4px; font-weight: 500; }
.card-price { font-size: 14px; font-weight: 700; margin-bottom: 3px; }
.card-change { font-size: 10px; font-weight: 500; padding: 2px 6px; border-radius: 6px; display: inline-block; }
.up { color: #16a34a; background: #f0fdf4; }
.down { color: #dc2626; background: #fef2f2; }

.chat-area { display: flex; flex-direction: column; gap: 12px; }

.msg-row { display: flex; gap: 8px; align-items: flex-start; }
.msg-row.user { flex-direction: row-reverse; }
.avatar { width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 12px; flex-shrink: 0; font-weight: 700; }
.ai-avatar { background: linear-gradient(135deg, #F7931A, #FFD700); color: white; }
.user-avatar { background: #e8eaf6; color: #5c6bc0; }
.bubble { max-width: 82%; padding: 10px 14px; border-radius: 16px; font-size: 13px; line-height: 1.7; }
.ai-bubble { background: white; color: #333; border-bottom-left-radius: 4px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); border: 1px solid #f0f0f0; }
.user-bubble { background: linear-gradient(135deg, #F7931A, #FFB347); color: white; border-bottom-right-radius: 4px; box-shadow: 0 2px 8px rgba(247,147,26,0.3); }

.chart-bubble { background: white; border-radius: 14px; padding: 14px; max-width: 95%; box-shadow: 0 1px 6px rgba(0,0,0,0.08); border: 1px solid #f0f0f0; }
.chart-title { color: #666; font-size: 11px; font-weight: 600; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 0.5px; }
.chart-wrap { position: relative; height: 150px; }
.data-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.data-table th { color: #999; font-weight: 500; padding: 4px 8px; text-align: right; font-size: 11px; }
.data-table th:first-child { text-align: left; }
.data-table td { padding: 8px 8px; border-top: 1px solid #f5f5f5; text-align: right; color: #333; }
.data-table td:first-child { text-align: left; color: #666; font-weight: 500; }
.chart-summary { color: #999; font-size: 11px; margin-top: 10px; padding-top: 8px; border-top: 1px solid #f5f5f5; }

.input-area { background: white; padding: 10px 14px; border-top: 1px solid #eee; flex-shrink: 0; box-shadow: 0 -1px 4px rgba(0,0,0,0.04); }
.quick-chips { display: flex; gap: 6px; flex-wrap: nowrap; overflow-x: auto; margin-bottom: 8px; scrollbar-width: none; }
.quick-chips::-webkit-scrollbar { display: none; }
.chip { background: #f8f9fa; border: 1px solid #eee; color: #666; border-radius: 14px; padding: 5px 12px; font-size: 11px; cursor: pointer; white-space: nowrap; transition: all 0.2s; }
.chip:hover:not(:disabled) { background: #fff3e0; border-color: #F7931A; color: #F7931A; }
.chip:disabled { opacity: 0.4; cursor: not-allowed; }
.input-row { display: flex; gap: 8px; align-items: center; }
.input-row input { flex: 1; background: #f8f9fa; border: 1.5px solid #eee; border-radius: 22px; padding: 9px 16px; font-size: 13px; color: #333; outline: none; transition: all 0.2s; }
.input-row input:focus { border-color: #F7931A88; background: white; box-shadow: 0 0 0 3px rgba(247,147,26,0.1); }
.send-btn { background: linear-gradient(135deg, #F7931A, #FFB347); border: none; border-radius: 50%; width: 38px; height: 38px; color: white; font-size: 16px; cursor: pointer; flex-shrink: 0; box-shadow: 0 2px 8px rgba(247,147,26,0.4); transition: all 0.2s; }
.send-btn:hover:not(:disabled) { transform: scale(1.05); }
.send-btn:disabled { opacity: 0.4; cursor: not-allowed; transform: none; }
.typing-dots { display: inline-flex; gap: 3px; }
.typing-dots span { width: 6px; height: 6px; background: #F7931A; border-radius: 50%; animation: bounce 1.2s infinite; }
.typing-dots span:nth-child(2) { animation-delay: 0.2s; }
.typing-dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce { 0%,60%,100%{transform:translateY(0)} 30%{transform:translateY(-6px)} }
</style>
</head>
<body>

<div class="header">
  <div class="logo">₿ CryptoVision</div>
  <div class="live-dot">● 实时数据</div>
</div>

<div class="content" id="content">
  <div class="top-cards">
    <div class="price-card" onclick="sendMsg('BTC走势图')">
      <div class="card-symbol">BITCOIN</div>
      <div class="card-price" style="color:#F7931A" id="btc-price">加载中...</div>
      <div class="card-change" id="btc-change">--</div>
    </div>
    <div class="price-card" onclick="sendMsg('ETH走势图')">
      <div class="card-symbol">ETHEREUM</div>
      <div class="card-price" style="color:#627EEA" id="eth-price">加载中...</div>
      <div class="card-change" id="eth-change">--</div>
    </div>
    <div class="price-card" onclick="sendMsg('SOL走势图')">
      <div class="card-symbol">SOLANA</div>
      <div class="card-price" style="color:#9945FF" id="sol-price">加载中...</div>
      <div class="card-change" id="sol-change">--</div>
    </div>
  </div>
  <div class="chat-area" id="chatArea">
    <div class="msg-row">
      <div class="avatar ai-avatar">AI</div>
      <div class="bubble ai-bubble">👋 你好！我是 CryptoVision AI。<br><br>我可以帮你：<br>• 查询任意币种实时价格<br>• 生成走势图表<br>• 分析市场行情<br>• 回答币圈问题<br><br>试试点击上方价格卡片，或直接提问！</div>
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
    [["BTC","btc","#F7931A"],["ETH","eth","#627EEA"],["SOL","sol","#9945FF"]].forEach(([s,id,color]) => {
      if (map[s]) {
        const pe = document.getElementById(id+"-price");
        const ce = document.getElementById(id+"-change");
        if (pe) pe.textContent = "$" + map[s].price.toLocaleString("en-US", {maximumFractionDigits:2});
        if (ce) {
          const up = map[s].change >= 0;
          ce.textContent = (up?"+":"") + map[s].change + "%";
          ce.className = "card-change " + (up?"up":"down");
        }
      }
    });
  } catch(e) {}
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
    appendAIMsg("⚠️ 网络超时，请重试～");
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
  div.innerHTML = `<div class="avatar ai-avatar">AI</div><div class="bubble ai-bubble"><div class="typing-dots"><span></span><span></span><span></span></div></div>`;
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
      <div class="chart-summary">${data.summary}</div>
    </div>`;
  area.appendChild(div);
  scrollBottom();

  setTimeout(() => {
    const ctx = document.getElementById(id);
    if (!ctx) return;
    const prices = data.prices;
    const up = prices[prices.length-1] >= prices[0];
    const color = up ? "#16a34a" : "#dc2626";
    const bgColor = up ? "rgba(22,163,74,0.08)" : "rgba(220,38,38,0.08)";

    new Chart(ctx.getContext("2d"), {
      type: "line",
      data: {
        labels: data.labels,
        datasets: [{
          data: prices,
          borderColor: color,
          backgroundColor: bgColor,
          borderWidth: 2,
          pointRadius: 0,
          tension: 0.4,
          fill: true
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: {
          callbacks: { label: ctx => "$" + ctx.parsed.y.toLocaleString("en-US", {maximumFractionDigits:4}) }
        }},
        scales: {
          x: { display: false },
          y: {
            grid: { color: "#f5f5f5" },
            ticks: { color: "#bbb", font: { size: 10 }, maxTicksLimit: 4,
              callback: v => "$" + (v >= 1000 ? (v/1000).toFixed(1)+"k" : v.toFixed(2)) }
          }
        }
      }
    });
  }, 100);
}

function appendTable(data) {
  const area = document.getElementById("chatArea");
  const div = document.createElement("div");
  div.className = "msg-row";
  let rows = data.rows.map(r => `
    <tr>
      <td><b>${r.symbol}</b><br><span style="color:#bbb;font-size:10px;">${r.name||''}</span></td>
      <td>$${r.price.toLocaleString("en-US",{maximumFractionDigits:4})}</td>
      <td><span class="${r.change>=0?'up':'down'}" style="padding:2px 6px;border-radius:5px;">${r.change>=0?'+':''}${r.change}%</span></td>
      <td style="color:#999;">$${(r.volume/1e9).toFixed(1)}B</td>
    </tr>`).join("");
  div.innerHTML = `
    <div class="avatar ai-avatar">AI</div>
    <div class="chart-bubble" style="max-width:95%;">
      <div class="chart-title">${data.title}</div>
      <table class="data-table">
        <tr><th>币种</th><th>价格</th><th>24h</th><th>成交量</th></tr>
        ${rows}
      </table>
      <div class="chart-summary">${data.summary}</div>
    </div>`;
  area.appendChild(div);
  scrollBottom();
}

function scrollBottom() {
  const c = document.getElementById("content");
  setTimeout(() => c.scrollTop = c.scrollHeight, 80);
}

loadTopPrices();
setInterval(loadTopPrices, 60000);
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
    import datetime
    data = request.json
    messages = data.get("messages", [])
    user_msg = messages[-1]["content"] if messages else ""
    msg_lower = user_msg.lower()

    chart_keywords = ["走势", "图", "chart", "趋势", "k线", "价格变化", "最近", "今天", "今日"]
    is_chart = any(k in msg_lower for k in chart_keywords)

    table_keywords = ["行情", "排行", "主流币", "市场概况", "概况", "所有", "top", "列表"]
    is_table = any(k in msg_lower for k in table_keywords)

    found_id = None
    found_symbol = None
    for name, cid in COIN_MAP.items():
        if name in msg_lower:
            found_id = cid
            found_symbol = SYMBOL_MAP.get(cid, cid.upper())
            break

    if is_chart and found_id:
        days = 7 if any(k in msg_lower for k in ["7天","一周","week","30天","月"]) else 1
        labels, prices = get_kline(found_id, days=days)
        if labels and prices:
            change = round((prices[-1]-prices[0])/prices[0]*100, 2) if prices[0] else 0
            return jsonify({
                "type": "chart",
                "title": f"{found_symbol}/USDT · {'7日' if days==7 else '24H'} 走势",
                "labels": labels,
                "prices": prices,
                "summary": f"当前 ${prices[-1]:,.4f} · {'▲' if change>=0 else '▼'} {abs(change)}% · 数据来源 CoinGecko",
                "reply": f"{found_symbol} 走势图已生成"
            })

    if is_table:
        top = get_top_prices()
        if top:
            return jsonify({
                "type": "table",
                "title": "主流币实时行情",
                "rows": top,
                "summary": f"共 {len(top)} 个币种 · 数据来源 CoinGecko · {datetime.datetime.now().strftime('%H:%M')} 更新",
                "reply": "主流币行情表格"
            })

    price_context = ""
    if found_id:
        top = get_top_prices()
        for t in top:
            if t["symbol"] == found_symbol:
                price_context = f"\n\n[实时数据] {found_symbol}: 价格=${t['price']}, 24h={t['change']}%"
                break

    system = """你是CryptoVision的AI助手，专业分析加密货币市场。支持中英文。
回复简洁专业，3-5句话。有实时数据时直接引用。
不给具体买卖建议，但可以分析市场情况。投资有风险请提醒用户。"""

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
