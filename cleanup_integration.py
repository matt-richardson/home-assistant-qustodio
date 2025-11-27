#!/usr/bin/env python3
"""Script to remove Qustodio integration and clean up all entities/devices."""
import json
import sys
from pathlib import Path

def cleanup_integration(storage_dir: Path):
    """Remove Qustodio integration from all storage files."""

    # Files to clean
    config_entries_file = storage_dir / "core.config_entries"
    entity_registry_file = storage_dir / "core.entity_registry"
    device_registry_file = storage_dir / "core.device_registry"

    changes_made = []

    # 1. Remove config entry
    if config_entries_file.exists():
        print(f"Processing {config_entries_file}")
        with open(config_entries_file, 'r') as f:
            data = json.load(f)

        original_count = len(data['data']['entries'])
        data['data']['entries'] = [
            entry for entry in data['data']['entries']
            if entry.get('domain') != 'qustodio'
        ]
        removed_count = original_count - len(data['data']['entries'])

        if removed_count > 0:
            with open(config_entries_file, 'w') as f:
                json.dump(data, f, indent=2)
            changes_made.append(f"Removed {removed_count} config entry/entries")

    # 2. Remove entities
    if entity_registry_file.exists():
        print(f"Processing {entity_registry_file}")
        with open(entity_registry_file, 'r') as f:
            data = json.load(f)

        original_count = len(data['data']['entities'])
        data['data']['entities'] = [
            entity for entity in data['data']['entities']
            if entity.get('platform') != 'qustodio'
        ]
        removed_count = original_count - len(data['data']['entities'])

        if removed_count > 0:
            with open(entity_registry_file, 'w') as f:
                json.dump(data, f, indent=2)
            changes_made.append(f"Removed {removed_count} entities")

    # 3. Remove devices
    if device_registry_file.exists():
        print(f"Processing {device_registry_file}")
        with open(device_registry_file, 'r') as f:
            data = json.load(f)

        original_count = len(data['data']['devices'])
        data['data']['devices'] = [
            device for device in data['data']['devices']
            if not any(
                identifier[0] == 'qustodio'
                for identifier in device.get('identifiers', [])
            )
        ]
        removed_count = original_count - len(data['data']['devices'])

        if removed_count > 0:
            with open(device_registry_file, 'w') as f:
                json.dump(data, f, indent=2)
            changes_made.append(f"Removed {removed_count} devices")

    return changes_made

if __name__ == '__main__':
    storage_dir = Path("homeassistant_test/.storage")

    if not storage_dir.exists():
        print(f"Error: Storage directory not found: {storage_dir}")
        sys.exit(1)

    print("Cleaning up Qustodio integration...")
    changes = cleanup_integration(storage_dir)

    if changes:
        print("\nChanges made:")
        for change in changes:
            print(f"  ✓ {change}")
        print("\n⚠️  You must restart Home Assistant for changes to take effect!")
    else:
        print("No Qustodio data found to clean up.")
