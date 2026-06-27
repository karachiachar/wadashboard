from flask import Blueprint, request
from database import SessionWhatsApp, SessionSaaS
from models import Message, Lead
from services.whatsapp_api import send_message, send_jaspers_menu, send_interactive_buttons, download_media
from services.meta_api import send_event
import os
import mimetypes
import uuid

from config_manager import get_config

webhook_bp = Blueprint("webhook", __name__)
VERIFY_TOKEN = get_config("WEBHOOK_VERIFY_TOKEN", "myverifytoken")

# In-memory dictionary state tracker to mimic Redis for user context paths
# Format: { "phone_number": {"state": "browsing", "cart_total": 0.0} }
USER_SESSIONS = {}

@webhook_bp.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Verification failed", 403

@webhook_bp.route("/webhook", methods=["POST"])
def receive_message():
    data = request.json
    try:
        entry = data["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]

        if "statuses" in value:
            db = SessionWhatsApp()
            for st in value["statuses"]:
                msg_id = st.get("id")
                status = st.get("status")
                m = db.query(Message).filter(Message.message_id == msg_id).first()
                if m:
                    # Update status, but prevent downgrade (e.g. read -> delivered)
                    # Statuses go: sent -> delivered -> read
                    rank = {"sent": 1, "delivered": 2, "read": 3, "failed": 4}
                    old_rank = rank.get(m.status, 0)
                    new_rank = rank.get(status, 0)
                    if new_rank > old_rank:
                        m.status = status
            db.commit()
            db.close()
            return "EVENT_RECEIVED", 200

        if "messages" in value:
            msg = value["messages"][0]
            phone = msg["from"]
            
            # Initialize Session Tracker if missing
            if phone not in USER_SESSIONS:
                USER_SESSIONS[phone] = {"state": "welcome", "cart_total": 0.0}
            
            user_session = USER_SESSIONS[phone]
            saved_text_content = ""

            # Check if this message was triggered from a Click-to-WhatsApp ad
            if "referral" in msg and "ctwa_clid" in msg["referral"]:
                ctwa_clid = msg["referral"]["ctwa_clid"]
                db_saas = SessionSaaS()
                lead = db_saas.query(Lead).filter(Lead.phone == phone).first()
                if not lead:
                    lead = Lead(phone=phone, click_id=ctwa_clid)
                    db_saas.add(lead)
                else:
                    lead.click_id = ctwa_clid
                db_saas.commit()
                db_saas.close()

            # -------------------------------------------------------------
            # CASE A: USER INTERACTED WITH AN INTERACTIVE LIST OR BUTTON
            # -------------------------------------------------------------
            if msg["type"] == "interactive":
                interactive_type = msg["interactive"]["type"]
                
                # User selected an item out of our 'View Aisles' List menu
                if interactive_type == "list_reply":
                    selection_id = msg["interactive"]["list_reply"]["id"]
                    selection_title = msg["interactive"]["list_reply"]["title"]
                    saved_text_content = selection_title
                    
                    if selection_id.startswith("item_"):
                        # Extract price dynamically from the ID string layout (ex: item_apples_2.99)
                        price = float(selection_id.split("_")[2])
                        user_session["cart_total"] += price
                        user_session["state"] = "shopping"
                        
                        send_interactive_buttons(
                            phone=phone,
                            text=f"🛒 Added *{selection_title}* to your cart!\nCurrent Total: ${user_session['cart_total']:.2f}",
                            buttons={"show_menu": "Keep Shopping", "cart_checkout": "Checkout Now"}
                        )
                        
                    elif selection_id == "cart_checkout":
                        if user_session["cart_total"] == 0.0:
                            send_message(phone, "Your cart is empty! Type 'menu' to view options.")
                        else:
                            user_session["state"] = "checkout"
                            send_message(phone, f"💳 Your total is *${user_session['cart_total']:.2f}*.\n\nPlease type your delivery address to complete your checkout order.")
                            
                    elif selection_id == "cart_clear":
                        user_session["cart_total"] = 0.0
                        user_session["state"] = "welcome"
                        send_message(phone, "🧹 Your shopping cart has been cleared. Type 'menu' to restart.")

                # User tapped a Quick Reply Action Button
                elif interactive_type == "button_reply":
                    button_id = msg["interactive"]["button_reply"]["id"]
                    button_title = msg["interactive"]["button_reply"].get("title", button_id)
                    saved_text_content = button_title
                    
                    if button_id == "show_menu":
                        send_jaspers_menu(phone)
                    elif button_id == "cart_checkout":
                        user_session["state"] = "checkout"
                        send_message(phone, f"💳 Your total is *${user_session['cart_total']:.2f}*.\n\nPlease reply with your delivery address to complete your purchase order.")

            # -------------------------------------------------------------
            # CASE B: USER DROPPED STANDARD OLD SCHOOL TEXT INPUTS
            # -------------------------------------------------------------
            elif msg["type"] == "text":
                text_input = msg["text"]["body"].strip().lower()
                saved_text_content = msg["text"]["body"]
                
                # Check out processing logic branch
                if user_session["state"] == "checkout":
                    # Fire Meta Conversion API Purchase Event from meta_api.py
                    try:
                        # Extract metadata context if present inside the webhook dictionary values
                        metadata = value.get("metadata", {})
                        page_id = metadata.get("display_phone_number", "default_page")
                        
                        send_event(
                            phone=phone,
                            ctwa_clid=msg.get("id", "none"),
                            value=user_session["cart_total"],
                            currency="USD",
                            page_id=page_id
                        )
                    except Exception as meta_err:
                        print("Conversion logging exception ignored:", meta_err)
                    
                    send_message(phone, f"✅ *Order Confirmed!*\nYour fresh groceries will be processed and delivered directly to:\n_{msg['text']['body']}_")
                    # Clear session profile state
                    user_session["cart_total"] = 0.0
                    user_session["state"] = "welcome"
                    
                    # Removed auto-reply

            elif msg["type"] == "location":
                loc = msg["location"]
                lat = loc.get("latitude", "")
                lng = loc.get("longitude", "")
                name = loc.get("name", "")
                address = loc.get("address", "")
                
                parts = []
                if name: parts.append(name)
                if address: parts.append(address)
                
                if parts:
                    saved_text_content = f"📍 Location: {', '.join(parts)}\nhttps://maps.google.com/?q={lat},{lng}"
                else:
                    saved_text_content = f"📍 Location: {lat}, {lng}\nhttps://maps.google.com/?q={lat},{lng}"

            elif msg["type"] in ["image", "video", "audio", "document", "sticker"]:
                media_info = msg[msg["type"]]
                media_id = media_info.get("id")
                caption = media_info.get("caption", "")
                
                saved_text_content = f"[{msg['type'].capitalize()} received]"
                
                if media_id:
                    file_bytes, mime_type = download_media(media_id)
                    if file_bytes:
                        ext = mimetypes.guess_extension(mime_type) or ""
                        if not ext and msg["type"] == "audio": ext = ".ogg"
                        if not ext and msg["type"] == "video": ext = ".mp4"
                        if not ext and msg["type"] == "image": ext = ".jpg"
                        if not ext and msg["type"] == "document": ext = ".pdf"
                        
                        filename = f"{uuid.uuid4().hex}{ext}"
                        save_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "chat_media")
                        os.makedirs(save_dir, exist_ok=True)
                        filepath = os.path.join(save_dir, filename)
                        
                        with open(filepath, "wb") as f:
                            f.write(file_bytes)
                            
                        # Format for the UI
                        icon_map = {"image": "📷 Image", "video": "🎬 Video", "audio": "🎙️ Audio", "document": "📄 Document", "sticker": "🖼️ Sticker"}
                        icon = icon_map.get(msg["type"], "Media")
                        
                        local_url = f"/static/chat_media/{filename}"
                        if caption:
                            saved_text_content = f"[{icon}] {local_url}\n{caption}"
                        else:
                            saved_text_content = f"[{icon}] {local_url}"
            else:
                # Fallback for unhandled message types
                saved_text_content = f"[{msg['type'].capitalize()} received]"

            # -------------------------------------------------------------
            # COMMIT TRANSACTION METRICS AND PAYLOAD STRINGS TO SQL DATABASE
            # -------------------------------------------------------------
            db = SessionWhatsApp()
            new_message = Message(
                phone=phone,
                direction="inbound",
                message=saved_text_content,
                timestamp=str(msg["timestamp"])
            )
            db.add(new_message)
            db.commit()
            db.close()
            print("MESSAGE SAVED SECURELY TO SQL STORAGE ENGINE")

    except Exception as e:
        print("WEBHOOK PROCESSING ERROR TRACE:", e)

    return "EVENT_RECEIVED", 200
