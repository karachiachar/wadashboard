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
            if not flow_id or not body:
                return jsonify({"error": "Flow ID and body text are required"}), 400
            result = send_flow(phone, flow_id, flow_token, cta_text, body, header, footer, flow_action, screen)

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
            
        _log_outbound(db, phone, log_text)
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
