# Telegram Video Downloader Bot 🤖

A professional Telegram bot that downloads videos from channels (public/private) and formats them with custom naming.

## Features ✨

- **Bulk Download**: Download all videos between two message links
- **Smart Filtering**: Automatically ignores text messages and stickers
- **Auto Formatting**: Extracts episode number, quality, and size
- **Direct File Support**: Send videos directly to the bot
- **Custom Naming**: Format files as `<Name><Episode.ext><Quality><Size>`
- **24/7 Operation**: Never sleeps, perfect for Koyeb hosting
- **Private Channel Support**: Can access private channels with user authorization

## File Format Example

```
<Death Note><11.mp4><720p><153MB>
```

## Setup Instructions

### 1. Get Telegram Credentials

1. Go to https://my.telegram.org
2. Login with your phone number
3. Click "API Development Tools"
4. Create a new application
5. Copy `API_ID` and `API_HASH`

### 2. Create Bot Token

1. Open Telegram and search for [@BotFather](https://t.me/BotFather)
2. Send `/newbot`
3. Follow instructions to create your bot
4. Copy the `BOT_TOKEN`

### 3. Setup for Private Channels (Optional)

For accessing private channels, you need to authorize a user session:

```bash
# Run this locally first
python3 setup_session.py
```

This will create a `user_session.session` file. Upload this to Koyeb.

### 4. Deploy to Koyeb

#### Method 1: Using GitHub (Recommended)

1. Fork this repository
2. Go to [Koyeb Dashboard](https://app.koyeb.com)
3. Click "Create App"
4. Select "GitHub" as source
5. Choose your repository
6. Set these **Environment Variables**:
   ```
   API_ID=your_api_id
   API_HASH=your_api_hash
   BOT_TOKEN=your_bot_token
   ```
7. Set the **Build command**: (leave empty, Dockerfile will handle it)
8. Set **Port**: `8080` (not used but required by Koyeb)
9. Click "Deploy"

#### Method 2: Using Docker Registry

```bash
# Build locally
docker build -t your-username/telegram-bot .

# Push to Docker Hub
docker push your-username/telegram-bot

# Deploy on Koyeb using the Docker image
```

## Environment Variables

Create these in Koyeb Dashboard:

| Variable | Description | Required |
|----------|-------------|----------|
| `API_ID` | Telegram API ID | Yes |
| `API_HASH` | Telegram API Hash | Yes |
| `BOT_TOKEN` | Bot token from BotFather | Yes |
| `USER_SESSION` | Session file name (for private channels) | No |

## Usage

### Bulk Download Mode

1. Send the bot the **first message link**:
   ```
   https://t.me/c/1606225518/1259
   ```

2. Send the **last message link**:
   ```
   https://t.me/c/1606225518/1414
   ```

3. Enter the **series name**:
   ```
   Death Note
   ```

4. Bot will download all videos between these messages!

### Direct File Mode

1. Forward or send any video to the bot
2. Bot asks for the series name
3. Enter the name (e.g., "Death Note")
4. Bot sends back the formatted file

## Bot Commands

- `/start` - Start the bot and see welcome message
- `/help` - Show help guide
- `/cancel` - Cancel current operation

## Caption Format

The bot extracts information from captions like:

```
📟 Episode - 22 [S05]
🎧 Language - Hindi #OFFICIAL 
📀 Quality : 1080p - FHD
🌐 [@Anime_Freak_Official_Hindi]
```

**Extracts:**
- Episode: `22`
- Quality: `1080p`
- Automatically gets file size

## File Structure

```
telegram-bot/
├── bot.py              # Main bot code
├── Dockerfile          # Docker configuration
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variables template
├── README.md           # This file
└── setup_session.py    # Session setup script (optional)
```

## Setup Session Script (For Private Channels)

Create `setup_session.py`:

```python
from telethon.sync import TelegramClient
import os

API_ID = int(input("Enter API_ID: "))
API_HASH = input("Enter API_HASH: ")

with TelegramClient('user_session', API_ID, API_HASH) as client:
    print("Session created successfully!")
    print("Upload 'user_session.session' file to your server")
```

Run locally:
```bash
python3 setup_session.py
```

## Troubleshooting

### Bot not responding?
- Check if environment variables are set correctly
- Verify bot token is valid
- Check Koyeb logs for errors

### Can't access private channels?
- You need to setup user session
- Make sure the user has access to the channel
- Upload the session file to Koyeb

### Files not downloading?
- Check if the links are correct
- Ensure the channel allows downloading
- Check storage space on Koyeb

### Flood wait errors?
- The bot automatically handles flood waits
- Be patient, it will resume after the wait period

## Advanced Configuration

### Modify File Format

Edit the filename format in `bot.py`:

```python
filename = f"<{session.name}><{episode}{ext}><{quality}><{file_size}>"
```

### Change Quality Detection

Modify the regex in `extract_quality()` function:

```python
patterns = [
    r'(\d+p)',
    r'Quality\s*:?\s*(\d+p)',
]
```

### Adjust Download Speed

Add delays between downloads:

```python
await asyncio.sleep(2)  # Wait 2 seconds between downloads
```

## Security Notes

⚠️ **Important:**
- Never share your `API_HASH` or `BOT_TOKEN`
- Keep `.session` files private
- Don't commit credentials to GitHub
- Use environment variables for all secrets

## Performance

- **Memory Usage**: ~100-200MB
- **CPU Usage**: Low (spikes during file processing)
- **Storage**: Temporary (files deleted after upload)
- **Bandwidth**: Depends on video sizes

## Koyeb Specific Notes

- Koyeb provides **512MB RAM** on free tier
- Bot uses minimal resources
- Automatic restarts on crashes
- Logs available in dashboard
- No need for keep-alive pings

## Support

If you encounter issues:

1. Check Koyeb logs
2. Verify all environment variables
3. Test bot locally first
4. Check Telegram API limits

## License

Free to use and modify!

## Credits

Built with:
- [Telethon](https://github.com/LonamiWebs/Telethon) - Telegram client library
- [Python](https://www.python.org/) - Programming language
- [Koyeb](https://www.koyeb.com/) - Hosting platform

---

**Happy Downloading! 🚀**