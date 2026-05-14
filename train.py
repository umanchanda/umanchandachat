"""
Fine-tune DialoGPT-small on Discord conversation pairs.

Usage:
    python train.py                         # uses training_data.json
    python train.py --data my_data.json     # custom data file
    python train.py --model microsoft/DialoGPT-medium  # larger base model
"""

import argparse
import json

import torch
from torch.utils.data import Dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments

DEFAULT_BASE_MODEL = "microsoft/DialoGPT-small"
DEFAULT_DATA_FILE = "training_data.json"
DEFAULT_OUTPUT_DIR = "./model"


class ConversationDataset(Dataset):
    def __init__(self, pairs, tokenizer, max_length=512):
        self.examples = []
        skipped = 0
        for context, response in pairs:
            turns = list(context) + [response]
            text = tokenizer.eos_token.join(turns) + tokenizer.eos_token
            enc = tokenizer(
                text,
                max_length=max_length,
                truncation=True,
                padding="max_length",
                return_tensors="pt",
            )
            ids = enc["input_ids"].squeeze()
            mask = enc["attention_mask"].squeeze()
            # skip examples that are entirely padding after truncation
            if mask.sum() < 4:
                skipped += 1
                continue
            self.examples.append({"input_ids": ids, "labels": ids.clone(), "attention_mask": mask})
        if skipped:
            print(f"Skipped {skipped} examples (too short after truncation)")

    def __len__(self):
        return len(self.examples)

    def __getitem__(self, idx):
        return self.examples[idx]


def train(data_file=DEFAULT_DATA_FILE, base_model=DEFAULT_BASE_MODEL, output_dir=DEFAULT_OUTPUT_DIR):
    print(f"Loading data from {data_file} ...")
    with open(data_file, encoding="utf-8") as f:
        pairs = json.load(f)
    print(f"  {len(pairs)} conversation pairs")

    print(f"Loading base model: {base_model}")
    tokenizer = AutoTokenizer.from_pretrained(base_model)
    tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(base_model)

    print("Building dataset ...")
    dataset = ConversationDataset(pairs, tokenizer)
    print(f"  {len(dataset)} training examples")

    use_fp16 = torch.cuda.is_available()
    args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=3,
        per_device_train_batch_size=4,
        gradient_accumulation_steps=2,
        learning_rate=5e-5,
        warmup_steps=100,
        save_steps=500,
        save_total_limit=2,
        logging_steps=50,
        fp16=use_fp16,
        report_to="none",
    )

    trainer = Trainer(model=model, args=args, train_dataset=dataset)

    print("Training ...")
    trainer.train()

    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    print(f"Model saved to {output_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default=DEFAULT_DATA_FILE)
    parser.add_argument("--model", default=DEFAULT_BASE_MODEL)
    parser.add_argument("--output", default=DEFAULT_OUTPUT_DIR)
    opts = parser.parse_args()
    train(data_file=opts.data, base_model=opts.model, output_dir=opts.output)
