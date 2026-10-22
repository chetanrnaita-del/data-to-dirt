"""
Deterministic Subword/Word Tokenizer for Data-to-Dirt On-Device Neural Network.
Converts text strings and (filename, reason) pairs to padded integer token sequences.
100% offline with zero external dependencies.
"""

import json
import os
import re
from typing import Dict, List, Optional, Union


class SubwordTokenizer:
    """
    Offline tokenizer using a fixed 1024-token vocabulary.
    Converts text strings into fixed-length integer token sequences for the MMCR-Transformer.
    """

    def __init__(self, vocab_path: Optional[str] = None):
        if vocab_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            vocab_path = os.path.join(current_dir, "vocab.json")

        if os.path.exists(vocab_path):
            with open(vocab_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.vocab: Dict[str, int] = data.get("tokens", {})
                self.extensions: Dict[str, int] = data.get("extensions", {})
        else:
            # Fallback built-in dictionary
            self.vocab = {
                "[PAD]": 0, "[UNK]": 1, "[BOS]": 2, "[EOS]": 3, "[SEP]": 4,
                "cache": 10, "temp": 11, "tmp": 12, "duplicate": 13, "copy": 14,
                "raw": 15, "render": 16, "draft": 17, "export": 18, "backup": 19,
                "old": 20, "obsolete": 21,
                "asdf": 100, "points": 101, "score": 102, "free": 103, "farm": 104, "need": 105,
                "system32": 200, "kernel": 201, "password": 202, "secret": 203
            }
            self.extensions = {"other": 0, "tmp": 1, "bak": 3, "log": 4, "mp4": 6, "mov": 7, "zip": 10}

        self.VOCAB = self.vocab
        self.inverse_vocab: Dict[int, str] = {idx: token for token, idx in self.vocab.items()}
        self.pad_id = self.vocab.get("[PAD]", 0)
        self.unk_id = self.vocab.get("[UNK]", 1)
        self.bos_id = self.vocab.get("[BOS]", 2)
        self.eos_id = self.vocab.get("[EOS]", 3)
        self.sep_id = self.vocab.get("[SEP]", 4)

    def clean_text(self, text: str) -> str:
        """Lowercases text and strips non-alphanumeric punctuation while retaining whitespace."""
        if not text:
            return ""
        # Remove null bytes and non-printable control characters
        text = text.replace("\x00", " ")
        # Strip punctuation but preserve word boundaries
        clean = re.sub(r"[^\w\s]", " ", text.lower())
        return clean.strip()

    def tokenize(self, text: str, max_length: int = 64) -> List[int]:
        """
        Tokenizes an input string into a padded integer token array of fixed length (default 64).
        Format: [BOS] + token_1 + token_2 + ... + [EOS] + [PAD]...
        """
        tokens = [self.bos_id]
        clean = self.clean_text(text)
        if clean:
            for word in clean.split():
                token_id = self.vocab.get(word, self.unk_id)
                tokens.append(token_id)
        tokens.append(self.eos_id)

        # Pad or truncate to max_length
        if len(tokens) < max_length:
            tokens.extend([self.pad_id] * (max_length - len(tokens)))
        return tokens[:max_length]

    def encode_pair(self, filename: str, reason: str, max_length: int = 64) -> List[int]:
        """
        Encodes a (filename, reason) pair separated by [SEP].
        Format: [BOS] + filename_tokens + [SEP] + reason_tokens + [EOS] + [PAD]...
        """
        tokens = [self.bos_id]
        clean_fn = self.clean_text(filename)
        if clean_fn:
            for w in clean_fn.split():
                tokens.append(self.vocab.get(w, self.unk_id))

        tokens.append(self.sep_id)

        clean_reason = self.clean_text(reason)
        if clean_reason:
            for w in clean_reason.split():
                tokens.append(self.vocab.get(w, self.unk_id))

        tokens.append(self.eos_id)

        if len(tokens) < max_length:
            tokens.extend([self.pad_id] * (max_length - len(tokens)))
        return tokens[:max_length]

    def decode(self, token_ids: List[int], skip_special_tokens: bool = True) -> str:
        """Decodes integer token IDs back to a human-readable text string."""
        words = []
        special_ids = {self.pad_id, self.bos_id, self.eos_id, self.sep_id}
        for tid in token_ids:
            if skip_special_tokens and tid in special_ids:
                continue
            word = self.inverse_vocab.get(tid, "[UNK]")
            words.append(word)
        return " ".join(words)

    def get_extension_index(self, extension: str) -> int:
        """Maps a file extension string (e.g. '.tmp', 'MP4', 'log') to integer category index (0-31)."""
        if not extension:
            return 0
        norm_ext = extension.lstrip(".").lower()
        return self.extensions.get(norm_ext, 0)
