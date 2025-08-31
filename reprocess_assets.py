#!/usr/bin/env python3
"""
Asset Reprocessing Script

This script reprocesses existing release databases to apply improved asset classification.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

from release import AssetPlatform, AssetArch, AssetGraphics, AssetSounds, ReleaseAsset, GameRelease


def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )


def load_release_database(file_path: Path) -> List[Dict[str, Any]]:
    """Load the existing release database from JSON file."""
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        logging.info(f"Loaded {len(data)} releases from {file_path}")
        return data
    except (json.JSONDecodeError, IOError) as e:
        logging.error(f"Failed to load release database from {file_path}: {e}")
        raise


def save_release_database(file_path: Path, releases_data: List[Dict[str, Any]]):
    """Save the updated release database to JSON file."""
    try:
        with open(file_path, 'w') as f:
            json.dump(releases_data, f, indent=2)
        logging.info(f"Saved {len(releases_data)} releases to {file_path}")
    except IOError as e:
        logging.error(f"Failed to save release database to {file_path}: {e}")
        raise


def update_asset_descriptors(asset_data: Dict[str, Any]) -> Dict[str, Any]:
    """Update asset descriptors using improved classification logic."""
    filename = asset_data.get('name', '')
    
    # Apply new classification methods
    platform = AssetPlatform.infer_from_filename(filename)
    arch = AssetArch.infer_from_filename(filename)
    graphics = AssetGraphics.infer_from_filename(filename)
    sounds = AssetSounds.infer_from_filename(filename)
    
    # Create updated asset data
    updated_asset = asset_data.copy()
    
    # Update platform (convert from string to enum value)
    old_platform = updated_asset.get('platform')
    updated_asset['platform'] = platform.value
    
    # Add architecture field (new)
    updated_asset['arch'] = arch.value
    
    # Update graphics (convert from boolean to enum value)
    old_graphics = updated_asset.get('graphics')
    updated_asset['graphics'] = graphics.value
    
    # Update sounds (convert from boolean to enum value)
    old_sounds = updated_asset.get('sounds')
    updated_asset['sounds'] = sounds.value
    
    # Log changes if any
    changes = []
    if old_platform != platform.value:
        changes.append(f"platform: {old_platform} -> {platform.value}")
    if 'arch' not in asset_data:
        changes.append(f"arch: added -> {arch.value}")
    if isinstance(old_graphics, bool):
        changes.append(f"graphics: {old_graphics} -> {graphics.value}")
    if isinstance(old_sounds, bool):
        changes.append(f"sounds: {old_sounds} -> {sounds.value}")
    
    if changes:
        logging.debug(f"Asset '{filename}': {', '.join(changes)}")
    
    return updated_asset


def reprocess_release_database(file_path: Path):
    """Reprocess the release database with improved asset descriptors."""
    logging.info(f"Starting reprocessing of {file_path}")
    
    # Load existing database
    releases_data = load_release_database(file_path)
    
    total_assets = 0
    updated_assets = 0
    
    # Process each release
    for release_idx, release_data in enumerate(releases_data):
        release_name = release_data.get('name', f'Release {release_idx}')
        assets = release_data.get('assets', [])
        
        logging.info(f"Processing release '{release_name}' with {len(assets)} assets")
        
        # Process each asset in the release
        updated_release_assets = []
        for asset_data in assets:
            total_assets += 1
            
            # Update asset descriptors
            original_asset = asset_data.copy()
            updated_asset = update_asset_descriptors(asset_data)
            
            # Check if any changes were made
            if updated_asset != original_asset:
                updated_assets += 1
            
            updated_release_assets.append(updated_asset)
        
        # Update the release with the new asset data
        release_data['assets'] = updated_release_assets
    
    # Save the updated database
    save_release_database(file_path, releases_data)
    
    logging.info(f"Reprocessing complete: {updated_assets}/{total_assets} assets updated")
    return updated_assets, total_assets


def find_all_release_databases(base_path: Path) -> List[Path]:
    """Find all release database files in the db directory structure."""
    db_files = []

    if not base_path.exists():
        logging.warning(f"Database directory not found: {base_path}")
        return db_files

    # Look for all game directories
    for game_dir in base_path.iterdir():
        if game_dir.is_dir():
            # Look for the releases JSON file
            releases_file = game_dir / f"{game_dir.name}_releases.json"
            if releases_file.exists():
                db_files.append(releases_file)
                logging.info(f"Found database: {releases_file}")

    return db_files


def main():
    """Main entry point."""
    setup_logging()

    # Define the base database directory
    db_base_path = Path("db")

    # Find all release databases
    db_files = find_all_release_databases(db_base_path)

    if not db_files:
        logging.error("No release database files found")
        return 1

    logging.info(f"Found {len(db_files)} database(s) to process")

    total_updated_assets = 0
    total_assets = 0
    processed_databases = 0
    failed_databases = 0

    # Process each database
    for db_file in db_files:
        try:
            logging.info(f"\n{'='*60}")
            logging.info(f"Processing database: {db_file}")
            logging.info(f"{'='*60}")

            # Create backup
            backup_file = db_file.with_suffix('.json.backup')
            logging.info(f"Creating backup at {backup_file}")
            with open(db_file, 'r') as src, open(backup_file, 'w') as dst:
                dst.write(src.read())

            # Reprocess the database
            updated_count, asset_count = reprocess_release_database(db_file)

            total_updated_assets += updated_count
            total_assets += asset_count
            processed_databases += 1

            logging.info(f"Successfully reprocessed {db_file}")
            logging.info(f"Updated {updated_count} out of {asset_count} assets")
            logging.info(f"Backup saved to {backup_file}")

        except Exception as e:
            logging.error(f"Failed to reprocess {db_file}: {e}")
            failed_databases += 1
            continue

    # Summary
    logging.info(f"\n{'='*60}")
    logging.info("REPROCESSING SUMMARY")
    logging.info(f"{'='*60}")
    logging.info(f"Databases processed successfully: {processed_databases}")
    logging.info(f"Databases failed: {failed_databases}")
    logging.info(f"Total assets updated: {total_updated_assets}")
    logging.info(f"Total assets processed: {total_assets}")

    return 0 if failed_databases == 0 else 1


if __name__ == "__main__":
    exit(main())
