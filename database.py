<<<<<<< HEAD
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# --- SaaS Database Setup ---
DATABASE_URL_SAAS = "sqlite:///saas.db"
engine_saas = create_engine(DATABASE_URL_SAAS, connect_args={"check_same_thread": False})
SessionSaaS = sessionmaker(bind=engine_saas)
BaseSaaS = declarative_base()

# --- WhatsApp Database Setup ---
DATABASE_URL_WHATSAPP = "sqlite:///whatsapp.db"
engine_whatsapp = create_engine(DATABASE_URL_WHATSAPP, connect_args={"check_same_thread": False})
SessionWhatsApp = sessionmaker(bind=engine_whatsapp)
BaseWhatsApp = declarative_base()
=======
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# --- SaaS Database Setup ---
DATABASE_URL_SAAS = "sqlite:///saas.db"
engine_saas = create_engine(DATABASE_URL_SAAS, connect_args={"check_same_thread": False})
SessionSaaS = sessionmaker(bind=engine_saas)
BaseSaaS = declarative_base()

# --- WhatsApp Database Setup ---
DATABASE_URL_WHATSAPP = "sqlite:///whatsapp.db"
engine_whatsapp = create_engine(DATABASE_URL_WHATSAPP, connect_args={"check_same_thread": False})
SessionWhatsApp = sessionmaker(bind=engine_whatsapp)
BaseWhatsApp = declarative_base()
>>>>>>> aed7e9e5d444501ed3d150681887b2334c720e52
