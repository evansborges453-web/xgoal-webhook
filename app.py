import mercadopago, requests, os, json
from flask import Flask, request, jsonify

app = Flask(__name__)
MP_TOKEN = os.environ.get("MP_TOKEN")
TG_TOKEN = os.environ.get("TG_TOKEN")
TG_VIP   = os.environ.get("TG_VIP")

PROCESSED_FILE = "/tmp/processed_payments.json"

def _load_processed():
    try:
        return set(json.load(open(PROCESSED_FILE)))
    except Exception:
        return set()

def _save_processed(s):
    try:
        json.dump(list(s), open(PROCESSED_FILE, "w"))
    except Exception:
        pass

processed_payments = _load_processed()

def tg_send(chat_id, text):
    requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
        json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"})

def tg_invite_link(chat_id):
    r = requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/createChatInviteLink",
        json={"chat_id": chat_id, "member_limit": 1})
    if r.json().get("ok"):
        return r.json()["result"]["invite_link"]
    return None

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
        return jsonify({"ok": True, "qr_code": qr, "qr_img": qr_img, "payment_id": pay["id"]})
    return jsonify({"ok": False, "error": str(pay)}), 400

@app.route("/webhook", methods=["POST"])
def webhook():
    global processed_payments
    data  = request.json or {}
    topic = data.get("type") or request.args.get("topic", "")
    if topic == "payment":
        pay_id = data.get("data", {}).get("id") or request.args.get("id")
        if pay_id:
            pay_id_str = str(pay_id)
            if pay_id_str in processed_payments:
                print(f"[WEBHOOK] payment_id {pay_id_str} ja processado, ignorando.")
                return jsonify({"ok": True, "skipped": True})
            try:
                sdk = mercadopago.SDK(MP_TOKEN)
                pay = sdk.payment().get(pay_id)["response"]
                if pay.get("status") == "approved":
                    user_id = pay.get("external_reference", "")
                    email   = pay.get("payer", {}).get("email", "")
                    processed_payments.add(pay_id_str)
                    _save_processed(processed_payments)
                    link = tg_invite_link(TG_VIP)
                    if link and user_id:
                        tg_send(user_id, f"Pagamento aprovado! Acesse o canal VIP:\n{link}")
                    tg_send(TG_VIP, f"Novo membro VIP!\nEmail: {email}\nUser ID: {user_id}")
            except Exception as e:
                print(f"Webhook erro: {e}")
    return jsonify({"ok": True})

@app.route("/")
def index():
    return open("index.html").read()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
