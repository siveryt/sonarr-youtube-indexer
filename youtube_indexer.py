#!/usr/bin/env python3
"""
YouTube Indexer for Prowlarr/Sonarr
====================================
A Torznab-compatible indexer that searches YouTube and returns results
that Sonarr can use to trigger downloads via the YouTube download client.

This bridges the gap between Sonarr's episode metadata (from TheTVDB) and
actual YouTube video URLs.

Author: Ioannis Kokkinis
License: MIT
"""

import os
import re
import json
import hashlib
import urllib.parse
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from xml.etree.ElementTree import Element, SubElement, tostring
import logging

# Try to import yt-dlp for YouTube search
try:
    import yt_dlp
    HAS_YTDLP = True
except ImportError:
    HAS_YTDLP = False
    print("WARNING: yt-dlp not installed. Install with: pip install yt-dlp")

# Configuration
CONFIG = {
    "host": "0.0.0.0",
    "port": 9117,
    "api_key": "youtubeindexer",
    "indexer_name": "YouTube",
    "log_level": "INFO",
}

logging.basicConfig(
    level=getattr(logging, CONFIG["log_level"]),
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def search_youtube(query, max_results=20):
    """Search YouTube and return video results"""
    if not HAS_YTDLP:
        logger.error("yt-dlp not available")
        return []

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'force_generic_extractor': False,
    }

    search_url = f"ytsearch{max_results}:{query}"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(search_url, download=False)

            videos = []
            if result and 'entries' in result:
                for entry in result['entries']:
                    if entry:
                        videos.append({
                            'id': entry.get('id', ''),
                            'title': entry.get('title', 'Unknown'),
                            'url': entry.get('url') or f"https://www.youtube.com/watch?v={entry.get('id', '')}",
                            'channel': entry.get('channel', entry.get('uploader', 'Unknown')),
                            'duration': entry.get('duration', 0),
                            'view_count': entry.get('view_count', 0),
                            'upload_date': entry.get('upload_date', ''),
                            'description': entry.get('description', ''),
                        })
            return videos
    except Exception as e:
        logger.error(f"YouTube search error: {e}")
        return []


def generate_guid(video_id):
    """Generate a unique GUID for the result"""
    return hashlib.md5(video_id.encode()).hexdigest()


def format_torznab_xml(videos, query=""):
    """Format search results as Torznab XML"""
    rss = Element('rss', {
        'version': '2.0',
        'xmlns:atom': 'http://www.w3.org/2005/Atom',
        'xmlns:torznab': 'http://torznab.com/schemas/2015/feed'
    })

    channel = SubElement(rss, 'channel')

    title = SubElement(channel, 'title')
    title.text = CONFIG['indexer_name']

    description = SubElement(channel, 'description')
    description.text = 'YouTube Video Indexer for Sonarr'

    # Add atom:link for self-reference
    SubElement(channel, '{http://www.w3.org/2005/Atom}link', {
        'href': f"http://localhost:{CONFIG['port']}/api",
        'rel': 'self',
        'type': 'application/rss+xml'
    })

    for video in videos:
        item = SubElement(channel, 'item')

        # Title - format for Sonarr recognition
        item_title = SubElement(item, 'title')
        item_title.text = video['title']

        # GUID
        guid = SubElement(item, 'guid')
        guid.text = generate_guid(video['id'])

        # Link to YouTube video
        link = SubElement(item, 'link')
        link.text = video['url']

        # Comments (channel info)
        comments = SubElement(item, 'comments')
        comments.text = f"Channel: {video['channel']}"

        # Publication date
        if video['upload_date']:
            try:
                pub_date = datetime.strptime(video['upload_date'], '%Y%m%d')
                pub_date_elem = SubElement(item, 'pubDate')
                pub_date_elem.text = pub_date.strftime('%a, %d %b %Y %H:%M:%S +0000')
            except:
                pass

        # Size (estimate based on duration, ~5MB per minute for 720p)
        size = SubElement(item, 'size')
        duration_mins = video.get('duration', 600) / 60
        estimated_size = int(duration_mins * 5 * 1024 * 1024)  # 5MB per minute
        size.text = str(estimated_size)

        # Category
        category = SubElement(item, 'category')
        category.text = '5000'  # TV category

        # Enclosure - This is what Sonarr uses to get the download URL
        SubElement(item, 'enclosure', {
            'url': video['url'],
            'length': str(estimated_size),
            'type': 'application/x-bittorrent'  # Sonarr expects this
        })

        # Torznab attributes
        SubElement(item, '{http://torznab.com/schemas/2015/feed}attr', {
            'name': 'category',
            'value': '5000'
        })
        SubElement(item, '{http://torznab.com/schemas/2015/feed}attr', {
            'name': 'seeders',
            'value': '100'
        })
        SubElement(item, '{http://torznab.com/schemas/2015/feed}attr', {
            'name': 'peers',
            'value': '100'
        })
        SubElement(item, '{http://torznab.com/schemas/2015/feed}attr', {
            'name': 'downloadvolumefactor',
            'value': '0'
        })
        SubElement(item, '{http://torznab.com/schemas/2015/feed}attr', {
            'name': 'uploadvolumefactor',
            'value': '1'
        })

    return tostring(rss, encoding='unicode')


def get_capabilities_xml():
    """Return Torznab capabilities XML"""
    caps = Element('caps')

    server = SubElement(caps, 'server', {
        'version': '1.0',
        'title': CONFIG['indexer_name'],
    })

    limits = SubElement(caps, 'limits', {
        'max': '100',
        'default': '20'
    })

    searching = SubElement(caps, 'searching')
    SubElement(searching, 'search', {'available': 'yes', 'supportedParams': 'q'})
    SubElement(searching, 'tv-search', {'available': 'yes', 'supportedParams': 'q,season,ep'})
    SubElement(searching, 'movie-search', {'available': 'no'})
    SubElement(searching, 'music-search', {'available': 'no'})
    SubElement(searching, 'audio-search', {'available': 'no'})
    SubElement(searching, 'book-search', {'available': 'no'})

    categories = SubElement(caps, 'categories')
    cat = SubElement(categories, 'category', {'id': '5000', 'name': 'TV'})
    SubElement(cat, 'subcat', {'id': '5030', 'name': 'TV/SD'})
    SubElement(cat, 'subcat', {'id': '5040', 'name': 'TV/HD'})
    SubElement(cat, 'subcat', {'id': '5045', 'name': 'TV/UHD'})
    SubElement(cat, 'subcat', {'id': '5050', 'name': 'TV/Other'})

    return tostring(caps, encoding='unicode')


class TorznabHandler(BaseHTTPRequestHandler):
    """HTTP handler for Torznab API"""

    def log_message(self, format, *args):
        logger.debug(f"HTTP: {format % args}")

    def _send_xml(self, xml_content):
        """Send XML response"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/xml; charset=utf-8')
        self.send_header('Content-Length', len(xml_content.encode('utf-8')))
        self.end_headers()
        self.wfile.write(xml_content.encode('utf-8'))

    def _send_error(self, code, message):
        """Send error response"""
        error_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<error code="{code}" description="{message}"/>'''
        self.send_response(200)  # Torznab uses 200 even for errors
        self.send_header('Content-Type', 'application/xml')
        self.end_headers()
        self.wfile.write(error_xml.encode('utf-8'))

    def do_GET(self):
        """Handle GET requests"""
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        # Get API key
        apikey = params.get('apikey', [''])[0]

        # Check API key (optional, for security)
        if CONFIG['api_key'] and apikey != CONFIG['api_key']:
            logger.warning(f"Invalid API key: {apikey}")
            self._send_error(100, 'Invalid API Key')
            return

        # Get the action (t parameter)
        action = params.get('t', [''])[0]

        logger.info(f"Request: action={action}, params={params}")

        if action == 'caps':
            # Return capabilities
            xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + get_capabilities_xml()
            self._send_xml(xml)
            return

        elif action == 'search' or action == 'tvsearch':
            # Build search query
            query_parts = []

            # Base query
            q = params.get('q', [''])[0]
            if q:
                query_parts.append(q)

            # Season and episode
            season = params.get('season', [''])[0]
            ep = params.get('ep', [''])[0]

            if season and ep:
                # Don't add S01E01 format for YouTube - just use natural language
                pass

            query = ' '.join(query_parts)

            if not query:
                # Return empty results for empty query (Prowlarr test)
                xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + format_torznab_xml([], "")
                self._send_xml(xml)
                return

            logger.info(f"Searching YouTube for: {query}")

            # Search YouTube
            videos = search_youtube(query)

            logger.info(f"Found {len(videos)} results")

            # Format as Torznab XML
            xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + format_torznab_xml(videos, query)
            self._send_xml(xml)
            return

        elif action == 'download' or parsed.path.startswith('/download'):
            # Direct download link - redirect to YouTube URL
            # This shouldn't normally be called since enclosure URL is the YouTube URL
            link = params.get('link', params.get('id', ['']))[0]
            if link:
                self.send_response(302)
                self.send_header('Location', link)
                self.end_headers()
            else:
                self._send_error(200, 'Missing download link')
            return

        else:
            self._send_error(201, f'Unknown action: {action}')
            return


def main():
    """Main entry point"""
    print(f'''
╔══════════════════════════════════════════════════════════════╗
║         YouTube Indexer for Prowlarr/Sonarr                 ║
║         Torznab-compatible API Server                       ║
║                                                              ║
║              Created by Ioannis Kokkinis                     ║
╠══════════════════════════════════════════════════════════════╣
║  Add this to Prowlarr as a Generic Torznab indexer:         ║
║                                                              ║
║  URL: http://localhost:{CONFIG["port"]}                              ║
║  API Path: /api                                              ║
║  API Key: {CONFIG["api_key"]}                                ║
║  Categories: 5000 (TV)                                       ║
╚══════════════════════════════════════════════════════════════╝
    ''')

    if not HAS_YTDLP:
        print("ERROR: yt-dlp is required. Install with: pip install yt-dlp")
        return

    server = HTTPServer((CONFIG["host"], CONFIG["port"]), TorznabHandler)
    logger.info(f"Starting Torznab server on {CONFIG['host']}:{CONFIG['port']}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
