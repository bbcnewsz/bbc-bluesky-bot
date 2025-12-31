import feedparser
import json
import os
from atproto import Client

RSS_URL = "http://feeds.bbci.co.uk/news/world/rss.xml"
STATE_FILE = "posted.json"

client = Client()
client.login(
    os.environ["BLUESKY_HANDLE"],
    os.environ["BLUESKY_PASSWORD"]
)

feed = feedparser.parse(RSS_URL)

if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r") as f:
        posted = json.load(f)
else:
    posted = []

for entry in feed.entries:
    if entry.link not in posted:
        text = entry.title

client.send_post(
    text=text,
    embed={
        "$type": "app.bsky.embed.external",
        "external": {
            "uri": entry.link,
            "title": entry.title,
            "description": "BBC News"
        }
    }
)
        posted.append(entry.link)
        break

with open(STATE_FILE, "w") as f:
    json.dump(posted, f)
