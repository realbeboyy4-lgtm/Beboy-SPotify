from flask import Flask, request, jsonify, render_template_string
import requests
import random

app = Flask(__name__)

# ================= CONFIGURATION =================
PREFIXES = ["8638250700", "86382507"]
# Global Session - Vercel reuses instances, so this can persist briefly 
mi_session = requests.Session()
mi_session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Referer": "https://www.mi.com/jp/imei-redemption/",
    "Origin": "https://www.mi.com",
    "X-Requested-With": "XMLHttpRequest"
})

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
    random_part = "".join([str(random.randint(0, 9)) for _ in range(14 - len(prefix))])
    base = prefix + random_part
    return base + str(calculate_luhn(base))

# Use your existing HTML_TEMPLATE string here...
HTML_TEMPLATE = """... (Keep your current HTML code here) ..."""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/login', methods=['POST'])
def login():
    url = request.json.get('url')
    try:
        resp = mi_session.get(url, timeout=10, allow_redirects=True)
        # Session automatically handles cookies; we spread them just in case
        cookies = mi_session.cookies.get_dict()
        for name, value in cookies.items():
            for domain in ['.mi.com', '.c.mi.com', 'hd.c.mi.com']:
                mi_session.cookies.set(name, value, domain=domain, path='/')
        return jsonify({"status": "success", "msg": "Backend Session Established!"})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

@app.route('/send_code', methods=['POST'])
def send_code():
    email = request.json.get('email')
    try:
        resp = mi_session.get("https://hd.c.mi.com/jp/eventapi/api/imeiexchange/sendcode", 
                              params={"from": "pc", "email": email, "tel": ""}, timeout=10)
        return jsonify({"status": "success", "msg": "Code Sent!"})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

@app.route('/scan_one', methods=['POST'])
def scan_one():
    data = request.json
    imei = get_next_imei()
    try:
        resp = mi_session.get("https://hd.c.mi.com/jp/eventapi/api/imeiexchange/getactinfo", 
                              params={"from": "pc", "imei": imei, "email": data['email'], "captchaCode": data['code']}, timeout=10)
        return jsonify({"status": "success", "imei": imei, "data": resp.json()})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})