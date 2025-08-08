from data.feeds import feeds
from feedparser import parse

def gather():
    for item in feeds:
        feed = fetch(item.url)


