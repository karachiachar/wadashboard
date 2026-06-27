
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
