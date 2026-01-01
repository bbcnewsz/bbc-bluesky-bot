import feedparser
import json
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urlunparse
from atproto import Client, models

# === CONFIG ===
FEEDS = {
    "World": "http://feeds.bbci.co.uk/news/world/rss.xml",
    "UK": "http://feeds.bbci.co.uk/news/uk/rss.xml",
    "Technology": "http://feeds.bbci.co.uk/news/technology/rss.xml"
}

STATE_FILE = "posted.json"

# === LOGIN ===
client = Client()
client.login(
    os.environ["BLUESKY_HANDLE"],
    os.environ["BLUESKY_PASSWORD"]
)

# === LOAD STATE ===
if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r") as f:
        posted = json.load(f)
else:
    posted = []

# === HELPERS ===
def get_og_image(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers, timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")
    tag = soup.find("meta", property="og:image")
    return tag["content"] if tag else None

def clean_bbc_url(url):
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))

def format_text(title, summary):
    text = title.strip()
    if summary:
        text += "\n\n" + summary.strip()
    return text

# === MAIN LOOP ===
for feed_name, rss_url in FEEDS.items():
    feed = feedparser.parse(rss_url)

    for entry in feed.entries:
    clean_url = clean_bbc_url(entry.link)

    if clean_url in posted:
        continue
        summary = entry.summary if hasattr(entry, "summary") else ""
        text_content = format_text(entry.title, summary)

        # Prepare image embed if available
        image_url = get_og_image(entry.link)
        image_embed = None
        if image_url:
            img_data = requests.get(image_url, headers={"User-Agent": "Mozilla/5.0"}).content
            blob = client.upload_blob(img_data)
            image_embed = models.AppBskyEmbedImages.Main(
                images=[models.AppBskyEmbedImages.Image(
                    image=blob.blob,
                    alt=entry.title
                )]
            )

        # Prepare external link embed (clickable)
        external_embed = models.AppBskyEmbedExternal.Main(
            external=models.AppBskyEmbedExternal.External(
                uri=clean_url,
                title=entry.title,
                description=summary if summary else "BBC News"
            )
        )

        # Post to Bluesky
        client.send_post(
            text=text_content,
            embed=image_embed if image_embed else external_embed
        )

        # Mark as posted
        posted.append(entry.link)
        break  # Only one article per feed per run

# === SAVE STATE ===
with open(STATE_FILE, "w") as f:
    json.dump(posted, f)
