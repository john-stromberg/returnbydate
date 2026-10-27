#!/usr/bin/env python3
"""Build returnbydate.com into ./public from data/*.json and src/*.

Edit data/retailers.json (policies), data/affiliates.json (tracking links) or
SITE below, then run:  python3 build.py
"""
import json, html, shutil, datetime
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / "public"

SITE = {
    "domain": "https://returnbydate.com",
    "name": "Return by Date",
    "contact": "hello@returnbydate.com",  # set up free forwarding (e.g. Cloudflare Email Routing)
    "analytics_token": "",                # Cloudflare Web Analytics token; blank = no analytics
}

data = json.loads((ROOT / "data/retailers.json").read_text())
AFF = json.loads((ROOT / "data/affiliates.json").read_text())
SOURCES = json.loads((ROOT / "data/sources.json").read_text())
R = data["retailers"]
CHECKED = datetime.date.fromisoformat(data["checked"])
CHECKED_TXT = CHECKED.strftime("%b %-d, %Y")
e = lambda s: html.escape(str(s), quote=True)


def d(s):
    return datetime.date.fromisoformat(s)


def long_date(s):
    return d(s).strftime("%B %-d, %Y")


def window_txt(r):
    return "no set time limit on most items" if r["window_days"] is None else f'{r["window_days"]} days'


def window_short(r):
    return "No limit" if r["window_days"] is None else f'{r["window_days"]} days'


def shop(r):
    return AFF.get(r["id"]) or r["homepage"]


def short_name(r):
    return r["name"].replace(",", "&").split("&")[0].strip()


LOGO = ('<svg width="26" height="26" viewBox="0 0 26 26" aria-hidden="true">'
        '<rect x="2" y="4" width="22" height="20" rx="3" fill="none" stroke="currentColor" stroke-width="2"/>'
        '<path d="M2 10h22M8 2v4M18 2v4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>'
        '<path d="M8.5 16.5l3 3 6-6" fill="none" stroke="var(--teal)" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg>')


FONTS = "https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,400..800&family=IBM+Plex+Mono:wght@400;500;600&display=swap"
CSS = (ROOT / "src/site.css").read_text()


def page(path, title, desc, body, extra_head="", nav="", og_type="website", modified=None):
    canonical = SITE["domain"] + path
    modified = modified or CHECKED.isoformat()
    analytics = ""
    if SITE["analytics_token"]:
        analytics = ("<script defer src='https://static.cloudflareinsights.com/beacon.min.js' "
                     f"data-cf-beacon='{{\"token\": \"{e(SITE['analytics_token'])}\"}}'></script>")
    navs = {"home": "", "about": "", "holiday": "", "pm": ""}
    if nav in navs:
        navs[nav] = ' aria-current="page"'
    return f"""<!doctype html>
<html lang="en-US">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="{SITE['name']}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{SITE['domain']}/og.png">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta property="article:modified_time" content="{modified}">
<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1">
<meta name="theme-color" content="#F5F6F2">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="preload" as="style" href="{FONTS}" onload="this.onload=null;this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="{FONTS}"></noscript>
<style>{CSS}</style>
{extra_head}{analytics}
</head>
<body>
<header class="site-head"><div class="wrap">
  <a class="logo" href="/">{LOGO}Return by Date</a>
  <nav><a href="/"{navs['home']}>All retailers</a><a href="/holiday-return-deadlines/"{navs['holiday']}>Holiday deadlines</a><a href="/price-match/"{navs['pm']}>Price match</a><a href="/about/"{navs['about']}>About</a></nav>
</div></header>
<main><div class="wrap">
{body}
</div></main>
<footer class="site-foot"><div class="wrap">
  <nav><a href="/">All retailers</a><a href="/holiday-return-deadlines/">2026 holiday return deadlines</a><a href="/price-match/">Stores that price match</a><a href="/about/">About &amp; methodology</a><a href="/privacy/">Privacy</a></nav>
  <div>Policies last checked {CHECKED_TXT}. Retailers change policies without notice; confirm on the retailer's site before relying on a deadline.</div>
  <div>Some links are affiliate links. If you buy through them, Return by Date may earn a commission at no extra cost to you. Retailer names are trademarks of their owners; this site isn't affiliated with or endorsed by any retailer.</div>
</div></footer>
</body>
</html>
"""


def data_script():
    blob = json.dumps({"retailers": R, "affiliates": AFF}, separators=(",", ":")).replace("</", "<\\/")
    return f'<script>window.RBD={blob};</script>\n<script src="/assets/app.js?v={CHECKED.isoformat()}" defer></script>'


PMLBL = {"comp": ("Matches competitors", "p-comp"), "own": ("Own prices only", "p-own"), "none": ("No price match", "p-none")}
HOLLBL = {"confirmed": ("2026 confirmed", "s-confirmed"), "expected": ("Expected", "s-expected"), "none": ("None", "s-none")}


def fmt(dt):
    return dt.strftime("%b %-d, %Y")


def due(r, bought):
    if r["window_days"] is None:
        return None, False
    std = bought + datetime.timedelta(days=r["window_days"])
    h = r["holiday"]
    if h["status"] == "confirmed" and d(h["start"]) <= bought <= d(h["end"]) and d(h["by"]) > std:
        return d(h["by"]), True
    return std, False


def row_html(r, bought):
    t, hol = due(r, bought)
    pm, hl = PMLBL[r["price_match"]], HOLLBL[r["holiday"]["status"]]
    return (f'<article class="row"><div class="rank">{e(r["nrf_rank"])}</div>'
            f'<div class="c-name"><div class="name"><a href="/returns/{r["slug"]}/">{e(r["name"])}</a></div>'
            f'<div class="cat">{e(r["category"])}</div><div class="src">'
            f'{"Checked on retailer page" if r["verified"]=="retailer" else "Secondary sources, confirm"}</div></div>'
            f'<div><span class="lbl">Standard window</span><div class="big">{e(window_short(r))}</div><div class="note">{e(r["window_note"])}</div></div>'
            f'<div><span class="lbl">Price match</span><span class="pill {pm[1]}">{pm[0]}</span><div class="note">{e(r["price_match_note"])}</div></div>'
            f'<div class="c-hol"><span class="lbl">Holiday 2026</span><span class="stamp {hl[1]}">{hl[0]}</span><div class="note">{e(r["holiday"]["note"])}</div></div>'
            f'<div><span class="lbl">Return by</span><div class="due{" hol" if hol else ""}">{fmt(t) if t else "No set limit"}</div>'
            f'<div class="note">{"Holiday extension" if hol else "Standard window" if t else "Most items"}</div></div>'
            f'<div class="c-shop"><a class="shop" href="{e(shop(r))}" target="_blank" rel="sponsored noopener">Shop {e(short_name(r))} ↗</a></div></article>')


def publisher():
    return {"@type": "Organization", "name": SITE["name"], "url": SITE["domain"] + "/",
            "logo": SITE["domain"] + "/favicon.svg"}


# ---------- copy for retailer pages ----------
def holiday_sentence(r):
    h, n = r["holiday"], r["name"]
    if h["status"] == "confirmed":
        return (f'{n} has posted its 2026 holiday extension: items bought {long_date(h["start"])} through '
                f'{long_date(h["end"])} can be returned until {long_date(h["by"])}.')
    if h["status"] == "expected":
        note = h["note"].replace(" 2026 dates not posted yet.", "").replace(" 2026 dates not posted.", "")
        return f"{n} hasn't posted 2026 holiday return dates yet. {note}"
    return h["note"] if h["note"].endswith(".") else h["note"] + "."


def pm_sentence(r):
    return {"comp": "Price match: yes, against competitors. ",
            "own": "Price match: only its own prices. ",
            "none": "Price match: no. "}[r["price_match"]] + r["price_match_note"]


def related(r):
    same = [x for x in R if x["category"] == r["category"] and x["id"] != r["id"]]
    others = sorted([x for x in R if x["id"] != r["id"] and x not in same],
                    key=lambda x: abs(R.index(x) - R.index(r)))
    return (same + others)[:6]


def faq(r):
    n = r["name"]
    qa = [
        (f"How long do I have to return something to {n}?",
         (f"{n} has no set time limit on most items" if r["window_days"] is None else f"{n} gives you {r['window_days']} days for most items") + f". Exceptions: {r['window_note']}."),
        (f"Does {n} extend returns for the 2026 holidays?", holiday_sentence(r)),
        (f"Does {n} price match?", r["price_match_note"]),
    ]
    schema = {"@context": "https://schema.org", "@type": "FAQPage",
              "mainEntity": [{"@type": "Question", "name": q,
                              "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in qa]}
    body = "".join(f"<h3>{e(q)}</h3><p>{e(a)}</p>" for q, a in qa)
    return body, schema


def retailer_page(r):
    n = r["name"]
    h = r["holiday"]
    stamp = {"confirmed": ("2026 confirmed", "s-confirmed"), "expected": ("Expected", "s-expected"),
             "none": ("None", "s-none")}[h["status"]]
    pill = {"comp": ("Matches competitors", "p-comp"), "own": ("Own prices only", "p-own"),
            "none": ("No price match", "p-none")}[r["price_match"]]
    lede = (f"{n} has no set time limit on most returns. " if r["window_days"] is None
            else f"{n} gives you {r['window_days']} days to return most purchases. ") + holiday_sentence(r)
    faq_html, faq_schema = faq(r)
    crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "All retailers", "item": SITE["domain"] + "/"},
        {"@type": "ListItem", "position": 2, "name": f"{n} return policy",
         "item": f'{SITE["domain"]}/returns/{r["slug"]}/'}]}
    upd = r.get("updated", CHECKED.isoformat())
    webpage = {"@context": "https://schema.org", "@type": "WebPage",
               "name": f"{n} return policy and 2026 holiday deadline",
               "url": f'{SITE["domain"]}/returns/{r["slug"]}/', "dateModified": upd,
               "about": {"@type": "Organization", "name": n, "url": r["homepage"]},
               "publisher": publisher()}
    head = (f'<script type="application/ld+json">{json.dumps(faq_schema)}</script>\n'
            f'<script type="application/ld+json">{json.dumps(crumbs)}</script>\n'
            f'<script type="application/ld+json">{json.dumps(webpage)}</script>\n')
    rel = "".join(f'<li><a href="/returns/{x["slug"]}/">{e(x["name"])}<span class="w">{window_short(x)}'
                  f'{" · holiday dates posted" if x["holiday"]["status"]=="confirmed" else ""}</span></a></li>'
                  for x in related(r))
    verified = ("Checked on the retailer's own policy page or notice."
                if r["verified"] == "retailer"
                else "Compiled from consumer-press and coupon-site summaries. Confirm with the retailer.")
    hol_detail = holiday_sentence(r) if h["status"] != "none" else h["note"]
    src_link = (f' <a href="{e(r["source"])}" rel="noopener" target="_blank">See source</a>' if r.get("source") else "")
    body = f"""
<div class="crumbs"><a href="/">All retailers</a> / {e(n)}</div>
<div class="eyebrow" style="margin-top:14px">{e(r['category'])} · Updated <time datetime="{upd}">{fmt(d(upd))}</time></div>
<h1>{e(n)} return policy and 2026 holiday deadline</h1>
<p class="lede">{e(lede)}</p>

<section class="calc" aria-labelledby="calc-h">
  <div class="field"><label for="calc-date" id="calc-h">I bought it on</label>
    <input id="calc-date" type="date" data-id="{e(r['id'])}"></div>
  <div class="answer" aria-live="polite"><span class="k">Return to {e(short_name(r))} by</span>
    <span class="v" id="calc-v">{e(window_short(r))}</span><span class="why" id="calc-why"></span></div>
</section>

<h2>The policy at a glance</h2>
<dl class="facts">
  <dt>Standard window</dt><dd><b>{e(window_short(r))}</b><span class="sub">{e(r['window_note'])}</span></dd>
  <dt>Holiday 2026</dt><dd><span class="stamp {stamp[1]}">{stamp[0]}</span><span class="sub">{e(hol_detail)}</span></dd>
  <dt>Price match</dt><dd><span class="pill {pill[1]}">{pill[0]}</span><span class="sub">{e(r['price_match_note'])}</span></dd>
  <dt>Size</dt><dd>#{e(r['nrf_rank'])} on NRF's 2026 Top 100 Retailers{" (counted within Walmart)" if r["id"]=="samsclub" else ""}</dd>
  <dt>How we checked</dt><dd>{e(verified)}<span class="sub">Last checked {fmt(d(upd))}.{src_link}</span></dd>
</dl>

<div class="cta"><a class="shop" href="{e(shop(r))}" target="_blank" rel="sponsored noopener">Shop {e(short_name(r))} ↗</a>
  <span class="note">Affiliate link</span></div>

<section class="faq"><h2>Common questions</h2>{faq_html}</section>

<h2>Compare with similar stores</h2>
<ul class="related">{rel}</ul>
<p><a href="/">See all {len(R)} retailers side by side →</a> · <a href="/holiday-return-deadlines/">2026 holiday return deadlines</a> · <a href="/price-match/">Stores that price match</a></p>
"""
    title = f"{n} Return Policy 2026: Holiday Deadline & Price Match"
    desc = (f"{n} return window: {window_short(r)}. "
            + ("2026 holiday returns until " + long_date(h["by"]) + ". " if h["status"] == "confirmed" else "")
            + "Price match rules and a return-by date calculator.")
    return page(f'/returns/{r["slug"]}/', title, desc[:300], body,
                extra_head=head + data_script(), og_type="article", modified=upd)


def home():
    confirmed = [x for x in R if x["holiday"]["status"] == "confirmed"]
    rk = lambda x: x["nrf_rank"] if isinstance(x["nrf_rank"], int) else 1.5
    rows = "".join(row_html(x, CHECKED) for x in sorted(R, key=rk))
    az = "".join(f'<li><a href="/returns/{x["slug"]}/">{e(x["name"])}</a></li>'
                 for x in sorted(R, key=lambda x: x["name"].lower()))
    srcs = "".join(f'<li><a href="{e(u)}" rel="noopener" target="_blank">{e(t)}</a></li>' for t, u in SOURCES)
    body = f"""
<div class="eyebrow">2026 holiday season · policies checked {CHECKED_TXT}</div>
<h1>When's the last day you can return it?</h1>
<p class="lede">Return windows, price-match rules and holiday return extensions at 50 of the biggest US retailers. Pick the day you bought something and every row shows your return-by date. {len(confirmed)} retailers have posted 2026 holiday dates so far.</p>
<p class="disclose">Some links are affiliate links. If you buy through them we may earn a commission at no extra cost to you.</p>

<div class="rail" role="search">
  <div class="field"><label for="q">Search retailers</label><input id="q" type="search" placeholder="Try “Target”, “electronics”, “Amazon”"></div>
  <div class="field"><label for="d">Bought on</label><input id="d" type="date"></div>
  <div class="field"><label for="pm">Price match</label>
    <select id="pm"><option value="">Any</option><option value="comp">Matches competitors</option><option value="own">Own prices only</option><option value="none">No price match</option></select></div>
  <div class="field"><label for="hol">Holiday extension</label>
    <select id="hol"><option value="">Any</option><option value="confirmed">Confirmed for 2026</option><option value="expected">Expected, dates not posted</option><option value="none">None / not needed</option></select></div>
  <div class="field"><label for="sort">Sort by</label>
    <select id="sort"><option value="rank">Retailer size</option><option value="due">Latest return-by date</option><option value="window">Longest standard window</option><option value="az">A to Z</option></select></div>
</div>
<div class="count"><span><b id="n">{len(R)}</b> retailers</span><span id="when"></span></div>
<div class="head" aria-hidden="true"><span>#</span><span>Retailer</span><span>Standard window</span><span>Price match</span><span>Holiday 2026</span><span>Return by</span><span></span></div>
<div class="list" id="list">{rows}</div>

<h2>Every retailer, A to Z</h2>
<ul class="related" style="max-width:none">{az}</ul>

<h2>How to read this</h2>
<div class="prose">
<p><b>Confirmed for 2026</b> means the retailer, or its notice to sellers, has posted this season's dates. <b>Expected</b> means it ran an extension last season but hasn't posted 2026 dates; we show last season's terms as a guide and use only the standard window in the return-by date.</p>
<p>Rank is the retailer's position on NRF's 2026 Top 100 (2025 US retail sales). <a href="/about/">More on how we pick and check retailers.</a></p>
</div>
<h2>Sources</h2>
<ul class="sources">{srcs}</ul>
"""
    org = {"@context": "https://schema.org", "@graph": [
        {"@type": "WebSite", "name": SITE["name"], "url": SITE["domain"] + "/", "publisher": publisher()},
        {"@type": "ItemList", "name": "Retailer return policies",
         "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": x["name"] + " return policy",
                              "url": f'{SITE["domain"]}/returns/{x["slug"]}/'} for i, x in enumerate(sorted(R, key=rk))]}]}
    return page("/", "Return by Date: Holiday Return Deadlines for 50 Big Retailers",
                "Look up the last day to return a purchase at Walmart, Amazon, Target, Best Buy and 46 more. "
                "2026 holiday return extensions, return windows and price-match rules.",
                body, extra_head=f'<script type="application/ld+json">{json.dumps(org)}</script>\n' + data_script(),
                nav="home")


def holiday_hub():
    conf = sorted([x for x in R if x["holiday"]["status"] == "confirmed"], key=lambda x: (x["holiday"]["by"], x["name"]))
    exp = sorted([x for x in R if x["holiday"]["status"] == "expected"], key=lambda x: x["name"])
    none = sorted([x for x in R if x["holiday"]["status"] == "none"], key=lambda x: x["name"])
    trs = "".join(f'<tr><td><a href="/returns/{x["slug"]}/">{e(x["name"])}</a></td>'
                  f'<td class="num">{fmt(d(x["holiday"]["start"]))} – {fmt(d(x["holiday"]["end"]))}</td>'
                  f'<td class="num"><b>{fmt(d(x["holiday"]["by"]))}</b></td><td>{e(x["holiday"]["note"].split(". ",1)[-1] if ". " in x["holiday"]["note"] else "")}</td></tr>'
                  for x in conf)
    exp_li = "".join(f'<li><a href="/returns/{x["slug"]}/">{e(x["name"])}</a>: {e(holiday_sentence(x).split(" yet. ",1)[-1])}</li>' for x in exp)
    none_li = "".join(f'<li><a href="/returns/{x["slug"]}/">{e(x["name"])}</a>: {e(window_short(x))} standard window.</li>' for x in none)
    latest_txt = ""
    if conf:
        top = conf[-1]["holiday"]["by"]
        names = [x["name"] for x in conf if x["holiday"]["by"] == top]
        who = names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]
        latest_txt = f", and the latest deadline is {long_date(top)} ({e(who)})"
    body = f"""
<div class="crumbs"><a href="/">All retailers</a> / Holiday return deadlines</div>
<div class="eyebrow" style="margin-top:14px">Updated <time datetime="{CHECKED.isoformat()}">{CHECKED_TXT}</time></div>
<h1>2026 holiday return deadlines</h1>
<p class="lede">{len(conf)} of the {len(R)} retailers we track have posted their 2026 holiday return dates so far{latest_txt}. We check the rest every day and update this page as dates are announced.</p>
<h2>Confirmed for 2026</h2>
<div class="tablewrap"><table class="dtable"><thead><tr><th>Retailer</th><th>Bought between</th><th>Return by</th><th>Notes</th></tr></thead><tbody>{trs}</tbody></table></div>
<h2>Not announced yet</h2>
<p class="prose">These retailers extended returns last season but haven't posted 2026 dates. Until they do, plan on their standard window.</p>
<ul class="prose">{exp_li}</ul>
<h2>No holiday extension</h2>
<p class="prose">These stores don't run a holiday extension, usually because their normal window is long enough to cover gifts, or because they never extend it.</p>
<ul class="prose">{none_li}</ul>
<p><a href="/">Calculate your exact return-by date for any store →</a></p>
"""
    lst = {"@context": "https://schema.org", "@type": "ItemList", "name": "2026 holiday return deadlines",
           "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": f'{x["name"]}: return by {long_date(x["holiday"]["by"])}',
                                "url": f'{SITE["domain"]}/returns/{x["slug"]}/'} for i, x in enumerate(conf)]}
    return page("/holiday-return-deadlines/", "2026 Holiday Return Deadlines: Amazon, Walmart, Target & 47 More",
                "Every 2026 holiday return extension in one list: when each big retailer's window starts and the last day to return gifts. Updated daily.",
                body, extra_head=f'<script type="application/ld+json">{json.dumps(lst)}</script>\n', nav="holiday")


def price_match_hub():
    groups = [("comp", "Stores that match competitors' prices", "Bring proof of a lower price on the identical item and these retailers will match it, within their rules."),
              ("own", "Stores that only match their own prices", "These retailers refund the difference if their own price drops after you buy, but won't match other stores."),
              ("none", "Stores with no price matching", "No competitor matching and no price adjustments. If the price drops, your only option is usually to return and rebuy within the return window.")]
    secs = ""
    for k, h, intro in groups:
        xs = sorted([x for x in R if x["price_match"] == k], key=lambda x: x["name"])
        li = "".join(f'<li><a href="/returns/{x["slug"]}/"><b>{e(x["name"])}</b></a>: {e(x["price_match_note"])}</li>' for x in xs)
        secs += f'<h2>{h} ({len(xs)})</h2><p class="prose">{intro}</p><ul class="prose pmlist">{li}</ul>'
    comp = sum(1 for x in R if x["price_match"] == "comp")
    body = f"""
<div class="crumbs"><a href="/">All retailers</a> / Price match</div>
<div class="eyebrow" style="margin-top:14px">Updated <time datetime="{CHECKED.isoformat()}">{CHECKED_TXT}</time></div>
<h1>Which stores price match in 2026?</h1>
<p class="lede">{comp} of the {len(R)} biggest US retailers still match competitors' prices. Walmart and Target don't anymore: both now match only their own prices. Here's every store's rule.</p>
{secs}
<p><a href="/">Compare return windows and holiday deadlines →</a></p>
"""
    return page("/price-match/", "Which Stores Price Match in 2026? Policies at 50 Big Retailers",
                f"{comp} big retailers still match competitors. Price match and price adjustment rules at Best Buy, Home Depot, Target, Walmart and more.",
                body, nav="pm")


def about():
    body = f"""
<div class="narrow">
<h1>About Return by Date</h1>
<div class="prose">
<p>Return by Date answers one question: how long do you have to take something back? We track return windows, price-match rules and holiday return extensions at 50 of the largest US retailers, and turn them into a date you can act on.</p>
<h2>Which retailers we cover</h2>
<p>We start from the National Retail Federation's 2026 Top 100 Retailers list, ranked by 2025 US retail sales, and skip grocery chains, convenience stores, pharmacy franchise networks and other banners where gift returns rarely come up. Sam's Club is listed on its own even though NRF counts it within Walmart.</p>
<h2>How we check policies</h2>
<p>Each retailer page says whether we confirmed the policy on the retailer's own site or notice, or compiled it from consumer-press and coupon-site summaries. During the holiday season we recheck the retailers that haven't posted their 2026 dates every day, and mark a retailer "2026 confirmed" only once the retailer itself publishes the dates.</p>
<p>Return-by dates use the standard window counted from the purchase date, or the holiday deadline when your purchase falls inside a confirmed holiday window, whichever is later. Online orders often count from the ship or delivery date, which can give you a few extra days.</p>
<h2>How we make money</h2>
<p>Some "Shop" links are affiliate links. If you buy through one, we may earn a commission at no extra cost to you. Commissions never change which retailers we list, how we rank them or what we say about their policies.</p>
<h2>Spotted something out of date?</h2>
<p>Email <b>{e(SITE['contact'])}</b> with the retailer and a link to its current policy and we'll update the page.</p>
</div></div>"""
    return page("/about/", "About Return by Date", "How Return by Date picks retailers, checks return policies and makes money.",
                body, nav="about")


def privacy():
    body = f"""
<div class="narrow">
<h1>Privacy policy</h1>
<p class="eyebrow">Effective {CHECKED_TXT}</p>
<div class="prose">
<p>Return by Date has no accounts, sign-ups or forms, and we don't collect your name, email or purchase details. Dates you type into the calculator stay in your browser.</p>
<h2>What your browser stores</h2>
<p>The comparison page saves your last search, filters and sort order in your browser's local storage so they're there next time. It never leaves your device. Clear your browser's site data to remove it.</p>
<h2>Analytics</h2>
<p>We may use Cloudflare Web Analytics to count page views. It doesn't use cookies or fingerprinting and doesn't track you across sites. Our hosting provider also keeps standard server logs, such as IP addresses and pages requested, for security and reliability.</p>
<h2>Affiliate links</h2>
<p>When you follow a "Shop" link, the retailer or an affiliate network (such as Amazon Associates, Impact, CJ or Rakuten) may set cookies on their own site to credit us for the referral. Their privacy policies cover that data.</p>
<h2>Contact</h2>
<p>Questions about this policy: <b>{e(SITE['contact'])}</b>.</p>
</div></div>"""
    return page("/privacy/", "Privacy Policy | Return by Date", "Return by Date's privacy policy.", body)


def not_found():
    body = """<div class="narrow"><h1>That page isn't here</h1>
<p class="lede">It may have moved. Every retailer we cover is on the comparison page.</p>
<p><a href="/">Go to all retailers →</a></p></div>"""
    return page("/404.html", "Page not found | Return by Date", "Page not found.", body)


def write(path, text):
    p = OUT / path.lstrip("/")
    if path.endswith("/"):
        p = p / "index.html"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "assets").mkdir(parents=True)
    shutil.copy(ROOT / "src/site.css", OUT / "assets/site.css")
    shutil.copy(ROOT / "src/app.js", OUT / "assets/app.js")
    (OUT / "favicon.svg").write_text(LOGO.replace('aria-hidden="true"', 'xmlns="http://www.w3.org/2000/svg"')
                                     .replace("currentColor", "#16212B").replace("var(--teal)", "#0B6B6B"))
    write("/", home())
    write("/about/", about())
    write("/holiday-return-deadlines/", holiday_hub())
    write("/price-match/", price_match_hub())
    if (ROOT / "src/og.png").exists():
        shutil.copy(ROOT / "src/og.png", OUT / "og.png")
    (OUT / "_headers").write_text(
        "/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n"
        "  X-Frame-Options: SAMEORIGIN\n  Cache-Control: public, max-age=0, must-revalidate\n"
        "/assets/*\n  Cache-Control: public, max-age=604800\n/og.png\n  Cache-Control: public, max-age=604800\n")
    write("/privacy/", privacy())
    write("/404.html", not_found())
    for r in R:
        write(f'/returns/{r["slug"]}/', retailer_page(r))
    newest = max([CHECKED.isoformat()] + [r.get("updated", "") for r in R])
    urls = [("/", newest), ("/holiday-return-deadlines/", newest), ("/price-match/", newest),
            ("/about/", CHECKED.isoformat()), ("/privacy/", CHECKED.isoformat())] + \
           [(f'/returns/{r["slug"]}/', r.get("updated", CHECKED.isoformat())) for r in R]
    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{SITE['domain']}{u}</loc><lastmod>{m}</lastmod></url>\n" for u, m in urls)
        + "</urlset>\n")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE['domain']}/sitemap.xml\n")
    print(f"Built {len(urls)} pages into {OUT}")


if __name__ == "__main__":
    main()
