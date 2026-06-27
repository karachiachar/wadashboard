from flask import Blueprint, render_template, request, jsonify, redirect, session, current_app
import json
from database import SessionWhatsApp, SessionSaaS
from models import Message, InteractiveTemplate, Lead
from sqlalchemy import func
from services.meta_api import send_event
from services.whatsapp_api import (
    send_message,
    send_jaspers_menu,
    send_interactive_buttons,
    upload_media,
    send_image,
    send_video,
    send_document,
    send_audio,
    send_sticker,
    send_location,
    send_catalog,
    send_list_message,
    send_reply_buttons,
    send_single_product,
    send_multi_product,
    send_location_request,
    send_address_message,
    send_flow,
)

dashboard_bp = Blueprint("dashboard", __name__)


# ─────────────────────────────────────────────
#  SHARED HELPERS
# ─────────────────────────────────────────────
def _auth_check():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    return None

def _log_outbound(db, phone, label, msg_id=None):
    msg = Message(phone=phone, direction="outbound", message=label, timestamp="now", message_id=msg_id)
    db.add(msg)
    db.commit()


# ─────────────────────────────────────────────
#  AUTH
# ─────────────────────────────────────────────
@dashboard_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form.get("password")
        if password == current_app.config["DASHBOARD_PASSWORD"]:
            session["logged_in"] = True
            return redirect("/")
        return render_template("login.html", error="Invalid password. Please try again.")
    return render_template("login.html")

@dashboard_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ─────────────────────────────────────────────
#  DASHBOARD
# ─────────────────────────────────────────────
@dashboard_bp.route("/")
def dashboard():
    if not session.get("logged_in"):
        return redirect("/login")
    return render_template("dashboard.html")

@dashboard_bp.route("/messenger")
def messenger():
    if not session.get("logged_in"):
        return redirect("/login")
    return render_template("messenger.html")

@dashboard_bp.route("/data")
def data_page():
    if not session.get("logged_in"):
        return redirect("/login")
    return render_template("data.html")

@dashboard_bp.route("/settings")
def settings_page():
    if not session.get("logged_in"):
        return redirect("/login")
    return render_template("settings.html")

from config_manager import get_config, set_config

@dashboard_bp.route("/api/settings", methods=["GET"])
def get_settings():
    err = _auth_check()
    if err: return err
    return jsonify({
        "WHATSAPP_TOKEN": get_config("WHATSAPP_TOKEN", "EAAQ02uTY1vwBRjkSM8CZCvGsOWZCESWKysXZByO1bDZA6ed1ZBWAwhSZCGfBwR3wP2zw4VLsMtlwEAzc3YroXX6rIMVpAgs9fiuR1E8uQyn8mOKdDMcw9Ir7T1GQIyTkfBmUM2Hr4YUQ61orY23WOgjfjWTyqpi8fFthoAlkLoA4A7ZCM7FT3IGIwGdDX3ADgZDZD"),
        "PHONE_NUMBER_ID": get_config("PHONE_NUMBER_ID", "1153175711206489"),
        "META_TOKEN": get_config("META_TOKEN", "EAAQ02uTY1vwBRa81SZC86tOnA2wQvVnDniCVt86NTuO2IhOxZBDahrZCEaVrG46AdYng0NR39CMYGWK0K2ZBCjSS4ZAFDnAyt3XUra1fFuTctUIlL7oCvk3nUzAI1uLmap4j7tjJtt52ZBwn2aeZACgsTW7jjxofBcuHUjjpCbjI8TsyejCKsqtnZAGS2ZB9EGCJMzf0S1Yc5PwZAYwPIRWxGMxNEOy4GkCygjNIE5HZADAKqyJVZCHHpuWXBZCnw85jr11IXGFhvFIZAqoHVCCH8mf66jZBa3N"),
        "META_DATASET_ID": get_config("META_DATASET_ID", "1568141444274727"),
        "WEBHOOK_VERIFY_TOKEN": get_config("WEBHOOK_VERIFY_TOKEN", "myverifytoken")
    })

@dashboard_bp.route("/api/settings", methods=["POST"])
def update_settings():
    err = _auth_check()
    if err: return err
    data = request.json
    for key in ["WHATSAPP_TOKEN", "PHONE_NUMBER_ID", "META_TOKEN", "META_DATASET_ID", "WEBHOOK_VERIFY_TOKEN"]:
        if key in data:
            set_config(key, data[key])
    
    # Also handle password specifically if passed
    if "DASHBOARD_PASSWORD" in data and data["DASHBOARD_PASSWORD"].strip():
        set_config("DASHBOARD_PASSWORD", data["DASHBOARD_PASSWORD"])
        current_app.config["DASHBOARD_PASSWORD"] = data["DASHBOARD_PASSWORD"]
        
    return jsonify({"success": True})


@dashboard_bp.route("/api/quick_replies", methods=["GET"])
def get_quick_replies():
    err = _auth_check()
    if err: return err
    db = SessionWhatsApp()
    try:
        from models import QuickReply
        replies = db.query(QuickReply).order_by(QuickReply.id.desc()).all()
        return jsonify([{"id": r.id, "shortcut": r.shortcut, "title": r.title, "body": r.body} for r in replies])
    finally:
        db.close()

@dashboard_bp.route("/api/quick_replies", methods=["POST"])
def add_quick_reply():
    err = _auth_check()
    if err: return err
    data = request.json
    db = SessionWhatsApp()
    try:
        from models import QuickReply
        qr = QuickReply(shortcut=data["shortcut"], title=data["title"], body=data["body"])
        db.add(qr)
        db.commit()
        return jsonify({"success": True, "id": qr.id})
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        db.close()

@dashboard_bp.route("/api/quick_replies/<int:qr_id>", methods=["PUT"])
def edit_quick_reply(qr_id):
    err = _auth_check()
    if err: return err
    data = request.json
    db = SessionWhatsApp()
    try:
        from models import QuickReply
        qr = db.query(QuickReply).get(qr_id)
        if not qr:
            return jsonify({"error": "Not found"}), 404
        qr.shortcut = data.get("shortcut", qr.shortcut)
        qr.title = data.get("title", qr.title)
        qr.body = data.get("body", qr.body)
        db.commit()
        return jsonify({"success": True})
    finally:
        db.close()

@dashboard_bp.route("/api/quick_replies/<int:qr_id>", methods=["DELETE"])
def delete_quick_reply(qr_id):
    err = _auth_check()
    if err: return err
    db = SessionWhatsApp()
    try:
        from models import QuickReply
        qr = db.query(QuickReply).get(qr_id)
        if qr:
            db.delete(qr)
            db.commit()
        return jsonify({"success": True})
    finally:
        db.close()

# ─────────────────────────────────────────────
#  CHAT DATA
# ─────────────────────────────────────────────
@dashboard_bp.route("/api/chats")
def get_chats():
    err = _auth_check()
    if err: return err
    db = SessionWhatsApp()
    try:
        subq = db.query(Message.phone, func.max(Message.id).label('max_id')).group_by(Message.phone).subquery()
        rows = db.query(Message).join(subq, Message.id == subq.c.max_id).order_by(Message.id.desc()).all()
        chats = []
        db_saas = SessionSaaS()
        for m in rows:
            last_inbound = db.query(Message).filter(Message.phone == m.phone, Message.direction == "inbound").order_by(Message.id.desc()).first()
            last_ts = last_inbound.timestamp if last_inbound else None
            lead = db_saas.query(Lead).filter(Lead.phone == m.phone).first()
            lead_status = lead.status if lead else "none"
            has_click_id = bool(lead and lead.click_id and lead.click_id.strip())
            
            from models import Order
            latest_order = db.query(Order).filter(Order.phone == m.phone).order_by(Order.id.desc()).first()
            order_status = latest_order.status if latest_order else None
            
            unread_count = db.query(func.count(Message.id)).filter(Message.phone == m.phone, Message.direction == "inbound", Message.is_read == 0).scalar()
            
            chats.append({"phone": m.phone, "last_message": m.message, "timestamp": m.timestamp, "last_inbound": last_ts, "lead_status": lead_status, "has_click_id": has_click_id, "order_status": order_status, "unread_count": unread_count})
        db_saas.close()
        return jsonify(chats)
    finally:
        db.close()

@dashboard_bp.route("/api/messages/<phone>")
def get_messages(phone):
    err = _auth_check()
    if err: return err
    db = SessionWhatsApp()
    try:
        db.query(Message).filter(Message.phone == phone, Message.direction == "inbound", Message.is_read == 0).update({"is_read": 1})
        db.commit()
        
        msgs = db.query(Message).filter(Message.phone == phone).order_by(Message.id.asc()).all()
        return jsonify([{"id": m.id, "text": m.message, "type": "outgoing" if m.direction == "outbound" else "incoming", "status": m.status, "timestamp": m.timestamp} for m in msgs])
    finally:
        db.close()

@dashboard_bp.route("/api/chats/<phone>", methods=["DELETE"])
def delete_chat(phone):
    err = _auth_check()
    if err: return err
    db = SessionWhatsApp()
    try:
        db.query(Message).filter(Message.phone == phone).delete(synchronize_session=False)
        db.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@dashboard_bp.route("/api/messages/bulk", methods=["DELETE"])
def bulk_delete_messages():
    err = _auth_check()
    if err: return err
    data = request.get_json() or {}
    ids = data.get("ids", [])
    if not ids:
        return jsonify({"success": True})
    db = SessionWhatsApp()
    try:
        db.query(Message).filter(Message.id.in_(ids)).delete(synchronize_session=False)
        db.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

# ─────────────────────────────────────────────
#  FORWARD MESSAGES
# ─────────────────────────────────────────────
@dashboard_bp.route("/api/forward", methods=["POST"])
def forward_api():
    err = _auth_check()
    if err: return err
    data = request.get_json() or {}
    message_ids = data.get("message_ids", [])
    target_phones = data.get("target_phones", [])
    
    if not message_ids or not target_phones:
        return jsonify({"error": "Missing message_ids or target_phones"}), 400
        
    db = SessionWhatsApp()
    try:
        msgs = db.query(Message).filter(Message.id.in_(message_ids)).order_by(Message.id.asc()).all()
        import re, os
        from services.whatsapp_api import upload_media, send_image, send_video, send_audio, send_document
        import mimetypes
        
        for phone in target_phones:
            for m in msgs:
                text = m.message or ""
                # Parse media
                media_match = re.search(r'\[(.*?)\] (.*?\.(?:jpg|jpeg|png|mp4|ogg|webm|wav|gif|webp|pdf))', text, re.IGNORECASE)
                sent_media = False
                if media_match:
                    media_type_raw = media_match.group(1).lower()
                    local_url = media_match.group(2).strip()
                    caption = text.split(local_url)[-1].strip()
                    
                    # Convert local_url to local filepath
                    if local_url.startswith("/"):
                        local_url = local_url[1:]
                    filepath = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), local_url)
                    
                    if os.path.exists(filepath):
                        with open(filepath, "rb") as f:
                            file_bytes = f.read()
                        mime_type = mimetypes.guess_type(filepath)[0] or "application/octet-stream"
                        filename = os.path.basename(filepath)
                        
                        up_res = upload_media(file_bytes, mime_type, filename)
                        media_id = up_res.get("id")
                        if media_id:
                            if "image" in media_type_raw or "📷" in media_type_raw:
                                res = send_image(phone, media_id=media_id, caption=caption)
                                _log_outbound(db, phone, f"[📷 Image] /{local_url}\n{caption}".strip(), res.get("messages", [{}])[0].get("id") if "messages" in res else None)
                                sent_media = True
                            elif "video" in media_type_raw or "🎬" in media_type_raw:
                                res = send_video(phone, media_id=media_id, caption=caption)
                                _log_outbound(db, phone, f"[🎬 Video] /{local_url}\n{caption}".strip(), res.get("messages", [{}])[0].get("id") if "messages" in res else None)
                                sent_media = True
                            elif "audio" in media_type_raw or "🎙️" in media_type_raw or "🎵" in media_type_raw:
                                res = send_audio(phone, media_id=media_id)
                                _log_outbound(db, phone, f"[🎙️ Audio] /{local_url}", res.get("messages", [{}])[0].get("id") if "messages" in res else None)
                                sent_media = True
                            elif "document" in media_type_raw or "📄" in media_type_raw:
                                res = send_document(phone, media_id=media_id, filename=filename, caption=caption)
                                _log_outbound(db, phone, f"[📄 Document] /{local_url}\n{caption}".strip(), res.get("messages", [{}])[0].get("id") if "messages" in res else None)
                                sent_media = True
                
                if not sent_media:
                    # Fallback: Treat as text
                    res = send_message(phone, text)
                    msg_id = res.get("messages", [{}])[0].get("id") if res and "messages" in res else None
                    _log_outbound(db, phone, text, msg_id)
                
        return jsonify({"success": True})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


# ─────────────────────────────────────────────
#  SEND TEXT
# ─────────────────────────────────────────────
@dashboard_bp.route("/api/send", methods=["POST"])
def send_api():
    err = _auth_check()
    if err: return err
    data  = request.get_json()
    text  = data.get("message")
    phone = data.get("phone")
    if not phone or not text:
        return jsonify({"error": "Missing phone or message"}), 400
    db = SessionWhatsApp()
    try:
        resp = send_message(phone, text)
        msg_id = resp.get("messages", [{}])[0].get("id") if resp and "messages" in resp else None
        _log_outbound(db, phone, text, msg_id)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


# ─────────────────────────────────────────────
#  UPLOAD MEDIA  ← Core upload route
#  Receives multipart file from browser,
#  uploads to Meta's servers, returns media_id
import uuid
import os

@dashboard_bp.route("/api/upload_media", methods=["POST"])
def upload_media_api():
    err = _auth_check()
    if err: return err

    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if not file or file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    file_bytes = file.read()
    filename   = file.filename or "upload"

    # ── Determine MIME type ──────────────────────────────────────
    mime_type = file.mimetype or ""

    # Flask may report application/octet-stream for blobs — guess from filename
    if not mime_type or mime_type == "application/octet-stream":
        import mimetypes
        guessed, _ = mimetypes.guess_type(filename)
        mime_type = guessed or "audio/wav"

    # WAV is directly supported by Meta — pass through as-is
    # For Chrome's webm recordings (fallback path), relabel as audio/ogg
    if "webm" in mime_type:
        mime_type = "audio/ogg"

    # Strip codec parameters Meta doesn't understand: "audio/ogg;codecs=opus" → "audio/ogg"
    mime_type = mime_type.split(";")[0].strip()

    # Normalize common aliases
    if mime_type == "audio/x-wav":
        mime_type = "audio/wav"

    try:
        result = upload_media(file_bytes, mime_type, filename)

        # ── Properly extract error string from Meta's error object ──
        if result.get("error"):
            raw_err = result["error"]
            if isinstance(raw_err, dict):
                # Meta returns {"message": "...", "type": "...", "code": ...}
                err_msg = raw_err.get("message") or raw_err.get("type") or str(raw_err)
            else:
                err_msg = str(raw_err)
            return jsonify({"error": err_msg}), 500

        media_id = result.get("id")
        if not media_id:
            return jsonify({"error": f"No media_id from Meta. Response: {result}"}), 500

        # Save locally for chat preview
        import mimetypes
        ext = mimetypes.guess_extension(mime_type) or ""
        if not ext and "webm" in mime_type: ext = ".webm"
        if not ext and "ogg" in mime_type: ext = ".ogg"
        if not ext and "mp4" in mime_type: ext = ".mp4"
        if not ext and "jpeg" in mime_type: ext = ".jpg"
        
        unique_filename = f"{uuid.uuid4().hex}{ext}"
        save_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "chat_media")
        os.makedirs(save_dir, exist_ok=True)
        filepath = os.path.join(save_dir, unique_filename)
        
        with open(filepath, "wb") as f:
            f.write(file_bytes)

        local_url = f"/static/chat_media/{unique_filename}"

        return jsonify({"media_id": media_id, "local_url": local_url})

    except Exception as e:
        return jsonify({"error": str(e)}), 500



# ─────────────────────────────────────────────
#  SEND IMAGE
# ─────────────────────────────────────────────
@dashboard_bp.route("/api/send_image", methods=["POST"])
def send_image_api():
    err = _auth_check()
    if err: return err
    data     = request.get_json()
    phone    = data.get("phone")
    media_id = data.get("media_id")
    local_url = data.get("local_url", "")
    caption  = data.get("caption", "").strip()
    if not phone or not media_id:
        return jsonify({"error": "Missing phone or media_id"}), 400
    db = SessionWhatsApp()
    try:
        result = send_image(phone, media_id=media_id, caption=caption)
        if result.get("error"):
            return jsonify({"error": result["error"]}), 500
        msg_id = result.get("messages", [{}])[0].get("id") if "messages" in result else None
        
        log_text = f"[📷 Image] {local_url}\n{caption}" if caption else f"[📷 Image] {local_url}"
        _log_outbound(db, phone, log_text, msg_id)
        
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


# ─────────────────────────────────────────────
#  SEND VIDEO
# ─────────────────────────────────────────────
@dashboard_bp.route("/api/send_video", methods=["POST"])
def send_video_api():
    err = _auth_check()
    if err: return err
    data     = request.get_json()
    phone    = data.get("phone")
    media_id = data.get("media_id")
    local_url = data.get("local_url", "")
    caption  = data.get("caption", "").strip()
    if not phone or not media_id:
        return jsonify({"error": "Missing phone or media_id"}), 400
    db = SessionWhatsApp()
    try:
        result = send_video(phone, media_id=media_id, caption=caption)
        if result.get("error"):
            return jsonify({"error": result["error"]}), 500
        msg_id = result.get("messages", [{}])[0].get("id") if "messages" in result else None
        
        log_text = f"[🎬 Video] {local_url}\n{caption}" if caption else f"[🎬 Video] {local_url}"
        _log_outbound(db, phone, log_text, msg_id)
        
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


# ─────────────────────────────────────────────
#  SEND DOCUMENT
# ─────────────────────────────────────────────
@dashboard_bp.route("/api/send_document", methods=["POST"])
def send_document_api():
    err = _auth_check()
    if err: return err
    data     = request.get_json()
    phone    = data.get("phone")
    media_id = data.get("media_id")
    local_url = data.get("local_url", "")
    filename = data.get("filename", "document")
    caption  = data.get("caption", "").strip()
    if not phone or not media_id:
        return jsonify({"error": "Missing phone or media_id"}), 400
    db = SessionWhatsApp()
    try:
        result = send_document(phone, media_id=media_id, filename=filename, caption=caption)
        if result.get("error"):
            return jsonify({"error": result["error"]}), 500
        msg_id = result.get("messages", [{}])[0].get("id") if "messages" in result else None
        
        log_text = f"[📄 Document] {local_url}\n{caption}" if caption else f"[📄 Document] {local_url}"
        _log_outbound(db, phone, log_text, msg_id)
        
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


# ─────────────────────────────────────────────
#  SEND AUDIO
# ─────────────────────────────────────────────
@dashboard_bp.route("/api/send_audio", methods=["POST"])
def send_audio_api():
    err = _auth_check()
    if err: return err
    data     = request.get_json()
    phone    = data.get("phone")
    media_id = data.get("media_id")
    local_url = data.get("local_url", "")
    if not phone or not media_id:
        return jsonify({"error": "Missing phone or media_id"}), 400
    db = SessionWhatsApp()
    try:
        result = send_audio(phone, media_id=media_id)
        if result.get("error"):
            return jsonify({"error": result["error"]}), 500
        msg_id = result.get("messages", [{}])[0].get("id") if "messages" in result else None
        
        _log_outbound(db, phone, f"[🎙️ Audio] {local_url}", msg_id)
        
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


# ─────────────────────────────────────────────
#  SEND STICKER
# ─────────────────────────────────────────────
@dashboard_bp.route("/api/send_sticker", methods=["POST"])
def send_sticker_api():
    err = _auth_check()
    if err: return err
    data     = request.get_json()
    phone    = data.get("phone")
    media_id = data.get("media_id")
    if not phone or not media_id:
        return jsonify({"error": "Missing phone or media_id"}), 400
    db = SessionWhatsApp()
    try:
        result = send_sticker(phone, media_id=media_id)
        if result.get("error"):
            return jsonify({"error": result["error"]}), 500
        msg_id = result.get("messages", [{}])[0].get("id") if "messages" in result else None
        _log_outbound(db, phone, "[😊 Sticker]", msg_id)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


# ─────────────────────────────────────────────
#  SEND LOCATION
# ─────────────────────────────────────────────
@dashboard_bp.route("/api/send_location", methods=["POST"])
def send_location_api():
    err = _auth_check()
    if err: return err
    data    = request.get_json()
    phone   = data.get("phone")
    lat     = data.get("latitude")
    lon     = data.get("longitude")
    name    = data.get("name", "").strip()
    address = data.get("address", "").strip()
    if not phone or lat is None or lon is None:
        return jsonify({"error": "Missing phone, latitude, or longitude"}), 400
    db = SessionWhatsApp()
    try:
        result = send_location(phone, lat, lon, name, address)
        if result.get("error"):
            return jsonify({"error": result["error"]}), 500
        msg_id = result.get("messages", [{}])[0].get("id") if "messages" in result else None
        _log_outbound(db, phone, f"[📍 Location: {name or f'{lat},{lon}'}]", msg_id)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


# ─────────────────────────────────────────────
#  SEND CATALOG
# ─────────────────────────────────────────────
@dashboard_bp.route("/api/send_catalog", methods=["POST"])
def send_catalog_api():
    err = _auth_check()
    if err: return err
    data      = request.get_json()
    phone     = data.get("phone")
    body_text = data.get("body", "Browse our catalog below 🛍️").strip()
    thumb_id  = data.get("thumbnail_product_id") or None
    if not phone:
        return jsonify({"error": "Missing phone"}), 400
    db = SessionWhatsApp()
    try:
        result = send_catalog(phone, body_text, thumb_id)
        if result.get("error"):
            return jsonify({"error": result["error"]}), 500
        msg_id = result.get("messages", [{}])[0].get("id") if "messages" in result else None
        _log_outbound(db, phone, "[🛍️ Catalog Sent]", msg_id)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


# ─────────────────────────────────────────────
#  SEND QUICK REPLY
# ─────────────────────────────────────────────
@dashboard_bp.route("/api/send_quick_reply", methods=["POST"])
def send_quick_reply_api():
    err = _auth_check()
    if err: return err
    data    = request.get_json()
    phone   = data.get("phone")
    text    = data.get("text", "").strip()
    buttons = data.get("buttons", {})
    if not phone or not text or not buttons:
        return jsonify({"error": "Missing phone, text, or buttons"}), 400
    if len(buttons) > 3:
        return jsonify({"error": "Maximum 3 buttons allowed"}), 400
    db = SessionWhatsApp()
    try:
        result = send_interactive_buttons(phone, text, buttons)
        if result.get("error"):
            return jsonify({"error": result["error"]}), 500
        msg_id = result.get("messages", [{}])[0].get("id") if "messages" in result else None
        _log_outbound(db, phone, f"[⚡ Quick Reply: {text[:40]}]", msg_id)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


# ─────────────────────────────────────────────
#  SEND INTERACTIVE MENU
# ─────────────────────────────────────────────
@dashboard_bp.route("/api/send_menu", methods=["POST"])
def send_menu_api():
    err = _auth_check()
    if err: return err
    data  = request.get_json()
    phone = data.get("phone")
    if not phone:
        return jsonify({"error": "Missing phone"}), 400
    db = SessionWhatsApp()
    try:
        result = send_jaspers_menu(phone)
        if result.get("error"):
            return jsonify({"error": result["error"]}), 500
        msg_id = result.get("messages", [{}])[0].get("id") if "messages" in result else None
        _log_outbound(db, phone, "[📋 Interactive Menu Sent]", msg_id)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


# ─────────────────────────────────────────────
#  SEND ORDER BOOKING
# ─────────────────────────────────────────────
@dashboard_bp.route("/api/send_order_booking", methods=["POST"])
def send_order_booking_api():
    err = _auth_check()
    if err: return err
    data  = request.get_json()
    phone = data.get("phone")
    if not phone:
        return jsonify({"error": "Missing phone"}), 400
    db = SessionWhatsApp()
    try:
        result = send_interactive_buttons(
            phone=phone,
            text="🛒 *Ready to place your order?*\nTap below to browse our menu or proceed directly to checkout.",
            buttons={"show_menu": "Browse Menu", "cart_checkout": "Checkout Now"}
        )
        if result.get("error"):
            return jsonify({"error": result["error"]}), 500
        msg_id = result.get("messages", [{}])[0].get("id") if "messages" in result else None
        _log_outbound(db, phone, "[🛒 Order Booking Prompt Sent]", msg_id)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

# ─────────────────────────────────────────────────────────────
#  INTERACTIVE MESSAGE  (all 8 types via single endpoint)
# ─────────────────────────────────────────────────────────────
@dashboard_bp.route("/api/send_interactive_msg", methods=["POST"])
def send_interactive_msg_api():
    err = _auth_check()
    if err: return err

    data  = request.get_json()
    phone = data.get("phone")
    itype = data.get("itype")
    if not phone or not itype:
        return jsonify({"error": "Missing phone or itype"}), 400

    db = SessionWhatsApp()
    try:
        result = None

        if itype == "list":
            body        = data.get("body", "").strip()
            button_text = data.get("button_text", "See Options").strip()
            header      = data.get("header", "").strip()
            footer      = data.get("footer", "").strip()
            sections    = data.get("sections", [])
            if not body:
                return jsonify({"error": "Body text is required"}), 400
            if not sections:
                return jsonify({"error": "At least one section with rows is required"}), 400
            result = send_list_message(phone, body, button_text, sections, header, footer)

        elif itype == "button":
            body    = data.get("body", "").strip()
            header  = data.get("header", "").strip()
            footer  = data.get("footer", "").strip()
            buttons = data.get("buttons", [])
            if not body:
                return jsonify({"error": "Body text is required"}), 400
            if not buttons:
                return jsonify({"error": "At least 1 button is required (max 3)"}), 400
            result = send_reply_buttons(phone, body, buttons[:3], header, footer)

        elif itype == "product":
            catalog_id = data.get("catalog_id", "").strip()
            product_id = data.get("product_retailer_id", "").strip()
            body       = data.get("body", "").strip()
            footer     = data.get("footer", "").strip()
            if not catalog_id or not product_id:
                return jsonify({"error": "Catalog ID and Product Retailer ID are required"}), 400
            result = send_single_product(phone, catalog_id, product_id, body, footer)

        elif itype == "product_list":
            catalog_id = data.get("catalog_id", "").strip()
            header     = data.get("header", "").strip()
            body       = data.get("body", "").strip()
            footer     = data.get("footer", "").strip()
            sections   = data.get("sections", [])
            if not catalog_id or not header or not body:
                return jsonify({"error": "Catalog ID, header, and body are required"}), 400
            if not sections:
                return jsonify({"error": "At least one product section is required"}), 400
            result = send_multi_product(phone, catalog_id, header, body, sections, footer)

        elif itype == "catalog_message":
            body     = data.get("body", "Browse our catalog below 🛍️").strip()
            thumb_id = data.get("thumbnail_product_retailer_id", "").strip()
            result   = send_catalog(phone, body, thumb_id or None)

        elif itype == "location_request_message":
            body   = data.get("body", "Please share your location.").strip()
            result = send_location_request(phone, body)

        elif itype == "address_message":
            body         = data.get("body", "").strip()
            country_code = data.get("country_code", "").strip().upper()
            if not body or not country_code:
                return jsonify({"error": "Body and country code are required"}), 400
            result = send_address_message(phone, country_code, body)

        elif itype == "flow":
            flow_id     = data.get("flow_id", "").strip()
            flow_token  = data.get("flow_token", "unused").strip()
            cta_text    = data.get("cta_text", "Open").strip()
            body        = data.get("body", "").strip()
            header      = data.get("header", "").strip()
            footer      = data.get("footer", "").strip()
            flow_action = data.get("flow_action", "navigate")
            screen      = data.get("screen", "").strip()
            flow_data   = data.get("flow_data") # optional dict
            if not flow_id or not body:
                return jsonify({"error": "Flow ID and body text are required"}), 400
            result = send_flow(phone, flow_id, flow_token, cta_text, body, header, footer, flow_action, screen, flow_data)

        else:
            return jsonify({"error": f"Unknown interactive type: {itype}"}), 400

        if result and result.get("error"):
            raw = result["error"]
            msg = raw.get("message", str(raw)) if isinstance(raw, dict) else str(raw)
            return jsonify({"error": msg}), 500

        # Format the outbound log for the chat history
        type_display = itype.replace("_", " ").title()
        if itype == "button":
            type_display = "Reply Button"
            
        log_text = f"{type_display}: {body}"
            
        msg_id = result.get("messages", [{}])[0].get("id") if result and "messages" in result else None
        _log_outbound(db, phone, log_text, msg_id)
        return jsonify({"status": "success"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────
#  INTERACTIVE TEMPLATES
# ─────────────────────────────────────────────────────────────
@dashboard_bp.route("/api/interactive_templates", methods=["GET"])
def get_templates_api():
    err = _auth_check()
    if err: return err

    db = SessionWhatsApp()
    try:
        templates = db.query(InteractiveTemplate).order_by(InteractiveTemplate.created_at.desc()).all()
        res = []
        for t in templates:
            res.append({
                "id": t.id,
                "name": t.name,
                "itype": t.itype,
                "payload": json.loads(t.payload_json)
            })
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@dashboard_bp.route("/api/interactive_templates", methods=["POST"])
def save_template_api():
    err = _auth_check()
    if err: return err

    data = request.get_json()
    name = data.get("name")
    itype = data.get("itype")
    payload = data.get("payload")

    if not name or not itype or not payload:
        return jsonify({"error": "Missing name, itype, or payload"}), 400

    db = SessionWhatsApp()
    try:
        t = InteractiveTemplate(
            name=name,
            itype=itype,
            payload_json=json.dumps(payload)
        )
        db.add(t)
        db.commit()
        return jsonify({"status": "success", "id": t.id})
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@dashboard_bp.route("/api/interactive_templates/<int:t_id>", methods=["PUT", "DELETE"])
def update_delete_template_api(t_id):
    err = _auth_check()
    if err: return err

    db = SessionWhatsApp()
    try:
        t = db.query(InteractiveTemplate).filter(InteractiveTemplate.id == t_id).first()
        if not t:
            return jsonify({"error": "Template not found"}), 404

        if request.method == "DELETE":
            db.delete(t)
            db.commit()
            return jsonify({"status": "success"})
        
        elif request.method == "PUT":
            data = request.get_json()
            if "name" in data: t.name = data["name"]
            if "payload" in data: t.payload_json = json.dumps(data["payload"])
            db.commit()
            return jsonify({"status": "success"})

    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()
# ─────────────────────────────────────────────
#  CONTACTS API
# ─────────────────────────────────────────────
@dashboard_bp.route("/api/contacts", methods=["GET"])
def get_contacts_api():
    err = _auth_check()
    if err: return err
    db = SessionWhatsApp()
    try:
        from models import Contact
        contacts = db.query(Contact).order_by(Contact.name.asc()).all()
        return jsonify([{"id": c.id, "name": c.name, "phone": c.phone} for c in contacts])
    finally:
        db.close()

@dashboard_bp.route("/api/contacts", methods=["POST"])
def add_contact_api():
    err = _auth_check()
    if err: return err
    data = request.get_json()
    name = data.get("name", "").strip()
    phone = data.get("phone", "").strip()
    if not name or not phone:
        return jsonify({"error": "Name and phone required"}), 400
    
    db = SessionWhatsApp()
    try:
        from models import Contact
        existing = db.query(Contact).filter(Contact.phone == phone).first()
        if existing:
            existing.name = name
        else:
            db.add(Contact(name=name, phone=phone))
        db.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@dashboard_bp.route("/api/contacts/<int:cid>", methods=["PUT"])
def edit_contact_api(cid):
    err = _auth_check()
    if err: return err
    data = request.get_json()
    name = data.get("name", "").strip()
    phone = data.get("phone", "").strip()
    if not name or not phone:
        return jsonify({"error": "Name and phone required"}), 400
    
    db = SessionWhatsApp()
    try:
        from models import Contact
        c = db.query(Contact).get(cid)
        if c:
            c.name = name
            c.phone = phone
            db.commit()
            return jsonify({"status": "success"})
        return jsonify({"error": "Contact not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@dashboard_bp.route("/api/contacts/<int:cid>", methods=["DELETE"])
def delete_contact_api(cid):
    err = _auth_check()
    if err: return err
    db = SessionWhatsApp()
    try:
        from models import Contact
        c = db.query(Contact).get(cid)
        if c:
            db.delete(c)
            db.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@dashboard_bp.route("/api/contacts/upload_vcf", methods=["POST"])
def upload_vcf_api():
    err = _auth_check()
    if err: return err
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files["file"]
    if not file or file.filename == "":
        return jsonify({"error": "No file selected"}), 400
    
    try:
        content = file.read().decode("utf-8", errors="ignore")
        db = SessionWhatsApp()
        from models import Contact
        
        # Simple VCF parser
        added_count = 0
        current_name = None
        current_phone = None
        
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("BEGIN:VCARD"):
                current_name = None
                current_phone = None
            elif line.startswith("FN:"):
                current_name = line[3:].strip()
            elif line.startswith("TEL;") or line.startswith("TEL:"):
                # Extract number, e.g. TEL;TYPE=CELL:+1234567890 -> +1234567890
                parts = line.split(":")
                if len(parts) >= 2:
                    current_phone = parts[-1].strip()
            elif line.startswith("END:VCARD"):
                if current_name and current_phone:
                    # Clean phone
                    clean_phone = "".join(c for c in current_phone if c.isdigit() or c == "+")
                    existing = db.query(Contact).filter(Contact.phone == clean_phone).first()
                    if not existing:
                        db.add(Contact(name=current_name, phone=clean_phone))
                        added_count += 1
        db.commit()
        db.close()
        return jsonify({"status": "success", "added": added_count})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@dashboard_bp.route("/api/fire_conversion", methods=["POST"])
def fire_conversion_api():
    err = _auth_check()
    if err: return err

    data = request.get_json()
    phone = data.get("phone")
    if not phone:
        return jsonify({"error": "Missing phone"}), 400

    db_saas = SessionSaaS()
    try:
        lead = db_saas.query(Lead).filter(Lead.phone == phone).first()
        if not lead or not lead.click_id:
            return jsonify({"error": "No Click-to-WhatsApp referral ID (ctwa_clid) found for this user."}), 404

        # Fire conversion
        result = send_event(
            phone=phone,
            ctwa_clid=lead.click_id,
            value=100.0,
            currency="USD",
            page_id=None # Optional for some Meta setups, if required user can update
        )

        lead.status = "sent"
        lead.meta_response = json.dumps(result)
        db_saas.commit()

        if result.get("error"):
            err_msg = result["error"].get("message", str(result["error"]))
            return jsonify({"error": err_msg}), 500

        return jsonify({"status": "success", "meta_response": result})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db_saas.close()

# ─────────────────────────────────────────────
#  PRODUCTS API
# ─────────────────────────────────────────────
import os
from werkzeug.utils import secure_filename
import uuid as _uuid

PRODUCT_IMAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'product_images')

@dashboard_bp.route('/api/products', methods=['GET'])
def get_products_api():
    err = _auth_check()
    if err: return err
    db = SessionWhatsApp()
    try:
        from models import Product
        products = db.query(Product).order_by(Product.created_at.desc()).all()
        return jsonify([{'id': p.id, 'name': p.name, 'image_path': p.image_path, 'weight': p.weight, 'price': p.price, 'created_at': p.created_at.isoformat() if p.created_at else None} for p in products])
    finally:
        db.close()

@dashboard_bp.route('/api/products', methods=['POST'])
def create_product_api():
    err = _auth_check()
    if err: return err
    data = request.get_json()
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': 'Product name is required'}), 400
    db = SessionWhatsApp()
    try:
        from models import Product
        p = Product(name=name, weight=data.get('weight',''), price=float(data.get('price',0) or 0), image_path=data.get('image_path',''))
        db.add(p)
        db.commit()
        return jsonify({'status': 'success', 'id': p.id})
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

@dashboard_bp.route('/api/products/<int:pid>', methods=['PUT'])
def update_product_api(pid):
    err = _auth_check()
    if err: return err
    data = request.get_json()
    db = SessionWhatsApp()
    try:
        from models import Product
        p = db.query(Product).get(pid)
        if not p: return jsonify({'error': 'Not found'}), 404
        if 'name' in data: p.name = data['name']
        if 'weight' in data: p.weight = data['weight']
        if 'price' in data: p.price = float(data['price'] or 0)
        if 'image_path' in data: p.image_path = data['image_path']
        db.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

@dashboard_bp.route('/api/products/<int:pid>', methods=['DELETE'])
def delete_product_api(pid):
    err = _auth_check()
    if err: return err
    db = SessionWhatsApp()
    try:
        from models import Product
        p = db.query(Product).get(pid)
        if p:
            db.delete(p)
            db.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

@dashboard_bp.route('/api/products/upload_image', methods=['POST'])
def upload_product_image_api():
    err = _auth_check()
    if err: return err
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    try:
        os.makedirs(PRODUCT_IMAGE_DIR, exist_ok=True)
        filename = secure_filename(file.filename)
        ext = filename.rsplit('.', 1)[-1] if '.' in filename else 'jpg'
        unique_name = f'{_uuid.uuid4().hex}.{ext}'
        save_path = os.path.join(PRODUCT_IMAGE_DIR, unique_name)
        file.save(save_path)
        url = f'/static/product_images/{unique_name}'
        return jsonify({'url': url})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ─────────────────────────────────────────────
#  ORDERS API
# ─────────────────────────────────────────────
@dashboard_bp.route('/api/orders', methods=['GET'])
def get_orders_api():
    err = _auth_check()
    if err: return err
    db = SessionWhatsApp()
    try:
        from models import Order, OrderItem
        orders = db.query(Order).order_by(Order.created_at.desc()).all()
        result = []
        for o in orders:
            items = db.query(OrderItem).filter(OrderItem.order_id == o.id).all()
            items_data = [{'id': i.id, 'product_id': i.product_id, 'product_name': i.product_name, 'product_price': i.product_price, 'quantity': i.quantity} for i in items]
            subtotal = sum(i.product_price * i.quantity for i in items)
            result.append({'id': o.id, 'customer_name': o.customer_name, 'phone': o.phone, 'address': o.address, 'location_link': o.location_link, 'delivery_date': o.delivery_date, 'delivery_charge': o.delivery_charge, 'status': o.status, 'notes': o.notes, 'items': items_data, 'subtotal': subtotal, 'total': subtotal + (o.delivery_charge or 0), 'created_at': o.created_at.isoformat() if o.created_at else None})
        active = [r for r in result if r['status'] != 'complete']
        done = [r for r in result if r['status'] == 'complete']
        return jsonify(active + done)
    finally:
        db.close()

@dashboard_bp.route('/api/orders', methods=['POST'])
def create_order_api():
    err = _auth_check()
    if err: return err
    data = request.get_json()
    db = SessionWhatsApp()
    try:
        from models import Order, OrderItem
        o = Order(customer_name=data.get('customer_name','').strip(), phone=data.get('phone','').strip(), address=data.get('address','').strip(), location_link=data.get('location_link','').strip(), delivery_date=data.get('delivery_date','').strip(), delivery_charge=float(data.get('delivery_charge',0) or 0), status='new', notes=data.get('notes','').strip())
        db.add(o)
        db.flush()
        for item in data.get('items', []):
            oi = OrderItem(order_id=o.id, product_id=item.get('product_id'), product_name=item.get('product_name',''), product_price=float(item.get('product_price',0) or 0), quantity=int(item.get('quantity',1)))
            db.add(oi)
        db.commit()
        return jsonify({'status': 'success', 'id': o.id})
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

@dashboard_bp.route('/api/orders/<int:oid>', methods=['PUT'])
def update_order_api(oid):
    err = _auth_check()
    if err: return err
    data = request.get_json()
    db = SessionWhatsApp()
    try:
        from models import Order
        o = db.query(Order).get(oid)
        if not o: return jsonify({'error': 'Not found'}), 404
        if 'status' in data: o.status = data['status']
        if 'delivery_date' in data: o.delivery_date = data['delivery_date']
        if 'delivery_charge' in data: o.delivery_charge = float(data['delivery_charge'] or 0)
        if 'notes' in data: o.notes = data['notes']
        db.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

@dashboard_bp.route('/api/orders/<int:oid>', methods=['DELETE'])
def delete_order_api(oid):
    err = _auth_check()
    if err: return err
    db = SessionWhatsApp()
    try:
        from models import Order, OrderItem
        db.query(OrderItem).filter(OrderItem.order_id == oid).delete()
        o = db.query(Order).get(oid)
        if o: db.delete(o)
        db.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

@dashboard_bp.route('/api/orders/packing', methods=['GET'])
def get_packing_api():
    err = _auth_check()
    if err: return err
    ids_str = request.args.get('ids', '')
    if not ids_str:
        return jsonify([])
    ids = [int(x) for x in ids_str.split(',') if x.strip().isdigit()]
    db = SessionWhatsApp()
    try:
        from models import Order, OrderItem
        result = []
        for oid in ids:
            o = db.query(Order).get(oid)
            if not o: continue
            items = db.query(OrderItem).filter(OrderItem.order_id == o.id).all()
            items_data = [{'product_name': i.product_name, 'product_price': i.product_price, 'quantity': i.quantity} for i in items]
            subtotal = sum(i.product_price * i.quantity for i in items)
            result.append({'id': o.id, 'customer_name': o.customer_name, 'phone': o.phone, 'address': o.address, 'location_link': o.location_link, 'delivery_date': o.delivery_date, 'delivery_charge': o.delivery_charge, 'status': o.status, 'items': items_data, 'subtotal': subtotal, 'total': subtotal + (o.delivery_charge or 0)})
        return jsonify(result)
    finally:
        db.close()

from flask import send_from_directory as _sfd
@dashboard_bp.route('/static/product_images/<path:filename>')
def serve_product_image(filename):
    return _sfd(PRODUCT_IMAGE_DIR, filename)

