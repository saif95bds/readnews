"""
Feed parser module for fetching and parsing RSS/Atom feeds.
Handles network requests, parsing, and time-based filtering.
"""

import feedparser
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse
import time

from logger_utils import NewsLogger, NetworkError, ParseError


class FeedParser:
    """Handles fetching and parsing of RSS/Atom feeds."""
    
    def __init__(self, logger: NewsLogger, timeout: int = 30, 
                 max_retries: int = 3, retry_delay: int = 5):
        """
        Initialize the feed parser.
        
        Args:
            logger: Logger instance for logging
            timeout: Network timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.logger = logger
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    
    def read_feed_file(self, feed_file: str) -> List[Tuple[str, str]]:
        """
        Read the feed file and parse feed names and URLs.
        
        Args:
            feed_file: Path to the file containing feed information
            
        Returns:
            List of tuples containing (feed_name, feed_url)
            
        Raises:
            FileNotFoundError: If feed file doesn't exist
            ParseError: If feed file format is invalid
        """
        feeds = []
        
        try:
            with open(feed_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse line (format: "Name, URL")
                    if ',' in line:
                        parts = line.split(',', 1)
                        name = parts[0].strip()
                        url = parts[1].strip()
                        
                        if name and url:
                            feeds.append((name, url))
                            self.logger.debug(f"Added feed: {name} - {url}")
                        else:
                            self.logger.warning(
                                f"Invalid feed format at line {line_num}: {line}"
                            )
                    else:
                        self.logger.warning(
                            f"Invalid feed format at line {line_num}: {line}"
                        )
            
            self.logger.info(f"Loaded {len(feeds)} feeds from {feed_file}")
            return feeds
            
        except FileNotFoundError:
            self.logger.error(f"Feed file not found: {feed_file}")
            raise
        except Exception as e:
            self.logger.error(f"Error reading feed file: {str(e)}", exc_info=True)
            raise ParseError(f"Failed to read feed file: {str(e)}")
    
    def fetch_feed(self, feed_url: str) -> Optional[feedparser.FeedParserDict]:
        """
        Fetch and parse a feed with retry logic.
        
        Args:
            feed_url: URL of the RSS/Atom feed
            
        Returns:
            Parsed feed dictionary or None if failed
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                self.logger.debug(
                    f"Fetching feed (attempt {attempt}/{self.max_retries}): {feed_url}"
                )
                
                # Fetch feed with timeout
                response = requests.get(
                    feed_url,
                    timeout=self.timeout,
                    headers={'User-Agent': 'NewsFetcher/1.0'}
                )
                response.raise_for_status()
                
                # Parse feed
                feed = feedparser.parse(response.content)
                
                # Check if parsing was successful
                if feed.bozo:
                    if hasattr(feed, 'bozo_exception'):
                        raise ParseError(
                            f"Feed parsing error: {str(feed.bozo_exception)}"
                        )
                
                self.logger.debug(f"Successfully fetched feed: {feed_url}")
                return feed
                
            except requests.exceptions.Timeout:
                self.logger.warning(
                    f"Timeout fetching feed (attempt {attempt}): {feed_url}"
                )
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay)
                else:
                    raise NetworkError(f"Timeout after {self.max_retries} attempts")
                    
            except requests.exceptions.ConnectionError as e:
                self.logger.warning(
                    f"Connection error (attempt {attempt}): {feed_url} - {str(e)}"
                )
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay)
                else:
                    raise NetworkError(f"Connection failed after {self.max_retries} attempts")
                    
            except requests.exceptions.HTTPError as e:
                self.logger.error(
                    f"HTTP error fetching feed: {feed_url} - {str(e)}"
                )
                raise NetworkError(f"HTTP error: {str(e)}")
                
            except requests.exceptions.RequestException as e:
                self.logger.error(
                    f"Request error fetching feed: {feed_url} - {str(e)}"
                )
                raise NetworkError(f"Request error: {str(e)}")
                
            except Exception as e:
                self.logger.error(
                    f"Unexpected error fetching feed: {feed_url} - {str(e)}",
                    exc_info=True
                )
                raise
        
        return None
    
    def parse_entry_date(self, entry: Dict) -> Optional[datetime]:
        """
        Parse the publication date from a feed entry.
        
        Args:
            entry: Feed entry dictionary
            
        Returns:
            Datetime object or None if parsing failed
        """
        try:
            # Try different date fields
            date_fields = ['published_parsed', 'updated_parsed', 'created_parsed']
            
            for field in date_fields:
                if hasattr(entry, field) and getattr(entry, field):
                    time_struct = getattr(entry, field)
                    return datetime(*time_struct[:6])
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Error parsing entry date: {str(e)}")
            return None
    
    def filter_entries_by_time(self, entries: List[Dict], 
                                time_window_minutes: int) -> List[Dict]:
        """
        Filter feed entries based on time window.
        
        Args:
            entries: List of feed entries
            time_window_minutes: Time window in minutes
            
        Returns:
            List of filtered entries
        """
        cutoff_time = datetime.now() - timedelta(minutes=time_window_minutes)
        filtered_entries = []
        
        for entry in entries:
            try:
                pub_date = self.parse_entry_date(entry)
                
                if pub_date:
                    if pub_date >= cutoff_time:
                        filtered_entries.append(entry)
                        self.logger.debug(
                            f"Entry included: {entry.get('title', 'No title')} "
                            f"(published: {pub_date})"
                        )
                    else:
                        self.logger.debug(
                            f"Entry filtered out (too old): "
                            f"{entry.get('title', 'No title')} "
                            f"(published: {pub_date})"
                        )
                else:
                    # If no date available, include the entry
                    self.logger.warning(
                        f"No date found for entry: {entry.get('title', 'No title')} "
                        f"- including it anyway"
                    )
                    filtered_entries.append(entry)
                    
            except Exception as e:
                self.logger.error(
                    f"Error filtering entry: {str(e)}",
                    exc_info=True
                )
                # Include entry if filtering fails
                filtered_entries.append(entry)
        
        return filtered_entries
    
    def extract_entry_data(self, entry: Dict, feed_name: str) -> Dict:
        """
        Extract relevant data from a feed entry.
        
        Args:
            entry: Feed entry dictionary
            feed_name: Name of the feed source
            
        Returns:
            Dictionary with extracted data
        """
        try:
            pub_date = self.parse_entry_date(entry)
            
            data = {
                'feed_name': feed_name,
                'title': entry.get('title', 'No title'),
                'link': entry.get('link', ''),
                'summary': entry.get('summary', entry.get('description', '')),
                'published': pub_date.isoformat() if pub_date else None,
                'author': entry.get('author', ''),
                'categories': [tag.get('term', '') for tag in entry.get('tags', [])],
                'fetched_at': datetime.now().isoformat()
            }
            
            return data
            
        except Exception as e:
            self.logger.error(
                f"Error extracting entry data: {str(e)}",
                exc_info=True
            )
            raise ParseError(f"Failed to extract entry data: {str(e)}")
