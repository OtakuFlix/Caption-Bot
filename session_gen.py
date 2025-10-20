"""
Setup script to create a user session for accessing private channels.
Run this ONCE before starting the bot.
"""
import os
from telethon.sync import TelegramClient

# Get credentials from environment or input
API_ID=25198711
API_HASH="2a99a1375e26295626c04b4606f72752"

if not API_ID or not API_HASH:
    print("\n🔐 Telegram User Session Setup")
    print("=" * 50)
    print("\nThis will create a session to access private channels.")
    print("You need to login with your personal Telegram account.\n")
    
    API_ID = input("Enter your API_ID: ").strip()
    API_HASH = input("Enter your API_HASH: ").strip()

API_ID = int(API_ID)

print("\n📱 Starting session creation...")
print("You will receive a code on your Telegram app.\n")

# Create the client
with TelegramClient('user_session', API_ID, API_HASH) as client:
    print("\n✅ Session created successfully!")
    print("\n📁 Files created:")
    print("   - user_session.session")
    print("\n⚠️  IMPORTANT:")
    print("   1. Keep this file safe and private")
    print("   2. Copy it to your bot directory")
    print("   3. Set USER_SESSION=user_session in your environment variables")
    print("\n🚀 Now you can run the bot with: python bot.py")