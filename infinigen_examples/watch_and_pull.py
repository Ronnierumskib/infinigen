#!/usr/bin/env python3
"""
watch_and_pull.py  —  run this on your LOCAL machine (WSL)

Polls the VM over SSH, detects newly completed plain_usd_* scene folders,
and scp's export_scene.blend down as each one finishes.

Usage:
    python3 -m infinigen_examples.watch_and_pull \
        --host 58.123.93.163 \
        --port 40264 \
        --user root \
        --remote_dir /workspace/infinigen/outputs/Terrains \
        --local_dir /mnt/c/vm_results \
        --poll 30 \
        --timeout 0

Arguments:
    --host        VM IP address
    --port        SSH port
    --user        SSH user (default: root)
    --remote_dir  Remote directory containing plain_usd_* folders
    --local_dir   Local destination directory
    --poll        Seconds between polls (default: 30)
    --timeout     Stop after this many seconds with no new scenes (default: 600).
                  Set to 0 to run until Ctrl+C.
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path


def ssh_list_completed(host: str, port: int, user: str, remote_dir: str) -> list[str]:
    """
    Ask the VM to list all plain_usd_* folders that contain export_scene.blend.
    Returns a list of folder names, e.g. ['plain_usd_00', 'plain_usd_01_tree_density_0.05'].
    Returns an empty list on SSH failure (VM may still be booting or busy).
    """
    # find all export_scene.blend files one level inside plain_usd_* dirs,
    # then print just the parent folder name
    remote_cmd = (
        f"find {remote_dir} -maxdepth 2 -name 'export_scene.blend' "
        f"| sed 's|/export_scene.blend||' | xargs -I{{}} basename {{}}"
    )
    cmd = [
        "ssh",
        "-p", str(port),
        "-o", "ConnectTimeout=10",
        "-o", "StrictHostKeyChecking=no",
        f"{user}@{host}",
        remote_cmd,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        if result.returncode != 0:
            print(f"[WARN] SSH list failed: {result.stderr.strip()}")
            return []
        lines = [l.strip() for l in result.stdout.splitlines() if l.strip()]
        return lines
    except subprocess.TimeoutExpired:
        print("[WARN] SSH list timed out")
        return []
    except Exception as e:
        print(f"[WARN] SSH list error: {e}")
        return []


def scp_scene(
    host: str,
    port: int,
    user: str,
    remote_dir: str,
    scene_folder: str,
    local_dir: Path,
) -> bool:
    """
    scp export_scene.blend from the given scene folder on the VM to local_dir/scene_folder/.
    Returns True on success.
    """
    remote_file = f"{remote_dir}/{scene_folder}/export_scene.blend"
    local_scene_dir = local_dir / scene_folder
    local_scene_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "scp",
        "-r",
        "-P", str(port),
        "-o", "ConnectTimeout=10",
        "-o", "StrictHostKeyChecking=no",
        f"{user}@{host}:{remote_file}",
        str(local_scene_dir),
    ]

    print(f"\n[PULL] {scene_folder}")
    print("  " + " ".join(cmd))

    try:
        result = subprocess.run(cmd, timeout=3000)  # 50 min max per file
        if result.returncode == 0:
            print(f"[OK]   {scene_folder} -> {local_scene_dir}/export_scene.blend")
            return True
        else:
            print(f"[FAIL] scp exited with code {result.returncode}")
            return False
    except subprocess.TimeoutExpired:
        print(f"[FAIL] scp timed out for {scene_folder}")
        return False
    except Exception as e:
        print(f"[FAIL] scp error: {e}")
        return False


def main(
    host: str,
    port: int,
    user: str,
    remote_dir: str,
    local_dir: Path,
    poll: int,
    timeout: int,
):
    local_dir.mkdir(parents=True, exist_ok=True)

    pulled: set[str] = set()       # scenes already transferred
    failed: set[str] = set()       # scenes that failed transfer (won't retry)
    last_new_scene = time.time()   # used for timeout tracking

    print(f"\n{'=' * 60}")
    print(f"  watch_and_pull starting")
    print(f"  VM      : {user}@{host}:{port}")
    print(f"  remote  : {remote_dir}")
    print(f"  local   : {local_dir}")
    print(f"  poll    : every {poll}s")
    print(f"  timeout : {'never (Ctrl+C to stop)' if timeout == 0 else f'{timeout}s of no new scenes'}")
    print(f"{'=' * 60}\n")

    try:
        while True:
            now = time.time()

            # Timeout check
            if timeout > 0 and (now - last_new_scene) > timeout:
                print(f"\n[INFO] No new scenes for {timeout}s — exiting.")
                break

            print(f"[POLL] {time.strftime('%H:%M:%S')} — checking VM...")
            completed = ssh_list_completed(host, port, user, remote_dir)

            new_scenes = [s for s in completed if s not in pulled and s not in failed]

            if new_scenes:
                print(f"[INFO] {len(new_scenes)} new scene(s) ready: {new_scenes}")
                for scene in new_scenes:
                    success = scp_scene(host, port, user, remote_dir, scene, local_dir)
                    if success:
                        pulled.add(scene)
                        last_new_scene = time.time()
                    else:
                        failed.add(scene)
            else:
                already = len(pulled)
                print(f"[INFO] No new scenes (already pulled: {already})")

            time.sleep(poll)

    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user.")

    # Final summary
    print(f"\n{'=' * 60}")
    print(f"  DONE")
    print(f"  Pulled  : {len(pulled)} scene(s)")
    if pulled:
        for s in sorted(pulled):
            print(f"            {s}")
    if failed:
        print(f"  Failed  : {len(failed)} scene(s)")
        for s in sorted(failed):
            print(f"            {s}")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Poll a remote VM and pull completed Infinigen scenes via scp"
    )
    parser.add_argument("--host",       required=True,              help="VM IP address")
    parser.add_argument("--port",       type=int, required=True,    help="SSH port")
    parser.add_argument("--user",       default="root",             help="SSH user (default: root)")
    parser.add_argument("--remote_dir", required=True,              help="Remote Terrains output directory")
    parser.add_argument("--local_dir",  required=True,              help="Local destination directory")
    parser.add_argument("--poll",       type=int, default=30,       help="Poll interval in seconds (default: 30)")
    parser.add_argument("--timeout",    type=int, default=600,
                        help="Exit after N seconds with no new scenes. 0 = run until Ctrl+C (default: 600)")

    args = parser.parse_args()
    main(
        host=args.host,
        port=args.port,
        user=args.user,
        remote_dir=args.remote_dir,
        local_dir=Path(args.local_dir),
        poll=args.poll,
        timeout=args.timeout,
    )