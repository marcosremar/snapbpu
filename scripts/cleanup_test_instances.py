#!/usr/bin/env python3
"""
Cleanup orphaned test GPU instances.

This script destroys VAST.ai instances with test labels that are older
than a specified age (default: 15 minutes).

SAFE to run during tests - only cleans up OLD instances.

Usage:
    python scripts/cleanup_test_instances.py           # Clean instances >15min old
    python scripts/cleanup_test_instances.py --age 30  # Clean instances >30min old
    python scripts/cleanup_test_instances.py --all     # Clean ALL test instances (dangerous!)
    python scripts/cleanup_test_instances.py --dry-run # Show what would be deleted

Environment:
    VAST_API_KEY: Your VAST.ai API key (or set in .env file)
"""

import os
import sys
import time
import argparse
import requests

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_env():
    """Load environment variables from .env file"""
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    k, v = line.strip().split("=", 1)
                    os.environ.setdefault(k, v)


def get_test_instances(api_key: str, max_age_minutes: int = None) -> list:
    """
    Get test instances, optionally filtered by age.

    If max_age_minutes is None, returns ALL test instances.
    Otherwise, only returns instances older than max_age_minutes.
    """
    headers = {"Authorization": f"Bearer {api_key}"}
    resp = requests.get(
        "https://console.vast.ai/api/v0/instances",
        headers=headers,
        timeout=30
    )

    if not resp.ok:
        print(f"Error fetching instances: {resp.status_code}")
        return []

    now = int(time.time())
    max_age_seconds = max_age_minutes * 60 if max_age_minutes else None
    test_instances = []

    for inst in resp.json().get("instances", []):
        label = inst.get("label") or ""

        # Only process test instances
        if not (label.startswith("test_gpu_") or label.startswith("pytest-")):
            continue

        # Calculate age from label timestamp
        age_minutes = None
        age_str = "unknown"

        if label.startswith("pytest-"):
            parts = label.split("-")
            if len(parts) >= 2:
                try:
                    timestamp = int(parts[1])
                    age_seconds = now - timestamp
                    age_minutes = age_seconds // 60
                    age_str = f"{age_minutes}min ago"
                except ValueError:
                    age_str = "old format"

        # Filter by age if specified
        if max_age_seconds is not None:
            if age_minutes is None:
                # Old format labels are always considered orphans
                pass
            elif age_minutes * 60 < max_age_seconds:
                # Too young, skip
                continue

        test_instances.append({
            "id": inst.get("id"),
            "label": label,
            "status": inst.get("actual_status", "unknown"),
            "gpu": inst.get("gpu_name", "unknown"),
            "price": inst.get("dph_total", 0),
            "age": age_str,
            "age_minutes": age_minutes,
        })

    return test_instances


def destroy_instance(api_key: str, instance_id: int) -> bool:
    """Destroy a single instance"""
    headers = {"Authorization": f"Bearer {api_key}"}
    resp = requests.delete(
        f"https://console.vast.ai/api/v0/instances/{instance_id}/",
        headers=headers,
        timeout=30
    )
    return resp.ok


def main():
    parser = argparse.ArgumentParser(description="Cleanup orphaned test GPU instances")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without actually deleting")
    parser.add_argument("--age", type=int, default=15, help="Only delete instances older than AGE minutes (default: 15)")
    parser.add_argument("--all", action="store_true", help="Delete ALL test instances regardless of age (dangerous!)")
    args = parser.parse_args()

    load_env()
    api_key = os.environ.get("VAST_API_KEY")

    if not api_key:
        print("Error: VAST_API_KEY not found in environment or .env file")
        sys.exit(1)

    print("=" * 60)
    print("GPU Test Instance Cleanup")
    print("=" * 60)

    if args.dry_run:
        print("DRY RUN - No instances will be destroyed\n")

    if args.all:
        print("⚠️  WARNING: --all flag - will delete ALL test instances!")
        print("   This is DANGEROUS if tests are running!\n")
        max_age = None
    else:
        max_age = args.age
        print(f"Cleaning instances older than {max_age} minutes")
        print("(Safe to run during tests - young instances are protected)\n")

    # Get test instances
    instances = get_test_instances(api_key, max_age_minutes=max_age)

    if not instances:
        print("No orphaned instances found. All clean!")
        return

    print(f"Found {len(instances)} orphaned instance(s):\n")

    total_cost = 0
    for inst in instances:
        print(f"  ID {inst['id']}: {inst['status']} ({inst['age']})")
        print(f"     GPU: {inst['gpu']}")
        print(f"     Label: {inst['label']}")
        print(f"     Price: ${inst['price']:.4f}/hr")
        total_cost += inst['price']
        print()

    print(f"Total hourly cost: ${total_cost:.4f}/hr")
    print()

    if args.dry_run:
        print("Dry run complete. Use without --dry-run to actually delete.")
        return

    # Confirm before deleting (only for --all or many instances)
    if args.all or len(instances) > 3:
        confirm = input("Type 'DELETE' to confirm destruction: ")
        if confirm != "DELETE":
            print("Aborted.")
            return

    # Destroy instances
    print("\nDestroying instances...")
    destroyed = 0
    for inst in instances:
        print(f"  Destroying {inst['id']} ({inst['label']})...", end=" ")
        if destroy_instance(api_key, inst['id']):
            print("✓")
            destroyed += 1
        else:
            print("✗ FAILED")

    print(f"\nDestroyed {destroyed}/{len(instances)} instances.")


if __name__ == "__main__":
    main()
