import mercadopago, requests, os, uuid
from flask import Flask, request, jsonify

app = Flask(__name__)
MP_TOKEN = os.environ.get("MP_TOKEN")
TG_TOKEN = os.environ.get("TG_TOKEN")
TG_VIP = os.environ.get("TG_VIP")

def tg_send(token, chat_id, text):
    requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"})

@app.route("/pix", methods=["POST"])
def criar_pix():
    data = request.json or {}
    user_id = data.get("user_id", "0")
    email = data.get("email", "cliente@email.com")
    sdk = mercadopago.SDK(MP_TOKEN)
    payment_data = {
        "transaction_amount": 29.90,
        "description": "XGoal Signals PRO",
        "payment_method_id": "pix",
        "payer": {"email": email},
        "external_reference": str(user_id),
        "notification_url": "https://xgoal-webhook.onrender.com/webhook"
    }
    result = sdk.payment().create(payment_data)
    pay = result["response"]
    if result["status"] == 201:
        qr = pay["point_of_interaction"]["transaction_data"]["qr_code"]
        qr_img = pay["point_of_interaction"]["transaction_data"]["qr_code_base64"]
        pay_id = pay["id"]
        return jsonify({"ok": True, "qr_code": qr, "qr_img": qr_img, "payment_id": pay_id})
    return jsonify({"ok": False, "error": pay}), 400

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json or {}
    topic = data.get("type") or request.args.get("topic", "")
    if topic == "payment":
        pay_id = data.get("data", {}).get("id") or request.args.get("id")
        if pay_id:
            try:
                sdk = mercadopago.SDK(MP_TOKEN)
                pay = sdk.payment().get(pay_id)["response"]
                if pay.get("status") == "approved":
                    user_id = pay.get("external_reference", "")
                    email = pay.get("payer", {}).get("email", "")
                    tg_send(TG_TOKEN, TG_VIP, f"✅ Pagamento aprovado!\nUser: {user_id}\nEmail: {email}")
            except Exception as e:
                print(f"Webhook erro: {e}")
    return jsonify({"ok": True})

@app.route("/")
def index():
    return open("index.html").read()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
