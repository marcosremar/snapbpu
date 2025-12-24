#!/usr/bin/env python3
"""
Quick Fine-tuning Test Script for Dumont Cloud Jobs
Uses Qwen2.5-0.5B (small, fast) with a tiny dataset

This script:
1. Loads a small LLM (Qwen2.5-0.5B-Instruct)
2. Fine-tunes for 3 steps (just to test the pipeline)
3. Saves the model
4. Creates completion marker

Expected runtime: ~2-5 minutes on any GPU
"""

import os
import sys
import torch
from datetime import datetime

# Completion marker path
MARKER_PATH = "/workspace/.job_complete"
FAILED_MARKER = "/workspace/.job_failed"

def log(msg):
    """Print with timestamp"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def main():
    log("=" * 60)
    log("Dumont Cloud Job Test - Quick Fine-tuning")
    log("=" * 60)

    try:
        # Check GPU
        log(f"PyTorch version: {torch.__version__}")
        log(f"CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            log(f"GPU: {torch.cuda.get_device_name(0)}")
            log(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")

        # Import transformers
        log("Importing transformers...")
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
            TrainingArguments,
            Trainer,
            DataCollatorForLanguageModeling
        )
        from datasets import Dataset

        # Model config
        MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"
        OUTPUT_DIR = "/workspace/output/qwen-finetuned"

        log(f"Loading model: {MODEL_NAME}")

        # Load tokenizer
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        # Load model (4-bit for speed)
        log("Loading model (this may take 1-2 min)...")
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_NAME,
            torch_dtype=torch.float16,
            device_map="auto",
            trust_remote_code=True,
        )
        log(f"Model loaded! Parameters: {model.num_parameters():,}")

        # Create tiny dataset (just for testing)
        log("Creating test dataset...")
        train_texts = [
            "Question: What is Dumont Cloud?\nAnswer: Dumont Cloud is a GPU cloud management platform that provides auto-hibernation and fast failover.",
            "Question: How does Dumont save money?\nAnswer: Dumont automatically hibernates idle GPUs and restores them in seconds when needed.",
            "Question: What is GPU warm pool?\nAnswer: GPU warm pool keeps a backup GPU ready for instant failover if the primary fails.",
            "Question: What is CPU standby?\nAnswer: CPU standby is a small CPU instance that syncs data continuously for fast recovery.",
            "Question: How fast is Dumont restore?\nAnswer: Dumont can restore a GPU environment in under 15 seconds using optimized snapshots.",
        ]

        # Tokenize
        def tokenize(text):
            return tokenizer(
                text,
                truncation=True,
                max_length=128,
                padding="max_length",
                return_tensors="pt"
            )

        tokenized = [tokenize(t) for t in train_texts]
        dataset = Dataset.from_dict({
            "input_ids": [t["input_ids"].squeeze() for t in tokenized],
            "attention_mask": [t["attention_mask"].squeeze() for t in tokenized],
        })

        log(f"Dataset size: {len(dataset)} samples")

        # Training arguments (minimal, just for testing)
        log("Setting up training...")
        training_args = TrainingArguments(
            output_dir=OUTPUT_DIR,
            num_train_epochs=1,
            max_steps=3,  # Just 3 steps for quick test
            per_device_train_batch_size=1,
            gradient_accumulation_steps=1,
            learning_rate=2e-5,
            logging_steps=1,
            save_steps=3,
            save_total_limit=1,
            fp16=True,
            report_to="none",  # No wandb/tensorboard
        )

        # Data collator
        data_collator = DataCollatorForLanguageModeling(
            tokenizer=tokenizer,
            mlm=False,  # Causal LM, not masked
        )

        # Trainer
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=dataset,
            data_collator=data_collator,
        )

        # Train!
        log("Starting training (3 steps)...")
        trainer.train()

        log("Training complete!")

        # Save model
        log(f"Saving model to {OUTPUT_DIR}...")
        trainer.save_model(OUTPUT_DIR)
        tokenizer.save_pretrained(OUTPUT_DIR)

        log("Model saved!")

        # Create completion marker
        log("Creating completion marker...")
        os.makedirs(os.path.dirname(MARKER_PATH), exist_ok=True)
        with open(MARKER_PATH, "w") as f:
            f.write(f"Job completed at {datetime.now().isoformat()}\n")
            f.write(f"Model: {MODEL_NAME}\n")
            f.write(f"Output: {OUTPUT_DIR}\n")

        log("=" * 60)
        log("JOB COMPLETED SUCCESSFULLY!")
        log("=" * 60)

        return 0

    except Exception as e:
        log(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

        # Create failed marker
        with open(FAILED_MARKER, "w") as f:
            f.write(f"Job failed at {datetime.now().isoformat()}\n")
            f.write(f"Error: {str(e)}\n")

        return 1

if __name__ == "__main__":
    sys.exit(main())
