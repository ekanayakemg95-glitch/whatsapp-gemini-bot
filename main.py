from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from google import genai
import requests
import os

app = FastAPI()

# ==============================
# Environment Variables
# ==============================

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


# ==============================
# Gemini AI Client
# ==============================

if GEMINI_API_KEY:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
else:
    gemini_client = None


# ==============================
# Home / Health Check
# ==============================

@app.get("/")
def home():
    return {
        "status": "online",
        "message": "WhatsApp Gemini AI Chatbot is running!"
    }


# ==============================
# WhatsApp Webhook Verification
# ==============================

@app.get("/api/webhook")
async def verify_webhook(request: Request):

    hub_mode = request.query_params.get("hub.mode")
    hub_verify_token = request.query_params.get("hub.verify_token")
    hub_challenge = request.query_params.get("hub.challenge")

    print("Webhook verification request")
    print("Mode:", hub_mode)

    if (
        hub_mode == "subscribe"
        and hub_verify_token == VERIFY_TOKEN
    ):
        return PlainTextResponse(
            content=hub_challenge or "",
            status_code=200
        )

    return PlainTextResponse(
        content="Verification failed",
        status_code=403
    )


# ==============================
# Receive WhatsApp Messages
# ==============================

@app.post("/api/webhook")
async def receive_webhook(request: Request):

    try:

        data = await request.json()

        print("Incoming WhatsApp Data:")
        print(data)

        entry = data.get("entry", [])

        if not entry:
            return {"status": "no entry"}

        changes = entry[0].get("changes", [])

        if not changes:
            return {"status": "no changes"}

        value = changes[0].get("value", {})

        messages = value.get("messages", [])

        if not messages:
            return {"status": "no message"}

        message = messages[0]

        customer_number = message.get("from")

        message_type = message.get("type")

        if message_type != "text":
            return {
                "status": "ignored",
                "reason": "Only text messages are supported"
            }

        customer_message = (
            message.get("text", {})
            .get("body", "")
        )

        print("Customer:", customer_number)
        print("Message:", customer_message)


        # ==============================
        # Send message to Gemini
        # ==============================

        if not gemini_client:

            print("Gemini API key is missing")

            return {
                "status": "gemini_api_key_missing"
            }


        system_instruction = """
You are a helpful WhatsApp customer service AI assistant.

You are helping customers of Yasoda Technology.

Rules:
- Reply in the same language used by the customer.
- If the customer writes Sinhala, reply in Sinhala.
- If the customer writes English, reply in English.
- Be polite, friendly and concise.
- Do not make up product prices, warranty information or stock information.
- If you do not know something, politely say that a human staff member can help.
"""


        prompt = f"""
{system_instruction}

Customer message:
{customer_message}

Write a helpful WhatsApp reply.
"""


        response = gemini_client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt
        )

        ai_reply = response.text


        if not ai_reply:

            ai_reply = (
                "කරුණාකර මොහොතක් රැඳී සිටින්න. "
                "අපගේ කාර්ය මණ්ඩලය ඔබට පිළිතුරු ලබා දෙනු ඇත."
            )


        print("Gemini Reply:")
        print(ai_reply)


        # ==============================
        # Send reply to WhatsApp
        # ==============================

        whatsapp_url = (
            f"https://graph.facebook.com/v26.0/"
            f"{PHONE_NUMBER_ID}/messages"
        )

        headers = {
            "Authorization": f"Bearer {WHATSAPP_TOKEN}",
            "Content-Type": "application/json"
        }

        whatsapp_data = {
            "messaging_product": "whatsapp",
            "to": customer_number,
            "type": "text",
            "text": {
                "body": ai_reply
            }
        }

        whatsapp_response = requests.post(
            whatsapp_url,
            headers=headers,
            json=whatsapp_data,
            timeout=20
        )


        print("WhatsApp API Response:")
        print(whatsapp_response.status_code)
        print(whatsapp_response.text)


        return {
            "status": "success",
            "whatsapp_status": whatsapp_response.status_code
        }


    except Exception as e:

        print("ERROR:")
        print(str(e))

        return {
            "status": "error",
            "message": str(e)
        }
