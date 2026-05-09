"""Configuration and shared constants for CogWatch."""

import os

# OpenRouter config
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
LLM_MODEL = "nvidia/nemotron-3-super-120b-a12b:free"
EMBEDDING_MODEL = "openai/text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536

# Detection thresholds
SIMILARITY_THRESHOLD = 0.75
TOP_K_SIMILAR = 5

# InsForge config (loaded from .insforge/project.json or env)
INSFORGE_URL = os.environ.get("INSFORGE_URL", "")
INSFORGE_ANON_KEY = os.environ.get("INSFORGE_ANON_KEY", "")

# GitHub config
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

# Judge model (Gemini via OpenRouter for eval)
JUDGE_MODEL = "google/gemini-2.5-flash"
