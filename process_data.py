import json
import csv
import re
import sys
from pathlib import Path

BOT_PREFIXES = ("!", "/", "$", ".", "?", "-")
MIN_WORDS = 2
MAX_LENGTH = 300


def _is_usable(text):
    text = text.strip()
    if not text or len(text) > MAX_LENGTH:
        return False
    if text.startswith(BOT_PREFIXES):
        return False
    if re.fullmatch(r"(<@!?\d+>[\s,]*)+", text):
        return False
    if re.fullmatch(r"https?://\S+", text):
        return False
    if len(text.split()) < MIN_WORDS:
        return False
    return True


def _extract_content(msg):
    """Pull message text from either DiscordChatExporter or official export format."""
    return (
        msg.get("content")
        or msg.get("Contents")
        or msg.get("text")
        or ""
    ).strip()


def _load_json_file(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return [_extract_content(m) for m in data]
    if isinstance(data, dict) and "messages" in data:
        return [
            _extract_content(m)
            for m in data["messages"]
            if m.get("type") in ("Default", "default", 0, None)
        ]
    return []


def _load_csv_file(path):
    messages = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            messages.append(_extract_content(row))
    return messages


def load_discord_export(data_path):
    """Load messages from a Discord export directory or single JSON file."""
    data_path = Path(data_path)
    raw = []

    if data_path.is_file():
        if data_path.suffix == ".json":
            raw = _load_json_file(data_path)
        elif data_path.suffix == ".csv":
            raw = _load_csv_file(data_path)
    elif data_path.is_dir():
        for p in sorted(data_path.rglob("*.json")):
            raw.extend(_load_json_file(p))
        for p in sorted(data_path.rglob("*.csv")):
            raw.extend(_load_csv_file(p))

    messages = [m for m in raw if _is_usable(m)]
    return messages


def create_conversation_pairs(messages, context_window=3):
    """Slide a window over sequential messages to build (context, response) pairs."""
    pairs = []
    for i in range(len(messages) - 1):
        context = messages[max(0, i - context_window + 1) : i + 1]
        response = messages[i + 1]
        if response and all(context):
            pairs.append((context, response))
    return pairs


def save_training_data(pairs, output_file="training_data.json"):
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(pairs, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(pairs)} conversation pairs → {output_file}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python process_data.py <discord_export_path> [output.json]")
        sys.exit(1)

    export_path = sys.argv[1]
    out_file = sys.argv[2] if len(sys.argv) > 2 else "training_data.json"

    msgs = load_discord_export(export_path)
    print(f"Loaded {len(msgs)} usable messages from {export_path}")

    pairs = create_conversation_pairs(msgs)
    save_training_data(pairs, out_file)
