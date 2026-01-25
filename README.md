# Sonarr YouTube Indexer

**Created by Ioannis Kokkinis**

A Torznab-compatible indexer that searches YouTube and returns results for Sonarr/Prowlarr. This is the missing link that allows Sonarr to automatically find YouTube videos for series tracked via TheTVDB.

---

## Quick Start

**1. Install & Run**
```bash
pip install yt-dlp
python youtube_indexer.py
```

**2. Add to Prowlarr** (Settings → Indexers → + → Generic Torznab)

| Setting | Value |
|---------|-------|
| URL | `http://localhost:9117` |
| API Path | `/api` |
| API Key | `youtubeindexer` |
| Categories | `5000` (TV) |

**3. Sync to Sonarr** - Prowlarr will sync the indexer to Sonarr automatically.

**4. Search!** - Go to a YouTube series in Sonarr (like Kurzgesagt), click an episode, and search. Results will come from YouTube.

---

## How It Works

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐
│   Sonarr    │────▶│  This Indexer    │────▶│   YouTube   │
│             │     │  (Torznab API)   │     │   Search    │
└─────────────┘     └──────────────────┘     └─────────────┘
       │                     │                      │
       │  "Find Kurzgesagt   │  yt-dlp ytsearch    │
       │   S2026E01"         │                      │
       │◀────────────────────│◀─────────────────────│
       │  YouTube URLs       │  Video results       │
       │                     │                      │
       ▼                     │                      │
┌─────────────┐              │                      │
│  YouTube    │              │                      │
│  Download   │◀─────────────┘                      │
│  Client     │  Sonarr sends URL to download      │
└─────────────┘
```

1. **Sonarr requests search** - "Find Kurzgesagt Trees Are Even More Crazy"
2. **Indexer searches YouTube** - Uses yt-dlp to search YouTube
3. **Returns Torznab XML** - Formatted like a torrent indexer, but with YouTube URLs
4. **Sonarr sends to download client** - The YouTube Download Client receives the URL
5. **Video downloads** - yt-dlp downloads the video

## Requirements

- Python 3.8+
- yt-dlp (`pip install yt-dlp`)

## Configuration

Edit the `CONFIG` dict at the top of `youtube_indexer.py`:

```python
CONFIG = {
    "host": "0.0.0.0",        # Listen address
    "port": 9117,              # Port (default Jackett port)
    "api_key": "youtubeindexer",  # API key for authentication
    "indexer_name": "YouTube",
    "log_level": "INFO",
}
```

## Prowlarr Setup (Recommended)

Using Prowlarr is recommended as it syncs indexers to all your *arr apps.

1. Go to **Settings → Indexers**
2. Click **+** → **Generic Torznab**
3. Configure:
   - **Name**: YouTube
   - **URL**: `http://localhost:9117`
   - **API Path**: `/api`
   - **API Key**: `youtubeindexer`
   - **Categories**: `5000` (TV)
4. Click **Test** then **Save**
5. Go to **Settings → Apps** and ensure Sonarr is connected
6. Click **Sync App Indexers**

## Direct Sonarr Setup

If not using Prowlarr:

1. Go to **Settings → Indexers**
2. Click **+** → **Torznab**
3. Configure:
   - **Name**: YouTube
   - **URL**: `http://localhost:9117/api`
   - **API Key**: `youtubeindexer`
   - **Categories**: `5000`
4. Click **Test** then **Save**

## Companion Project

This indexer works together with the **[Sonarr YouTube Download Client](https://github.com/YOUR_USERNAME/sonarr-youtube-dl)** which handles the actual downloading.

**Full Setup:**
1. Run the YouTube Download Client (port 8181)
2. Run this YouTube Indexer (port 9117)
3. Add both to Sonarr/Prowlarr
4. Search and download YouTube content automatically!

## Limitations

- **Search accuracy depends on video titles** - YouTube video titles may not match TheTVDB episode names exactly
- **Rate limiting** - YouTube may rate-limit excessive searches
- **No automatic matching** - Manual search usually works better than automatic for YouTube content

## Troubleshooting

### No results found
- Check yt-dlp is working: `yt-dlp "ytsearch5:kurzgesagt" --flat-playlist -j`
- Check the search query in the logs
- Try a simpler search term

### Connection refused
- Ensure the indexer is running: `python youtube_indexer.py`
- Check firewall settings

### Results don't trigger downloads
- Ensure the YouTube Download Client is configured in Sonarr
- Check that the download client is set as the default for the indexer

## License

MIT License - Use freely, contribute back if you can!

## Credits

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - YouTube search and download
- [Prowlarr](https://prowlarr.com/) - Indexer management
- [Sonarr](https://sonarr.tv/) - TV series management
