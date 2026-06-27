# models.py
from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from datetime import datetime
from database import BaseWhatsApp, BaseSaaS

class Lead(BaseSaaS):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True)
    phone = Column(String)
    click_id = Column(String)
    value = Column(Float)
    currency = Column(String)

    status = Column(String, default="pending")  # pending / sent / failed
    meta_response = Column(String)

    created_at = Column(DateTime, default=datetime.utcnow)


class Message(BaseWhatsApp):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    phone = Column(String(20))
    direction = Column(String(10))  # inbound / outbound
    message = Column(Text)
    timestamp = Column(String(50))
    message_id = Column(String(100))
    status = Column(String(20), default="sent")
    is_read = Column(Integer, default=0)


class InteractiveTemplate(BaseWhatsApp):
    __tablename__ = "interactive_templates"

    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    itype = Column(String(50))
    payload_json = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class Contact(BaseWhatsApp):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    phone = Column(String(20), unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class QuickReply(BaseWhatsApp):
    __tablename__ = "quick_replies"

    id = Column(Integer, primary_key=True)
    shortcut = Column(String(50), unique=True)
    title = Column(String(100))
    body = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class Product(BaseWhatsApp):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    name = Column(String(200))
    image_path = Column(String(500))
    weight = Column(String(50))
    price = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)


class Order(BaseWhatsApp):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    customer_name = Column(String(200))
    phone = Column(String(50))
    address = Column(Text)
    location_link = Column(String(500))
    delivery_date = Column(String(50))
    delivery_charge = Column(Float, default=0.0)
    status = Column(String(50), default="new")  # new / packed / delivered / complete
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class OrderItem(BaseWhatsApp):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer)
    product_id = Column(Integer)
    product_name = Column(String(200))
    product_price = Column(Float, default=0.0)
    quantity = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)