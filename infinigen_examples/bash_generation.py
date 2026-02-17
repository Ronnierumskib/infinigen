#!/usr/bin/env python3

import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

# =============================================================================
# SEARCH SPACE DEFINITION
# Define a list of (gin_key, value) tuples to explore. Each entry generates
# one scene per run-index with that single parameter overriding the default
# config. All variants for the same index share the same seed.
#
# Leave the list EMPTY to disable search space mode and run normally.
#
# Examples:
#   GIN_SEARCH_SPACE = [
#       ("compose_nature.tree_density", 0.01),
#       ("compose_nature.tree_density", 0.05),
#       ("compose_nature.grass_select_max", 0.5),
#       ("Terrain.populated_bounds", "(-100, 100, -100, 100, -5, 25)"),
#   ]
# =============================================================================
GIN_SEARCH_SPACE: list[tuple[str, object]] = [
    ("compose_nature.grass_chance", 1),
    ("compose_nature.ferns_chance", 1),
    ("compose_nature.monocots_chance", 1),
    ("compose_nature.flowers_chance", 1),
    ("compose_nature.pinecone_chance", 1),
    ("compose_nature.pine_needle_chance", 1),
    ("compose_nature.rain_particles_chance", 1),
    ("compose_nature.snow_particles_chance", 1),
    ("compose_nature.dust_particles_chance", 1),
    ("compose_nature.leaf_particles_chance", 1),
    ("compose_nature.marine_snow_particles_chance", 1),
]

# Directory where plain.gin lives — override .gin files are written here too
GIN_CONFIG_DIR = Path("infinigen_examples/configs_nature")


# =============================================================================
# GIN HELPERS
# =============================================================================

def gin_key_to_label(gin_key: str, value: object) -> str:
    """
    Build a filesystem-safe label from a gin key + value.
    e.g. ("compose_nature.tree_density", 0.05) -> "tree_density_0.05"
    """
    short_key = gin_key.split(".")[-1]
    safe_value = (
        str(value)
        .replace(" ", "")
        .replace(",", "-")
        .replace("(", "")
        .replace(")", "")
    )
    return f"{short_key}_{safe_value}"


def create_override_gin(gin_key: str, value: object, label: str) -> Path:
    """
    Write a single-line .gin file to GIN_CONFIG_DIR/<label>.gin.
    Returns the Path to the created file.
    """
    if isinstance(value, str):
        gin_value_str = f'"{value}"'
    else:
        gin_value_str = str(value)

    gin_line = f"{gin_key} = {gin_value_str}\n"
    gin_path = GIN_CONFIG_DIR / f"searchspace.gin"
    gin_path.write_text(gin_line)
    print(f"[GIN] created override: {gin_path}  ({gin_line.strip()})")
    return gin_path


def delete_override_gin(gin_path: Path):
    """Delete the temporary override .gin file."""
    try:
        gin_path.unlink()
        print(f"[GIN] deleted override: {gin_path}")
    except FileNotFoundError:
        pass


# =============================================================================
# SUMMARY
# =============================================================================

def print_summary(results: dict):
    print("\n\n================ FINAL GENERATION SUMMARY ================")
    print(f"\n{'Scene':<40} | Coarse | Populate | Fine | Road | Export")
    print("-" * 80)

    for scene_key, steps in results.items():
        print(
            f"{scene_key:<40} |"
            f"   {steps['coarse']}    |"
            f"    {steps['populate']}     |"
            f"  {steps['fine']}   |"
            f"   {steps['road']}  |"
            f"    {steps['export']}"
        )

    print("\nLegend: O = Success | X = Fail | - = Skipped")
    print("==========================================================\n")


# =============================================================================
# COMMAND RUNNER
# =============================================================================

def run_command(cmd: list[str], step_name: str) -> bool:
    """Run a shell command, return True on success."""
    print(f"\n=== Running {step_name} ===")
    print(" ".join(cmd))
    try:
        subprocess.run(cmd, check=True)
        print(f"[BASH_GENERATION] {step_name} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[BASH_GENERATION] {step_name} FAILED (exit code {e.returncode})")
        return False


# =============================================================================
# SCENE GENERATION
# =============================================================================

def generate_scene(
    idx: str,
    seed: int | None,
    summary: dict,
    summary_key: str,
    override_gin_name: str | None = None,
):
    """
    Run all 5 generation steps for one scene.

    Args:
        idx:              Zero-padded scene index string, e.g. "00"
        seed:             Integer seed, or None for random
        summary:          Dict to record step outcomes into
        summary_key:      Key used in summary dict and folder names
        override_gin_name: Stem of the override .gin file (no extension),
                          or None for normal mode. Appended last to -g args.
    """
    summary[summary_key] = {
        "coarse":   "-",
        "populate": "-",
        "fine":     "-",
        "road":     "-",
        "export":   "-",
    }

    header = f"### Generating scene {summary_key} ###"
    print(f"\n\n{'#' * len(header)}")
    print(header)
    print(f"{'#' * len(header)}")
    if seed is not None:
        print(f"    seed : {seed}")
    if override_gin_name:
        print(f"    gin override : {override_gin_name}.gin")

    coarse_dir  = f"outputs/Terrains/plain_coarse_{summary_key}"
    pop_dir     = f"outputs/Terrains/plain_pop_{summary_key}"
    popfine_dir = f"outputs/Terrains/plain_popfine_{summary_key}"
    export_dir  = f"outputs/Terrains/plain_usd_{summary_key}"

    seed_args = ["--seed", str(seed)] if seed is not None else []

    # Base configs — override appended at the end if present
    gin_configs = ["base_nature", "simple", "plain"]
    if override_gin_name:
        gin_configs.append(override_gin_name)
    g_args = ["-g"] + gin_configs

    # ------------------------------------------------------------------
    # Step 1: Coarse terrain
    # ------------------------------------------------------------------
    step1 = [
        sys.executable, "-m", "infinigen_examples.generate_nature",
        "--task", "coarse",
        *seed_args,
        *g_args,
        "--output_folder", coarse_dir,
    ]
    if not run_command(step1, "Step 1 (Coarse Terrain)"):
        summary[summary_key]["coarse"] = "X"
        return
    summary[summary_key]["coarse"] = "O"

    # ------------------------------------------------------------------
    # Step 2: Populate
    # ------------------------------------------------------------------
    step2 = [
        sys.executable, "-m", "infinigen_examples.generate_nature",
        "--task", "populate",
        *seed_args,
        *g_args,
        "--input_folder",  coarse_dir,
        "--output_folder", pop_dir,
    ]
    if not run_command(step2, "Step 2 (Populate Assets)"):
        summary[summary_key]["populate"] = "X"
        return
    summary[summary_key]["populate"] = "O"

    # ------------------------------------------------------------------
    # Step 3: Fine terrain
    # ------------------------------------------------------------------
    step3 = [
        sys.executable, "-m", "infinigen_examples.generate_nature",
        "--task", "fine_terrain",
        *seed_args,
        *g_args,
        "--input_folder",  pop_dir,
        "--output_folder", popfine_dir,
    ]
    fine_success = run_command(step3, "Step 3 (Fine Terrain)")
    summary[summary_key]["fine"] = "O" if fine_success else "X"

    # ------------------------------------------------------------------
    # Step 4: Apply road
    # ------------------------------------------------------------------
    blend_input = popfine_dir if fine_success else pop_dir
    step4 = [
        sys.executable, "-m", "infinigen_examples.apply_road",
        "--", f"{blend_input}/scene.blend",
    ]
    road_success = run_command(step4, "Step 4 (Apply Road)")
    summary[summary_key]["road"] = "O" if road_success else "X"

    # ------------------------------------------------------------------
    # Step 5: Export (skipped if road failed)
    # ------------------------------------------------------------------
    export_input = popfine_dir if fine_success else pop_dir
    step5 = [
        sys.executable, "-m", "infinigen.tools.export",
        "--input_folder",  export_input,
        "--output_folder", export_dir,
        "-f", "usdc",
        "-r", "1024",
        "--omniverse",
    ]
    if road_success:
        export_success = run_command(step5, "Step 5 (Export)")
        summary[summary_key]["export"] = "O" if export_success else "X"

    print(f"[BASH_GENERATION] Scene {summary_key} completed\n")


# =============================================================================
# MAIN
# =============================================================================

def main(num_runs: int, start_idx: int, use_seed: bool):
    summary: dict = {}

    if not GIN_CONFIG_DIR.exists():
        print(f"[ERROR] GIN_CONFIG_DIR not found: {GIN_CONFIG_DIR}")
        sys.exit(1)

    for i in range(start_idx, start_idx + num_runs):
        idx  = f"{i:02d}"
        seed = i if use_seed else None

        if GIN_SEARCH_SPACE:
            # ----------------------------------------------------------------
            # SEARCH SPACE MODE
            # ----------------------------------------------------------------
            print(f"\n\n{'=' * 60}")
            print(f"=== Scene {idx} — {len(GIN_SEARCH_SPACE)} config variant(s) ===")
            print(f"{'=' * 60}")

            for gin_key, value in GIN_SEARCH_SPACE:
                label       = gin_key_to_label(gin_key, value)
                summary_key = f"{idx}_{label}"

                override_gin = create_override_gin(gin_key, value, label)
                try:
                    generate_scene(
                        idx=idx,
                        seed=seed,
                        summary=summary,
                        summary_key=summary_key,
                        override_gin_name="searchspace",
                    )
                finally:
                    delete_override_gin(override_gin)

        else:
            # ----------------------------------------------------------------
            # NORMAL MODE
            # ----------------------------------------------------------------
            generate_scene(
                idx=idx,
                seed=seed,
                summary=summary,
                summary_key=idx,
                override_gin_name=None,
            )

    print_summary(summary)


if __name__ == "__main__":
    start_time = time.time()

    parser = argparse.ArgumentParser(description="Batch Infinigen terrain generation")
    parser.add_argument("--num_runs",  type=int, required=True, help="Number of scenes to generate")
    parser.add_argument("--start_idx", type=int, default=0,     help="Starting index (default: 0)")
    parser.add_argument("--s",         type=int, default=0,     help="Use scene index as seed (1=on, 0=off)")

    args = parser.parse_args()
    main(args.num_runs, args.start_idx, bool(args.s))
    print("Bash generation executed in %s seconds" % (time.time() - start_time))