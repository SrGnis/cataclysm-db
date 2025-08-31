# GitHub Release Database Builder

A Python application that builds a database of GitHub releases for specified repositories, with configurable filtering to capture only relevant version tags.

## Features

- **Tag Discovery**: Uses `git ls-remote --tags` to fetch all tags from target repositories without cloning
- **Tag Filtering**: Applies regex patterns from configuration to filter relevant version tags
- **Release Data Retrieval**: Queries GitHub API to fetch release metadata for each filtered tag
- **Multi-Game Support**: Process multiple games from a single configuration file

## Requirements

- Python 3.6+
- Git (must be available in PATH)
- Internet connection
- Optional: GitHub personal access token for higher rate limits

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
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

## Configuration

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

### Configuration Fields

- **game_name**: Used for the output directory and filenames
- **git_repo**: GitHub repository in "owner/repo" format
- **filters**: Array of regex patterns to filter relevant version tags

### Example Filter Patterns

- `^[0-9]+\\.[0-9]+$` - Matches tags like "1.0", "2.5"
- `^[0-9]+\\.[0-9]+\\.[0-9]+$` - Matches tags like "1.0.0", "2.5.3"
- `^v[0-9]+\\.[0-9]+` - Matches tags starting with "v" like "v1.0", "v2.5.3"
- `^[0-9]+\\.[0-9]+-[A-Za-z]+$` - Matches tags like "1.0-alpha", "2.5-beta"

## Output

The application creates an organized directory structure for each game:

```
db/
└── {game_name}/
    ├── {game_name}_releases.json     # Release database
    └── {game_name}_processed_tags.json  # Cache of processed tags
```

### Files Generated

- **`{game_name}_releases.json`**: Contains an array of release objects with complete GitHub API data
- **`{game_name}_processed_tags.json`**: Cache file tracking which tags have been processed to avoid duplicate work

Each release database contains an array of simplified release objects with essential information:

**Release Information:**
- Release ID, name, and tag name
- Publication and creation dates
- Release notes/body
- Prerelease flag and channel (stable/experimental)
- Game type classification

**Asset Information:**
- Asset name and download URL
- File size and platform detection (Windows, Linux, macOS, Android)
- Graphics and sounds detection based on filename patterns
- Creation and update timestamps

The data structure is optimized to include only relevant information, significantly reducing storage size compared to the full GitHub API response.

## GitHub API Rate Limiting

- **Without token**: 60 requests per hour
- **With token**: 5,000 requests per hour

The application automatically handles rate limiting and will wait when limits are approached.

## Caching and Efficiency

The application employs a caching system to prevent duplicate work. 

It maintains a processed tags cache that tracks which tags have already been processed to avoid duplicate API calls, implements incremental updates to only process new tags, and uses persistent storage so the cache survives between runs, making subsequent executions much faster. 

The cache files are automatically created and updated. When the application runs for the first time, it processes all matching tags, but on subsequent runs, it only processes new tags if any exist, which significantly reduces GitHub API usage and execution time.

## Examples

### Cataclysm: Dark Days Ahead

The included `config.json` is configured for Cataclysm: Dark Days Ahead with filters that capture:
- Major.minor versions (e.g., "0.F")
- Semantic versions (e.g., "0.F.1")
- Pre-release versions (e.g., "0.F-alpha")

### Adding More Games

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

This project is open source. Please check the repository for license details.
