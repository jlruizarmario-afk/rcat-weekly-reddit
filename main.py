"""Download public Daily Discussion threads directly from Reddit's read-only API."""

import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
import sys


DAILY = re.compile(r"\bdaily\s+discussion\b", re.IGNORECASE)


def iso(timestamp):
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()


def discover(subreddit, start, end):
    """Walk newest posts; explicitly report whether we reached the window boundary."""
    found = {}
    scanned = 0
    reached_start = False
    for post in subreddit.new(limit=None):
        scanned += 1
        if post.created_utc < start:
            reached_start = True
            break
        if start <= post.created_utc <= end and DAILY.search(post.title):
            found[post.id] = post
    return sorted(found.values(), key=lambda p: p.created_utc), {
        "posts_scanned": scanned,
        "reached_window_start": reached_start,
        "warning": None if reached_start else (
            "Reddit terminó el listado antes de alcanzar el inicio del intervalo; "
            "no se puede confirmar que estén todos los hilos."
        ),
    }


def extract(post):
    from praw.models import MoreComments

    record = {
        "id": post.id,
        "title": post.title,
        "url": "https://www.reddit.com" + post.permalink,
        "created_at": iso(post.created_utc),
        "author": str(post.author) if post.author else None,
        "body": post.selftext,
        "reported_comment_count": post.num_comments,
        "status": "partial",
        "error_type": None,
        "comments": [],
    }
    forest = None
    unresolved = []
    try:
        post.comment_sort = "old"
        forest = post.comments
        # None expands without a request-count cap; 0 includes continuation links.
        unresolved = forest.replace_more(limit=None, threshold=0)
        record["status"] = "complete" if not unresolved else "partial"
    except Exception as exc:
        # Do not serialize exception messages, which could contain credentials.
        record["error_type"] = type(exc).__name__

    seen = set()
    remaining = []
    if forest is not None:
        for comment in forest.list():
            if isinstance(comment, MoreComments):
                remaining.append(comment)
                continue
            if comment.id in seen:
                continue
            seen.add(comment.id)
            record["comments"].append({
                "id": comment.id,
                "fullname": "t1_" + comment.id,
                "parent_id": comment.parent_id,
                "submission_id": post.id,
                "author": str(comment.author) if comment.author else None,
                "body": comment.body,
                "created_at": iso(comment.created_utc),
                "score": comment.score,
                "url": "https://www.reddit.com" + comment.permalink,
            })
    record["unresolved_more_blocks"] = len(unresolved) + len(remaining)
    if remaining:
        record["status"] = "partial"
    record["downloaded_comment_count"] = len(record["comments"])
    record["fetched_at"] = datetime.now(timezone.utc).isoformat()
    return record


def save(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--output", type=Path, default=Path("weekly_comments.json"))
    args = parser.parse_args()
    if args.days < 1:
        parser.error("--days debe ser mayor que cero")
    try:
        import praw
        from dotenv import load_dotenv
    except ImportError:
        print("Instala las dependencias: python -m pip install -r requirements.txt", file=sys.stderr)
        return 1
    load_dotenv(Path(__file__).with_name(".env"))
    names = ("REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USER_AGENT")
    if any(not os.getenv(name) for name in names):
        print("Faltan credenciales: copia .env.example a .env y completa sus tres valores.", file=sys.stderr)
        return 1
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=args.days)
    payload = {
        "schema_version": 1,
        "subreddit": "RedCatHoldings",
        "window_start": start.isoformat(),
        "window_end": now.isoformat(),
        "status": "partial",
        "discovery": {},
        "threads": [],
    }
    reddit = praw.Reddit(
        client_id=os.environ[names[0]], client_secret=os.environ[names[1]],
        user_agent=os.environ[names[2]], requestor_kwargs={"timeout": 30},
    )
    reddit.read_only = True
    try:
        posts, payload["discovery"] = discover(
            reddit.subreddit("RedCatHoldings"), start.timestamp(), now.timestamp()
        )
        print(f"Encontrados {len(posts)} Daily Discussion en los últimos {args.days} días.")
        for post in posts:
            record = extract(post)
            payload["threads"].append(record)
            save(args.output, payload)
            print(f"{record['title']}: {record['downloaded_comment_count']} comentarios ({record['status']})")
        if payload["discovery"]["reached_window_start"] and all(
            item["status"] == "complete" for item in payload["threads"]
        ):
            payload["status"] = "complete"
    except Exception as exc:
        payload["error_type"] = type(exc).__name__
        print(f"Descarga incompleta ({type(exc).__name__}). Comprueba acceso a Reddit y conexión.", file=sys.stderr)
    finally:
        payload["finished_at"] = datetime.now(timezone.utc).isoformat()
        payload["total_comments"] = sum(t["downloaded_comment_count"] for t in payload["threads"])
        save(args.output, payload)
        reddit.close()
    print(f"Guardado: {args.output} | {payload['total_comments']} comentarios | {payload['status']}")
    return 0 if payload["status"] == "complete" else 2


if __name__ == "__main__":
    sys.exit(main())
