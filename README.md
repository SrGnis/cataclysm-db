# Cataclysm Database

A Python application that builds a database of GitHub releases for specified repositories.

## Features

- **Tag Discovery**: Uses `git ls-remote --tags` to fetch all tags from target repositories without cloning
- **Tag Filtering**: Applies regex patterns from configuration to filter relevant version tags
- **Release Data Retrieval**: Queries GitHub API to fetch release metadata for each filtered tag
- **Multi-Game Support**: Process multiple games from a single configuration file

## Requirements

- Python 3.6+
- Git
- Git LFS (Large File Storage)
- Internet connection
- Optional: GitHub personal access token for higher rate limits

## Installation

1. Clone this repository:
```bash
git clone https://github.com/SrGnis/cataclysm-db
cd cataclysm-db
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

```bash
python release_db_builder.py config.json
```

### With GitHub Token (Recommended)

For higher rate limits, use a GitHub personal access token:

```bash
python release_db_builder.py config.json --token YOUR_GITHUB_TOKEN
```

### Verbose Output

```bash
python release_db_builder.py config.json --verbose
```

### Configuration

Create a JSON configuration file with the following structure:

```json
{
  "games": [
    {
      "game_name": "dda",
      "git_repo": "CleverRaven/Cataclysm-DDA",
      "filters": [
        "^[0-9]+\\.[0-9]+$",
        "^[0-9]+\\.[0-9]+\\.[0-9]+$"
      ]
    }
  ]
}
```

#### Configuration Fields

- **game_name**: Used for the output directory and filenames
- **git_repo**: GitHub repository in "owner/repo" format
- **filters**: Array of regex patterns to filter relevant version tags

#### Example Filter Patterns

- `^[0-9]+\\.[0-9]+$` - Matches tags like "1.0", "2.5"
- `^[0-9]+\\.[0-9]+\\.[0-9]+$` - Matches tags like "1.0.0", "2.5.3"
- `^v[0-9]+\\.[0-9]+` - Matches tags starting with "v" like "v1.0", "v2.5.3"
- `^[0-9]+\\.[0-9]+-[A-Za-z]+$` - Matches tags like "1.0-alpha", "2.5-beta"

## Output

The application creates an organized directory structure for each game:

```
db/
├── index.json                           # Database version index for client synchronization
└── {game_name}/
    ├── {game_name}_releases.json        # Release database
    ├── {game_name}_processed_tags.json  # Cache of successfully processed tags
    └── {game_name}_failed_tags.json     # Cache of tags without releases
```

### Files Generated:

- **`index.json`**: Central index file tracking database versions (Unix timestamps) for efficient client synchronization
- **`{game_name}_releases.json`**: Contains an array of simplified release objects with essential GitHub API data
- **`{game_name}_processed_tags.json`**: Cache file tracking which tags have been successfully processed to avoid duplicate work
- **`{game_name}_failed_tags.json`**: Cache file tracking tags that don't have associated GitHub releases to avoid repeated failed API calls

Each release database contains an array of simplified release objects with essential information:

**Release Information:**
- Release ID, name, and tag name
- Publication and creation dates
- Release notes/body
- Prerelease flag and channel (stable/experimental)
- Game type classification

**Asset Information:**
- Asset name and download URL
- File size and creation/update timestamps
- **Platform detection**: Windows, Linux, macOS, Android, Unknown
- **Architecture detection**: x32, x64, ARM32, ARM64, Universal, Unknown
- **Graphics type**: Tiles, ASCII, Unknown
- **Sounds support**: Sounds, Unknown
- All classifications are automatically inferred from filename patterns

## Usage for Client Applications

1. Fetch `index.json` to get current database versions
2. Compare with local version cache to identify outdated databases
3. Download only the `{game_name}_releases.json` files that have newer versions
4. Update local version cache with new timestamps

**NOTE**: To get the files easily, you can use the urls https://github.com/SrGnis/cataclysm-db/releases/download/latest/{file_name}

### Index File

The `db/index.json` file enables efficient client application synchronization by tracking database versions:

### Index Structure
```json
{
  "dda": {
    "version": 1756653636
  },
  "bn": {
    "version": 1756653637
  }
}
```

## Caching

The cache files are automatically created and updated. When the application runs for the first time, it processes all matching tags, but on subsequent runs, it only processes new tags if any exist, which significantly reduces GitHub API usage and execution time.

## Asset Reprocessing

The `reprocess_assets.py` script provides functionality to update existing release databases with improved asset classification. It automatically scans all game databases in the `db/` directory and applies the latest detection logic for platforms, architectures, graphics, and sounds.

This tool is particularly useful when you've updated the asset classification logic in `release.py` or want to standardize asset metadata across all collected releases. Simply run `python reprocess_assets.py` to update all existing databases with the latest classification algorithms.

## Adding More Games

To add more games, extend the `games` array in your configuration:

```json
{
  "games": [
    {
      "game_name": "dda",
      "git_repo": "CleverRaven/Cataclysm-DDA",
      "filters": ["^[0-9]+\\.[A-Z]+"]
    },
    {
      "game_name": "another-game",
      "git_repo": "owner/repo",
      "filters": ["^v[0-9]+\\.[0-9]+\\.[0-9]+$"]
    }
  ]
}
```

## License

This project is licensed under the MIT License. See the LICENSE file in the repository for details.
