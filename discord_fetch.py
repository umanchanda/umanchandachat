#!/usr/bin/env python3
"""
Fetch messages from a single Discord channel and save them to a JSON file.

Usage:
  python discord_fetch.py --channel CHANNEL_ID [--token TOKEN] [--limit N] [--out file.json]
Or set the bot token in the `DISCORD_TOKEN` environment variable.
"""
import argparse
import os
import json
import discord
from dotenv import load_dotenv


def parse_args():
    p = argparse.ArgumentParser(description="Fetch messages from a Discord channel")
    p.add_argument("--token", help="Discord bot token (or set DISCORD_TOKEN env var)")
    p.add_argument("--channel", type=int, help="Channel ID to fetch from (or set DISCORD_CHANNEL in .env)")
    p.add_argument("--limit", type=int, default=None, help="Maximum number of messages to fetch (default: all)")
    p.add_argument("--out", default="messages.json", help="Output JSON file (default: messages.json)")
    return p.parse_args()


class FetchClient(discord.Client):
    def __init__(self, channel_id, limit, outfile, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.channel_id = channel_id
        self.limit = limit
        self.outfile = outfile

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        try:
            channel = self.get_channel(self.channel_id)
            if channel is None:
                channel = await self.fetch_channel(self.channel_id)

            # Diagnostic: print channel/guild/member and permission info before fetching
            try:
                print("Channel resolved:", type(channel), getattr(channel, "id", None))
                if getattr(channel, "guild", None):
                    guild = channel.guild
                    print("Guild:", getattr(guild, "name", None), getattr(guild, "id", None))
                    try:
                        member = guild.get_member(self.user.id) or await guild.fetch_member(self.user.id)
                    except Exception as em:
                        print("Could not fetch member from guild:", em)
                        member = None
                    perms = channel.permissions_for(member) if member else None
                    print("Bot permissions on channel:", perms)
                else:
                    print("Channel has no guild (likely a DM or unsupported channel type).")
            except Exception as ex:
                print("Error during permission diagnostic:", ex)

            messages = []
            async for m in channel.history(limit=self.limit, oldest_first=True):
                messages.append({
                    "id": m.id,
                    "author": {"id": getattr(m.author, 'id', None), "name": str(m.author)},
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                    "content": m.content,
                    "attachments": [a.url for a in m.attachments],
                    "embeds": [e.to_dict() for e in m.embeds],
                    "pinned": m.pinned,
                    "mention_everyone": m.mention_everyone,
                })

            with open(self.outfile, "w", encoding="utf-8") as f:
                json.dump(messages, f, ensure_ascii=False, indent=2)

            print(f"Wrote {len(messages)} messages to {self.outfile}")
        except Exception as e:
            print("Error while fetching messages:", e)
        await self.close()


def main():
    # Load environment variables from a local .env file (if present)
    load_dotenv()

    args = parse_args()
    token = args.token or os.getenv("DISCORD_TOKEN")
    if not token:
        print("No token provided. Use --token or set DISCORD_TOKEN environment variable.")
        raise SystemExit(1)

    # Determine channel ID: prefer CLI arg, fall back to .env keys
    channel_id = args.channel
    if channel_id is None:
        env_channel = os.getenv("DISCORD_CHANNEL") or os.getenv("CHANNEL_ID") or os.getenv("CHANNEL")
        if env_channel:
            try:
                channel_id = int(env_channel)
            except ValueError:
                print("Environment variable for channel must be an integer.")
                raise SystemExit(1)

    if channel_id is None:
        print("No channel ID provided. Use --channel or set DISCORD_CHANNEL in .env.")
        raise SystemExit(1)

    intents = discord.Intents.default()
    intents.guilds = True
    intents.messages = True
    intents.message_content = True

    client = FetchClient(
        channel_id=channel_id,
        limit=args.limit,
        outfile=args.out,
        intents=intents,
    )
    client.run(token)


if __name__ == "__main__":
    main()
