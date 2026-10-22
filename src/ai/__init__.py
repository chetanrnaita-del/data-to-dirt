"""
Data-to-Dirt AI Accountability Module.
Provides on-device neural network validation, subword tokenization,
training pipeline, and anti-gaming penalty enforcement.
"""

from src.ai.tokenizer import SubwordTokenizer
from src.ai.model import MMCRTransformer
from src.ai.anti_gaming import AntiGamingEngine
from src.ai.generate_dataset import generate_dataset
from src.ai.train import train_model

__all__ = [
    "SubwordTokenizer",
    "MMCRTransformer",
    "AntiGamingEngine",
    "generate_dataset",
    "train_model",
]
