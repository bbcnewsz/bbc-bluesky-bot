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
    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        tag = soup.find("meta", property="og:image")
        return tag["content"] if tag else None
    except:
        return None

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

    # Skip empty feeds safely
    if not hasattr(feed, "entries") or len(feed.entries) == 0:
        print(f"No articles found in {feed_name} feed, skipping.")
        continue

    for entry in feed.entries:
        try:
            clean_url = clean_bbc_url(entry.link)

            # Skip duplicates
            if clean_url in posted:
                continue

            summary = entry.summary if hasattr(entry, "summary") else ""
            text_content = format_text(entry.title, summary)

            # Try image embed
            image_embed = None
            image_url = get_og_image(entry.link)
            if image_url:
                try:
                    img_data = requests.get(image_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10).content
                    blob = client.upload_blob(img_data)
                    image_embed = models.AppBskyEmbedImages.Main(
                        images=[models.AppBskyEmbedImages.Image(
                            image=blob.blob,
                            alt=entry.title
                        )]
                    )
                except Exception as e:
                    print(f"Failed to fetch/upload image for {clean_url}: {e}")
                    image_embed = None

            # External embed for clickable link if no image
            external_embed = models.AppBskyEmbedExternal.Main(
                external=models.AppBskyEmbedExternal.External(
                    uri=clean_url,
                    title=entry.title,
                    description=summary if summary else "BBC News"
                )
            )

            # Send post
            client.send_post(
                text=text_content,
                embed=image_embed if image_embed else external_embed
            )

            # Mark as posted
            posted.append(clean_url)
            break  # only one article per feed per run

        except Exception as e:
            print(f"Error processing article {entry.link}: {e}")
            continue

# === SAVE STATE ===
with open(STATE_FILE, "w") as f:
    json.dump(posted, f)
