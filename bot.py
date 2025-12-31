import feedparser
import json
import os
import requests
from bs4 import BeautifulSoup
from atproto import Client, models

RSS_URL = "http://feeds.bbci.co.uk/news/world/rss.xml"
STATE_FILE = "posted.json"

client = Client()
client.login(
    os.environ["BLUESKY_HANDLE"],
    os.environ["BLUESKY_PASSWORD"]
)

feed = feedparser.parse(RSS_URL)

if os.path.exists(STATE_FILE):
    posted = json.load(open(STATE_FILE))
else:
    posted = []

def get_og_image(url):
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    r = requests.get(url, headers=headers, timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")
    tag = soup.find("meta", property="og:image")
    return tag["content"] if tag else None

for entry in feed.entries:
    if entry.link in posted:
        continue

    image_url = get_og_image(entry.link)
    embed = None

    if image_url:
        img = requests.get(image_url, headers={"User-Agent": "Mozilla/5.0"}).content
        blob = client.upload_blob(img)

        embed = models.AppBskyEmbedImages.Main(
            images=[
                models.AppBskyEmbedImages.Image(
                    image=blob.blob,
                    alt=entry.title
                )
            ]
        )

    client.send_post(
        text=f"{entry.title}\n{entry.link}",
        embed=embed
    )

    posted.append(entry.link)
    break

json.dump(posted, open(STATE_FILE, "w"))
