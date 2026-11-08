#!/usr/bin/env python3
"""Sync the Instagram feed of a Professional (Creator/Business) account into site/data/posts.json.

Uses the official Instagram API (Instagram Login). Standard library only.

Env:
  IG_ACCESS_TOKEN   long-lived Instagram user access token (required; without it the script exits 0 and changes nothing)
  IG_API_BASE       default https://graph.instagram.com  (override for tests)
  IG_API_VERSION    default v22.0
  IG_MAX_POSTS      default 60
  IG_REFRESH        "1" -> also refresh the token and write the new one to IG_TOKEN_OUT
  IG_TOKEN_OUT      file the refreshed token is written to
"""
import json, os, sys, time, urllib.parse, urllib.request, urllib.error, pathlib, datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent / "site"
DATA = ROOT / "data" / "posts.json"
MEDIA = ROOT / "media" / "ig"
BASE = os.environ.get("IG_API_BASE", "https://graph.instagram.com").rstrip("/")
VER = os.environ.get("IG_API_VERSION", "v22.0")
MAX = int(os.environ.get("IG_MAX_POSTS", "60"))
TOKEN = os.environ.get("IG_ACCESS_TOKEN", "").strip()
UA = {"User-Agent": "narc-site-sync/1.0"}

FIELDS = ("id,caption,media_type,media_url,thumbnail_url,permalink,timestamp,"
          "children{id,media_type,media_url,thumbnail_url}")


def log(*a):
    print("[ig-sync]", *a, flush=True)


def http(url, tries=3):
    err = None
    for n in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:400]
            err = RuntimeError(f"HTTP {e.code} for {url.split('?')[0]}: {body}")
            if e.code < 500 and e.code != 429:
                break
        except Exception as e:  # network
            err = e
        time.sleep(2 * (n + 1))
    raise err


def api_json(path_or_url, params=None):
    if path_or_url.startswith("http"):
        url = path_or_url
    else:
        url = f"{BASE}/{VER}/{path_or_url}?" + urllib.parse.urlencode(params or {})
    return json.loads(http(url))


def ext_for(url, kind):
    path = urllib.parse.urlparse(url).path.lower()
    for e in (".mp4", ".mov", ".jpg", ".jpeg", ".png", ".webp"):
        if path.endswith(e):
            return ".jpg" if e == ".jpeg" else e
    return ".mp4" if kind == "VIDEO" else ".jpg"


def fetch_file(url, name):
    """Download once; IG CDN URLs expire, so the site hosts its own copies."""
    dest = MEDIA / name
    if not dest.exists() or dest.stat().st_size == 0:
        MEDIA.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(dest.suffix + ".part")
        tmp.write_bytes(http(url))
        tmp.replace(dest)
    return f"media/ig/{name}"


def build_media(item, post_id, idx):
    kind = item.get("media_type", "IMAGE")
    url = item.get("media_url")
    if not url:
        return None
    base = f"{post_id}_{idx}"
    if kind == "VIDEO":
        src = fetch_file(url, base + ext_for(url, "VIDEO"))
        poster = None
        if item.get("thumbnail_url"):
            poster = fetch_file(item["thumbnail_url"], base + "_poster" + ext_for(item["thumbnail_url"], "IMAGE"))
        return {"type": "VIDEO", "src": src, "poster": poster}
    return {"type": "IMAGE", "src": fetch_file(url, base + ext_for(url, "IMAGE"))}


def fetch_feed():
    out, data = [], api_json("me/media", {"fields": FIELDS, "limit": 25, "access_token": TOKEN})
    while True:
        out += data.get("data", [])
        nxt = data.get("paging", {}).get("next")
        if not nxt or len(out) >= MAX:
            break
        data = api_json(nxt)
    return out[:MAX]


def main():
    if not TOKEN:
        log("IG_ACCESS_TOKEN not set; nothing to do (site keeps its current content).")
        return 0

    if os.environ.get("IG_REFRESH") == "1" and os.environ.get("IG_TOKEN_OUT"):
        try:
            r = api_json(f"{BASE}/refresh_access_token?" + urllib.parse.urlencode(
                {"grant_type": "ig_refresh_token", "access_token": TOKEN}))
            pathlib.Path(os.environ["IG_TOKEN_OUT"]).write_text(r["access_token"])
            log(f"token refreshed, valid for {r.get('expires_in', '?')} s")
        except Exception as e:
            log("::warning::token refresh failed:", e)

    items = fetch_feed()
    log(f"API returned {len(items)} posts")

    posts, keep = [], set()
    for it in items:
        pid = it["id"]
        children = it.get("children", {}).get("data") or [it]
        media = []
        for i, c in enumerate(children):
            m = build_media(c, pid, i)
            if m:
                media.append(m)
        if not media:
            continue
        for m in media:
            keep.update(x.split("/")[-1] for x in (m["src"], m.get("poster")) if x)
        t = it.get("media_type", "IMAGE")
        posts.append({
            "id": pid,
            "permalink": it.get("permalink"),
            "timestamp": it.get("timestamp"),
            "caption": it.get("caption", ""),
            "type": "CAROUSEL" if t == "CAROUSEL_ALBUM" else t,
            "media": media,
        })

    if not posts and items:
        raise RuntimeError("API returned posts but none had usable media; keeping old data")

    # remove local media of posts that were deleted on Instagram
    if MEDIA.exists():
        for f in MEDIA.iterdir():
            if f.is_file() and f.name not in keep:
                f.unlink()

    doc = {"updated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+0000"),
           "source": "instagram", "posts": posts}
    new = json.dumps(doc, ensure_ascii=False, indent=1)
    # only touch the file when content (ignoring the timestamp) changed -> no empty commits
    try:
        old = json.loads(DATA.read_text(encoding="utf-8"))
        if old.get("posts") == posts and old.get("source") == "instagram":
            log("no changes")
            return 0
    except Exception:
        pass
    DATA.write_text(new, encoding="utf-8")
    log(f"wrote {len(posts)} posts")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        log("::error::sync failed:", e)
        sys.exit(1)
