import mercadopago, requests, os
from flask import Flask, request, jsonify

app = Flask(__name__)
MP_TOKEN = os.environ.get("MP_TOKEN")
TG_TOKEN = os.environ.get("TG_TOKEN")
TG_VIP = os.environ.get("TG_VIP")

def tg_send(token, chat_id, text):
    requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"})

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json or {}
    if data.get("type") == "payment":
        pid = data["data"]["id"]
        sdk = mercadopago.SDK(MP_TOKEN)
        pay = sdk.payment().get(pid)["response"]
        if pay.get("status") == "approved":
            email = pay.get("payer",{}).get("email","")
            tg_send(TG_TOKEN, TG_VIP, f"✅ Pagamento aprovado!\nEmail: {email}")
    return jsonify({"ok": True})

@app.route("/")
def index():
    return open("index.html").read()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
