"""
Main news fetcher application.
Fetches news from RSS/Atom feeds based on configuration.
"""

import os
import sys
import json
import csv
from datetime import datetime
from typing import List, Dict
import yaml

from logger_utils import NewsLogger, FeedError, NetworkError, ParseError, ConfigError
from feed_parser import FeedParser


class NewsFetcher:
    """Main application class for fetching news from feeds."""
    
    def __init__(self, config_file: str = "config.yaml"):
        """
        Initialize the news fetcher application.
        
        Args:
            config_file: Path to the configuration file
        """
        self.config = self.load_config(config_file)
        
        # Initialize logger
        log_config = self.config.get('logging', {})
        self.logger = NewsLogger(
            log_file=log_config.get('log_file', 'news_fetcher.log'),
            level=log_config.get('level', 'INFO'),
            max_bytes=log_config.get('max_log_size_mb', 10) * 1024 * 1024,
            backup_count=log_config.get('backup_count', 5)
        )
        
        self.logger.info("=" * 60)
        self.logger.info("News Fetcher Application Started")
        self.logger.info("=" * 60)
        
        # Initialize feed parser
        network_config = self.config.get('network', {})
        self.parser = FeedParser(
            logger=self.logger,
            timeout=network_config.get('timeout_seconds', 30),
            max_retries=network_config.get('max_retries', 3),
            retry_delay=network_config.get('retry_delay_seconds', 5)
        )
        
        # Get configuration values
        self.feed_file = self.config.get('feed_file', 'news_feeds.txt')
        self.time_window_minutes = self.config.get('time_window_minutes', 30)
        
        # Output configuration
        output_config = self.config.get('output', {})
        self.save_to_file = output_config.get('save_to_file', True)
        self.output_directory = output_config.get('output_directory', 'downloaded_news')
        self.output_format = output_config.get('output_format', 'json')
    
    def load_config(self, config_file: str) -> Dict:
        """
        Load configuration from YAML file.
        
        Args:
            config_file: Path to configuration file
            
        Returns:
            Configuration dictionary
            
        Raises:
            ConfigError: If configuration file is invalid
        """
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                return config if config else {}
        except FileNotFoundError:
            print(f"Configuration file not found: {config_file}")
            print("Using default configuration")
            return {}
        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML in config file: {str(e)}")
        except Exception as e:
            raise ConfigError(f"Error loading config: {str(e)}")
    
    def fetch_all_news(self) -> List[Dict]:
        """
        Fetch news from all configured feeds.
        
        Returns:
            List of news articles
        """
        all_news = []
        
        try:
            # Read feed file
            feeds = self.parser.read_feed_file(self.feed_file)
            
            if not feeds:
                self.logger.warning("No feeds found in feed file")
                return all_news
            
            # Process each feed
            for feed_name, feed_url in feeds:
                self.logger.info(f"Processing feed: {feed_name}")
                
                try:
                    # Fetch feed
                    feed = self.parser.fetch_feed(feed_url)
                    
                    if not feed:
                        self.logger.error(f"Failed to fetch feed: {feed_name}")
                        continue
                    
                    # Get entries
                    entries = feed.get('entries', [])
                    self.logger.info(f"Found {len(entries)} total entries in {feed_name}")
                    
                    # Filter by time window
                    filtered_entries = self.parser.filter_entries_by_time(
                        entries,
                        self.time_window_minutes
                    )
                    self.logger.info(
                        f"Filtered to {len(filtered_entries)} entries "
                        f"within last {self.time_window_minutes} minutes"
                    )
                    
                    # Extract data from each entry
                    for entry in filtered_entries:
                        try:
                            article_data = self.parser.extract_entry_data(
                                entry,
                                feed_name
                            )
                            all_news.append(article_data)
                            self.logger.debug(
                                f"Extracted article: {article_data['title']}"
                            )
                        except ParseError as e:
                            self.logger.error(
                                f"Error parsing entry from {feed_name}: {str(e)}"
                            )
                            continue
                        except Exception as e:
                            self.logger.error(
                                f"Unexpected error parsing entry from {feed_name}: {str(e)}",
                                exc_info=True
                            )
                            continue
                    
                except NetworkError as e:
                    self.logger.error(
                        f"Network error fetching {feed_name}: {str(e)}"
                    )
                    continue
                except ParseError as e:
                    self.logger.error(
                        f"Parse error for {feed_name}: {str(e)}"
                    )
                    continue
                except Exception as e:
                    self.logger.error(
                        f"Unexpected error processing {feed_name}: {str(e)}",
                        exc_info=True
                    )
                    continue
            
            self.logger.info(f"Total articles fetched: {len(all_news)}")
            return all_news
            
        except FileNotFoundError:
            self.logger.error(f"Feed file not found: {self.feed_file}")
            raise
        except Exception as e:
            self.logger.error(
                f"Error fetching news: {str(e)}",
                exc_info=True
            )
            raise
    
    def save_news(self, news_articles: List[Dict]):
        """
        Save news articles to file.
        
        Args:
            news_articles: List of news articles to save
        """
        if not news_articles:
            self.logger.warning("No news articles to save")
            return
        
        try:
            # Create output directory if it doesn't exist
            os.makedirs(self.output_directory, exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            if self.output_format == 'json':
                output_file = os.path.join(
                    self.output_directory,
                    f'news_{timestamp}.json'
                )
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(news_articles, f, indent=2, ensure_ascii=False)
                    
            elif self.output_format == 'csv':
                output_file = os.path.join(
                    self.output_directory,
                    f'news_{timestamp}.csv'
                )
                if news_articles:
                    keys = news_articles[0].keys()
                    with open(output_file, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=keys)
                        writer.writeheader()
                        writer.writerows(news_articles)
                        
            elif self.output_format == 'txt':
                output_file = os.path.join(
                    self.output_directory,
                    f'news_{timestamp}.txt'
                )
                with open(output_file, 'w', encoding='utf-8') as f:
                    for i, article in enumerate(news_articles, 1):
                        f.write(f"{'=' * 80}\n")
                        f.write(f"Article {i}\n")
                        f.write(f"{'=' * 80}\n")
                        f.write(f"Feed: {article['feed_name']}\n")
                        f.write(f"Title: {article['title']}\n")
                        f.write(f"Link: {article['link']}\n")
                        f.write(f"Published: {article['published']}\n")
                        f.write(f"Author: {article['author']}\n")
                        f.write(f"Categories: {', '.join(article['categories'])}\n")
                        f.write(f"\nSummary:\n{article['summary']}\n\n")
            else:
                self.logger.error(f"Unsupported output format: {self.output_format}")
                return
            
            self.logger.info(f"News articles saved to: {output_file}")
            
        except Exception as e:
            self.logger.error(
                f"Error saving news articles: {str(e)}",
                exc_info=True
            )
            raise
    
    def run(self):
        """Run the news fetcher application."""
        try:
            self.logger.info(f"Feed file: {self.feed_file}")
            self.logger.info(f"Time window: {self.time_window_minutes} minutes")
            
            # Fetch news
            news_articles = self.fetch_all_news()
            
            # Save to file if configured
            if self.save_to_file and news_articles:
                self.save_news(news_articles)
            
            self.logger.info("=" * 60)
            self.logger.info("News Fetcher Application Completed Successfully")
            self.logger.info("=" * 60)
            
            return news_articles
            
        except Exception as e:
            self.logger.critical(
                f"Fatal error in news fetcher: {str(e)}",
                exc_info=True
            )
            raise


def main():
    """Main entry point for the application."""
    try:
        # Check for config file argument
        config_file = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
        
        # Create and run fetcher
        fetcher = NewsFetcher(config_file)
        fetcher.run()
        
        return 0
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 1
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
