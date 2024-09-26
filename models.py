from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# SQLAlchemy instance is initialized in app.py and imported here
from app import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(128), unique=True, nullable=True)
    phone = db.Column(db.String(20), unique=True, nullable=True)
    otp = db.Column(db.String(6), nullable=True)  # Temporarily store OTP for login

class Item(db.Model):
    id = db.Column(db.String(5), primary_key=True)
    title = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    image = db.Column(db.String(120), nullable=False)  # This can store the main image
    reported = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    tracked_since = db.Column(db.DateTime, default=datetime.utcnow)
    reported_since = db.Column(db.DateTime, nullable=True)
    
    # Relationship with ItemImage (switch to eager-loading)
    images = db.relationship('ItemImage', backref='item', lazy='joined')


class ItemImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.String(5), db.ForeignKey('item.id'), nullable=False)
    filename = db.Column(db.String(120), nullable=False)

