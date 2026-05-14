import os
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_PATH = os.getenv("MODEL_PATH", "./model")
FALLBACK_MODEL = "microsoft/DialoGPT-small"

MAX_HISTORY_TOKENS = 900
MAX_NEW_TOKENS = 100


def _load_model():
    model_dir = MODEL_PATH if Path(MODEL_PATH).exists() else FALLBACK_MODEL
    source = "fine-tuned model" if model_dir == MODEL_PATH else "base DialoGPT-small"
    print(f"Loading {source} from {model_dir} ...")
    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(model_dir)
    model.eval()
    return tokenizer, model


_tokenizer, _model = _load_model()


def respond(user_input: str, history_ids=None):
    """
    Generate a bot reply given user input and optional prior conversation tensors.

    Returns (reply_text, updated_history_ids).
    history_ids is a 1×N LongTensor that callers should store per session.
    """
    input_ids = _tokenizer.encode(
        user_input + _tokenizer.eos_token, return_tensors="pt"
    )

    bot_input_ids = (
        torch.cat([history_ids, input_ids], dim=-1)
        if history_ids is not None
        else input_ids
    )

    # Trim to keep within token budget
    if bot_input_ids.shape[-1] > MAX_HISTORY_TOKENS:
        bot_input_ids = bot_input_ids[:, -MAX_HISTORY_TOKENS:]

    with torch.no_grad():
        output_ids = _model.generate(
            bot_input_ids,
            max_new_tokens=MAX_NEW_TOKENS,
            pad_token_id=_tokenizer.eos_token_id,
            do_sample=True,
            top_k=50,
            top_p=0.95,
            temperature=0.75,
        )

    reply = _tokenizer.decode(
        output_ids[:, bot_input_ids.shape[-1] :][0],
        skip_special_tokens=True,
    ).strip()

    return reply or "...", output_ids
