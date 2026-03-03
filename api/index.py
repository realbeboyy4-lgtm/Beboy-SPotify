from flask import Flask, render_template_string, request, jsonify
import requests
import random

app = Flask(__name__)
app.secret_key = "super_secret_key_for_session"

# ================= CONFIGURATION =================
PREFIXES = ["8638250700", "86382507"]

# Global Session 
mi_session = requests.Session()
mi_session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Referer": "https://www.mi.com/jp/imei-redemption/",
    "Origin": "https://www.mi.com",
    "X-Requested-With": "XMLHttpRequest"
})

# ================= HELPER FUNCTIONS =================

def calculate_luhn(partial_imei):
    sum_ = 0
    should_double = True
    for i in range(len(partial_imei) - 1, -1, -1):
        digit = int(partial_imei[i])
        if should_double:
            digit *= 2
            if digit > 9: digit -= 9
        sum_ += digit
        should_double = not should_double
    return (10 - (sum_ % 10)) % 10

def get_next_imei():
    prefix = random.choice(PREFIXES)
    needed = 14 - len(prefix)
    random_part = "".join([str(random.randint(0, 9)) for _ in range(needed)])
    base = prefix + random_part
    return base + str(calculate_luhn(base))

# ================= FLASK ROUTES =================

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    callback_url = data.get('url')
    if not callback_url:
        return jsonify({"status": "error", "msg": "URL Required"})
    try:
        resp = mi_session.get(callback_url, timeout=30, allow_redirects=True)
        cookies_dict = mi_session.cookies.get_dict()
        if 'serviceToken' not in cookies_dict:
            for r in resp.history:
                for c in r.cookies:
                    mi_session.cookies.set(c.name, c.value)
        cookies_dict = mi_session.cookies.get_dict()
        if 'serviceToken' in cookies_dict or 'xm_user_id' in cookies_dict:
            for name, value in cookies_dict.items():
                mi_session.cookies.set(name, value, domain='.mi.com', path='/')
                mi_session.cookies.set(name, value, domain='.c.mi.com', path='/')
                mi_session.cookies.set(name, value, domain='hd.c.mi.com', path='/')
            return jsonify({"status": "success", "msg": "Login Successful!"})
        else:
            return jsonify({"status": "error", "msg": "Login Failed (No Token)"})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

@app.route('/send_code', methods=['POST'])
def send_code():
    email = request.json.get('email')
    url = "https://hd.c.mi.com/jp/eventapi/api/imeiexchange/sendcode"
    try:
        mi_session.headers.update({"Referer": "https://www.mi.com/jp/imei-redemption/"})
        resp = mi_session.get(url, params={"from": "pc", "email": email, "tel": ""}, timeout=10)
        return jsonify({"status": "success", "msg": "Code Sent!"}) if resp.status_code == 200 else jsonify({"status": "error", "msg": "Failed"})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

@app.route('/scan_one', methods=['POST'])
def scan_one():
    req_data = request.json
    email = req_data.get('email')
    code = req_data.get('code')
    custom_imei = req_data.get('imei')
    
    # Use custom IMEI if provided, otherwise generate random
    imei = custom_imei if custom_imei and len(custom_imei) >= 14 else get_next_imei()
    
    url = "https://hd.c.mi.com/jp/eventapi/api/imeiexchange/getactinfo"
    try:
        mi_session.headers.update({"Referer": "https://www.mi.com/jp/imei-redemption/"})
        resp = mi_session.get(url, params={"from": "pc", "imei": imei, "email": email, "captchaCode": code}, timeout=10)
        return jsonify({"status": "success", "imei": imei, "data": resp.json()})
    except Exception as e:
        return jsonify({"status": "error", "imei": imei, "msg": str(e)})

@app.route('/redeem', methods=['POST'])
def redeem():
    d = request.json
    url = "https://hd.c.mi.com/jp/eventapi/api/imeiexchange/redeem"
    payload = {"from": "pc", "goodsId": d['goodsId'], "channel": "Mi.com", "email": d['email'], "captchaCode": d['code'], "imei": d['imei'], "activityId": d['actId'], "goodsName": d['goodsName'], "isSubscribe": "1"}
    try:
        resp = mi_session.post(url, data=payload, timeout=15)
        return jsonify({"status": "success", "data": resp.json()})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

# ================= THE FRONTEND HTML =================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Xiaomi Miner UI</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; background-color: #0f172a; color: #e2e8f0; }
        #log-window::-webkit-scrollbar { width: 6px; }
        #log-window::-webkit-scrollbar-thumb { background: #334155; border-radius: 10px; }
    </style>
</head>
<body class="min-h-screen p-4 md:p-8 flex items-center justify-center">
    <div class="max-w-5xl w-full grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div class="lg:col-span-4 space-y-6">
            <div class="bg-slate-800 border border-slate-700 rounded-2xl p-6 shadow-xl">
                <h1 class="text-xl font-bold text-white mb-6">Miner Control</h1>
                <div class="space-y-4 text-sm">
                    <label class="block text-xs text-slate-400 font-bold uppercase">Auth</label>
                    <input type="text" id="login-url" class="w-full bg-slate-900 border border-slate-700 rounded-lg p-3 outline-none" placeholder="Callback URL">
                    <button onclick="doLogin()" class="w-full bg-blue-600 hover:bg-blue-500 py-2.5 rounded-lg font-bold transition">Initialize Session</button>
                    
                    <hr class="border-slate-700">
                    
                    <label class="block text-xs text-slate-400 font-bold uppercase">Target Information</label>
                    <input type="text" id="custom-imei" class="w-full bg-slate-900 border border-slate-700 rounded-lg p-3 outline-none" placeholder="Custom IMEI (Leave empty for random)">
                    
                    <div class="flex gap-2">
                        <input type="email" id="email" class="w-full bg-slate-900 border border-slate-700 rounded-lg p-3 outline-none" placeholder="Email">
                        <button onclick="sendCode()" class="bg-slate-700 px-4 rounded-lg font-bold">Send</button>
                    </div>
                    <input type="text" id="code" class="w-full bg-slate-900 border border-slate-700 rounded-lg p-3 outline-none" placeholder="Captcha">
                    
                    <select id="mode" class="w-full bg-slate-900 border border-slate-700 rounded-lg p-3 outline-none">
                        <option value="1">Scan Only</option>
                        <option value="2">Scan & Redeem</option>
                    </select>
                    
                    <button onclick="toggleMining()" id="btn-mine" class="w-full bg-green-600 hover:bg-green-500 py-4 rounded-lg font-black text-lg transition shadow-lg">START MINER</button>
                </div>
            </div>
        </div>
        <div class="lg:col-span-8 flex flex-col gap-6">
            <div class="grid grid-cols-2 gap-4">
                <div class="bg-slate-800 p-4 rounded-xl text-center shadow-lg border border-slate-700"><span class="text-xs text-slate-400 font-bold block uppercase">Attempts</span><span id="ui-attempts" class="text-3xl font-black">0</span></div>
                <div class="bg-slate-800 p-4 rounded-xl text-center shadow-lg border border-slate-700"><span class="text-xs text-slate-400 font-bold block uppercase text-green-400">Jackpots</span><span id="ui-jackpots" class="text-3xl font-black text-green-400">0</span></div>
            </div>
            <div class="bg-slate-950 rounded-2xl border border-slate-800 shadow-2xl flex flex-col overflow-hidden">
                <div class="bg-slate-900/50 px-4 py-2 border-b border-slate-800 text-[10px] text-slate-500 font-mono">LIVE_LOG.TXT</div>
                <div id="log-window" class="p-6 text-xs font-mono h-[420px] overflow-y-auto space-y-1">
                    <div class="text-slate-500">>> Ready to initialize...</div>
                </div>
            </div>
        </div>
    </div>
    <script>
        let isRunning = false; let attempts = 0; let jackpots = 0;
        function log(msg, color="text-slate-300") {
            const win = document.getElementById('log-window');
            win.innerHTML += `<div><span class="text-slate-600">[${new Date().toLocaleTimeString()}]</span> <span class="${color}">${msg}</span></div>`;
            win.scrollTop = win.scrollHeight;
        }
        async function doLogin() {
            const url = document.getElementById('login-url').value;
            if(!url) return log("❌ URL Required", "text-red-400");
            log("🔑 Authenticating...");
            const res = await fetch('/login', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({url})});
            const data = await res.json();
            log(data.status === 'success' ? "✅ Session established!" : "❌ Error: " + data.msg, data.status === 'success' ? "text-green-400" : "text-red-400");
        }
        async function sendCode() {
            const email = document.getElementById('email').value;
            if(!email) return log("❌ Email Required", "text-red-400");
            const res = await fetch('/send_code', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({email})});
            log("📨 Verification code requested.");
        }
        function toggleMining() {
            const btn = document.getElementById('btn-mine');
            isRunning = !isRunning;
            btn.innerText = isRunning ? "STOP MINER" : "START MINER";
            btn.className = isRunning ? "w-full bg-red-600 hover:bg-red-500 py-4 rounded-lg font-black text-lg transition shadow-lg" : "w-full bg-green-600 hover:bg-green-500 py-4 rounded-lg font-black text-lg transition shadow-lg";
            if(isRunning) {
                log("🚀 Miner process started...", "text-green-400");
                scanLoop();
            } else {
                log("🛑 Miner process stopped.", "text-yellow-400");
            }
        }
        async function scanLoop() {
            if(!isRunning) return;
            const email = document.getElementById('email').value;
            const code = document.getElementById('code').value;
            const imei = document.getElementById('custom-imei').value;
            
            const res = await fetch('/scan_one', {
                method:'POST', 
                headers:{'Content-Type':'application/json'}, 
                body:JSON.stringify({email, code, imei})
            });
            const d = await res.json();
            
            attempts++; document.getElementById('ui-attempts').innerText = attempts;
            
            if(d.data && d.data.code === 0) {
                jackpots++; document.getElementById('ui-jackpots').innerText = jackpots;
                log("💎 JACKPOT: " + d.imei, "text-green-400 font-bold");
                if(document.getElementById('mode').value === "2") {
                    const item = d.data.data.goodsList[0];
                    const r = await fetch('/redeem', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({imei:d.imei, email, code, goodsId:item.goodsId, actId:item.actList[0].activityId, goodsName:item.goodsName})});
                    log("🏆 Redeemed successfully!"); toggleMining(); return;
                }
            } else { 
                log(`🔸 [Try ${attempts}] ${d.imei} : ${d.data.msg || d.data.code}`, "text-slate-500"); 
            }
            
            // Short delay to prevent overwhelming the function
            setTimeout(scanLoop, 1300);
        }
    </script>
</body>
</html>
"""
