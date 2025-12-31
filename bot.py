import feedparser
import json
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urlunparse
from atproto import Client, models

# === CONFIG ===
RSS_URL = "http://feeds.bbci.co.uk/news/world/rss.xml"
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
        posted = json.load(f)
else:
    posted = []

# === HELPERS ===
def get_og_image(url):
    """Fetch the og:image from a BBC article."""
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers, timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")
    tag = soup.find("meta", property="og:image")
    return tag["content"] if tag else None

def clean_bbc_url(url):
    """Remove RSS tracking parameters from BBC URL."""
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))

# === POST FIRST NEW ARTICLE ===
for entry in feed.entries:
    if entry.link in posted:
        continue

    clean_url = clean_bbc_url(entry.link)
    image_url = get_og_image(entry.link)
    embed = None

    # If an image exists, upload it
    if image_url:
        img_data = requests.get(image_url, headers={"User-Agent": "Mozilla/5.0"}).content
        blob = client.upload_blob(img_data)
        embed = models.AppBskyEmbedImages.Main(
            images=[models.AppBskyEmbedImages.Image(
                image=blob.blob,
                alt=entry.title
            )]
        )

    # Post headline + optional image
    client.send_post(
        text=entry.title,
        embed=embed
    )

    # Mark as posted
    posted.append(entry.link)
    break  # Only post one new article per run

# === SAVE STATE ===
with open(STATE_FILE, "w") as f:
    json.dump(posted, f)
