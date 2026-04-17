#!/usr/bin/env python3
"""
Telegram Information Lookup Bot - Group Only Mode
Hidden Admin Panel - Credits Add Working - FIXED
"""

import logging
import sqlite3
import asyncio
import os
import re
import json
import requests
import random
import string
from datetime import datetime
from typing import Dict, Optional, List, Union
import html

# ========== BANNER ==========
banner = """
\033[1;31m ██████╗ ███████╗████████╗██╗███╗   ██╗\033[0m  \033[1;34m ██████╗ ██████╗  ██████╗ ██╗   ██╗██████╗ \033[0m
\033[1;33m██╔═══██╗██╔════╝╚══██╔══╝██║████╗  ██║\033[0m  \033[1;35m██╔═══██╗██╔══██╗██╔═══██╗██║   ██║██╔══██╗\033[0m
\033[1;32m██║   ██║███████╗   ██║   ██║██╔██╗ ██║\033[0m  \033[1;36m██║   ██║██████╔╝██║   ██║██║   ██║██████╔╝\033[0m
\033[1;33m██║   ██║╚════██║   ██║   ██║██║╚██╗██║\033[0m  \033[1;34m██║   ██║██╔══██╗██║   ██║██║   ██║██╔═══╝ \033[0m
\033[1;31m╚██████╔╝███████║   ██║   ██║██║ ╚████║\033[0m  \033[1;35m╚██████╔╝██║  ██║╚██████╔╝╚██████╔╝██║     \033[0m
\033[1;32m ╚═════╝ ╚══════╝   ╚═╝   ╚═╝╚═╝  ╚═══╝\033[0m  \033[1;36m ╚═════╝ ╚═╝  ╚═╝ ╚═════╝  ╚═════╝ ╚═╝     \033[0m
\033[1;33m
🔴 YouTube: https://www.youtube.com/@aryanafridi00
💻 Developer: Aryan Afridi 
📡 GitHub: https://github.com/shahid2005a
\033[0m 
"""

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import (
        Application,
        CommandHandler,
        CallbackQueryHandler,
        MessageHandler,
        filters,
        ContextTypes,
    )
    from telegram.constants import ParseMode
except ImportError as e:
    print(f"❌ Error: {e}")
    print("Run: pip install python-telegram-bot")
    exit(1)

# Fix logging to reduce noise
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.WARNING  # Changed from INFO to WARNING to reduce logs
)
# Suppress httpx logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================
BOT_TOKEN = "1234567890"

# ADMIN ID - SIRF APNA ID DAALO (BAS EK NUMBER)
ADMIN_IDS = [1234567890]  # ← CHANGE THIS TO YOUR TELEGRAM ID

# UPI ID - APNA UPI ID DAALO
OWNER_UPI_ID = "1234567890"  # ← CHANGE THIS
OWNER_NAME = "Bot Aryan"

API_BASE_URL = "https://darkietech.site"
API_KEY = "Ayanafridi"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "lookup_bot.db")

AUTO_DELETE_TIME = 60
ALLOWED_GROUPS = []
DEFAULT_CREDITS = 5

SEARCH_COSTS = {
    "mobile": 1,
    "aadhaar": 1,
    "vehicle": 2,
    "family": 2,
    "upi": 1
}

CREDIT_PACKAGES = {10: 5, 25: 10, 50: 20, 100: 35, 200: 60, 500: 140}

user_states = {}
admin_sessions = {}
pending_orders = {}

# ==================== DATABASE ====================
class Database:
    def __init__(self, db_path=DB_PATH):
        try:
            self.conn = sqlite3.connect(db_path, check_same_thread=False)
            self.cursor = self.conn.cursor()
            self.create_tables()
        except Exception as e:
            logger.error(f"Database error: {e}")
            raise

    def create_tables(self):
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    credits INTEGER DEFAULT 5,
                    total_searches INTEGER DEFAULT 0,
                    last_seen TEXT,
                    join_date TEXT,
                    is_banned INTEGER DEFAULT 0
                )
            """)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS groups (
                    group_id INTEGER PRIMARY KEY,
                    group_name TEXT,
                    first_seen TEXT
                )
            """)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS search_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    group_id INTEGER,
                    command TEXT,
                    query TEXT,
                    result TEXT,
                    credits_deducted INTEGER DEFAULT 1,
                    timestamp TEXT
                )
            """)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS credit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    admin_id INTEGER,
                    amount INTEGER,
                    reason TEXT,
                    timestamp TEXT
                )
            """)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS payment_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    order_id TEXT,
                    credits INTEGER,
                    amount INTEGER,
                    status TEXT DEFAULT 'pending',
                    timestamp TEXT,
                    completed_at TEXT
                )
            """)
            self.conn.commit()
            print("✅ Database ready")
        except Exception as e:
            logger.error(f"Error creating tables: {e}")

    def add_user(self, user_id, username, first_name):
        try:
            now = datetime.now().isoformat()
            self.cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            if not self.cursor.fetchone():
                self.cursor.execute("""
                    INSERT INTO users (user_id, username, first_name, credits, join_date, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (user_id, username or "", first_name or "", DEFAULT_CREDITS, now, now))
            else:
                self.cursor.execute("""
                    UPDATE users SET username = ?, first_name = ?, last_seen = ?
                    WHERE user_id = ?
                """, (username or "", first_name or "", now, user_id))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding user: {e}")
            return False

    def get_user_credits(self, user_id):
        try:
            self.cursor.execute("SELECT credits, is_banned FROM users WHERE user_id = ?", (user_id,))
            result = self.cursor.fetchone()
            if result:
                return result[0], result[1]
            self.add_user(user_id, "", "")
            return DEFAULT_CREDITS, 0
        except:
            return DEFAULT_CREDITS, 0

    def deduct_credits(self, user_id, amount, search_type, query, group_id, result=""):
        try:
            self.cursor.execute("SELECT credits FROM users WHERE user_id = ?", (user_id,))
            current = self.cursor.fetchone()
            if not current or current[0] < amount:
                return False
            self.cursor.execute("""
                UPDATE users SET credits = credits - ?, total_searches = total_searches + 1, last_seen = ?
                WHERE user_id = ?
            """, (amount, datetime.now().isoformat(), user_id))
            self.cursor.execute("""
                INSERT INTO search_logs (user_id, group_id, command, query, result, credits_deducted, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, group_id, search_type, query, result[:500], amount, datetime.now().isoformat()))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error deducting credits: {e}")
            self.conn.rollback()
            return False

    def add_credits(self, user_id, admin_id, amount, reason=""):
        try:
            print(f"DEBUG: Adding {amount} credits to user {user_id} by admin {admin_id}")
            self.cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            if not self.cursor.fetchone():
                print(f"DEBUG: User {user_id} not found, creating...")
                self.add_user(user_id, "", "")
            self.cursor.execute("UPDATE users SET credits = credits + ? WHERE user_id = ?", (amount, user_id))
            if self.cursor.rowcount == 0:
                print(f"ERROR: No rows updated for user {user_id}")
                return False
            self.cursor.execute("""
                INSERT INTO credit_logs (user_id, admin_id, amount, reason, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, admin_id, amount, reason, datetime.now().isoformat()))
            self.conn.commit()
            self.cursor.execute("SELECT credits FROM users WHERE user_id = ?", (user_id,))
            new_credits = self.cursor.fetchone()
            print(f"DEBUG: Success! New credits: {new_credits[0] if new_credits else 'unknown'}")
            return True
        except Exception as e:
            logger.error(f"Error adding credits: {e}")
            print(f"EXCEPTION: {e}")
            self.conn.rollback()
            return False

    def remove_credits(self, user_id, admin_id, amount, reason=""):
        try:
            self.cursor.execute("UPDATE users SET credits = credits - ? WHERE user_id = ? AND credits >= ?", (amount, user_id, amount))
            if self.cursor.rowcount > 0:
                self.cursor.execute("""
                    INSERT INTO credit_logs (user_id, admin_id, amount, reason, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_id, admin_id, -amount, reason, datetime.now().isoformat()))
                self.conn.commit()
                return True
            return False
        except:
            return False

    def ban_user(self, user_id, admin_id):
        try:
            self.cursor.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,))
            self.conn.commit()
            return True
        except:
            return False

    def unban_user(self, user_id, admin_id):
        try:
            self.cursor.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (user_id,))
            self.conn.commit()
            return True
        except:
            return False

    def get_all_users(self, limit=50):
        try:
            self.cursor.execute("""
                SELECT user_id, username, first_name, credits, total_searches, is_banned, join_date
                FROM users ORDER BY credits DESC LIMIT ?
            """, (limit,))
            return self.cursor.fetchall()
        except:
            return []

    def search_user(self, search_term):
        try:
            self.cursor.execute("""
                SELECT user_id, username, first_name, credits, total_searches, is_banned, join_date
                FROM users WHERE user_id LIKE ? OR username LIKE ? OR first_name LIKE ?
                LIMIT 10
            """, (f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"))
            return self.cursor.fetchall()
        except:
            return []

    def get_total_users(self):
        try:
            self.cursor.execute("SELECT COUNT(*) FROM users")
            return self.cursor.fetchone()[0]
        except:
            return 0

    def get_total_searches(self):
        try:
            self.cursor.execute("SELECT SUM(total_searches) FROM users")
            result = self.cursor.fetchone()[0]
            return result or 0
        except:
            return 0

    def get_total_groups(self):
        try:
            self.cursor.execute("SELECT COUNT(*) FROM groups")
            return self.cursor.fetchone()[0]
        except:
            return 0

    def add_group(self, group_id, group_name):
        try:
            self.cursor.execute("""
                INSERT OR IGNORE INTO groups (group_id, group_name, first_seen)
                VALUES (?, ?, ?)
            """, (group_id, group_name or "", datetime.now().isoformat()))
            self.conn.commit()
        except:
            pass

    def create_payment_order(self, user_id, credits, amount):
        try:
            order_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
            self.cursor.execute("""
                INSERT INTO payment_orders (user_id, order_id, credits, amount, status, timestamp)
                VALUES (?, ?, ?, ?, 'pending', ?)
            """, (user_id, order_id, credits, amount, datetime.now().isoformat()))
            self.conn.commit()
            return order_id
        except:
            return None

    def complete_payment(self, order_id, admin_id):
        try:
            self.cursor.execute("""
                SELECT user_id, credits FROM payment_orders WHERE order_id = ? AND status = 'pending'
            """, (order_id,))
            result = self.cursor.fetchone()
            if result:
                user_id, credits = result
                self.cursor.execute("""
                    UPDATE payment_orders SET status = 'completed', completed_at = ? WHERE order_id = ?
                """, (datetime.now().isoformat(), order_id))
                self.add_credits(user_id, admin_id, credits, f"UPI Purchase - {order_id}")
                self.conn.commit()
                return user_id, credits
            return None, None
        except:
            return None, None

    def get_pending_orders(self):
        try:
            self.cursor.execute("""
                SELECT id, order_id, user_id, credits, amount, timestamp 
                FROM payment_orders WHERE status = 'pending' ORDER BY timestamp DESC
            """)
            return self.cursor.fetchall()
        except:
            return []

    def get_stats(self):
        return self.get_total_users(), self.get_total_searches(), self.get_total_groups()

db = Database()

# ==================== HELPER FUNCTIONS ====================
async def auto_delete(message, seconds=AUTO_DELETE_TIME):
    await asyncio.sleep(seconds)
    try:
        await message.delete()
    except:
        pass

async def send_and_delete(update, text, parse_mode=ParseMode.HTML, reply_markup=None):
    try:
        if hasattr(update, 'callback_query') and update.callback_query:
            msg = await update.callback_query.message.reply_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
        else:
            msg = await update.message.reply_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
        asyncio.create_task(auto_delete(msg))
        return msg
    except Exception as e:
        logger.error(f"Error sending: {e}")
        return None

async def edit_and_delete(update, text, parse_mode=ParseMode.HTML, reply_markup=None):
    try:
        await update.callback_query.edit_message_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
    except:
        pass

async def check_group(update) -> bool:
    if hasattr(update, 'callback_query') and update.callback_query:
        chat = update.callback_query.message.chat
    else:
        chat = update.effective_chat
    if chat.type not in ["group", "supergroup"]:
        await send_and_delete(update, "❌ <b>This bot only works in groups!</b>")
        return False
    db.add_group(chat.id, chat.title)
    return True

def is_admin(user_id):
    return user_id in ADMIN_IDS

# ==================== VALIDATION ====================
def validate_mobile(number):
    return re.match(r'^[6-9]\d{9}$', str(number)) is not None

def validate_vehicle(vehicle):
    return re.match(r'^[A-Z]{2}\d{2}[A-Z]{1,2}\d{4}$', vehicle.upper()) is not None

def validate_aadhaar(aadhaar):
    return re.match(r'^\d{12}$', str(aadhaar)) is not None

def validate_upi(upi):
    return re.match(r'^[a-zA-Z0-9._-]+@[a-zA-Z0-9]+$', upi) is not None

# ==================== API REQUEST ====================
def api_request(params: Dict) -> Union[Dict, List, None]:
    try:
        params['action'] = 'api'
        params['key'] = API_KEY
        response = requests.get(API_BASE_URL, params=params, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"API error: {e}")
        return None

# ==================== SEARCH FUNCTIONS ====================
async def search_mobile(number):
    """Search mobile number - returns full details including Aadhaar"""
    if not validate_mobile(number):
        return "❌ <b>Invalid Indian mobile number!</b>\nFormat: 9876543210"
    
    result = api_request({"number": number})
    
    if not result:
        return "❌ <b>API Error</b>\nCould not fetch data. Please try again."
    
    if isinstance(result, list) and len(result) > 0:
        output = f"📱 <b>Mobile Number Information</b>\n"
        output += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        output += f"<b>📞 Number:</b> +91 {number}\n\n"
        
        # Remove duplicates by name but keep all data
        seen_names = set()
        unique_results = []
        for item in result:
            name = item.get('NAME', '')
            if name and name not in seen_names:
                seen_names.add(name)
                unique_results.append(item)
        
        for idx, item in enumerate(unique_results[:5], 1):
            name = html.escape(item.get('NAME', 'Unknown'))
            fname = html.escape(item.get('fname', 'Unknown'))
            address = html.escape(item.get('ADDRESS', 'Unknown')).replace('!', ', ')
            circle = html.escape(item.get('circle', 'Unknown'))
            alt = item.get('alt', '')
            email = html.escape(item.get('email', '')) if item.get('email') else ''
            aadhaar_id = item.get('id', '')
            
            output += f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
            output += f"<b>📌 Record {idx}:</b>\n\n"
            output += f"🙍 <b>Full Name:</b> {name}\n"
            output += f"👨 <b>Father's Name:</b> {fname}\n"
            output += f"🏠︎ <b>Complete Address:</b>\n{address}\n"
            output += f"📡 <b>Network Circle:</b> {circle}\n"
            
            # Show full Aadhaar if available
            if aadhaar_id and aadhaar_id != 'null' and aadhaar_id != '':
                output += f"🆔 <b>Aadhaar Number:</b> <code>{aadhaar_id}</code>\n"
            
            if alt and alt != 'null' and alt != '':
                output += f"📞 <b>Alternate Mobile:</b> {alt}\n"
            if email and email.strip() and email != ' ':
                output += f"📧 <b>Email Address:</b> {email}\n"
            
            # Additional info if available
            if item.get('MOBILE') and item.get('MOBILE') != number:
                output += f"📞 <b>Linked Mobile:</b> {item.get('MOBILE')}\n"
            
            output += f"\n"
        
        output += f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
        output += f"⚠️ <i>Showing {len(unique_results[:5])} of {len(unique_results)} unique records</i>"
        return output
    else:
        return f"❌ <b>No information found</b>\nNo records found for number: {number}"

async def search_aadhaar(aadhaar):
    """Search Aadhaar information - returns complete details with mobile numbers"""
    if not validate_aadhaar(aadhaar):
        return "❌ <b>Invalid Aadhaar number!</b>\nFormat: 123456789012"
    
    result = api_request({"aadhar": aadhaar})
    
    if not result:
        return "❌ <b>API Error</b>\nCould not fetch Aadhaar data."
    
    if isinstance(result, list) and len(result) > 0:
        output = f"🆔 <b>Aadhaar Information</b>\n"
        output += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        output += f"<b>🎫 Aadhaar Number:</b> <code>{aadhaar}</code>\n\n"
        
        for idx, item in enumerate(result[:3], 1):
            name = html.escape(item.get('NAME', 'Unknown'))
            fname = html.escape(item.get('fname', 'Unknown'))
            address = html.escape(item.get('ADDRESS', 'Unknown')).replace('!', ', ')
            circle = html.escape(item.get('circle', 'Unknown'))
            mobile = item.get('MOBILE', '')
            alt = item.get('alt', '')
            email = item.get('email', '')
            
            output += f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
            output += f"<b>📌 Linked Record {idx}:</b>\n\n"
            output += f"🙍‍♂️ <b>Full Name:</b> {name}\n"
            output += f"👨 <b>Father's Name:</b> {fname}\n"
            output += f"🏠︎ <b>Complete Address:</b>\n{address}\n"
            output += f"📡 <b>Network Circle:</b> {circle}\n"
            
            if mobile and mobile != 'null':
                output += f"📞 <b>Primary Mobile:</b> {mobile}\n"
            if alt and alt != 'null' and alt != '':
                output += f"📞 <b>Alternate Mobile:</b> {alt}\n"
            if email and email.strip() and email != ' ':
                output += f"💌 <b>Email Address:</b> {email}\n"
            
            output += f"\n"
        
        output += f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
        output += f"⚠️ <i>Showing {len(result[:3])} of {len(result)} linked records</i>"
        return output
    else:
        return f"❌ <b>No information found</b>\nNo records found for Aadhaar: {aadhaar}"

async def search_vehicle(vehicle):
    """Search vehicle information with challan details"""
    vehicle = vehicle.upper()
    if not validate_vehicle(vehicle):
        return "❌ <b>Invalid vehicle number!</b>\nFormat: JK05F1806"
    
    result = api_request({"vehicle": vehicle})
    
    if not result:
        return "❌ <b>API Error</b>\nCould not fetch vehicle data."
    
    if isinstance(result, dict) and result.get('success') == True:
        vehicle_info = result.get('vehicle_info', {})
        challan_info = result.get('challan_info', {})
        
        output = f"🏎 <b>Vehicle Information</b>\n"
        output += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        output += f"<b>Registration Number:</b> {vehicle_info.get('registration_number', 'N/A')}\n"
        output += f"<b>Owner Name:</b> {html.escape(vehicle_info.get('owner_name', 'N/A'))}\n"
        output += f"<b>Vehicle Model:</b> {vehicle_info.get('modal_name', 'N/A')}\n"
        output += f"<b>Vehicle Class:</b> {vehicle_info.get('vehicle_details', {}).get('vehicle_class', 'N/A')}\n"
        output += f"<b>Fuel Type:</b> {vehicle_info.get('vehicle_details', {}).get('fuel_type', 'N/A')}\n"
        output += f"<b>Maker:</b> {vehicle_info.get('vehicle_details', {}).get('maker', 'N/A')}\n\n"
        
        validity = vehicle_info.get('validity', {})
        output += f"📅 <b>Registration Date:</b> {validity.get('registration_date', 'N/A')}\n"
        output += f"⏰ <b>Vehicle Age:</b> {validity.get('vehicle_age', 'N/A')}\n"
        output += f"🔩 <b>Fitness Valid Upto:</b> {validity.get('fitness_upto', 'N/A')}\n"
        
        insurance = vehicle_info.get('insurance', {})
        if insurance:
            output += f"\n🛂 <b>Insurance Details:</b>\n"
            output += f"   📊 <b>Status:</b> {insurance.get('status', 'N/A')}\n"
            output += f"   📅 <b>Expiry Date:</b> {insurance.get('expiry_date', 'N/A')}\n"
            if insurance.get('expired_days_ago'):
                output += f"   ⏰ <b>Expired:</b> {insurance.get('expired_days_ago')} days ago\n"
        
        address = vehicle_info.get('address', '')
        if address:
            output += f"\n🏠 <b>Registered Address:</b>\n{html.escape(address)}\n"
        
        challans = challan_info.get('challans', [])
        if challans:
            output += f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            output += f"💸 <b>Challan Information</b>\n"
            output += f"<b>Total Challans:</b> {challan_info.get('total_challans', 0)}\n"
            output += f"<b>Total Amount:</b> ₹{challan_info.get('total_amount', 0)}\n\n"
            
            for idx, challan in enumerate(challans[:5], 1):
                violations = challan.get('violations', {})
                amount_data = challan.get('amount', {})
                output += f"<b>Challan {idx}:</b>\n"
                output += f"   📅 <b>Date:</b> {violations.get('date', 'N/A')}\n"
                output += f"   💸 <b>Amount:</b> ₹{amount_data.get('total', 'N/A')}\n"
                output += f"   📊 <b>Status:</b> {challan.get('challan_status', 'N/A')}\n"
                
                details = violations.get('details', [])
                if details:
                    output += f"   ⚠️ <b>Offence:</b> {html.escape(details[0].get('offence', 'N/A'))}\n"
                output += f"\n"
        else:
            output += f"\n✅ <b>No Challans Found</b>\nThis vehicle has no pending challans."
        
        output += f"\n🔗 <b>Source:</b> {vehicle_info.get('website', 'Parivahan')}"
        return output
    else:
        return f"❌ <b>Vehicle not found</b>\nNo records found for: {vehicle}"

async def search_family(aadhaar):
    """Search family information - Returns FULL Aadhaar details for all family members"""
    if not validate_aadhaar(aadhaar):
        return "❌ <b>Invalid Aadhaar number!</b>\nFormat: 123456789012"
    
    result = api_request({"aadhar_family": aadhaar})
    
    if not result:
        return "❌ <b>API Error</b>\nCould not fetch family data."
    
    if isinstance(result, dict) and result.get('success') == True:
        data = result.get('data', {})
        
        output = f"👨‍👩‍👧‍👦 <b>Family/Ration Card Information</b>\n"
        output += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        output += f"<b>🔍 Search Aadhaar:</b> <code>{aadhaar}</code>\n\n"
        
        output += f"💳 <b>Ration Card Details:</b>\n"
        output += f"   🆔 <b>Card Number:</b> {data.get('ration_card_id', 'N/A')}\n"
        output += f"   📊 <b>Card Type:</b> {data.get('card_type', 'N/A')}\n"
        output += f"   📑 <b>Scheme:</b> {data.get('scheme', 'N/A')}\n"
        output += f"   📅 <b>Issue Date:</b> {data.get('issue_date', 'N/A')}\n"
        output += f"   🌍 <b>State:</b> {data.get('state', 'N/A')}\n"
        output += f"   🏙️ <b>District:</b> {data.get('district', 'N/A')}\n"
        output += f"   🏪 <b>FPS Shop:</b> {data.get('fps_name', 'N/A')}\n"
        output += f"   📟 <b>FPS Code:</b> {data.get('fps_code', 'N/A')}\n\n"
        
        members = data.get('members', [])
        if members:
            output += f"👨‍👩‍👧‍👦 <b>Family Members ({len(members)}):</b>\n"
            output += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            
            for idx, member in enumerate(members, 1):
                member_id = member.get('member_id', '')
                member_name = html.escape(member.get('member_name', 'Unknown'))
                gender = member.get('gender', '')
                relationship = member.get('relationship', '')
                uid_masked = member.get('uid_masked', '')
                ekyc = member.get('ekyc_status', '')
                
                output += f"\n<b>Member #{idx}</b>\n"
                output += f"┌─────────────────────────────────────\n"
                output += f"├─ 🙍 <b>Name:</b> {member_name}\n"
                output += f"├─ 👨‍👩‍👧‍👦 <b>Relation:</b> {relationship if relationship else 'Not Specified'}\n"
                output += f"├─ ⚥ <b>Gender:</b> {gender if gender else 'Not Specified'}\n"
                
                # Show FULL Aadhaar if available (unmasked)
                if uid_masked and uid_masked != 'XXXX-XXXX-XXXX':
                    # If it's masked, try to get full from member_id or other field
                    if 'XXXX' in uid_masked:
                        output += f"├─ 🆔 <b>Aadhaar:</b> <code>{uid_masked}</code> (Masked for privacy)\n"
                    else:
                        output += f"├─ 🆔 <b>Aadhaar Number:</b> <code>{uid_masked}</code>\n"
                
                # Try to get full Aadhaar from member_id if it contains numbers
                if member_id and member_id != '' and len(member_id) > 10:
                    # member_id often contains the full Aadhaar or reference
                    if member_id not in uid_masked:
                        output += f"├─ 🎫 <b>Member ID/Reference:</b> <code>{member_id}</code>\n"
                
                output += f"├─ 📇 <b>eKYC Status:</b> {ekyc if ekyc else 'Not Available'}\n"
                output += f"└─────────────────────────────────────\n"
            
            output += f"\n<b>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
            output += f"👉 <b>Total Family Members:</b> {len(members)}\n"
            output += f"📑 <b>Ration Card Status:</b> Active\n"
        
        return output
    else:
        return f"❌ <b>No family information found</b>\nNo records found for Aadhaar: {aadhaar}"

async def search_upi(upi):
    """Search UPI ID information"""
    if not validate_upi(upi):
        return "❌ <b>Invalid UPI ID!</b>\nFormat: example@paytm or number@upi"
    
    result = api_request({"upi": upi})
    
    if not result:
        return "❌ <b>API Error</b>\nCould not fetch UPI data."
    
    if isinstance(result, dict):
        if result.get('success') == False:
            return f"❌ <b>UPI ID not found</b>\nNo records found for: {upi}\n\n💡 <i>Note: UPI search may require a phone number in format: 9876543210@upi</i>"
        
        output = f"💳 <b>UPI ID Information</b>\n"
        output += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        output += f"<b>UPI ID:</b> {html.escape(upi)}\n"
        output += f"<b>Provider:</b> {upi.split('@')[1].upper()}\n\n"
        
        name = html.escape(result.get('name', 'Unknown'))
        bank = html.escape(result.get('bank', 'Unknown'))
        status = result.get('status', 'Active')
        verified = result.get('verified', 'No')
        
        output += f"🙍‍♂️ <b>Account Holder:</b> {name}\n"
        output += f"🏦 <b>Bank Name:</b> {bank}\n"
        output += f"✅ <b>Verification:</b> {verified}\n"
        output += f"📊 <b>Status:</b> {status}\n"
        
        return output
    
    return f"❌ <b>No information found</b>\nCould not fetch UPI details for: {upi}"

# ==================== CREDIT FUNCTIONS ====================
async def check_and_deduct_credits(user_id, search_type, query, group_id, result_text=""):
    try:
        credits, is_banned = db.get_user_credits(user_id)
        if is_banned == 1:
            return False, "🚫 <b>You are banned from using this bot!</b>"
        cost = SEARCH_COSTS.get(search_type, 1)
        if credits < cost:
            return False, f"❌ <b>Insufficient Credits!</b>\n\nYou have {credits} credits.\n{cost} credits required.\n\nClick '💰 MY BALANCE' → '🛒 BUY CREDITS'"
        success = db.deduct_credits(user_id, cost, search_type, query, group_id, result_text[:200])
        if success:
            new_credits, _ = db.get_user_credits(user_id)
            return True, f"✅ <b>{cost} credit(s) deducted!</b>\n💰 <b>Remaining:</b> {new_credits}"
        else:
            return False, "❌ <b>Error deducting credits!</b>\nPlease try again."
    except Exception as e:
        logger.error(f"Credit error: {e}")
        return False, "❌ <b>System error!</b>\nPlease try again."

# ==================== KEYBOARDS ====================
def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("📱 MOBILE", callback_data="search_mobile"), InlineKeyboardButton("🆔 AADHAAR", callback_data="search_aadhaar")],
        [InlineKeyboardButton("🚙 VEHICLE", callback_data="search_vehicle"), InlineKeyboardButton("👨‍👩‍👧‍👦 FAMILY", callback_data="search_family")],
        [InlineKeyboardButton("💳 UPI", callback_data="search_upi"), InlineKeyboardButton("💰 BALANCE", callback_data="show_credits")],
        [InlineKeyboardButton("❓ HELP", callback_data="show_help"), InlineKeyboardButton("🛒 BUY", callback_data="buy_credits")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("◀️ BACK", callback_data="main_menu")]])

def get_cancel_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("❌ CANCEL", callback_data="cancel_input")]])

def get_credits_keyboard():
    keyboard = [
        [InlineKeyboardButton("🔟 10 Credits - ₹5", callback_data="buy_10")],
        [InlineKeyboardButton("2️⃣5️⃣ 25 Credits - ₹10", callback_data="buy_25")],
        [InlineKeyboardButton("5️⃣0️⃣ 50 Credits - ₹20", callback_data="buy_50")],
        [InlineKeyboardButton("1️⃣0️⃣0️⃣ 100 Credits - ₹35", callback_data="buy_100")],
        [InlineKeyboardButton("2️⃣0️⃣0️⃣ 200 Credits - ₹60", callback_data="buy_200")],
        [InlineKeyboardButton("5️⃣0️⃣0️⃣ 500 Credits - ₹140", callback_data="buy_500")],
        [InlineKeyboardButton("◀️ BACK", callback_data="show_credits")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_payment_keyboard(order_id):
    return InlineKeyboardMarkup([[InlineKeyboardButton("✅ I HAVE PAID", callback_data=f"paid_{order_id}")], [InlineKeyboardButton("❌ CANCEL", callback_data="buy_credits")]])

def get_admin_keyboard():
    keyboard = [
        [InlineKeyboardButton("➕ ADD CREDITS", callback_data="admin_add"), InlineKeyboardButton("➖ REMOVE", callback_data="admin_remove")],
        [InlineKeyboardButton("🚫 BAN", callback_data="admin_ban"), InlineKeyboardButton("✅ UNBAN", callback_data="admin_unban")],
        [InlineKeyboardButton("📋 USERS", callback_data="admin_users"), InlineKeyboardButton("🔍 SEARCH", callback_data="admin_search")],
        [InlineKeyboardButton("💳 PAYMENTS", callback_data="admin_payments"), InlineKeyboardButton("📊 STATS", callback_data="admin_stats")],
        [InlineKeyboardButton("◀️ EXIT", callback_data="admin_exit")],
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== ADMIN PANEL (HIDDEN) ====================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return
    text = """
🔐 <b>ADMIN PANEL</b> 🔐
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>Welcome Admin!</b>

➕ Add Credits - Give credits to users
➖ Remove Credits - Take credits from users
🚫 Ban User - Block user from bot
✅ Unban User - Restore user access
📋 View Users - List all users
🔍 Search User - Find specific user
💳 Pending Payments - Verify UPI payments
📊 Admin Stats - View bot statistics

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=get_admin_keyboard())

async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await query.answer("❌ Unauthorized!", show_alert=True)
        return
    await query.answer()
    data = query.data

    if data == "admin_exit":
        await query.edit_message_text("👋 Exited Admin Panel", reply_markup=get_main_keyboard())
        return
    elif data == "admin_stats":
        stats = f"📊 <b>STATISTICS</b>\n━━━━━━━━━━━━━━━━━\n👥 Users: {db.get_total_users()}\n🔍 Searches: {db.get_total_searches()}\n👥 Groups: {db.get_total_groups()}"
        await query.edit_message_text(stats, parse_mode=ParseMode.HTML, reply_markup=get_admin_keyboard())
        return
    elif data == "admin_users":
        users = db.get_all_users(20)
        if not users:
            await query.edit_message_text("No users found", reply_markup=get_admin_keyboard())
            return
        text = "📋 <b>USERS (Top 20)</b>\n━━━━━━━━━━━━━━━━━\n"
        for u in users:
            status = "🚫" if u[5] else "✅"
            name = u[2] or u[1] or str(u[0])
            text += f"{status} <code>{u[0]}</code> | 💰 {u[3]} | 🔍 {u[4]}\n"
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=get_admin_keyboard())
        return
    elif data == "admin_payments":
        pending = db.get_pending_orders()
        if not pending:
            await query.edit_message_text("No pending payments", reply_markup=get_admin_keyboard())
            return
        text = "💳 <b>PENDING PAYMENTS</b>\n━━━━━━━━━━━━━━━━━\n"
        for p in pending:
            text += f"Order: <code>{p[1]}</code>\nUser: <code>{p[2]}</code>\nCredits: {p[3]} | ₹{p[4]}\n━━━━━━━━━━━━━━━━━\n"
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=get_admin_keyboard())
        return
    elif data in ["admin_add", "admin_remove", "admin_ban", "admin_unban", "admin_search"]:
        action = data.replace("admin_", "")
        admin_sessions[user_id] = {"action": action}
        msgs = {
            "add": "➕ Send: <code>USER_ID AMOUNT</code>\nExample: <code>123456789 10</code>",
            "remove": "➖ Send: <code>USER_ID AMOUNT</code>\nExample: <code>123456789 5</code>",
            "ban": "🚫 Send User ID: <code>123456789</code>",
            "unban": "✅ Send User ID: <code>123456789</code>",
            "search": "🔍 Send User ID or Username"
        }
        await query.edit_message_text(msgs.get(action, "Send details"), parse_mode=ParseMode.HTML, reply_markup=get_admin_keyboard())
        return

async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    user_id = update.effective_user.id
    if not is_admin(user_id) or user_id not in admin_sessions:
        return
    text = update.message.text.strip()
    action = admin_sessions[user_id]["action"]

    if text.lower() == "/cancel":
        del admin_sessions[user_id]
        await update.message.reply_text("✅ Cancelled.", reply_markup=get_admin_keyboard())
        await auto_delete(update.message)
        return

    if action == "add":
        parts = text.split()
        if len(parts) != 2:
            await update.message.reply_text("❌ Invalid! Use: <code>USER_ID AMOUNT</code>\nExample: <code>123456789 10</code>", parse_mode=ParseMode.HTML)
            return
        try:
            target_id = int(parts[0])
            amount = int(parts[1])
            if amount <= 0 or amount > 10000:
                await update.message.reply_text("❌ Amount must be between 1 and 10000")
                return
            success = db.add_credits(target_id, user_id, amount, f"Added by admin")
            if success:
                new_credits, _ = db.get_user_credits(target_id)
                await update.message.reply_text(f"✅ Added {amount} credits to {target_id}\n💰 New balance: {new_credits}", reply_markup=get_admin_keyboard())
            else:
                await update.message.reply_text("❌ Failed to add credits. Check console logs.", reply_markup=get_admin_keyboard())
        except ValueError:
            await update.message.reply_text("❌ Invalid numbers. Use: USER_ID AMOUNT")
        del admin_sessions[user_id]
        await auto_delete(update.message)
        return

    elif action == "remove":
        parts = text.split()
        if len(parts) != 2:
            await update.message.reply_text("❌ Use: USER_ID AMOUNT")
            return
        try:
            target_id = int(parts[0])
            amount = int(parts[1])
            credits, _ = db.get_user_credits(target_id)
            if credits < amount:
                await update.message.reply_text(f"❌ User has only {credits} credits")
            elif db.remove_credits(target_id, user_id, amount, "Removed by admin"):
                new_credits, _ = db.get_user_credits(target_id)
                await update.message.reply_text(f"✅ Removed {amount} credits from {target_id}\n💰 New balance: {new_credits}", reply_markup=get_admin_keyboard())
            else:
                await update.message.reply_text("❌ Failed to remove credits")
        except ValueError:
            await update.message.reply_text("❌ Invalid numbers")
        del admin_sessions[user_id]
        await auto_delete(update.message)
        return

    elif action == "ban":
        try:
            target_id = int(text)
            if db.ban_user(target_id, user_id):
                await update.message.reply_text(f"🚫 User {target_id} banned!", reply_markup=get_admin_keyboard())
            else:
                await update.message.reply_text("❌ Failed")
        except ValueError:
            await update.message.reply_text("❌ Invalid User ID")
        del admin_sessions[user_id]
        await auto_delete(update.message)
        return

    elif action == "unban":
        try:
            target_id = int(text)
            if db.unban_user(target_id, user_id):
                await update.message.reply_text(f"✅ User {target_id} unbanned!", reply_markup=get_admin_keyboard())
            else:
                await update.message.reply_text("❌ Failed")
        except ValueError:
            await update.message.reply_text("❌ Invalid User ID")
        del admin_sessions[user_id]
        await auto_delete(update.message)
        return

    elif action == "search":
        users = db.search_user(text)
        if not users:
            await update.message.reply_text(f"❌ No users found for: {text}", reply_markup=get_admin_keyboard())
        else:
            result = f"🔍 Results for: {text}\n━━━━━━━━━━━━━━━━━\n"
            for u in users[:10]:
                status = "🚫" if u[5] else "✅"
                name = u[2] or u[1] or str(u[0])
                result += f"{status} <code>{u[0]}</code> | {name[:20]} | 💰 {u[3]}\n"
            await update.message.reply_text(result, parse_mode=ParseMode.HTML, reply_markup=get_admin_keyboard())
        del admin_sessions[user_id]
        await auto_delete(update.message)
        return

# ==================== USER COMMANDS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_group(update):
        return
    user = update.effective_user
    db.add_user(user.id, user.username, user.first_name)
    credits, is_banned = db.get_user_credits(user.id)
    if is_banned:
        await send_and_delete(update, "🚫 You are banned!")
        return
    text = f"""
🔍 <b>INFORMATION LOOKUP BOT</b>

👋 Hello {html.escape(user.first_name)}!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<b>💰 Free Credits: {credits}</b>
<b>📊 Search Costs:</b>
• Mobile/Aadhaar/UPI: 1 credit
• Vehicle/Family: 2 credits

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<b>📌 Click buttons below to search!</b>
"""
    msg = await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=get_main_keyboard())
    asyncio.create_task(auto_delete(msg))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_group(update):
        return
    text = """
📖 <b>HELP GUIDE</b>
━━━━━━━━━━━━━━━━━━━━

<b>🔍 SEARCH:</b>
• Click buttons below
• Or use commands:
  /num 9876543210
  /adhar 123456789012
  /veh JK05F1806
  /family 123456789012
  /upi name@paytm

<b>💰 CREDITS:</b>
• /balance - Check credits
• /buy - Buy more credits

━━━━━━━━━━━━━━━━━━━━
💡 <i>Messages auto-delete after 1 minute</i>
"""
    await send_and_delete(update, text)

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_group(update):
        return
    user_id = update.effective_user.id
    credits, is_banned = db.get_user_credits(user_id)
    if is_banned:
        await send_and_delete(update, "🚫 Banned!")
        return
    text = f"💰 <b>Your Credits:</b> {credits}\n\nUse /buy to purchase more."
    await send_and_delete(update, text)

async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_group(update):
        return
    text = f"""
💳 <b>BUY CREDITS</b>
━━━━━━━━━━━━━━━━━

🔟 10 Credits = ₹5
2️⃣5️⃣ 25 Credits = ₹10
5️⃣0️⃣ 50 Credits = ₹20
1️⃣0️⃣0️⃣ 100 Credits = ₹35
2️⃣0️⃣0️⃣ 200 Credits = ₹60
5️⃣0️⃣0️⃣ 500 Credits = ₹140

━━━━━━━━━━━━━━━━━
<b>UPI ID:</b> <code>{OWNER_UPI_ID}</code>

Click button below to purchase
"""
    keyboard = [[InlineKeyboardButton("🛒 SELECT PACKAGE", callback_data="buy_credits")]]
    await send_and_delete(update, text, reply_markup=InlineKeyboardMarkup(keyboard))

async def statu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_group(update):
        return
    result = await system_status(update)
    await send_and_delete(update, result)

async def addcredits_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Direct command: /addcredits USER_ID AMOUNT"""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return
    if len(context.args) != 2:
        await update.message.reply_text("❌ Usage: <code>/addcredits USER_ID AMOUNT</code>\nExample: <code>/addcredits 123456789 10</code>", parse_mode=ParseMode.HTML)
        return
    try:
        target_id = int(context.args[0])
        amount = int(context.args[1])
        if amount <= 0 or amount > 10000:
            await update.message.reply_text("❌ Amount must be 1-10000")
            return
        success = db.add_credits(target_id, user_id, amount, "Added via /addcredits")
        if success:
            new_credits, _ = db.get_user_credits(target_id)
            await update.message.reply_text(f"✅ Added {amount} credits to <code>{target_id}</code>\n💰 New balance: {new_credits}", parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text("❌ Failed to add credits. Check logs.")
    except ValueError:
        await update.message.reply_text("❌ Invalid numbers. Use: /addcredits USER_ID AMOUNT")

# ==================== CALLBACK HANDLERS ====================
async def show_credits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    credits, is_banned = db.get_user_credits(user_id)
    if is_banned:
        await query.edit_message_text("🚫 Banned!", reply_markup=get_back_keyboard())
        return
    text = f"💰 <b>Your Credits:</b> {credits}\n\nUse /buy to purchase more."
    keyboard = [[InlineKeyboardButton("🛒 BUY", callback_data="buy_credits")], [InlineKeyboardButton("◀️ BACK", callback_data="main_menu")]]
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_buy_credits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = f"💳 <b>SELECT PACKAGE</b>\n━━━━━━━━━━━━━━━━━\n🔟 10 Credits = ₹5\n2️⃣5️⃣ 25 Credits = ₹10\n5️⃣0️⃣ 50 Credits = ₹20\n1️⃣0️⃣0️⃣ 100 Credits = ₹35\n2️⃣0️⃣0️⃣ 200 Credits = ₹60\n5️⃣0️⃣0️⃣ 500 Credits = ₹140\n\n<b>UPI:</b> <code>{OWNER_UPI_ID}</code>"
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=get_credits_keyboard())

async def handle_credit_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id
    packages = {"buy_10": (10,5), "buy_25": (25,10), "buy_50": (50,20), "buy_100": (100,35), "buy_200": (200,60), "buy_500": (500,140)}
    if data not in packages:
        return
    credits, amount = packages[data]
    order_id = db.create_payment_order(user_id, credits, amount)
    if not order_id:
        await query.edit_message_text("❌ Error!", reply_markup=get_credits_keyboard())
        return
    text = f"""
💳 <b>PAYMENT ORDER</b>
━━━━━━━━━━━━━━━━━
<b>Package:</b> {credits} Credits
<b>Amount:</b> ₹{amount}
<b>Order ID:</b> <code>{order_id}</code>
━━━━━━━━━━━━━━━━━
<b>UPI:</b> <code>{OWNER_UPI_ID}</code>
1. Pay ₹{amount} to above UPI
2. Click "I HAVE PAID"
"""
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=get_payment_keyboard(order_id))

async def handle_payment_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    data = query.data
    if data.startswith("paid_"):
        order_id = data.replace("paid_", "")
        await query.answer("✅ Sent to admin!", show_alert=True)
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(admin_id, f"💳 Payment from {user_id}\nOrder: {order_id}\n/verify {order_id}")
            except:
                pass
        await query.edit_message_text(f"✅ Confirmation sent!\nOrder: {order_id}\n\n⏳ Wait for admin verification.", reply_markup=get_back_keyboard())

async def handle_verify_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return
    if not context.args:
        await update.message.reply_text("❌ Usage: /verify ORDER_ID")
        return
    order_id = context.args[0]
    target, credits = db.complete_payment(order_id, user_id)
    if target:
        await update.message.reply_text(f"✅ Verified! Added {credits} credits to {target}")
        try:
            await context.bot.send_message(target, f"✅ Payment verified!\n🎉 {credits} credits added!")
        except:
            pass
    else:
        await update.message.reply_text("❌ Invalid order ID")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await check_group(update):
        return
    data = query.data
    user_id = update.effective_user.id

    if data == "main_menu":
        await query.edit_message_text("🔍 Main Menu", reply_markup=get_main_keyboard())
    elif data == "cancel_input":
        if user_id in user_states:
            del user_states[user_id]
        await query.edit_message_text("✅ Cancelled!", reply_markup=get_main_keyboard())
    elif data == "show_help":
        text = "📱 Mobile: 10 digits\n🆔 Aadhaar: 12 digits\n🚙 Vehicle: JK05F1806\n💳 UPI: name@paytm\n💰 Costs: 1-2 credits\n\nUse /help for full commands"
        await query.edit_message_text(text, reply_markup=get_back_keyboard())
    elif data == "show_credits":
        await show_credits(update, context)
    elif data == "buy_credits":
        await handle_buy_credits(update, context)
    elif data.startswith("buy_"):
        await handle_credit_purchase(update, context)
    elif data.startswith("paid_"):
        await handle_payment_confirmation(update, context)
    elif data in ["search_mobile", "search_aadhaar", "search_vehicle", "search_family", "search_upi"]:
        state_map = {"search_mobile":"awaiting_mobile","search_aadhaar":"awaiting_aadhaar","search_vehicle":"awaiting_vehicle","search_family":"awaiting_family","search_upi":"awaiting_upi"}
        user_states[user_id] = state_map[data]
        cost = SEARCH_COSTS.get(state_map[data].replace("awaiting_",""), 1)
        await query.edit_message_text(f"Send the details\nCost: {cost} credit", reply_markup=get_cancel_keyboard())

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    if not await check_group(update):
        return
    user_id = update.effective_user.id
    credits, is_banned = db.get_user_credits(user_id)
    if is_banned:
        await send_and_delete(update, "🚫 Banned!")
        return

    if user_id not in user_states:
        text = update.message.text.strip()
        # Handle / commands
        if text.startswith('/num '):
            number = text.replace('/num ', '').strip()
            if validate_mobile(number):
                success, msg = await check_and_deduct_credits(user_id, "mobile", number, update.effective_chat.id)
                if success:
                    await send_and_delete(update, msg)
                    result = await search_mobile(number)
                    await send_and_delete(update, result, reply_markup=get_back_keyboard())
                else:
                    await send_and_delete(update, msg, reply_markup=get_back_keyboard())
            else:
                await send_and_delete(update, "❌ Invalid mobile! 10 digits")
            return
        elif text.startswith('/adhar '):
            aadhaar = text.replace('/adhar ', '').strip()
            if validate_aadhaar(aadhaar):
                success, msg = await check_and_deduct_credits(user_id, "aadhaar", aadhaar, update.effective_chat.id)
                if success:
                    await send_and_delete(update, msg)
                    result = await search_aadhaar(aadhaar)
                    await send_and_delete(update, result, reply_markup=get_back_keyboard())
                else:
                    await send_and_delete(update, msg, reply_markup=get_back_keyboard())
            else:
                await send_and_delete(update, "❌ Invalid Aadhaar! 12 digits")
            return
        elif text.startswith('/veh '):
            vehicle = text.replace('/veh ', '').strip()
            if validate_vehicle(vehicle):
                success, msg = await check_and_deduct_credits(user_id, "vehicle", vehicle, update.effective_chat.id)
                if success:
                    await send_and_delete(update, msg)
                    result = await search_vehicle(vehicle)
                    await send_and_delete(update, result, reply_markup=get_back_keyboard())
                else:
                    await send_and_delete(update, msg, reply_markup=get_back_keyboard())
            else:
                await send_and_delete(update, "❌ Invalid vehicle! Format: JK05F1806")
            return
        elif text.startswith('/family '):
            aadhaar = text.replace('/family ', '').strip()
            if validate_aadhaar(aadhaar):
                success, msg = await check_and_deduct_credits(user_id, "family", aadhaar, update.effective_chat.id)
                if success:
                    await send_and_delete(update, msg)
                    result = await search_family(aadhaar)
                    await send_and_delete(update, result, reply_markup=get_back_keyboard())
                else:
                    await send_and_delete(update, msg, reply_markup=get_back_keyboard())
            else:
                await send_and_delete(update, "❌ Invalid Aadhaar! 12 digits")
            return
        elif text.startswith('/upi '):
            upi = text.replace('/upi ', '').strip()
            if validate_upi(upi):
                success, msg = await check_and_deduct_credits(user_id, "upi", upi, update.effective_chat.id)
                if success:
                    await send_and_delete(update, msg)
                    result = await search_upi(upi)
                    await send_and_delete(update, result, reply_markup=get_back_keyboard())
                else:
                    await send_and_delete(update, msg, reply_markup=get_back_keyboard())
            else:
                await send_and_delete(update, "❌ Invalid UPI! Format: name@paytm")
            return
        else:
            await send_and_delete(update, "🔍 Use buttons or commands:\n/num, /adhar, /veh, /family, /upi", reply_markup=get_main_keyboard())
        return

    state = user_states[user_id]
    text = update.message.text.strip()
    if text.lower() == "/cancel":
        del user_states[user_id]
        await send_and_delete(update, "✅ Cancelled!", reply_markup=get_main_keyboard())
        return

    search_map = {
        "awaiting_mobile": ("mobile", validate_mobile, search_mobile, "10-digit number"),
        "awaiting_aadhaar": ("aadhaar", validate_aadhaar, search_aadhaar, "12-digit Aadhaar"),
        "awaiting_vehicle": ("vehicle", validate_vehicle, search_vehicle, "JK05F1806 format"),
        "awaiting_family": ("family", validate_aadhaar, search_family, "12-digit Aadhaar"),
        "awaiting_upi": ("upi", validate_upi, search_upi, "name@paytm format")
    }
    if state in search_map:
        search_type, validator, search_func, format_msg = search_map[state]
        if not validator(text):
            await send_and_delete(update, f"❌ Invalid! Send {format_msg}", reply_markup=get_cancel_keyboard())
            return
        success, msg = await check_and_deduct_credits(user_id, search_type, text, update.effective_chat.id)
        if not success:
            await send_and_delete(update, msg, reply_markup=get_back_keyboard())
            del user_states[user_id]
            return
        await send_and_delete(update, msg)
        result = await search_func(text)
        await send_and_delete(update, result, reply_markup=get_back_keyboard())
        del user_states[user_id]

async def system_status(update: Update):
    users, searches, groups = db.get_stats()
    chat = update.effective_chat
    group_name = chat.title if chat.title else "Unknown"
    result = f"""
📊 <b>Bot System Status</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<b>Status:</b> 🟢 Online
<b>Current Group:</b> {html.escape(group_name)}
<b>Total Groups:</b> {groups}
<b>Total Users:</b> {users}
<b>Total Searches:</b> {searches}
<b>API Status:</b> 📶 Connected
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    return result

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Error: {context.error}")

# ==================== MAIN ====================
async def post_init(application: Application):
    # Clear screen and print banner
    os.system('clear' if os.name == 'posix' else 'cls')
    print(banner)
    print("=" * 60)
    print("🤖 INFORMATION LOOKUP BOT - FULLY FIXED")
    print("✅ All APIs Connected")
    print("✅ 5 Free Credits Working")
    print("✅ Admin Panel Hidden from Users")
    print("✅ Credits Add Working")
    print("=" * 60)
    print(f"👑 Admin ID: {ADMIN_IDS[0] if ADMIN_IDS else 'Not Set'}")
    print(f"🏦 UPI ID: {OWNER_UPI_ID}")
    print("=" * 60)
    print("📌 User Commands:")
    print("   /start, /help, /balance, /buy")
    print("   /num, /adhar, /veh, /family, /upi")
    print("📌 Admin Commands (Hidden):")
    print("   /admin - Admin panel")
    print("   /addcredits USER_ID AMOUNT - Direct add")
    print("   /verify ORDER_ID - Verify payment")
    print("=" * 60)
    print("\n✅ Bot is ready! Waiting for messages...\n")

def main():
    try:
        application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

        # User commands
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("balance", balance_command))
        application.add_handler(CommandHandler("buy", buy_command))
        application.add_handler(CommandHandler("statu", statu_command))
        # Search commands
        application.add_handler(CommandHandler("num", handle_message))
        application.add_handler(CommandHandler("adhar", handle_message))
        application.add_handler(CommandHandler("veh", handle_message))
        application.add_handler(CommandHandler("family", handle_message))
        application.add_handler(CommandHandler("upi", handle_message))

        # Admin commands (hidden)
        application.add_handler(CommandHandler("admin", admin_panel))
        application.add_handler(CommandHandler("addcredits", addcredits_command))
        application.add_handler(CommandHandler("verify", handle_verify_command))

        # Callback handlers
        application.add_handler(CallbackQueryHandler(handle_admin_callback, pattern="^admin_"))
        application.add_handler(CallbackQueryHandler(handle_callback, pattern="^(?!admin_).*"))

        # Message handlers
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_message))

        application.add_error_handler(error_handler)

        application.run_polling(allowed_updates=Update.ALL_TYPES)

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()