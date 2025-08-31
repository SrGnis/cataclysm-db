#!/usr/bin/env python3
"""
GitHub Release Database Builder

A Python application that builds a database of GitHub releases for specified repositories.
Supports configurable filtering to capture only relevant version tags.
"""

import json
import re
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import argparse
import logging
import requests
from release import GameRelease


class GitHubAPIClient:
    """GitHub API client with rate limiting and error handling."""
    
    def __init__(self, token: Optional[str] = None):
        self.session = requests.Session()
        self.base_url = "https://api.github.com"
        
        if token:
            self.session.headers.update({"Authorization": f"token {token}"})
        
        # Rate limiting tracking
        self.rate_limit_remaining = 5000
        self.rate_limit_reset = 0
        
    def _handle_rate_limit(self, response: requests.Response) -> None:
        """Handle GitHub API rate limiting."""
        self.rate_limit_remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
        self.rate_limit_reset = int(response.headers.get('X-RateLimit-Reset', 0))
        
        if self.rate_limit_remaining < 10:
            reset_time = self.rate_limit_reset - time.time()
            if reset_time > 0:
                logging.warning(f"Rate limit low ({self.rate_limit_remaining}). Waiting {reset_time:.0f}s")
                time.sleep(reset_time + 1)
    
    def get_release_by_tag(self, git_repo: str, tag: str, game_type: str = "") -> Optional[GameRelease]:
        """Get release information for a specific tag."""
        url = f"{self.base_url}/repos/{git_repo}/releases/tags/{tag}"

        try:
            response = self.session.get(url, timeout=30)
            self._handle_rate_limit(response)

            if response.status_code == 200:
                raw_data = response.json()
                release = GameRelease()
                release.from_github_data(raw_data, game_type)
                return release
            elif response.status_code == 404:
                logging.debug(f"No release found for tag {tag}")
                return None
            else:
                logging.warning(f"API error for tag {tag}: {response.status_code}")
                return None

        except requests.RequestException as e:
            logging.error(f"Request failed for tag {tag}: {e}")
            return None


class ReleaseDBBuilder:
    """Main application class for building release databases."""
    
    def __init__(self, config_path: str, github_token: Optional[str] = None):
        self.config_path = Path(config_path)
        self.github_client = GitHubAPIClient(github_token)
        self.config = self._load_config()
        
    def _load_config(self) -> Dict:
        """Load and validate configuration file."""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            
            # Validate config structure
            if 'games' not in config:
                raise ValueError("Config must contain 'games' key")
            
            for game in config['games']:
                required_keys = ['game_name', 'git_repo', 'filters']
                for key in required_keys:
                    if key not in game:
                        raise ValueError(f"Game config missing required key: {key}")
            
            return config
            
        except (json.JSONDecodeError, FileNotFoundError) as e:
            raise ValueError(f"Failed to load config: {e}")
    
    def _get_repo_tags(self, git_repo: str) -> List[str]:
        """Get all tags from a Git repository using git ls-remote."""
        repo_url = f"https://github.com/{git_repo}.git"
        try:
            cmd = ['git', 'ls-remote', '--tags', repo_url]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                logging.error(f"Git command failed: {result.stderr}")
                return []
            
            tags = []
            for line in result.stdout.strip().split('\n'):
                if line and 'refs/tags/' in line:
                    # Extract tag name from "hash refs/tags/tagname"
                    tag = line.split('refs/tags/')[-1]
                    # Skip annotated tag references (ending with ^{})
                    if not tag.endswith('^{}'):
                        tags.append(tag)
            
            return tags
            
        except subprocess.TimeoutExpired:
            logging.error(f"Timeout getting tags from {repo_url}")
            return []
        except Exception as e:
            logging.error(f"Error getting tags from {repo_url}: {e}")
            return []
    
    def _filter_tags(self, tags: List[str], filters: List[str]) -> List[str]:
        """Filter tags using regex patterns."""
        filtered_tags = []

        for tag in tags:
            for filter_pattern in filters:
                try:
                    if re.match(filter_pattern, tag):
                        filtered_tags.append(tag)
                        break  # Tag matches, no need to check other patterns
                except re.error as e:
                    logging.warning(f"Invalid regex pattern '{filter_pattern}': {e}")

        return filtered_tags

    def _get_game_directory(self, game_name: str) -> Path:
        return Path("db") / game_name

    def _get_releases_file_path(self, game_name: str) -> Path:
        return self._get_game_directory(game_name) / f"{game_name}_releases.json"

    def _get_processed_tags_file_path(self, game_name: str) -> Path:
        return self._get_game_directory(game_name) / f"{game_name}_processed_tags.json"

    def _get_failed_tags_file_path(self, game_name: str) -> Path:
        """Get the file path for a game's failed tags cache."""
        return self._get_game_directory(game_name) / f"{game_name}_failed_tags.json"

    def _get_database_index_file_path(self) -> Path:
        """Get the file path for the database index."""
        return Path("db") / "index.json"

    def _ensure_game_directory(self, game_name: str) -> None:
        game_dir = self._get_game_directory(game_name)
        game_dir.mkdir(parents=True, exist_ok=True)

    def _load_processed_tags(self, game_name: str) -> List[str]:
        """Load the list of processed tags from cache."""
        processed_tags_file = self._get_processed_tags_file_path(game_name)

        if processed_tags_file.exists():
            try:
                with open(processed_tags_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logging.warning(f"Failed to load processed tags cache for {game_name}: {e}")

        return []

    def _save_processed_tags(self, game_name: str, processed_tags: List[str]) -> None:
        """Save the list of processed tags to cache."""
        self._ensure_game_directory(game_name)
        processed_tags_file = self._get_processed_tags_file_path(game_name)

        try:
            with open(processed_tags_file, 'w') as f:
                json.dump(sorted(processed_tags), f, indent=2)
            logging.debug(f"Saved {len(processed_tags)} processed tags to cache for {game_name}")
        except IOError as e:
            logging.error(f"Failed to save processed tags cache for {game_name}: {e}")

    def _load_failed_tags(self, game_name: str) -> List[str]:
        """Load the list of failed tags from cache."""
        failed_tags_file = self._get_failed_tags_file_path(game_name)

        if failed_tags_file.exists():
            try:
                with open(failed_tags_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logging.warning(f"Failed to load failed tags cache for {game_name}: {e}")

        return []

    def _save_failed_tags(self, game_name: str, failed_tags: List[str]) -> None:
        """Save the list of failed tags to cache."""
        self._ensure_game_directory(game_name)
        failed_tags_file = self._get_failed_tags_file_path(game_name)

        try:
            with open(failed_tags_file, 'w') as f:
                json.dump(sorted(failed_tags), f, indent=2)
            logging.debug(f"Saved {len(failed_tags)} failed tags to cache for {game_name}")
        except IOError as e:
            logging.error(f"Failed to save failed tags cache for {game_name}: {e}")

    def _load_database_index(self) -> Dict[str, Dict[str, int]]:
        """Load the database index from file."""
        index_file = self._get_database_index_file_path()

        if index_file.exists():
            try:
                with open(index_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logging.warning(f"Failed to load database index: {e}")

        return {}

    def _save_database_index(self, index: Dict[str, Dict[str, int]]) -> None:
        """Save the database index to file."""
        index_file = self._get_database_index_file_path()

        # Ensure the db directory exists
        index_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(index_file, 'w') as f:
                json.dump(index, f, indent=2, sort_keys=True)
            logging.debug(f"Updated database index with {len(index)} games")
        except IOError as e:
            logging.error(f"Failed to save database index: {e}")

    def _load_existing_releases(self, game_name: str) -> List[GameRelease]:
        """Load existing releases data from file."""
        releases_file = self._get_releases_file_path(game_name)

        if releases_file.exists():
            try:
                with open(releases_file, 'r') as f:
                    data = json.load(f)
                    releases = []
                    for release_dict in data:
                        release = GameRelease.from_dict(release_dict)
                        releases.append(release)
                    return releases
            except (json.JSONDecodeError, IOError) as e:
                logging.warning(f"Failed to load existing releases for {game_name}: {e}")

        return []

    def _save_releases(self, game_name: str, releases: List[GameRelease]) -> None:
        """Save releases data to file and update database index."""
        self._ensure_game_directory(game_name)
        releases_file = self._get_releases_file_path(game_name)

        try:
            # Sort releases by published_at date (newest first), fallback to created_at, then to epoch for None values
            def get_sort_date(release):
                from datetime import datetime
                return release.published_at or release.created_at or datetime.fromtimestamp(0)

            sorted_releases = sorted(releases, key=get_sort_date, reverse=True)

            # Convert GameRelease objects to dictionaries for JSON serialization
            releases_data = [release.to_dict() for release in sorted_releases]
            with open(releases_file, 'w') as f:
                json.dump(releases_data, f, indent=2)
            logging.info(f"Saved {len(releases)} releases to {releases_file} (sorted by date)")

            # Update database index with current timestamp
            self._update_database_index(game_name)

        except IOError as e:
            logging.error(f"Failed to save releases for {game_name}: {e}")

    def _update_database_index(self, game_name: str) -> None:
        """Update the database index with current timestamp for the specified game."""
        try:
            # Load current index
            index = self._load_database_index()

            # Update timestamp for this game (Unix timestamp in seconds)
            current_timestamp = int(time.time())
            index[game_name] = {"version": current_timestamp}

            # Save updated index
            self._save_database_index(index)

            logging.debug(f"Updated database index for {game_name} with version {current_timestamp}")

        except Exception as e:
            logging.error(f"Failed to update database index for {game_name}: {e}")
    
    def build_database(self, game_config: Dict) -> Tuple[List[GameRelease], bool]:
        """Build release database for a single game."""
        game_name = game_config['game_name']
        git_repo = game_config['git_repo']
        filters = game_config['filters']

        logging.info(f"Building database for {game_name}")

        # Load processed tags cache
        processed_tags = self._load_processed_tags(game_name)
        logging.info(f"Loaded {len(processed_tags)} previously processed tags from cache")

        # Load failed tags cache
        failed_tags = self._load_failed_tags(game_name)
        logging.info(f"Loaded {len(failed_tags)} previously failed tags from cache")

        # Get all tags from repository
        logging.info(f"Fetching tags from {git_repo}")
        all_tags = self._get_repo_tags(git_repo)
        logging.info(f"Found {len(all_tags)} total tags")

        # Filter tags using regex patterns
        filtered_tags = self._filter_tags(all_tags, filters)
        logging.info(f"Filtered to {len(filtered_tags)} relevant tags")

        # Determine which tags need to be processed (not in processed or failed cache)
        new_tags = [tag for tag in filtered_tags if tag not in processed_tags and tag not in failed_tags]
        logging.info(f"Found {len(new_tags)} new tags to process (excluding {len(failed_tags)} previously failed tags)")

        # Load existing releases data if it exists
        releases = self._load_existing_releases(game_name)
        initial_release_count = len(releases)
        logging.info(f"Loaded {initial_release_count} existing releases from database")

        # Get release data for each new filtered tag
        new_releases_added = 0
        for i, tag in enumerate(new_tags, 1):
            logging.info(f"Processing new tag {i}/{len(new_tags)}: {tag}")

            release_data = self.github_client.get_release_by_tag(git_repo, tag, game_name)
            if release_data:
                releases.append(release_data)
                processed_tags.append(tag)
                new_releases_added += 1
                logging.debug(f"Successfully processed tag: {tag}")
            else:
                failed_tags.append(tag)
                logging.debug(f"No release found for tag: {tag}")

            # Small delay to be respectful to GitHub API
            time.sleep(0.1)

        # Update caches
        if new_tags:
            self._save_processed_tags(game_name, processed_tags)
            self._save_failed_tags(game_name, failed_tags)

        # Determine if releases changed (new releases were added)
        releases_changed = new_releases_added > 0

        logging.info(f"Successfully retrieved {len(releases)} total releases for {game_name}")
        if releases_changed:
            logging.info(f"Added {new_releases_added} new releases")
        else:
            logging.info("No new releases found")

        return releases, releases_changed
    
    def run(self) -> None:
        """Run the database builder for all configured games."""
        for game_config in self.config['games']:
            try:
                releases, releases_changed = self.build_database(game_config)

                game_name = game_config['game_name']

                # Only save releases and update index if there were changes
                if releases_changed:
                    self._save_releases(game_name, releases)
                    logging.info(f"Database updated for {game_name}")
                else:
                    logging.info(f"No changes for {game_name}, skipping save and index update")

            except Exception as e:
                logging.error(f"Failed to build database for {game_config['game_name']}: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Build GitHub release databases")
    parser.add_argument("config", help="Path to configuration JSON file")
    parser.add_argument("--token", help="GitHub API token (optional)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    try:
        builder = ReleaseDBBuilder(args.config, args.token)
        builder.run()
        
    except Exception as e:
        logging.error(f"Application failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
