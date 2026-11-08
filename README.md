# NARC website

Static one-page site (`site/`) plus an importer that runs every 3 hours and that copies new Instagram posts and reels onto the site.

## What you edit
- `site/data/event.json` — the **Next event** block (date, time, place, sign-up link). After the date passes the site shows "Soon." by itself.
- `site/index.html` — manifesto and house rules (draft copy, change freely).
- Everything under `site/data/posts.json` and `site/media/ig/` is written by the importer. Don't edit by hand.

## Go live (free): GitHub Pages, ~10 minutes
1. Create a GitHub account/repo. Name it `notanother-run` (URL: `https://<user>.github.io/notanother-run/`), or `<user>.github.io` for a root URL.
2. Upload this whole folder (keep `.github/`), branch `main`.
3. Repo → Settings → Pages → Source: **GitHub Actions**.
4. Actions tab → "Sync Instagram and deploy" → Run workflow. The site is live after ~1 minute.

Alternative: Cloudflare Pages (free, `<name>.pages.dev`), build output directory `site`, no build command. The Instagram sync still runs in GitHub Actions.

A custom `.run` domain (for example notanother.run) is not free (roughly 30 EUR per year). Add it later under Settings → Pages → Custom domain.

## Turn on the Instagram auto-import (one time)
The importer uses Instagram's official API. It needs a **Professional (Creator or Business) account**; switching is free: Instagram → Settings → Account type and tools.
1. developers.facebook.com → My Apps → Create app → use case "Instagram" (Instagram API with Instagram login).
2. App → Instagram → API setup → add your account as an Instagram tester, accept the invite in the Instagram app (Settings → Website permissions → Tester invites).
3. Generate an access token (permissions `instagram_business_basic`), then exchange it for a **long-lived token** (60 days).
4. Repo → Settings → Secrets and variables → Actions → new secret `IG_ACCESS_TOKEN` = that token.
5. Optional, so the token renews itself every Sunday: create a fine-grained GitHub token with *Secrets: read & write* on this repo and save it as the secret `SECRETS_PAT`. Without it, create a new token before the 60 days run out.

From then on, every 3 hours the workflow pulls the latest posts, carousels and reels, downloads the media (Instagram links expire), commits them, and redeploys. If Instagram is unreachable the site keeps its last content.

Before the first sync the Archive shows the intro carousel and the reel as placeholders; the first successful sync replaces them with your real feed.

## Local preview
`cd site && python3 -m http.server 8000`
