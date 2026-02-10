#!/usr/bin/env python3

import argparse
import subprocess
import sys
import time
from pathlib import Path

def print_summary(results: dict):
    print("\n\n================ FINAL GENERATION SUMMARY ================")
    print("\nScene  | Coarse | Populate | Fine | Road | Export")
    print("---------------------------------------------------")

    for scene, steps in results.items():
        print(
            f"{scene}     |"
            f"   {steps['coarse']}    |"
            f"    {steps['populate']}     |"
            f"  {steps['fine']}   |"
            f"   {steps['road']}  |"
            f"    {steps['export']}"
        )

    print("\nLegend: O = Success | X = Fail | - = Skipped")
    print("==========================================================\n")


def run_command(cmd: list[str], step_name: str) -> bool:
    """
    Run a shell command and return True if successful, False otherwise.
    """
    print(f"\n=== Running {step_name} ===")
    print(" ".join(cmd))

    try:
        subprocess.run(cmd, check=True)
        print(f"[BASH_GENERATION] {step_name} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[BASH_GENERATION] {step_name} FAILED (exit code {e.returncode})")
        return False

def main(num_runs: int, start_idx: int, seed: int):
    summary = {}   # <-- store all results
    for i in range(start_idx, start_idx + num_runs):
        idx = f"{i:02d}"
        if seed: # setting seed to terrain index
            seed = i
        # init status
        summary[idx] = {
            "coarse": "-",
            "populate": "-",
            "fine": "-",
            "road": "-",
            "export": "-"
        }

        print(f"\n\n##############################")
        print(f"### Generating scene {idx} ###")
        print(f"##############################")

        coarse_dir = f"outputs/Terrains/plain_coarse_{idx}"
        pop_dir = f"outputs/Terrains/plain_pop_{idx}"
        popfine_dir = f"outputs/Terrains/plain_popfine_{idx}"
        export_dir = f"outputs/Terrains/plain_usd_{idx}"

        # Step 1: Coarse terrain
        if seed:
            step1 = [
                sys.executable, "-m", "infinigen_examples.generate_nature",
                "--task", "coarse",
                "--seed", f"{seed}",
                "-g", "base_nature", "simple", "plain",
                "--output_folder", coarse_dir
            ]
        else:
            step1 = [
                sys.executable, "-m", "infinigen_examples.generate_nature",
                "--task", "coarse",
                "-g", "base_nature", "simple", "plain",
                "--output_folder", coarse_dir
            ]

        if not run_command(step1, "Step 1 (Coarse Terrain)"):
            summary[idx]["coarse"] = "X"
            continue
        summary[idx]["coarse"] = "O"

        # Step 2: Populate
        if seed:
            step2 = [
                sys.executable, "-m", "infinigen_examples.generate_nature",
                "--task", "populate",
                "--seed", f"{seed}",
                "-g", "base_nature", "simple", "plain",
                "--input_folder", coarse_dir,
                "--output_folder", pop_dir
            ]
        else:
            step2 = [
                sys.executable, "-m", "infinigen_examples.generate_nature",
                "--task", "populate",
                "-g", "base_nature", "simple", "plain",
                "--input_folder", coarse_dir,
                "--output_folder", pop_dir
            ]

        if not run_command(step2, "Step 2 (Populate Assets)"):
            summary[idx]["populate"] = "X"
            continue
        summary[idx]["populate"] = "O"

        # Step 3: Fine terrain
        if seed:
            step3 = [
                sys.executable, "-m", "infinigen_examples.generate_nature",
                "--task", "fine_terrain",
                "--seed", f"{seed}",
                "-g", "base_nature", "simple", "plain",#, "cuda",
                "--input_folder", pop_dir,
                "--output_folder", popfine_dir
            ]
        else:
            step3 = [
                sys.executable, "-m", "infinigen_examples.generate_nature",
                "--task", "fine_terrain",
                "-g", "base_nature", "simple", "plain",#, "cuda",
                "--input_folder", pop_dir,
                "--output_folder", popfine_dir
            ]

        fine_success = run_command(step3, "Step 3 (Fine Terrain)")
        summary[idx]["fine"] = "O" if fine_success else "X"
        
        # Step 4: Apply road
        if fine_success:
            step4 = [
            sys.executable, "-m", "infinigen_examples.apply_road",
            "--", f"{popfine_dir}/scene.blend"
            ]
        else:
            step4 = [
            sys.executable, "-m", "infinigen_examples.apply_road",
            "--", f"{pop_dir}/scene.blend"
            ]
            
        road_success = run_command(step4, "Step 4 (Apply Road)")
        summary[idx]["road"] = "O" if road_success else "X"
        
        # Step 5: Export
        export_input = popfine_dir if fine_success else pop_dir

        step5 = [
            sys.executable, "-m", "infinigen.tools.export",
            "--input_folder", export_input,
            "--output_folder", export_dir,
            "-f", "usdc",
            "-r", "1024",
            "--omniverse"
        ]

        if road_success: # Skip export if road is not attached.
            export_success = run_command(step5, "Step 5 (Export)")
            summary[idx]["export"] = "O" if export_success else "X"

        print(f"[BASH_GENERATION] Scene {idx} completed\n")

    print_summary(summary)



if __name__ == "__main__":
    start_time = time.time()
    parser = argparse.ArgumentParser(description="Batch Infinigen terrain generation")
    parser.add_argument("--num_runs", type=int, required=True, help="Number of scenes to generate")
    parser.add_argument("--start_idx", type=int, default=0, help="Starting index (default: 0)")
    parser.add_argument("--s", type=int, default=0, help="Seed for generation (on/off) (default: 0)")

    args = parser.parse_args()
    main(args.num_runs, args.start_idx, args.s)
    print("Bash generation executed in %s seconds" % (time.time() - start_time))
