#!/usr/bin/env python3
"""Seed the sources table from data/feeds.json."""
import json
import os
import sys

import psycopg2

DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", 5432)),
    "dbname": os.getenv("POSTGRES_DB", "news_ai"),
    "user": os.getenv("POSTGRES_USER", "news_user"),
    "password": os.getenv("POSTGRES_PASSWORD", "news_pass"),
}

FEEDS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "feeds.json")


def seed():
    with open(FEEDS_PATH) as f:
        feeds = json.load(f)

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    inserted = 0
    skipped = 0
    for feed in feeds:
        try:
            category = feed.get("category", feed.get("group", ""))
            cur.execute(
                """INSERT INTO sources (name, url, language, country, group_name, category, subcategory)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (url) DO NOTHING""",
                (
                    feed.get("name", ""),
                    feed["url"],
                    feed.get("language", "en"),
                    feed.get("country"),
                    category,
                    category,
                    feed.get("subcategory"),
                ),
            )
            if cur.rowcount > 0:
                inserted += 1
            else:
                skipped += 1
        except Exception as e:
            print(f"Error inserting {feed.get('name')}: {e}")
            conn.rollback()
            continue

    conn.commit()
    cur.close()
    conn.close()
    print(f"Seeded {inserted} sources ({skipped} already existed)")


if __name__ == "__main__":
    seed()
