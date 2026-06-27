
# app.py
from flask import Flask
from database import engine_saas, engine_whatsapp, BaseSaaS, BaseWhatsApp
from routes.webhook import webhook_bp
from routes.dashboard import dashboard_bp
from config_manager import get_config

app = Flask(__name__)

# Essential for tracking logged-in states securely
app.secret_key = "CHANGE_THIS_TO_A_LONG_RANDOM_SECRET_KEY" 

# Set your dashboard access password here
app.config["DASHBOARD_PASSWORD"] = get_config("DASHBOARD_PASSWORD", "nadra@123")


# Allow media uploads up to 50 MB
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB

# Inside app.py (if applicable)
BaseSaaS.metadata.create_all(bind=engine_saas)
BaseWhatsApp.metadata.create_all(bind=engine_whatsapp)


app.register_blueprint(webhook_bp)
app.register_blueprint(dashboard_bp)

@app.route('/sw.js')
def serve_sw():
    return app.send_static_file('sw.js')

if __name__ == "__main__":
# app.py
from flask import Flask
from database import engine_saas, engine_whatsapp, BaseSaaS, BaseWhatsApp
from routes.webhook import webhook_bp
from routes.dashboard import dashboard_bp
from config_manager import get_config

app = Flask(__name__)

# Essential for tracking logged-in states securely
app.secret_key = "CHANGE_THIS_TO_A_LONG_RANDOM_SECRET_KEY" 

# Set your dashboard access password here
app.config["DASHBOARD_PASSWORD"] = get_config("DASHBOARD_PASSWORD", "nadra@123")


# Allow media uploads up to 50 MB
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB

# Inside app.py (if applicable)
BaseSaaS.metadata.create_all(bind=engine_saas)
BaseWhatsApp.metadata.create_all(bind=engine_whatsapp)


app.register_blueprint(webhook_bp)
app.register_blueprint(dashboard_bp)

@app.route('/sw.js')
def serve_sw():
    return app.send_static_file('sw.js')

if __name__ == "__main__":

    app.run(host="0.0.0.0", port=5000, debug=True)
