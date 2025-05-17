from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship

# Initialize SQLAlchemy with no app
db = SQLAlchemy()

class Server(db.Model):
    """Discord server settings"""
    __tablename__ = 'servers'
    
    id = db.Column(db.Integer, primary_key=True)
    discord_id = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100))
    auto_translate_enabled = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    channels = db.relationship('Channel', back_populates='server', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Server {self.name}>'

class Channel(db.Model):
    """Discord channel settings"""
    __tablename__ = 'channels'
    
    id = db.Column(db.Integer, primary_key=True)
    discord_id = db.Column(db.String(20), unique=True, nullable=False)
    server_id = db.Column(db.Integer, db.ForeignKey('servers.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(100))
    auto_translate_enabled = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    server = db.relationship('Server', back_populates='channels')
    
    def __repr__(self):
        return f'<Channel {self.name}>'

class User(db.Model):
    """Discord user settings"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    discord_id = db.Column(db.String(20), unique=True, nullable=False)
    username = db.Column(db.String(100))
    preferred_language = db.Column(db.String(10), default='en')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<User {self.username}>'

class TranslationLog(db.Model):
    """Logs of translations performed by the bot"""
    __tablename__ = 'translation_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.String(20))
    server_id = db.Column(db.String(20))
    channel_id = db.Column(db.String(20))
    user_id = db.Column(db.String(20))
    source_language = db.Column(db.String(10))
    target_language = db.Column(db.String(10))
    source_text = db.Column(db.Text)
    translated_text = db.Column(db.Text)
    translation_service = db.Column(db.String(20))  # google, libre, etc.
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<TranslationLog {self.id}>'

class BotSetting(db.Model):
    """General bot settings"""
    __tablename__ = 'bot_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<BotSetting {self.key}>'

class APIKey(db.Model):
    """API keys for translation services"""
    __tablename__ = 'api_keys'
    
    id = db.Column(db.Integer, primary_key=True)
    service = db.Column(db.String(50), unique=True, nullable=False)  # google, libre, etc.
    key = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<APIKey {self.service}>'