#!/usr/bin/env python3
import subprocess
import os
import logging
from datetime import datetime

# ------------------------------------------------------------
# Logging setup
# ------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# ------------------------------------------------------------
# Constants
# ------------------------------------------------------------
BASE_OUTPUT_DIR = "/mnt/c/isaac-sim/RoadAssets"
NUM_ASSETS = 1

# ------------------------------------------------------------
# Asset configuration
# Only relevant assets, minimal data object
# ------------------------------------------------------------
ASSETS = [
    # Large
    {"name": "bush", "size": "Large", "factory": "BushFactory"},
    {"name": "boulder", "size": "Large", "factory": "BoulderFactory"},
    #{"name": "tree", "size": "Large", "factory": "TreeFlowerFactory"},

    # Medium
    {"name": "ground_leaves", "size": "Medium", "factory": "LeafFactory"},
    #{"name": "ground_twigs", "size": "Medium", "factory": "TwigCoralFactory"},
    #{"name": "chopped_trees", "size": "Medium", "factory": "TreeFlowerFactory"},
    {"name": "rocks", "size": "Medium", "factory": "BlenderRockFactory"},

    # Small
    {"name": "grass", "size": "Small", "factory": "GrassTuftFactory"},
    {"name": "ferns", "size": "Small", "factory": "FernFactory"},
    {"name": "monocots", "size": "Small", "factory": "MonocotFactory"},
    {"name": "flowers", "size": "Small", "factory": "FlowerPlantFactory"},
    {"name": "pinecone", "size": "Small", "factory": "PineconeFactory"},
    {"name": "pine_needle", "size": "Small", "factory": "PineNeedleFactory"},
]

# ------------------------------------------------------------
# Generation function
# ------------------------------------------------------------
def generate_asset(asset):
    output_dir = os.path.join(
        BASE_OUTPUT_DIR,
        asset["size"],
        asset["name"],
    )

    os.makedirs(output_dir, exist_ok=True)

    cmd = [
        "python",
        "-m",
        "infinigen_examples.generate_individual_assets",
        "--output_folder",
        output_dir,
        "-f",
        asset["factory"],
        "-n",
        str(NUM_ASSETS),
        "--render",
        "none",
        "--export",
        "usdc",
    ]

    logging.info(
        "Generating asset: %s | Size: %s | Factory: %s",
        asset["name"],
        asset["size"],
        asset["factory"],
    )
    logging.debug("Command: %s", " ".join(cmd))

    try:
        subprocess.run(cmd, check=True)
        logging.info("✔ Finished %s", asset["name"])
    except subprocess.CalledProcessError as e:
        logging.error("✖ Failed generating %s", asset["name"])
        logging.error(e)


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------
def main():
    start_time = datetime.now()
    logging.info("=== Infinigen Individual Asset Generation Started ===")

    for asset in ASSETS:
        generate_asset(asset)

    elapsed = datetime.now() - start_time
    logging.info("=== Generation completed in %s ===", elapsed)


if __name__ == "__main__":
    main()
