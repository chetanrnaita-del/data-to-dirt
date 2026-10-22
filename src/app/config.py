"""
Data-to-Dirt — Configuration & System Constants
"""

import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
SRC_DIR = BASE_DIR / "src"
UI_DIR = SRC_DIR / "ui"
DATA_DIR = BASE_DIR / "data"

# Ensure data dir exists
os.makedirs(DATA_DIR, exist_ok=True)

# Networking
DEFAULT_PORT = 8088
DEFAULT_HOST = "0.0.0.0"

# Scientific Carbon Model Constants
KWH_PER_GB_YEAR = 0.28            # Operational energy per GB/yr (PUE 1.35 standard)
GRID_INTENSITY_SINGAPORE = 405.7   # g CO2e / kWh (Singapore EMA benchmark)
GLOBAL_GRID_INTENSITY = 475.0      # g CO2e / kWh (IEA average)
TREE_ABSORPTION_KG_YEAR = 20.0     # kg CO2 sequestered by 1 mature tree per year

# Ecological Reforestation Triggers
TREE_DONATION_THRESHOLD_BYTES = 1024 * 1024 * 1024  # 1.0 GB
TREE_DONATION_COST_USD = 1.50                       # USD per tree planted

# Gamification Rules
DAILY_DELETION_LIMIT = 5           # Max verified deletions per student per day
POINTS_PER_MB_DELETED = 0.5        # Base eco-points
POINTS_PER_STREAK_DAY = 15         # Streak bonus points
PENALTY_POINTS_FLAG = 50           # Deduction for intentional gaming strike

# Tree Growth Stage Thresholds (in bytes deleted)
# Stage 0: Prepared Soil (0 to 1 MB)
# Stage 1: The Sprout (1 MB to 50 MB)
# Stage 2: The Sapling (50 MB to 250 MB)
# Stage 3: Young Oak (250 MB to 1 GB)
# Stage 4: Ancient Tree (1 GB to 5 GB)
# Stage 5: Legendary Golden Tree (>5 GB)
TREE_STAGE_THRESHOLDS = [
    (0, "Prepared Soil"),
    (1 * 1024 * 1024, "The Sprout"),
    (50 * 1024 * 1024, "The Sapling"),
    (250 * 1024 * 1024, "Young Oak"),
    (1024 * 1024 * 1024, "Ancient Tree"),
    (5 * 1024 * 1024 * 1024, "Legendary Golden Tree"),
]
