import os
import requests
from fastapi import FastAPI, Request, Response, BackgroundTasks
import google.generativeai as genai

app = FastAPI()

# Environment Variables
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "my_secret_token_123")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Gemini AI response & WhatsApp message process එක පසුබිමෙන් (Background) සිදුකිරීම
def process_whatsapp_message(msg_body: str, from_number: str):
    try:
        response = model.generate_content(msg_body)
        reply_text = response.text

        url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
        headers = {
            "Authorization": f"Bearer {WHATSAPP_TOKEN}",
            "Content-Type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": from_number,
            "type": "text",
            "text": {"body": reply_text}
        }
        requests.post(url, json=payload, headers=headers)
    except Exception as e:
        print(f"Error processing message: {e}")

@app.get("/api/webhook")
async def verify_webhook(request: Request):
    params = request.query_params
    if params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == VERIFY_TOKEN:
        return Response(content=params.get("hub.challenge"), status_code=200, media_type="text/plain")
    return Response(content="Verification failed", status_code=403)

@app.post("/api/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    
    try:
        entry = data['entry'][0]['changes'][0]['value']
        if 'messages' in entry:
            message = entry['messages'][0]
            from_number = message['from']
            msg_body = message.get('text', {}).get('body', '')

            if msg_body:
                # Meta එකට 200 OK වහාම යවා, Gemini task එක background එකෙන් දුවන්න සැලැස්වීම
                background_tasks.add_task(process_whatsapp_message, msg_body, from_number)
    except Exception as e:
        print(f"Error parsing webhook: {e}")
        
    return Response(content="EVENT_RECEIVED", status_code=200)
