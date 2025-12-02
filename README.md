# readnews

A modular Python application for fetching and filtering news from RSS/Atom feeds.

## Features

- Fetch news from multiple RSS/Atom feeds
- Filter news based on time window (e.g., last 30 minutes)
- Comprehensive error handling for network issues and parsing errors
- Detailed logging with rotation support
- Configurable via YAML configuration file
- Multiple output formats (JSON, CSV, TXT)
- Retry logic for network failures

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

Edit `config.yaml` to customize the application:

- `feed_file`: Path to file containing RSS feed URLs (default: `news_feeds.txt`)
- `time_window_minutes`: Fetch news from last N minutes (default: 30)
- `logging`: Configure log level, file, and rotation
- `network`: Set timeout, retries, and retry delay
- `output`: Configure output directory and format

## Usage

Run the application:
```bash
python news_fetcher.py
```

Or specify a custom config file:
```bash
python news_fetcher.py custom_config.yaml
```

## Feed File Format

The feed file (`news_feeds.txt`) should contain one feed per line in the format:
```
Feed Name, Feed URL
```

Example:
```
BBC, https://www.bbc.com/bengali/index.xml
DW, https://rss.dw.com/xml/rss-bn-all
```

## Output

News articles are saved to the `downloaded_news/` directory with timestamps. Supported formats:
- JSON (default)
- CSV
- TXT

## Modules

- `news_fetcher.py`: Main application entry point
- `feed_parser.py`: RSS/Atom feed parsing and filtering
- `logger_utils.py`: Logging configuration and custom exceptions

## Error Handling

The application handles:
- Network timeouts and connection errors
- Invalid feed formats
- Missing configuration files
- Parsing errors in individual news items

All errors are logged to `news_fetcher.log` with rotation.
Reads news from feeds and show in the terminal
