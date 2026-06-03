import streamlit as st
import requests
import streamlit.components.v1 as components
from datetime import datetime

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Voice Flight Assistant",
    page_icon="✈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Session state defaults ────────────────────────────────────────────────────
if "backend_url" not in st.session_state:
    st.session_state.backend_url = "http://localhost:5000"
if "state_data" not in st.session_state:
    st.session_state.state_data = None
if "offline" not in st.session_state:
    st.session_state.offline = False

# ── Helpers ───────────────────────────────────────────────────────────────────
def fetch_state(url):
    try:
        r = requests.get(f"{url}/state", timeout=2)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

def post_stop(url):
    try:
        requests.post(f"{url}/stop", timeout=2)
        return True
    except Exception:
        return False

def post_start(url):
    try:
        requests.post(f"{url}/start", timeout=2)
        return True
    except Exception:
        return False

# ── One-time poll on page load only (for initial state) ──────────────────────
data = fetch_state(st.session_state.backend_url)
if data:
    st.session_state.state_data = data
    st.session_state.offline = False
else:
    st.session_state.offline = True

snap        = st.session_state.state_data or {}
backend_url = st.session_state.backend_url

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=Space+Grotesk:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family:'DM Sans',sans-serif; background:#0d0d14 !important; color:#e2e2f0; }
h1,h2,h3,h4 { font-family:'Space Grotesk',sans-serif; }
.stApp { background:#0d0d14; }
::-webkit-scrollbar{width:4px} ::-webkit-scrollbar-track{background:#0d0d14} ::-webkit-scrollbar-thumb{background:#1f1f30;border-radius:2px}
.panel-title{font-family:'Space Grotesk',sans-serif;font-size:.7rem;letter-spacing:.12em;text-transform:uppercase;color:#6b7280;margin-bottom:10px}
.section-heading{font-family:'Space Grotesk',sans-serif;font-size:.75rem;letter-spacing:.1em;text-transform:uppercase;color:#4b4b6a;margin-bottom:14px;margin-top:4px;border-bottom:1px solid #1a1a28;padding-bottom:8px}
div[data-testid="stButton"]>button{background:linear-gradient(135deg,#7f1d1d,#991b1b)!important;color:#fca5a5!important;border:1px solid #b91c1c!important;border-radius:10px!important;font-family:'Space Grotesk',sans-serif!important;font-weight:600!important;font-size:.85rem!important;width:100%!important;padding:10px!important}
input[type="text"],.stTextInput input{background:#0d0d14!important;border:1px solid #1f1f30!important;color:#e2e2f0!important;border-radius:8px!important}
.offline-banner{background:#1c1205;border:1px solid #854d0e;color:#fbbf24;border-radius:10px;padding:10px 16px;font-size:.85rem;margin-bottom:10px}
</style>
""", unsafe_allow_html=True)

# ── Page header ───────────────────────────────────────────────────────────────
st.markdown("""
<div style="display:flex;align-items:center;gap:14px;padding:10px 0 20px 0;">
  <span style="font-size:2rem;">✈</span>
  <div>
    <div style="font-family:'Space Grotesk',sans-serif;font-size:1.5rem;font-weight:700;color:#e2e2f0;line-height:1;">Voice Flight Assistant</div>
    <div style="font-size:.78rem;color:#4b4b6a;margin-top:2px;letter-spacing:.05em;">REAL-TIME VOICE BOOKING INTERFACE</div>
  </div>
</div>
""", unsafe_allow_html=True)

if st.session_state.offline:
    st.markdown('<div class="offline-banner">⚠ <strong>Backend offline</strong> — start the server with <code>python server.py</code> then click Connect.</div>', unsafe_allow_html=True)

# ── Left sidebar controls (pure Streamlit — only reruns on button clicks) ────
left, centre, right = st.columns([1, 2, 1])

with left:
    st.markdown('<div class="panel-title">Controls</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("▶ Start", key="start_btn"):
            if post_start(st.session_state.backend_url):
                st.success("Started!")
            else:
                st.error("Unreachable")
    with c2:
        if st.button("⏹ Stop", key="stop_btn"):
            if post_stop(st.session_state.backend_url):
                st.success("Stopped.")
            else:
                st.error("Unreachable")

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    st.markdown('<div class="panel-title">Backend URL</div>', unsafe_allow_html=True)
    new_url = st.text_input("URL", value=st.session_state.backend_url, label_visibility="collapsed", key="url_input")
    if st.button("Connect", key="connect_btn"):
        st.session_state.backend_url = new_url
        if fetch_state(new_url):
            st.success("Connected ✓")
            st.session_state.offline = False
        else:
            st.error("Unreachable")

# ── Centre + Right: pure JS live dashboard — polls /state itself every 800ms ─
# This component renders the full live UI in an iframe.
# It polls the Flask server directly from the browser — zero Streamlit reruns.

DASHBOARD_HTML = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=Space+Grotesk:wght@400;500;600;700&display=swap');
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:'DM Sans',sans-serif;background:#0d0d14;color:#e2e2f0;padding:0 8px 8px 0}}
  ::-webkit-scrollbar{{width:4px}}::-webkit-scrollbar-thumb{{background:#1f1f30;border-radius:2px}}

  /* Layout */
  .grid{{display:grid;grid-template-columns:1fr 220px;gap:10px}}

  /* Section label */
  .sec{{font-family:'Space Grotesk',sans-serif;font-size:.68rem;letter-spacing:.1em;text-transform:uppercase;
        color:#4b4b6a;border-bottom:1px solid #1a1a28;padding-bottom:6px;margin-bottom:10px}}

  /* Status badge */
  @keyframes pulse{{0%,100%{{opacity:1;transform:scale(1)}}50%{{opacity:.4;transform:scale(.8)}}}}
  .dot{{width:9px;height:9px;border-radius:50%;display:inline-block;animation:pulse 1.5s infinite;margin-right:7px;vertical-align:middle}}
  .badge{{display:inline-flex;align-items:center;background:#13131f;border:1px solid #1f1f30;
          border-radius:20px;padding:5px 13px;font-size:.82rem;font-weight:500;margin-bottom:12px}}

  /* Stat rows */
  .stats{{background:#13131f;border:1px solid #1f1f30;border-radius:12px;padding:12px 14px;margin-bottom:10px}}
  .stat{{display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid #1a1a28;font-size:.82rem}}
  .stat:last-child{{border-bottom:none}}
  .sk{{color:#6b7280}}.sv{{color:#c8c8e0;font-weight:500}}

  /* Chat */
  .chat-box{{height:440px;overflow-y:auto;padding-right:4px}}
  .msg{{display:flex;gap:8px;align-items:flex-start;margin-bottom:12px}}
  .msg.user{{flex-direction:row-reverse}}
  .av{{font-size:1.1rem;flex-shrink:0;margin-top:2px}}
  .bbl{{max-width:80%;border-radius:13px;padding:9px 12px;font-size:.86rem;line-height:1.55}}
  .bbl.agent{{background:#13131f;border:1px solid #1f1f30;border-top-left-radius:4px}}
  .bbl.user{{background:linear-gradient(135deg,#1e3a5f,#1d4ed8);border-top-right-radius:4px;color:#e0eeff}}
  .ts{{display:block;font-size:.68rem;color:#4b4b6a;margin-top:4px}}
  .empty-chat{{text-align:center;color:#3b3b52;padding:60px 0;font-size:.85rem}}

  /* Thinking row */
  @keyframes blink{{0%,80%,100%{{opacity:.2}}40%{{opacity:1}}}}
  .thinking{{display:flex;align-items:center;gap:8px;padding:6px 0 0 28px;color:#6b7280;font-size:.82rem;font-style:italic}}
  .dots span{{display:inline-block;width:5px;height:5px;border-radius:50%;background:#6b7280;margin:0 1.5px;animation:blink 1.4s infinite}}
  .dots span:nth-child(2){{animation-delay:.2s}}.dots span:nth-child(3){{animation-delay:.4s}}

  /* Flight cards */
  .fc{{background:#13131f;border:1px solid #1f1f30;border-radius:11px;padding:12px 14px;margin-bottom:10px;position:relative}}
  .fc.best{{border-color:#185FA5;border-width:1.5px}}
  .best-tag{{position:absolute;top:-9px;left:11px;background:linear-gradient(90deg,#1d4ed8,#2563eb);
             color:#fff;font-size:.65rem;font-weight:600;padding:2px 8px;border-radius:5px;letter-spacing:.05em}}
  .fc-airline{{font-family:'Space Grotesk',sans-serif;font-size:.88rem;font-weight:600;color:#c8c8e0;margin-bottom:6px}}
  .fc-route{{font-size:.68rem;color:#4b4b6a;margin-bottom:7px}}
  .fc-times{{display:flex;align-items:center;gap:8px;margin-bottom:7px}}
  .fc-t{{font-size:1.05rem;font-weight:600;font-family:'Space Grotesk',sans-serif}}
  .fc-line{{flex:1;border-top:1px dashed #2f2f48;position:relative;text-align:center}}
  .fc-dur{{position:absolute;top:-8px;left:50%;transform:translateX(-50%);background:#13131f;
           padding:0 4px;font-size:.65rem;color:#6b7280;white-space:nowrap}}
  .fc-meta{{display:flex;justify-content:space-between;align-items:center}}
  .fc-stops{{font-size:.75rem;color:#6b7280;background:#0d0d14;border:1px solid #1f1f30;border-radius:5px;padding:2px 7px}}
  .fc-price{{font-family:'Space Grotesk',sans-serif;font-size:1.1rem;font-weight:700;color:#60a5fa}}
  .fc-book{{font-size:.72rem;color:#60a5fa;text-decoration:none;background:#0d1929;border:1px solid #1d4ed8;
            border-radius:6px;padding:3px 9px;font-weight:500}}
  .empty-fc{{text-align:center;color:#3b3b52;padding:30px 0;font-size:.82rem}}

  /* Pulse bar at bottom */
  .pulse-bar{{font-size:.62rem;color:#2d2d44;text-align:right;padding-top:6px;letter-spacing:.04em}}
</style>
</head>
<body>

<div class="grid">
  <!-- LEFT: status + chat -->
  <div>
    <div class="sec">Conversation</div>

    <!-- Status -->
    <div id="badge" class="badge">
      <span class="dot" id="dot" style="background:#6b7280"></span>
      <span id="status-lbl" style="color:#6b7280">Stopped</span>
    </div>

    <!-- Session stats -->
    <div class="stats">
      <div class="stat"><span class="sk">Started</span><span class="sv" id="sess-start">—</span></div>
      <div class="stat"><span class="sk">Duration</span><span class="sv" id="sess-dur">—</span></div>
      <div class="stat"><span class="sk">Turns</span><span class="sv" id="turns">0</span></div>
    </div>

    <!-- Chat -->
    <div class="chat-box" id="chat-box">
      <div class="empty-chat" id="chat-empty">🎙 Conversation will appear here once the session starts.</div>
    </div>

    <!-- Thinking spinner -->
    <div class="thinking" id="thinking-row" style="display:none">
      <div class="dots"><span></span><span></span><span></span></div>
      <span id="thinking-label">Thinking…</span>
    </div>
  </div>

  <!-- RIGHT: flight results -->
  <div>
    <div class="sec">Flight Results</div>
    <div id="flights-box">
      <div class="empty-fc" id="fc-empty">🔍 No flights yet</div>
    </div>
  </div>
</div>

<div class="pulse-bar" id="pulse-bar">POLLING…</div>

<script>
const BACKEND = "{backend_url}";
const STATUS_COLORS = {{listening:'#4ade80',speaking:'#60a5fa',thinking:'#facc15',searching:'#c084fc',stopped:'#6b7280'}};
const STATUS_LABELS = {{listening:'Listening',speaking:'Speaking',thinking:'Thinking',searching:'Searching',stopped:'Stopped'}};

let sessionStartEpoch = null;
let durationTimer = null;

function fmtDurMin(m) {{ const h=Math.floor(m/60),r=m%60; return h?`${{h}}h ${{r}}m`:`${{r}}m`; }}
function fmtPrice(p) {{ return '₹'+p.toLocaleString('en-IN'); }}

function startDurationTimer(startStr) {{
  if (durationTimer) clearInterval(durationTimer);
  // startStr is HH:MM:SS
  const [hh,mm,ss] = startStr.split(':').map(Number);
  const now = new Date();
  const base = new Date(now.getFullYear(),now.getMonth(),now.getDate(),hh,mm,ss);
  durationTimer = setInterval(() => {{
    const elapsed = Math.floor((Date.now()-base.getTime())/1000);
    if (elapsed < 0) return;
    const m=Math.floor(elapsed/60),s=elapsed%60,h=Math.floor(m/60);
    document.getElementById('sess-dur').textContent = h ? `${{h}}h ${{m%60}}m ${{s}}s` : `${{m}}m ${{s}}s`;
  }}, 1000);
}}

function renderChat(history, status) {{
  const box = document.getElementById('chat-box');
  const empty = document.getElementById('chat-empty');
  if (!history || history.length === 0) {{
    if (empty) empty.style.display='block';
    // remove old messages
    box.querySelectorAll('.msg').forEach(e=>e.remove());
    return;
  }}
  if (empty) empty.style.display='none';

  // Build keyed map of existing messages to avoid full re-render flicker
  const existing = {{}};
  box.querySelectorAll('.msg[data-idx]').forEach(el => {{ existing[el.dataset.idx] = el; }});

  history.forEach((m, i) => {{
    if (existing[i]) return; // already rendered
    const isUser = m.role === 'user';
    const div = document.createElement('div');
    div.className = 'msg' + (isUser?' user':'');
    div.dataset.idx = i;
    div.innerHTML = `
      <div class="av">${{isUser?'👤':'✈'}}</div>
      <div class="bbl ${{isUser?'user':'agent'}}">${{m.text}}<span class="ts">${{m.ts}}</span></div>`;
    box.appendChild(div);
  }});

  // Scroll to bottom only if near bottom already
  const atBottom = box.scrollHeight - box.scrollTop - box.clientHeight < 80;
  if (atBottom) box.scrollTop = box.scrollHeight;

  // Thinking row
  const tr = document.getElementById('thinking-row');
  if (status==='thinking'||status==='searching') {{
    tr.style.display='flex';
    document.getElementById('thinking-label').textContent = status==='thinking'?'Thinking…':'Searching flights…';
  }} else {{
    tr.style.display='none';
  }}
}}

function renderFlights(flights, history) {{
  const box = document.getElementById('flights-box');
  const empty = document.getElementById('fc-empty');
  if (!flights || flights.length===0) {{
    box.querySelectorAll('.fc').forEach(e=>e.remove());
    if (empty) empty.style.display='block';
    return;
  }}
  if (empty) empty.style.display='none';

  // Infer route from history
  let route = '';
  for (let i=history.length-1;i>=0;i--) {{
    const t = (history[i].text||'').toLowerCase();
    if (t.includes('from')&&t.includes('to')) {{
      try {{
        const a = t.split('from')[1].split('to')[0].trim();
        const b = t.split('to')[1].trim().split(/[ ,.	]/)[0];
        if (a&&b) {{ route=a[0].toUpperCase()+a.slice(1)+' → '+b[0].toUpperCase()+b.slice(1); break; }}
      }} catch(e){{}}
    }}
  }}

  // Only re-render if count changed
  const existing = box.querySelectorAll('.fc');
  if (existing.length === flights.length) return;
  box.querySelectorAll('.fc').forEach(e=>e.remove());

  flights.forEach((f,i) => {{
    const isBest = i===0;
    const stops = f.stops===0?'Direct':`${{f.stops}} stop${{f.stops>1?'s':''}}`;
    const div = document.createElement('div');
    div.className = 'fc'+(isBest?' best':'');
    div.innerHTML = `
      ${{isBest?'<div class="best-tag">★ Best Pick</div>':''}}
      <div class="fc-airline">${{f.airline||'—'}}</div>
      <div class="fc-route">${{route||'Route'}}</div>
      <div class="fc-times">
        <div class="fc-t">${{f.departure||'—'}}</div>
        <div class="fc-line"><span class="fc-dur">${{fmtDurMin(f.duration_minutes||0)}}</span></div>
        <div class="fc-t">${{f.arrival||'—'}}</div>
      </div>
      <div class="fc-meta">
        <span class="fc-stops">${{stops}}</span>
        <span class="fc-price">${{fmtPrice(f.price||0)}}</span>
        <a class="fc-book" href="${{f.bookingUrl||'#'}}" target="_blank">Book →</a>
      </div>`;
    box.appendChild(div);
  }});
}}

let lastStartStr = null;

async function poll() {{
  try {{
    const r = await fetch(BACKEND+'/state', {{cache:'no-store'}});
    if (!r.ok) throw new Error('not ok');
    const d = await r.json();

    // Status dot
    const color = STATUS_COLORS[d.status]||'#6b7280';
    document.getElementById('dot').style.background = color;
    const lbl = document.getElementById('status-lbl');
    lbl.textContent = STATUS_LABELS[d.status]||d.status;
    lbl.style.color = color;

    // Session info
    document.getElementById('sess-start').textContent = d.session_start||'—';
    document.getElementById('turns').textContent = d.turn_count||0;
    if (d.session_start && d.session_start !== lastStartStr) {{
      lastStartStr = d.session_start;
      startDurationTimer(d.session_start);
    }}

    renderChat(d.history||[], d.status);
    renderFlights(d.flights||[], d.history||[]);

    document.getElementById('pulse-bar').textContent = 'LIVE · '+new Date().toLocaleTimeString();
  }} catch(e) {{
    document.getElementById('pulse-bar').textContent = 'BACKEND OFFLINE · '+new Date().toLocaleTimeString();
    document.getElementById('dot').style.background = '#6b7280';
    document.getElementById('status-lbl').textContent = 'Offline';
    document.getElementById('status-lbl').style.color = '#6b7280';
  }}
}}

poll();
setInterval(poll, 800);
</script>
</body>
</html>
"""

with centre:
    st.markdown('<div class="section-heading">Live Dashboard</div>', unsafe_allow_html=True)
    components.html(DASHBOARD_HTML, height=580, scrolling=False)

# Right column is rendered inside the iframe above
with right:
    pass

st.markdown("""
<div style="border-top:1px solid #1a1a28;margin-top:8px;padding-top:10px;text-align:center;
            font-size:.7rem;color:#3b3b52;letter-spacing:.04em;">
  VOICE FLIGHT ASSISTANT · UI POLLS EVERY 800ms DIRECTLY FROM BROWSER · NO PAGE RELOADS
</div>
""", unsafe_allow_html=True)