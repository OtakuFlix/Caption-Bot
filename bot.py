import os
import re
import asyncio
import socket
import threading
from telethon import TelegramClient, events
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.errors import FloodWaitError, AuthKeyUnregisteredError, UserDeactivatedBanError, ChannelPrivateError
from dotenv import load_dotenv
import logging
import glob
from datetime import datetime

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='[%(levelname)s/%(asctime)s] %(name)s: %(message)s',
    level=logging.INFO
)

# Bot configuration
API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('BOT_TOKEN')
SESSIONS_DIR = 'sessions'  # Directory containing session files

# Store user states and session clients
user_states = {}
session_clients = []  # List of active user clients
bot_id = None

class UserState:
    def __init__(self):
        self.mode = None
        self.start_link = None
        self.end_link = None
        self.name = None
        self.current_session_index = 0

def run_tcp_health_check():
    """Simple TCP server for Koyeb health checks"""
    host = '0.0.0.0'
    port = 8000  # Koyeb default health check port
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind((host, port))
        server_socket.listen(5)
        logging.info(f"✅ TCP Health check server running on port {port}")
        
        while True:
            client_socket, address = server_socket.accept()
            # Simply accept and close connection - Koyeb just needs to connect
            client_socket.close()
            
    except Exception as e:
        logging.error(f"TCP health check error: {e}")
    finally:
        server_socket.close()

def extract_episode(caption):
    """Extract episode number from caption"""
    if not caption:
        return "00"
    
    patterns = [
        r'Episode\s*-?\s*(\d+)',
        r'Ep\.?\s*-?\s*(\d+)',
        r'E(\d+)',
        r'\[S\d+E(\d+)\]',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, caption, re.IGNORECASE)
        if match:
            return match.group(1).zfill(2)
    
    return "00"

async def load_sessions():
    """Load all session files from sessions directory"""
    global session_clients
    
    # Create sessions directory if it doesn't exist
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    
    # Find all .session files
    session_files = glob.glob(os.path.join(SESSIONS_DIR, '*.session'))
    
    if not session_files:
        logging.warning(f"No session files found in '{SESSIONS_DIR}' directory!")
        logging.info(f"Please add session files (e.g., session1.session, session2.session) to the '{SESSIONS_DIR}' directory")
        return
    
    logging.info(f"Found {len(session_files)} session file(s)")
    
    for session_file in session_files:
        try:
            # Get session name without extension
            session_name = session_file.replace('.session', '')
            
            # Create and start client
            client = TelegramClient(session_name, API_ID, API_HASH)
            await client.start()
            
            # Verify session is valid
            me = await client.get_me()
            session_clients.append(client)
            
            logging.info(f"✅ Loaded session: {os.path.basename(session_name)} ({me.first_name} {me.last_name or ''})")
            
        except Exception as e:
            logging.error(f"❌ Failed to load session {os.path.basename(session_file)}: {e}")
    
    if session_clients:
        logging.info(f"Successfully loaded {len(session_clients)} session(s)")
    else:
        logging.error("No valid sessions loaded! Bot may not function properly.")

def extract_quality(caption):
    """Extract quality from caption"""
    if not caption:
        return "720p"
    
    patterns = [
        r'(\d{3,4}p)',
        r'Quality\s*:?\s*(\d{3,4}p)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, caption, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return "720p"

def format_size(size_bytes):
    """Convert bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.0f}{unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.0f}TB"

def parse_channel_link(link):
    """Parse Telegram channel link to get channel ID and message ID"""
    # Pattern: https://t.me/c/1606225518/1259
    match = re.search(r't\.me/c/(\d+)/(\d+)', link)
    if match:
        channel_id = int('-100' + match.group(1))
        message_id = int(match.group(2))
        return channel_id, message_id
    
    # Pattern: https://t.me/channel_name/1259
    match = re.search(r't\.me/([^/]+)/(\d+)', link)
    if match:
        channel_username = match.group(1)
        message_id = int(match.group(2))
        return channel_username, message_id
    
    return None, None

async def start_handler(event):
    sessions_count = len(session_clients)
    await event.respond(
        f"🎬 **Multi-Session Video Forwarding Bot**\n\n"
        f"**Active Sessions:** {sessions_count}\n\n"
        f"**Features:**\n"
        f"• Bulk download videos from channels\n"
        f"• Automatic session failover\n"
        f"• Custom caption formatting\n\n"
        f"**Usage:**\n"
        f"Send start and end links:\n"
        f"`https://t.me/c/1606225518/1259`\n"
        f"`https://t.me/c/1606225518/1414`\n\n"
        f"Ready to process your videos! 🚀",
        parse_mode='markdown'
    )

async def handle_message(event, bot):
    global bot_id
    
    user_id = event.sender_id
    text = event.message.text
    
    if not text:
        return
    
    # Ignore bot's own messages
    if user_id == bot_id:
        return
    
    # Check if we have any active sessions
    if not session_clients:
        await event.respond("❌ No active sessions available! Please add session files to the 'sessions' directory.")
        return
    
    # Initialize user state
    if user_id not in user_states:
        user_states[user_id] = UserState()
    
    state = user_states[user_id]
    
    # Check for links
    links = re.findall(r'https://t\.me/[^\s]+', text)
    
    # Handle second link
    if len(links) == 1 and state.mode == 'waiting_second_link':
        state.end_link = links[0]
        state.mode = 'bulk_name'
        
        await event.respond(
            "📋 **Bulk Mode Activated**\n\n"
            f"Start: `{state.start_link}`\n"
            f"End: `{state.end_link}`\n\n"
            "Please enter the **Name** for the videos:",
            parse_mode='markdown'
        )
        return
    
    # Handle first link
    if len(links) == 1 and state.mode != 'bulk_name':
        state.mode = 'waiting_second_link'
        state.start_link = links[0]
        
        await event.respond(
            "📝 **First link received!**\n\n"
            f"Link: `{links[0]}`\n\n"
            "Now send the **second link** (end message):",
            parse_mode='markdown'
        )
        return
    
    # Handle both links at once
    if len(links) >= 2 and state.mode != 'bulk_name':
        state.mode = 'bulk_name'
        state.start_link = links[0]
        state.end_link = links[1]
        
        await event.respond(
            "📋 **Bulk Mode Activated**\n\n"
            f"Start: `{links[0]}`\n"
            f"End: `{links[1]}`\n\n"
            "Please enter the **Name** for the videos:",
            parse_mode='markdown'
        )
        return
    
    # Handle name input
    if state.mode == 'bulk_name':
        state.name = text.strip()
        state.mode = None
        
        status_msg = await event.respond("🔄 **Processing bulk forward...**\nUsing multiple sessions for reliability.", parse_mode='markdown')
        
        try:
            await process_bulk_forward(event, state, status_msg)
        except Exception as e:
            await status_msg.edit(f"❌ **Error:** {str(e)}")
            logging.error(f"Bulk forward error: {e}")
        
        # Reset state
        user_states[user_id] = UserState()
        return

async def join_channel_if_needed(client, channel_id):
    """Try to join a channel if not already a member"""
    try:
        # Try to get channel entity
        await client.get_entity(channel_id)
        return True
    except Exception as e:
        logging.info(f"Not a member of channel {channel_id}, attempting to join...")
        
        try:
            # Try to join the channel
            await client(JoinChannelRequest(channel_id))
            logging.info(f"Successfully joined channel {channel_id}")
            return True
        except Exception as join_error:
            logging.error(f"Failed to join channel {channel_id}: {join_error}")
            return False

async def get_working_client(channel_id, msg_id):
    """Try each session client until one works"""
    for i, client in enumerate(session_clients):
        try:
            # First try to ensure we're a member of the channel
            await join_channel_if_needed(client, channel_id)
            
            # Test if client can access the message
            message = await client.get_messages(channel_id, ids=msg_id)
            if message:
                logging.info(f"Using session {i+1} for message {msg_id}")
                return client, i
        except (AuthKeyUnregisteredError, UserDeactivatedBanError) as e:
            logging.error(f"Session {i+1} is invalid: {e}")
            continue
        except Exception as e:
            logging.warning(f"Session {i+1} failed to access message: {e}")
            continue
    
    return None, -1

async def process_bulk_forward(event, state, status_msg):
    """Process bulk forward with automatic session failover - FAST VERSION"""
    channel_id_start, msg_id_start = parse_channel_link(state.start_link)
    channel_id_end, msg_id_end = parse_channel_link(state.end_link)
    
    if not channel_id_start or not channel_id_end:
        await status_msg.edit("❌ **Error:** Invalid links provided!")
        return
    
    if channel_id_start != channel_id_end:
        await status_msg.edit("❌ **Error:** Both links must be from the same channel!")
        return
    
    video_count = 0
    processed = 0
    failed_count = 0
    total = msg_id_end - msg_id_start + 1
    target_chat = event.chat_id
    
    # Find a working client for this channel
    await status_msg.edit("🔍 **Finding available session...**")
    test_client, session_index = await get_working_client(channel_id_start, msg_id_start)
    
    if not test_client:
        await status_msg.edit(
            "❌ **Error:** No session can access this channel!\n\n"
            "**Possible reasons:**\n"
            "• Channel is private and sessions are not members\n"
            "• Sessions need to join the channel first\n\n"
            "**Solution:** Make sure at least one session account joins the channel manually first."
        )
        return
    
    await status_msg.edit(f"✅ **Using session {session_index + 1}**\n\n🚀 Starting rapid download...")
    
    current_client = test_client
    current_session = session_index
    
    try:
        # Process messages in batches for speed
        batch_size = 10  # Process 10 messages at a time
        
        for batch_start in range(msg_id_start, msg_id_end + 1, batch_size):
            batch_end = min(batch_start + batch_size - 1, msg_id_end)
            batch_ids = list(range(batch_start, batch_end + 1))
            
            try:
                # Get multiple messages at once
                messages = await current_client.get_messages(channel_id_start, ids=batch_ids)
                
                # Process all messages in batch concurrently
                tasks = []
                for message in messages:
                    if message and message.media:
                        # Check if it's a video
                        is_video = False
                        if message.document:
                            mime_type = message.document.mime_type
                            if mime_type and 'video' in mime_type:
                                is_video = True
                        elif message.video:
                            is_video = True
                        
                        if is_video:
                            tasks.append(send_video(message, state, target_chat, current_client))
                
                # Send all videos in batch concurrently
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Count successes
                for result in results:
                    if result is True:
                        video_count += 1
                    elif isinstance(result, Exception):
                        failed_count += 1
                        logging.error(f"Error sending video: {result}")
                
                processed = batch_end - msg_id_start + 1
                
                # Update status every batch
                await status_msg.edit(
                    f"🚀 **Fast Processing:** {processed}/{total}\n"
                    f"✅ **Videos sent:** {video_count}\n"
                    f"❌ **Failed:** {failed_count}\n"
                    f"📱 **Session:** {current_session + 1}/{len(session_clients)}"
                )
                
            except FloodWaitError as e:
                wait_time = e.seconds
                logging.warning(f"Session {current_session + 1} hit flood wait: {wait_time}s. Switching session...")
                
                # Switch to next session
                current_session = (current_session + 1) % len(session_clients)
                current_client = session_clients[current_session]
                
                await status_msg.edit(
                    f"⏳ **Switched to session {current_session + 1}**\n"
                    f"Waiting {wait_time}s...\n"
                    f"Processing: {processed}/{total}"
                )
                
                await asyncio.sleep(wait_time)
                
            except Exception as e:
                logging.error(f"Error processing batch {batch_start}-{batch_end}: {e}")
                failed_count += len(batch_ids)
        
        await status_msg.edit(
            f"✅ **Completed!**\n\n"
            f"📊 **Stats:**\n"
            f"• Total messages: {total}\n"
            f"• Videos sent: {video_count}\n"
            f"• Failed: {failed_count}\n"
            f"• Sessions used: {len(session_clients)}\n"
            f"⚡ **Speed:** RAPID MODE"
        )
        
    except Exception as e:
        await status_msg.edit(f"❌ **Error:** {str(e)}")
        raise

async def send_video(message, state, target_chat, client):
    """Send a single video - used for concurrent processing"""
    try:
        # Extract information
        caption = message.message or ""
        episode = extract_episode(caption)
        quality = extract_quality(caption)
        
        # Get file size and extension
        if message.document:
            file_size = format_size(message.document.size)
            ext = 'mp4'
            for attr in message.document.attributes:
                if hasattr(attr, 'file_name') and attr.file_name:
                    ext = attr.file_name.split('.')[-1] if '.' in attr.file_name else 'mp4'
                    break
        else:
            file_size = "Unknown"
            ext = "mp4"
        
        # Construct new caption
        new_caption = f"<{state.name}><{episode}.{ext}><{quality}><{file_size}>"
        
        # Send message
        await client.send_message(
            target_chat,
            new_caption,
            file=message.media
        )
        
        logging.info(f"Successfully sent video with caption: {new_caption}")
        return True
        
    except Exception as e:
        logging.error(f"Error sending video: {e}")
        raise

async def keep_alive():
    """Keep-alive function to prevent bot from sleeping"""
    while True:
        try:
            # Log heartbeat every 5 minutes
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logging.info(f"💓 Heartbeat: Bot is alive at {current_time}")
            
            # Check all session clients are still connected
            for i, client in enumerate(session_clients):
                if not client.is_connected():
                    logging.warning(f"Session {i+1} disconnected! Reconnecting...")
                    try:
                        await client.connect()
                        logging.info(f"✅ Session {i+1} reconnected")
                    except Exception as e:
                        logging.error(f"❌ Failed to reconnect session {i+1}: {e}")
            
            # Wait 5 minutes before next heartbeat
            await asyncio.sleep(200)  # 300 seconds = 5 minutes
            
        except Exception as e:
            logging.error(f"Error in keep_alive: {e}")
            await asyncio.sleep(60)  # Wait 1 minute and retry

async def ping_self(bot):
    """Periodically ping the bot to keep it active"""
    while True:
        try:
            # Wait 30 minutes
            await asyncio.sleep(1800)  # 1800 seconds = 30 minutes
            
            # Get bot info to keep connection active
            me = await bot.get_me()
            logging.info(f"🏓 Ping: Bot '{me.first_name}' is responsive")
            
        except Exception as e:
            logging.error(f"Error in ping_self: {e}")
            await asyncio.sleep(200)  # Wait 5 minutes and retry

async def main():
    """Main function to keep the bot running"""
    global bot_id
    
    # Start TCP health check server in background thread
    health_thread = threading.Thread(target=run_tcp_health_check, daemon=True)
    health_thread.start()
    logging.info("🏥 TCP health check server started on port 8000")
    
    # Initialize bot
    bot = TelegramClient('bot', API_ID, API_HASH)
    await bot.start(bot_token=BOT_TOKEN)
    
    # Get bot ID
    bot_me = await bot.get_me()
    bot_id = bot_me.id
    
    logging.info(f"🤖 Bot started successfully! Bot ID: {bot_id}")
    logging.info(f"🕐 Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Load all session files
    await load_sessions()
    
    if not session_clients:
        logging.warning("⚠️  Bot is running but no sessions are loaded!")
        logging.info(f"Add .session files to '{SESSIONS_DIR}/' directory and restart the bot")
    
    # Register handlers
    @bot.on(events.NewMessage(pattern='/start'))
    async def start_wrapper(event):
        await start_handler(event)
    
    @bot.on(events.NewMessage(func=lambda e: e.message.text and not e.message.text.startswith('/')))
    async def message_wrapper(event):
        await handle_message(event, bot)
    
    # Start background tasks for anti-sleep
    asyncio.create_task(keep_alive())
    asyncio.create_task(ping_self(bot))
    
    logging.info("✅ Bot is now running with anti-sleep protection...")
    logging.info("💓 Heartbeat every 5 minutes | 🏓 Ping every 30 minutes")
    logging.info("🏥 TCP health check available on port 8000")
    
    # Keep running
    await bot.run_until_disconnected()

if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.error(f"Fatal error: {e}")
    finally:
        loop.close()
