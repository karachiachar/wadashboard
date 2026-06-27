import requests
import time

from config_manager import get_config

ACCESS_TOKEN = get_config("META_TOKEN", "EAAQ02uTY1vwBRa81SZC86tOnA2wQvVnDniCVt86NTuO2IhOxZBDahrZCEaVrG46AdYng0NR39CMYGWK0K2ZBCjSS4ZAFDnAyt3XUra1fFuTctUIlL7oCvk3nUzAI1uLmap4j7tjJtt52ZBwn2aeZACgsTW7jjxofBcuHUjjpCbjI8TsyejCKsqtnZAGS2ZB9EGCJMzf0S1Yc5PwZAYwPIRWxGMxNEOy4GkCygjNIE5HZADAKqyJVZCHHpuWXBZCnw85jr11IXGFhvFIZAqoHVCCH8mf66jZBa3N")
DATASET_ID = get_config("META_DATASET_ID", "1568141444274727")


def send_event(phone, ctwa_clid, value, currency, page_id, test_event_code=None):

    url = f"https://graph.facebook.com/v25.0/{DATASET_ID}/events"

    event = {
        "event_name": "Purchase",
        "event_time": int(time.time()),
        "action_source": "business_messaging",
        "messaging_channel": "whatsapp",
        "user_data": {
            "ctwa_clid": ctwa_clid,
            "page_id": page_id
        },
        "custom_data": {
            "currency": currency or "USD",
            "value": float(value or 0)
        }
    }

    payload = {
        "data": [event]
    }

    # only add if exists
    if test_event_code and test_event_code.strip():
        payload["test_event_code"] = test_event_code.strip()

    response = requests.post(
        url,
        params={"access_token": ACCESS_TOKEN},
        json=payload
    )

    return response.json()