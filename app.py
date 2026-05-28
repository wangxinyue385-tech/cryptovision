from flask import Flask, request, jsonify, render_template_string
import requests
import os
import datetime

app = Flask(__name__)
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")

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
    "atom": "cosmos",
}

SYMBOL_MAP = {
    "bitcoin": "BTC", "ethereum": "ETH", "binancecoin": "BNB",
    "dogecoin": "DOGE", "solana": "SOL", "ripple": "XRP",
    "cardano": "ADA", "avalanche-2": "AVAX", "polkadot": "DOT",
    "shiba-inu": "SHIB", "litecoin": "LTC", "chainlink": "LINK",
    "uniswap": "UNI", "tron": "TRX", "matic-network": "MATIC",
    "cosmos": "ATOM",
}

def get_top_prices():
    try:
        ids = "bitcoin,ethereum,solana,binancecoin,ripple,cardano,dogecoin,avalanche-2,polkadot,chainlink,litecoin,cosmos"
        res = requests.get(
            "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=" + ids + "&order=market_cap_desc&sparkline=true",
            timeout=10
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
                "market_cap": d["market_cap"],
                "sparkline": d.get("sparkline_in_7d", {}).get("price", [])[::8]
            })
        return result
    except:
        return []

def get_kline(coin_id, days=1):
    try:
        res = requests.get(
            "https://api.coingecko.com/api/v3/coins/" + coin_id + "/market_chart?vs_currency=usd&days=" + str(days),
            timeout=10
        )
        data = res.json()
        prices = data.get("prices", [])
        step = max(1, len(prices) // 72)
        sampled = prices[::step][-72:]
        labels = []
        vals = []
        for p in sampled:
            t = datetime.datetime.fromtimestamp(p[0] / 1000)
            labels.append(t.strftime("%m/%d %H:%M") if days > 1 else t.strftime("%H:%M"))
            vals.append(round(p[1], 6))
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
:root {
  --bg: #f0f4ff;
  --surface: #ffffff;
  --surface2: #f8faff;
  --border: #e2e8f8;
  --accent: #6366f1;
  --accent2: #8b5cf6;
  --green: #059669;
  --green-bg: #ecfdf5;
  --red: #dc2626;
  --red-bg: #fef2f2;
  --text: #0f172a;
  --text2: #334155;
  --muted: #64748b;
  --shadow: 0 4px 24px rgba(99,102,241,0.08);
}
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, "Inter", sans-serif; background: var(--bg); color: var(--text); height: 100vh; display: flex; flex-direction: column; overflow: hidden; }

.header {
  background: rgba(255,255,255,0.95);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--border);
  padding: 0 20px;
  height: 58px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
  box-shadow: 0 1px 12px rgba(99,102,241,0.06);
}
.logo {
  display: flex; align-items: center; gap: 10px;
  font-size: 18px; font-weight: 800; color: var(--text);
}
.logo-icon {
  width: 34px; height: 34px; border-radius: 10px;
  background: linear-gradient(135deg, var(--accent), var(--accent2));
  display: flex; align-items: center; justify-content: center;
  color: white; font-size: 14px; font-weight: 900;
  box-shadow: 0 4px 12px rgba(99,102,241,0.3);
}
.logo span { background: linear-gradient(90deg, var(--accent), var(--accent2)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.live-badge {
  display: flex; align-items: center; gap: 7px;
  background: var(--green-bg);
  border: 1px solid #a7f3d0;
  color: var(--green);
  padding: 6px 14px; border-radius: 20px;
  font-size: 12px; font-weight: 700;
}
.live-dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--green);
  box-shadow: 0 0 6px var(--green);
  animation: pulse 2s infinite;
}
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }

.body { display: flex; flex: 1; overflow: hidden; }

.sidebar {
  width: 210px; flex-shrink: 0;
  background: var(--surface);
  border-right: 1px solid var(--border);
  display: flex; flex-direction: column;
}
.sidebar-title {
  padding: 14px 16px 8px;
  font-size: 10px; font-weight: 800;
  color: var(--muted); letter-spacing: 1.2px; text-transform: uppercase;
}
.coin-list { flex: 1; overflow-y: auto; }
.coin-item {
  display: flex; align-items: center; justify-content: space-between;
  padding: 9px 14px; cursor: pointer;
  border-left: 2px solid transparent;
  transition: all 0.15s;
}
.coin-item:hover { background: #f5f7ff; border-left-color: var(--accent); }
.ci-left { display: flex; flex-direction: column; gap: 1px; }
.ci-sym { font-size: 12px; font-weight: 800; color: var(--text); }
.ci-name { font-size: 10px; color: var(--muted); }
.ci-right { display: flex; flex-direction: column; align-items: flex-end; gap: 1px; }
.ci-price { font-size: 12px; font-weight: 600; color: var(--text2); }
.ci-change { font-size: 10px; font-weight: 700; }
.green { color: var(--green); }
.red { color: var(--red); }

.main { flex: 1; display: flex; flex-direction: column; overflow: hidden; }

.ticker-bar {
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  padding: 0 16px;
  height: 74px;
  display: flex; align-items: center; gap: 10px;
  flex-shrink: 0; overflow-x: auto;
  box-shadow: 0 1px 8px rgba(0,0,0,0.03);
}
.ticker-card {
  flex-shrink: 0;
  background: var(--surface2);
  border: 1.5px solid var(--border);
  border-radius: 12px;
  padding: 10px 14px;
  cursor: pointer;
  transition: all 0.2s;
  min-width: 140px;
}
.ticker-card:hover { border-color: var(--accent); background: #f5f7ff; box-shadow: 0 4px 16px rgba(99,102,241,0.1); }
.tc-sym { font-size: 10px; font-weight: 700; color: var(--muted); margin-bottom: 3px; letter-spacing: 0.5px; }
.tc-price { font-size: 15px; font-weight: 800; color: var(--text); }
.tc-change { font-size: 11px; font-weight: 700; margin-top: 3px; }

.chat-area {
  flex: 1; overflow-y: auto;
  padding: 18px 20px;
  display: flex; flex-direction: column; gap: 14px;
  background: var(--bg);
}

.msg { display: flex; gap: 10px; align-items: flex-start; }
.msg.user { flex-direction: row-reverse; }
.av {
  width: 32px; height: 32px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 800; flex-shrink: 0;
}
.ai-av { background: linear-gradient(135deg, var(--accent), var(--accent2)); color: white; box-shadow: 0 4px 12px rgba(99,102,241,0.25); }
.u-av { background: #e0e7ff; color: var(--accent); border: 1px solid #c7d2fe; }
.bubble {
  max-width: 75%; padding: 12px 16px; border-radius: 14px;
  font-size: 13.5px; line-height: 1.7;
}
.ai-b { background: var(--surface); color: var(--text2); border: 1px solid var(--border); box-shadow: var(--shadow); }
.u-b { background: linear-gradient(135deg, var(--accent), var(--accent2)); color: white; box-shadow: 0 4px 16px rgba(99,102,241,0.25); }

.chart-card {
  max-width: 88%;
  background: var(--surface);
  border: 1.5px solid var(--border);
  border-radius: 16px;
  padding: 18px;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: var(--shadow);
}
.chart-card:hover { border-color: var(--accent); box-shadow: 0 8px 32px rgba(99,102,241,0.12); }
.chart-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.chart-sym { font-size: 15px; font-weight: 800; color: var(--text); }
.chart-wrap { height: 210px; position: relative; }
.chart-footer { display: flex; gap: 16px; color: var(--muted); font-size: 11px; margin-top: 12px; padding-top: 10px; border-top: 1px solid var(--border); flex-wrap: wrap; }
.chart-footer b { color: var(--text2); }
.chart-analysis {
  margin-top: 12px; padding: 10px 14px;
  background: #f5f7ff;
  border: 1px solid #e0e7ff;
  border-radius: 10px;
  font-size: 12px; color: var(--muted); line-height: 1.6;
}
.chart-analysis::before { content: "AI Analysis  "; font-weight: 700; color: var(--accent); }

.badge { padding: 4px 10px; border-radius: 8px; font-size: 12px; font-weight: 700; }
.badge-green { background: var(--green-bg); color: var(--green); }
.badge-red { background: var(--red-bg); color: var(--red); }

.table-card {
  max-width: 92%;
  background: var(--surface);
  border: 1.5px solid var(--border);
  border-radius: 16px;
  padding: 18px;
  box-shadow: var(--shadow);
  overflow-x: auto;
}
.table-title { font-size: 15px; font-weight: 800; color: var(--text); margin-bottom: 14px; }
.dtable { width: 100%; border-collapse: collapse; font-size: 12.5px; }
.dtable th { color: var(--muted); font-weight: 600; padding: 6px 10px; text-align: right; border-bottom: 1.5px solid var(--border); font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; }
.dtable th:first-child { text-align: left; }
.dtable td { padding: 10px 10px; border-top: 1px solid var(--border); text-align: right; color: var(--text2); }
.dtable td:first-child { text-align: left; }
.dtable tr:hover td { background: #f8faff; }
.spark { width: 72px; height: 30px; }
.table-analysis { margin-top: 12px; padding: 10px 14px; background: #f5f7ff; border: 1px solid #e0e7ff; border-radius: 10px; font-size: 12px; color: var(--muted); line-height: 1.6; }
.table-analysis::before { content: "AI Analysis  "; font-weight: 700; color: var(--accent); }

.input-bar {
  background: rgba(255,255,255,0.97);
  border-top: 1px solid var(--border);
  padding: 10px 16px 14px;
  flex-shrink: 0;
  box-shadow: 0 -4px 20px rgba(99,102,241,0.05);
}
.chips { display: flex; gap: 8px; overflow-x: auto; margin-bottom: 10px; scrollbar-width: none; }
.chips::-webkit-scrollbar { display: none; }
.chip {
  background: var(--surface2); border: 1.5px solid var(--border);
  color: var(--muted); border-radius: 20px;
  padding: 6px 14px; font-size: 12px; cursor: pointer;
  white-space: nowrap; transition: all 0.2s; flex-shrink: 0;
}
.chip:hover { border-color: var(--accent); color: var(--accent); background: #f0f1ff; }
.chip:disabled { opacity: 0.4; cursor: not-allowed; }
.irow { display: flex; gap: 10px; }
.irow input {
  flex: 1; background: var(--surface2);
  border: 1.5px solid var(--border);
  border-radius: 12px; padding: 10px 16px;
  font-size: 13px; color: var(--text); outline: none;
  transition: all 0.2s;
}
.irow input:focus { border-color: var(--accent); box-shadow: 0 0 0 4px rgba(99,102,241,0.1); background: white; }
.irow input::placeholder { color: var(--muted); }
.sbtn {
  background: linear-gradient(135deg, var(--accent), var(--accent2));
  border: none; border-radius: 12px;
  width: 46px; color: white; font-size: 18px;
  cursor: pointer; flex-shrink: 0;
  box-shadow: 0 4px 16px rgba(99,102,241,0.3);
  transition: all 0.2s;
}
.sbtn:hover:not(:disabled) { transform: scale(1.05); box-shadow: 0 6px 20px rgba(99,102,241,0.4); }
.sbtn:disabled { opacity: 0.4; cursor: not-allowed; transform: none; }

.dots span {
  display: inline-block; width: 6px; height: 6px; margin: 0 2px;
  border-radius: 50%; background: var(--accent);
  animation: bounce 1.2s infinite;
}
.dots span:nth-child(2) { animation-delay: 0.2s; }
.dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce { 0%,60%,100%{transform:translateY(0)} 30%{transform:translateY(-5px)} }

.modal-overlay {
  display: none; position: fixed; inset: 0;
  background: rgba(15,23,42,0.6);
  backdrop-filter: blur(8px);
  z-index: 1000; align-items: center; justify-content: center;
}
.modal-overlay.show { display: flex; }
.modal {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 20px; padding: 24px;
  width: 92vw; max-width: 860px;
  box-shadow: 0 24px 80px rgba(99,102,241,0.15);
}
.modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.modal-title { font-size: 17px; font-weight: 800; color: var(--text); }
.modal-close { background: none; border: none; color: var(--muted); font-size: 22px; cursor: pointer; line-height: 1; }
.modal-close:hover { color: var(--text); }
.modal-chart { height: 380px; position: relative; }
</style>
</head>
<body>

<div class="header">
  <div class="logo">
    <div class="logo-icon">CV</div>
    <span>CryptoVision</span>
  </div>
  <div class="live-badge"><div class="live-dot"></div>Live Market Data</div>
</div>

<div class="body">
  <div class="sidebar">
    <div class="sidebar-title">Watchlist</div>
    <div class="coin-list" id="coinList">
      <div style="padding:16px;color:var(--muted);font-size:12px;">Loading...</div>
    </div>
  </div>

  <div class="main">
    <div class="ticker-bar" id="tickerBar">
      <div style="color:var(--muted);font-size:12px;padding:0 4px;">Loading...</div>
    </div>

    <div class="chat-area" id="chatArea">
      <div class="msg">
        <div class="av ai-av">AI</div>
        <div class="bubble ai-b">Welcome to <b>CryptoVision</b>.<br><br>I can generate live price charts with AI analysis, market tables, and answer crypto questions.<br><br>Try: <b>BTC 7 day chart</b> &nbsp;|&nbsp; <b>top coins table</b> &nbsp;|&nbsp; <b>what is Ethereum?</b></div>
      </div>
    </div>

    <div class="input-bar">
      <div class="chips">
        <button class="chip" onclick="doSend('BTC chart')">BTC Chart</button>
        <button class="chip" onclick="doSend('ETH chart')">ETH Chart</button>
        <button class="chip" onclick="doSend('SOL chart')">SOL Chart</button>
        <button class="chip" onclick="doSend('top coins table')">Top Coins</button>
        <button class="chip" onclick="doSend('BTC 7 day chart')">BTC 7D</button>
        <button class="chip" onclick="doSend('ETH 7 day chart')">ETH 7D</button>
        <button class="chip" onclick="doSend('market analysis')">Market Analysis</button>
      </div>
      <div class="irow">
        <input type="text" id="inp" placeholder="Ask about any coin, chart, or market trend..." />
        <button class="sbtn" id="sbtn" onclick="doSend()">&#9658;</button>
      </div>
    </div>
  </div>
</div>

<div class="modal-overlay" id="modalOverlay" onclick="closeModal(event)">
  <div class="modal" onclick="event.stopPropagation()">
    <div class="modal-header">
      <div class="modal-title" id="modalTitle">Chart</div>
      <button class="modal-close" onclick="closeModal()">&#10005;</button>
    </div>
    <div class="modal-chart"><canvas id="modalCanvas"></canvas></div>
  </div>
</div>

<script>
var chatHistory = [];
var busy = false;
var modalChart = null;

function setBusy(v) {
  busy = v;
  document.getElementById('sbtn').disabled = v;
  document.getElementById('inp').disabled = v;
  document.querySelectorAll('.chip').forEach(function(c) { c.disabled = v; });
}

function loadMarket() {
  fetch('/top_prices').then(function(r) { return r.json(); }).then(function(data) {
    if (!data || !data.length) return;
    renderTicker(data);
    renderSidebar(data);
  }).catch(function() {});
}

function renderTicker(data) {
  var bar = document.getElementById('tickerBar');
  bar.innerHTML = data.slice(0,8).map(function(d) {
    var up = d.change >= 0;
    return '<div class="ticker-card" onclick="doSend(\\'' + d.symbol + ' chart\\')">' +
      '<div class="tc-sym">' + d.symbol + '/USDT</div>' +
      '<div class="tc-price">$' + d.price.toLocaleString('en-US',{maximumFractionDigits:4}) + '</div>' +
      '<div class="tc-change ' + (up?'green':'red') + '">' + (up?'+':'') + d.change + '%</div>' +
      '</div>';
  }).join('');
}

function renderSidebar(data) {
  var list = document.getElementById('coinList');
  list.innerHTML = data.map(function(d) {
    var up = d.change >= 0;
    return '<div class="coin-item" onclick="doSend(\\'' + d.symbol + ' chart\\')">' +
      '<div class="ci-left"><div class="ci-sym">' + d.symbol + '</div><div class="ci-name">' + d.name + '</div></div>' +
      '<div class="ci-right"><div class="ci-price">$' + d.price.toLocaleString('en-US',{maximumFractionDigits:2}) + '</div><div class="ci-change ' + (up?'green':'red') + '">' + (up?'+':'') + d.change + '%</div></div>' +
      '</div>';
  }).join('');
}

function doSend(text) {
  if (busy) return;
  var inp = document.getElementById('inp');
  var msg = text || inp.value.trim();
  if (!msg) return;
  inp.value = '';
  addUser(msg);
  chatHistory.push({role:'user', content:msg});
  setBusy(true);
  var typing = addTyping();
  fetch('/chat', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({messages: chatHistory})
  }).then(function(r) { return r.json(); }).then(function(data) {
    typing.remove();
    if (data.type === 'chart') addChart(data);
    else if (data.type === 'table') addTable(data);
    else addAI(data.reply);
    chatHistory.push({role:'assistant', content: data.reply || data.summary || ''});
    setBusy(false);
  }).catch(function() {
    typing.remove();
    addAI('Network error, please retry.');
    chatHistory.pop();
    setBusy(false);
  });
}

document.getElementById('inp').addEventListener('keydown', function(e) {
  if (e.key === 'Enter' && !busy) doSend();
});

function addUser(text) {
  var area = document.getElementById('chatArea');
  var d = document.createElement('div');
  d.className = 'msg user';
  d.innerHTML = '<div class="av u-av">U</div><div class="bubble u-b">' + text + '</div>';
  area.appendChild(d); scrollDown();
}

function addAI(text) {
  var area = document.getElementById('chatArea');
  var d = document.createElement('div');
  d.className = 'msg';
  d.innerHTML = '<div class="av ai-av">AI</div><div class="bubble ai-b">' + text.replace(/\n/g,'<br>') + '</div>';
  area.appendChild(d); scrollDown();
}

function addTyping() {
  var area = document.getElementById('chatArea');
  var d = document.createElement('div');
  d.className = 'msg';
  d.innerHTML = '<div class="av ai-av">AI</div><div class="bubble ai-b"><div class="dots"><span></span><span></span><span></span></div></div>';
  area.appendChild(d); scrollDown();
  return d;
}

function drawLine(canvasId, labels, prices, up, h) {
  var ctx = document.getElementById(canvasId);
  if (!ctx) return null;
  var color = up ? '#059669' : '#dc2626';
  var bg = up ? 'rgba(5,150,105,0.07)' : 'rgba(220,38,38,0.07)';
  return new Chart(ctx.getContext('2d'), {
    type:'line',
    data:{ labels:labels, datasets:[{ data:prices, borderColor:color, backgroundColor:bg, borderWidth:2, pointRadius:0, tension:0.35, fill:true }] },
    options:{
      responsive:true, maintainAspectRatio:false,
      animation:{ duration:600, easing:'easeInOutQuart' },
      plugins:{
        legend:{display:false},
        tooltip:{
          backgroundColor:'rgba(255,255,255,0.97)',
          borderColor:'#e2e8f8', borderWidth:1,
          titleColor:'#0f172a', bodyColor:'#334155',
          callbacks:{ label:function(c){ return '$'+c.parsed.y.toLocaleString('en-US',{maximumFractionDigits:6}); } }
        }
      },
      scales:{
        x:{ grid:{color:'rgba(226,232,248,0.6)'}, ticks:{color:'#94a3b8',font:{size:10},maxTicksLimit:6} },
        y:{ grid:{color:'rgba(226,232,248,0.6)'}, ticks:{color:'#94a3b8',font:{size:10},maxTicksLimit:5,
          callback:function(v){ return '$'+(v>=1000?(v/1000).toFixed(1)+'k':v.toFixed(4)); }
        }}
      }
    }
  });
}

function addChart(data) {
  var area = document.getElementById('chatArea');
  var id = 'ch' + Date.now();
  var prices = data.prices;
  var up = prices[prices.length-1] >= prices[0];
  var d = document.createElement('div');
  d.className = 'msg';
  var badge = '<span class="badge '+(up?'badge-green':'badge-red')+'">'+(up?'+':'')+data.change+'%</span>';
  var safeData = JSON.stringify(data).replace(/\\/g,'\\\\').replace(/'/g,'&#39;');
  d.innerHTML = '<div class="av ai-av">AI</div><div class="chart-card" onclick="openModal(this)" data-chart=\'' + safeData + '\'>' +
    '<div class="chart-header"><div class="chart-sym">'+data.title+'</div>'+badge+'</div>' +
    '<div class="chart-wrap"><canvas id="'+id+'"></canvas></div>' +
    '<div class="chart-footer">' +
      '<span>Now: <b>$'+parseFloat(prices[prices.length-1]).toLocaleString('en-US',{maximumFractionDigits:4})+'</b></span>' +
      '<span>High: <b style="color:var(--green)">$'+data.high+'</b></span>' +
      '<span>Low: <b style="color:var(--red)">$'+data.low+'</b></span>' +
      '<span style="margin-left:auto;color:var(--muted);font-size:10px">Click to expand &#8599;</span>' +
    '</div>' +
    (data.analysis ? '<div class="chart-analysis">'+data.analysis+'</div>' : '') +
    '</div>';
  area.appendChild(d); scrollDown();
  setTimeout(function() { drawLine(id, data.labels, data.prices, up, 210); }, 80);
}

function openModal(el) {
  var data = JSON.parse(el.getAttribute('data-chart').replace(/&#39;/g,"'"));
  var up = data.prices[data.prices.length-1] >= data.prices[0];
  document.getElementById('modalTitle').textContent = data.title;
  document.getElementById('modalOverlay').classList.add('show');
  if (modalChart) { modalChart.destroy(); modalChart = null; }
  setTimeout(function() { modalChart = drawLine('modalCanvas', data.labels, data.prices, up, 380); }, 80);
}

function closeModal(e) {
  if (!e || e.target === document.getElementById('modalOverlay')) {
    document.getElementById('modalOverlay').classList.remove('show');
  }
}

function addTable(data) {
  var area = document.getElementById('chatArea');
  var d = document.createElement('div');
  d.className = 'msg';
  var rows = data.rows.map(function(r) {
    var up = r.change >= 0;
    var spark = (r.sparkline && r.sparkline.length) ? '<canvas class="spark" id="sp'+r.symbol+'"></canvas>' : '';
    return '<tr onclick="doSend(\\'' + r.symbol + ' chart\\')" style="cursor:pointer">' +
      '<td><div style="font-weight:800;color:var(--text)">'+r.symbol+'</div><div style="color:var(--muted);font-size:11px">'+r.name+'</div></td>' +
      '<td style="font-weight:700">$'+r.price.toLocaleString('en-US',{maximumFractionDigits:4})+'</td>' +
      '<td><span class="badge '+(up?'badge-green':'badge-red')+'">'+(up?'+':'')+r.change+'%</span></td>' +
      '<td style="color:var(--muted)">$'+(r.volume/1e9).toFixed(1)+'B</td>' +
      '<td>'+spark+'</td></tr>';
  }).join('');
  d.innerHTML = '<div class="av ai-av">AI</div><div class="table-card">' +
    '<div class="table-title">'+data.title+'</div>' +
    '<table class="dtable"><tr><th>Coin</th><th>Price</th><th>24h</th><th>Volume</th><th>7D</th></tr>'+rows+'</table>' +
    '<div style="color:var(--muted);font-size:11px;margin-top:10px">'+data.summary+'</div>' +
    (data.analysis ? '<div class="table-analysis">'+data.analysis+'</div>' : '') +
    '</div>';
  area.appendChild(d); scrollDown();
  setTimeout(function() {
    data.rows.forEach(function(r) {
      if (!r.sparkline || !r.sparkline.length) return;
      var sp = document.getElementById('sp'+r.symbol);
      if (!sp) return;
      var sl = r.sparkline;
      var up = sl[sl.length-1] >= sl[0];
      new Chart(sp.getContext('2d'), {
        type:'line',
        data:{labels:sl.map(function(_,i){return i;}),datasets:[{data:sl,borderColor:up?'#059669':'#dc2626',borderWidth:1.5,pointRadius:0,tension:0.3}]},
        options:{responsive:false,plugins:{legend:{display:false},tooltip:{enabled:false}},scales:{x:{display:false},y:{display:false}},animation:{duration:0}}
      });
    });
  }, 100);
}

function scrollDown() {
  var c = document.getElementById('chatArea');
  setTimeout(function() { c.scrollTop = c.scrollHeight; }, 80);
}

loadMarket();
setInterval(loadMarket, 90000);
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
    data = request.json
    messages = data.get("messages", [])
    user_msg = messages[-1]["content"] if messages else ""
    msg_lower = user_msg.lower()

    chart_kw = ["chart","trend","btc","eth","sol","bnb","doge","xrp","ada","avax","dot","shib","ltc","link","uni","trx","matic","atom","走势","图","比特币","以太坊"]
    table_kw = ["table","market","top","overview","coins","list","行情","排行","主流","概况"]

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
        days = 7 if any(k in msg_lower for k in ["7","week","7d","month","30"]) else 1
        labels, prices = get_kline(found_id, days=days)
        if labels and prices:
            change = round((prices[-1]-prices[0])/prices[0]*100, 2) if prices[0] else 0
            high = round(max(prices), 4)
            low = round(min(prices), 4)
            analysis = ""
            try:
                r = requests.post(
                    "https://api.deepseek.com/chat/completions",
                    headers={"Authorization":"Bearer "+DEEPSEEK_API_KEY,"Content-Type":"application/json"},
                    json={"model":"deepseek-chat","messages":[
                        {"role":"system","content":"You are a crypto analyst. Give a 2-sentence analysis of this price action. No buy/sell advice. Be concise."},
                        {"role":"user","content":found_symbol+" "+str(days)+"d: current=$"+str(prices[-1])+" high=$"+str(high)+" low=$"+str(low)+" change="+str(change)+"%"}
                    ],"max_tokens":100,"temperature":0.4},
                    timeout=10
                )
                analysis = r.json()["choices"][0]["message"]["content"]
            except: pass
            return jsonify({"type":"chart","title":found_symbol+"/USDT  "+("7D" if days==7 else "24H"),"labels":labels,"prices":prices,"change":change,"high":high,"low":low,"analysis":analysis,"reply":found_symbol+" chart"})

    if is_table:
        top = get_top_prices()
        if top:
            analysis = ""
            try:
                summary = ", ".join([t["symbol"]+"="+str(t["change"])+"%" for t in top[:6]])
                r = requests.post(
                    "https://api.deepseek.com/chat/completions",
                    headers={"Authorization":"Bearer "+DEEPSEEK_API_KEY,"Content-Type":"application/json"},
                    json={"model":"deepseek-chat","messages":[
                        {"role":"system","content":"You are a crypto analyst. Summarize the market in 2 sentences. No buy/sell advice."},
                        {"role":"user","content":"24h changes: "+summary}
                    ],"max_tokens":100,"temperature":0.4},
                    timeout=10
                )
                analysis = r.json()["choices"][0]["message"]["content"]
            except: pass
            return jsonify({"type":"table","title":"Top Coins — Live Market","rows":top,"analysis":analysis,"summary":str(len(top))+" coins  |  "+datetime.datetime.now().strftime("%H:%M")+"  |  CoinGecko","reply":"market table"})

    price_context = ""
    if found_id:
        top = get_top_prices()
        for t in top:
            if t["symbol"] == found_symbol:
                price_context = " [Live] "+found_symbol+": $"+str(t["price"])+", 24h="+str(t["change"])+"%"
                break

    system = "You are CryptoVision AI. Answer in the same language the user uses. Be concise and professional. No specific buy/sell advice."
    api_msgs = [{"role":"system","content":system}]
    for h in messages[:-1]: api_msgs.append(h)
    api_msgs.append({"role":"user","content":user_msg+price_context})

    try:
        res = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization":"Bearer "+DEEPSEEK_API_KEY,"Content-Type":"application/json"},
            json={"model":"deepseek-chat","messages":api_msgs,"max_tokens":500,"temperature":0.4},
            timeout=12
        )
        reply = res.json()["choices"][0]["message"]["content"]
    except:
        reply = "Network timeout, please retry."

    return jsonify({"type":"text","reply":reply})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
