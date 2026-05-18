# umanchandachat

## Discord message fetcher

This repo includes a small script to fetch messages from a single Discord channel and save them to JSON (`discord_fetch.py`). The script reads configuration from a `.env` file or command-line flags.

Prerequisites
- Python 3.8+
- A Discord bot token with access to the target server

Install

```bash
python3 -m pip install -r requirements.txt
```

Prepare environment

Create a `.env` file in the project root with at least:

```
DISCORD_TOKEN=your_bot_token
DISCORD_CHANNEL=123456789012345678
```

If your bot needs message text, enable the Message Content Intent in the Discord Developer Portal for your application (Developer Portal → Applications → your app → Bot → toggle "Message Content Intent").

Invite the bot to the server with at least these bot permissions: `View Channels`, `Read Message History`.

Run

```bash
# using .env
python3 discord_fetch.py --out channel_messages.json

# or specify channel/token directly
python3 discord_fetch.py --channel 123456789012345678 --token YOUR_TOKEN --out channel_messages.json
```

Notes
- The script will respect Discord permissions — the bot must be a member of the guild and have permission to view the channel and read its history.
- Sensitive data (bot tokens and exported messages) should not be committed. See `.gitignore` for defaults.

