import requests

from config_manager import get_config

# ─────────────────────────────────────────────
#  CREDENTIALS
# ─────────────────────────────────────────────
ACCESS_TOKEN     = get_config("WHATSAPP_TOKEN", "EAAQ02uTY1vwBRjkSM8CZCvGsOWZCESWKysXZByO1bDZA6ed1ZBWAwhSZCGfBwR3wP2zw4VLsMtlwEAzc3YroXX6rIMVpAgs9fiuR1E8uQyn8mOKdDMcw9Ir7T1GQIyTkfBmUM2Hr4YUQ61orY23WOgjfjWTyqpi8fFthoAlkLoA4A7ZCM7FT3IGIwGdDX3ADgZDZD")
PHONE_NUMBER_ID  = get_config("PHONE_NUMBER_ID", "1153175711206489")
GRAPH_API_VERSION = "v25.0"

MESSAGES_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{PHONE_NUMBER_ID}/messages"
MEDIA_URL    = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{PHONE_NUMBER_ID}/media"

AUTH_HEADERS = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
JSON_HEADERS = {**AUTH_HEADERS, "Content-Type": "application/json"}



def _post_json(payload):
    """POST a JSON payload to the WhatsApp Messages endpoint."""
    response = requests.post(MESSAGES_URL, headers=JSON_HEADERS, json=payload)
    return response.json()


# ─────────────────────────────────────────────
#  MEDIA UPLOAD  ← THE KEY FUNCTION
#  Uploads a file to Meta's servers and returns
#  a media_id that can be used in send calls.
# ─────────────────────────────────────────────
def upload_media(file_bytes, mime_type, filename="file"):
    """
    Uploads a media file to the WhatsApp Cloud API media endpoint.
    Returns the full API response dict which contains 'id' (the media_id).
    
    Args:
        file_bytes: raw bytes of the file
        mime_type:  MIME type string, e.g. 'image/jpeg'
        filename:   original filename for the upload
    """
    # multipart/form-data — do NOT set Content-Type manually; requests adds boundary
    response = requests.post(
        MEDIA_URL,
        headers=AUTH_HEADERS,           # only auth header, no Content-Type
        files={
            "file": (filename, file_bytes, mime_type),
        },
        data={
            "messaging_product": "whatsapp",
            "type": mime_type,
        }
    )
    return response.json()


# ─────────────────────────────────────────────
#  MEDIA DOWNLOAD
# ─────────────────────────────────────────────
def download_media(media_id):
    """
    Fetches the media URL and downloads the raw bytes.
    Returns (bytes, mime_type) or (None, None) if failed.
    """
    try:
        url_res = requests.get(f"https://graph.facebook.com/{GRAPH_API_VERSION}/{media_id}", headers=AUTH_HEADERS)
        data = url_res.json()
        if "url" not in data:
            return None, None
        
        media_url = data["url"]
        mime_type = data.get("mime_type", "")
        
        # Download the actual file
        img_res = requests.get(media_url, headers=AUTH_HEADERS)
        if img_res.status_code == 200:
            return img_res.content, mime_type
        return None, None
    except Exception as e:
        print(f"Media download failed: {e}")
        return None, None


# ─────────────────────────────────────────────
#  TEXT
# ─────────────────────────────────────────────
def send_message(phone, text):
    """Sends a plain text message."""
    return _post_json({
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {"body": text, "preview_url": True}
    })


# ─────────────────────────────────────────────
#  IMAGE   (media_id  OR  public URL)
# ─────────────────────────────────────────────
def send_image(phone, media_id=None, url=None, caption=""):
    """Sends an image using a media_id (preferred) or a public URL."""
    img = {}
    if media_id:
        img["id"] = media_id
    elif url:
        img["link"] = url
    else:
        raise ValueError("Either media_id or url must be provided")
    if caption:
        img["caption"] = caption
    return _post_json({
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "image",
        "image": img
    })


# ─────────────────────────────────────────────
#  VIDEO   (media_id  OR  public URL)
# ─────────────────────────────────────────────
def send_video(phone, media_id=None, url=None, caption=""):
    """Sends a video using a media_id (preferred) or a public URL."""
    vid = {}
    if media_id:
        vid["id"] = media_id
    elif url:
        vid["link"] = url
    else:
        raise ValueError("Either media_id or url must be provided")
    if caption:
        vid["caption"] = caption
    return _post_json({
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "video",
        "video": vid
    })


# ─────────────────────────────────────────────
#  DOCUMENT   (media_id  OR  public URL)
# ─────────────────────────────────────────────
def send_document(phone, media_id=None, url=None, filename="document", caption=""):
    """Sends a document using a media_id (preferred) or a public URL."""
    doc = {"filename": filename}
    if media_id:
        doc["id"] = media_id
    elif url:
        doc["link"] = url
    else:
        raise ValueError("Either media_id or url must be provided")
    if caption:
        doc["caption"] = caption
    return _post_json({
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "document",
        "document": doc
    })


# ─────────────────────────────────────────────
#  AUDIO   (media_id  OR  public URL)
# ─────────────────────────────────────────────
def send_audio(phone, media_id=None, url=None):
    """Sends audio using a media_id (preferred) or a public URL."""
    aud = {}
    if media_id:
        aud["id"] = media_id
    elif url:
        aud["link"] = url
    else:
        raise ValueError("Either media_id or url must be provided")
    return _post_json({
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "audio",
        "audio": aud
    })


# ─────────────────────────────────────────────
#  STICKER   (media_id  OR  public URL)
# ─────────────────────────────────────────────
def send_sticker(phone, media_id=None, url=None):
    """Sends a sticker (WebP) using a media_id or public URL."""
    stk = {}
    if media_id:
        stk["id"] = media_id
    elif url:
        stk["link"] = url
    else:
        raise ValueError("Either media_id or url must be provided")
    return _post_json({
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "sticker",
        "sticker": stk
    })


# ─────────────────────────────────────────────
#  LOCATION
# ─────────────────────────────────────────────
def send_location(phone, latitude, longitude, name="", address=""):
    """Sends a location pin with coordinates and optional name/address."""
    loc = {"latitude": float(latitude), "longitude": float(longitude)}
    if name:    loc["name"]    = name
    if address: loc["address"] = address
    return _post_json({
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "location",
        "location": loc
    })


# ─────────────────────────────────────────────
#  CATALOG
# ─────────────────────────────────────────────
def send_catalog(phone, body_text="Browse our catalog below 🛍️", thumbnail_product_retailer_id=None):
    """Sends a WhatsApp Business catalog interactive message."""
    action = {"name": "catalog_message"}
    if thumbnail_product_retailer_id:
        action["parameters"] = {"thumbnail_product_retailer_id": thumbnail_product_retailer_id}
    return _post_json({
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "interactive",
        "interactive": {
            "type": "catalog_message",
            "body": {"text": body_text},
            "action": action
        }
    })


# ─────────────────────────────────────────────
#  INTERACTIVE: JASPER'S MENU LIST
# ─────────────────────────────────────────────
def send_jaspers_menu(phone):
    """Sends Jasper's Market interactive aisle catalog list."""
    return _post_json({
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {"type": "text", "text": "Jasper's Market"},
            "body":   {"text": "Welcome to Jasper's Market! 🍏\nSelect an option below to browse our inventory items:"},
            "footer": {"text": "Fresh groceries daily"},
            "action": {
                "button": "View Aisles",
                "sections": [
                    {
                        "title": "Fresh Produce",
                        "rows": [
                            {"id": "item_apples_2.99",  "title": "Organic Apples",  "description": "$2.99 / lb"},
                            {"id": "item_bananas_0.59", "title": "Fresh Bananas",   "description": "$0.59 / lb"}
                        ]
                    },
                    {
                        "title": "Bakery & Counter",
                        "rows": [
                            {"id": "item_bread_4.50", "title": "Sourdough Bread", "description": "$4.50 / loaf"}
                        ]
                    },
                    {
                        "title": "Shopping Cart Management",
                        "rows": [
                            {"id": "cart_checkout", "title": "Complete Order", "description": "Review and purchase"},
                            {"id": "cart_clear",    "title": "Empty Cart",     "description": "Clear all selections"}
                        ]
                    }
                ]
            }
        }
    })


# ─────────────────────────────────────────────
#  INTERACTIVE: QUICK REPLY BUTTONS (max 3)
# ─────────────────────────────────────────────
def send_interactive_buttons(phone, text, buttons):
    """
    Sends interactive quick-reply buttons.
    buttons: dict of {id: title}  — max 3
    """
    button_actions = [
        {"type": "reply", "reply": {"id": str(k), "title": str(v)}}
        for k, v in buttons.items()
    ]
    return _post_json({
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": text},
            "action": {"buttons": button_actions}
        }
    })


# ─────────────────────────────────────────────
#  INTERACTIVE: LIST MESSAGE (custom)
# ─────────────────────────────────────────────
def send_list_message(phone, body, button_text, sections, header="", footer=""):
    """
    Sends a custom list message with sections and rows.

    sections format:
    [
        {
            "title": "Section Name",
            "rows": [
                {"id": "row_id", "title": "Row Title", "description": "optional"},
                ...
            ]
        },
        ...
    ]
    """
    interactive = {
        "type": "list",
        "body": {"text": body},
        "action": {"button": button_text, "sections": sections}
    }
    if header:
        interactive["header"] = {"type": "text", "text": header}
    if footer:
        interactive["footer"] = {"text": footer}
    return _post_json({
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "interactive",
        "interactive": interactive
    })


# ─────────────────────────────────────────────
#  INTERACTIVE: REPLY BUTTONS (custom with header/footer)
# ─────────────────────────────────────────────
def send_reply_buttons(phone, body, buttons, header="", footer=""):
    """
    Sends up to 3 reply buttons with optional header and footer.
    buttons: list of {"id": "...", "title": "..."} — max 3
    """
    btn_objs = [{"type": "reply", "reply": {"id": str(b["id"]), "title": str(b["title"])}} for b in buttons[:3]]
    interactive = {
        "type": "button",
        "body": {"text": body},
        "action": {"buttons": btn_objs}
    }
    if header:
        interactive["header"] = {"type": "text", "text": header}
    if footer:
        interactive["footer"] = {"text": footer}
    return _post_json({
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "interactive",
        "interactive": interactive
    })


# ─────────────────────────────────────────────
#  INTERACTIVE: SINGLE PRODUCT
# ─────────────────────────────────────────────
def send_single_product(phone, catalog_id, product_retailer_id, body="", footer=""):
    """Sends a single product card from your Meta Commerce Catalog."""
    interactive = {
        "type": "product",
        "action": {
            "catalog_id": str(catalog_id),
            "product_retailer_id": str(product_retailer_id)
        }
    }
    if body:
        interactive["body"] = {"text": body}
    if footer:
        interactive["footer"] = {"text": footer}
    return _post_json({
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "interactive",
        "interactive": interactive
    })


# ─────────────────────────────────────────────
#  INTERACTIVE: MULTI-PRODUCT
# ─────────────────────────────────────────────
def send_multi_product(phone, catalog_id, header, body, sections, footer=""):
    """
    Sends a multi-product list (up to 30 products across sections).

    sections format:
    [
        {
            "title": "Section Name",
            "product_items": [
                {"product_retailer_id": "sku_123"},
                ...
            ]
        }
    ]
    """
    interactive = {
        "type": "product_list",
        "header": {"type": "text", "text": header},
        "body": {"text": body},
        "action": {
            "catalog_id": str(catalog_id),
            "sections": sections
        }
    }
    if footer:
        interactive["footer"] = {"text": footer}
    return _post_json({
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "interactive",
        "interactive": interactive
    })


# ─────────────────────────────────────────────
#  INTERACTIVE: LOCATION REQUEST
# ─────────────────────────────────────────────
def send_location_request(phone, body):
    """
    Sends a native location-request prompt.
    The user taps a button to share their location back.
    """
    return _post_json({
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "interactive",
        "interactive": {
            "type": "location_request_message",
            "body": {"text": body},
            "action": {"name": "send_location"}
        }
    })


# ─────────────────────────────────────────────
#  INTERACTIVE: ADDRESS MESSAGE
# ─────────────────────────────────────────────
def send_address_message(phone, country_code, body, values=None):
    """
    Sends an address-entry form (supported in IN and SG).
    country_code: ISO 3166-1 alpha-2, e.g. "IN", "SG"
    values: optional dict to pre-fill fields
    """
    params = {"country": country_code.upper()}
    if values:
        params["values"] = values
    return _post_json({
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "interactive",
        "interactive": {
            "type": "address_message",
            "body": {"text": body},
            "action": {
                "name": "address_message",
                "parameters": params
            }
        }
    })


# ─────────────────────────────────────────────
#  INTERACTIVE: WHATSAPP FLOWS
# ─────────────────────────────────────────────
def send_flow(phone, flow_id, flow_token, cta_text, body,
              header="", footer="", flow_action="navigate", screen="", flow_data=None):
    """
    Triggers a WhatsApp Flow inside the conversation.
    flow_action: "navigate" (go to a screen) or "data_exchange"
    screen: starting screen name (required when flow_action="navigate")
    flow_data: dict of default values to pre-fill the screen with
    """
    params = {
        "flow_message_version": "3",
        "flow_token": flow_token,
        "flow_id": str(flow_id),
        "flow_cta": cta_text,
        "flow_action": flow_action
    }
    
    if flow_action == "navigate" and screen:
        payload = {"screen": screen}
        if flow_data and isinstance(flow_data, dict):
            payload["data"] = flow_data
        params["flow_action_payload"] = payload

    interactive = {
        "type": "flow",
        "body": {"text": body},
        "action": {"name": "flow", "parameters": params}
    }
    if header:
        interactive["header"] = {"type": "text", "text": header}
    if footer:
        interactive["footer"] = {"text": footer}
        
    return _post_json({
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": phone,
        "type": "interactive",
        "interactive": interactive
    })

