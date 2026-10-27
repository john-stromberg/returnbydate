# returnbydate.com

Static site built from JSON: a comparison tool on the homepage, one page per retailer, and hub pages for
2026 holiday return deadlines and price matching.

## Files
- `data/retailers.json` – every policy. When a retailer changes, edit its entry and set its `updated` date
  (that date feeds the page's "Updated" line, its structured data and the sitemap). `checked` is the site-wide date.
- `data/affiliates.json` – paste each retailer's affiliate tracking link next to its id. Blank = plain homepage link.
- `data/sources.json` – sources listed on the homepage.
- `src/` – stylesheet, script and social preview image (`og.png`).
- `build.py` – `python3 build.py` writes the site to `public/` (git-ignored). Set the contact email and the
  Cloudflare Web Analytics token in `SITE` at the top.

## Deploy: GitHub + Cloudflare Pages (auto-deploys on every push)
1. Create an empty GitHub repo (e.g. `returnbydate`), then from this folder:
   `git init && git add . && git commit -m "Initial site" && git branch -M main && git remote add origin https://github.com/<you>/returnbydate.git && git push -u origin main`
2. Cloudflare → Workers & Pages → Create → Pages → Connect to Git → pick the repo.
   Build command `python3 build.py` · Build output directory `public`.
3. Custom domains → add `returnbydate.com` and `www.returnbydate.com` (redirect www to the bare domain).
4. Email → Email Routing → forward hello@returnbydate.com to your inbox.
5. Analytics → Web Analytics → add the site, paste the token into `SITE["analytics_token"]`, push.
6. Caching → Configuration → turn on **Crawler Hints** (tells Bing and others about changes via IndexNow).
7. Google Search Console and Bing Webmaster Tools → verify the domain → submit `https://returnbydate.com/sitemap.xml`.

Any edit pushed to `main` (by you, Copilot CLI, or the daily recheck) rebuilds and redeploys the live site.
