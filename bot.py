import feedparser
import json
import os
from atproto import Client, models

# === CONFIG ===
RSS_URL = "http://feeds.bbci.co.uk/news/technology/rss.xml"
STATE_FILE = "posted.json"

# === LOGIN ===
client = Client()
client.login(
    os.environ["BLUESKY_HANDLE"],
    os.environ["BLUESKY_PASSWORD"]
)

# === LOAD FEED ===
feed = feedparser.parse(RSS_URL)

# === LOAD POSTED STATE ===
if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r") as f:
        posted_links = json.load(f)
else:
    posted_links = []

# === POST FIRST NEW ARTICLE ===
for entry in feed.entries:
    if entry.link not in posted_links:
        text = entry.title

        embed = models.AppBskyEmbedExternal.Main(
            external=models.AppBskyEmbedExternal.External(
                uri=entry.link,
                title=entry.title,
                description="BBC News"
            )
        )

        client.send_post(text=text, embed=embed)

        posted_links.append(entry.link)
        break

# === SAVE STATE ===
with open(STATE_FILE, "w") as f:
    json.dump(posted_links, f)
