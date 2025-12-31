import feedparser
import json
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urlunparse
from atproto import Client, models
from PIL import Image
from io import BytesIO

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

def format_text(title, summary, clean_url):
    text = title.strip()
    if summary:
        text += "\n\n" + summary.strip()
    text += "\n\nRead more: " + clean_url
    return text

def process_image(image_url, target_ratio=4/3):
    # Fetch image
    img_data = requests.get(image_url, headers={"User-Agent": "Mozilla/5.0"}).content
    img = Image.open(BytesIO(img_data))

    # Crop to target ratio (4:3)
    width, height = img.size
    current_ratio = width / height

    if current_ratio > target_ratio:
        # Too wide → crop sides
        new_width = int(height * target_ratio)
        left = (width - new_width) // 2
        img = img.crop((left, 0, left + new_width, height))
    elif current_ratio < target_ratio:
        # Too tall → crop top/bottom
        new_height = int(width / target_ratio)
        top = (height - new_height) // 2
        img = img.crop((0, top, width, top + new_height))

    # Save to bytes
    output = BytesIO()
    img.save(output, format="JPEG")
    output.seek(0)
    return output.read()

# === MAIN LOOP ===
for feed_name, rss_url in FEEDS.items():
    feed = feedparser.parse(rss_url)

    for entry in feed.entries:
        if entry.link in posted:
            continue

        clean_url = clean_bbc_url(entry.link)
        summary = entry.summary if hasattr(entry, "summary") else ""
        image_url = get_og_image(entry.link)
        embed = None

        if image_url:
            processed_image = process_image(image_url)
            blob = client.upload_blob(processed_image)
            embed = models.AppBskyEmbedImages.Main(
                images=[models.AppBskyEmbedImages.Image(
                    image=blob.blob,
                    alt=entry.title
                )]
            )

        # Post to Bluesky
        client.send_post(
            text=format_text(entry.title, summary, clean_url),
            embed=embed
        )

        # Mark as posted
        posted.append(entry.link)
        break  # Only one article per feed per run

# === SAVE STATE ===
with open(STATE_FILE, "w") as f:
    json.dump(posted, f)
