"""
KelsAI Job Search Agent v2
- Parallel scraping via ThreadPoolExecutor
- 24-hour SQLite cache
- Fuzzy deduplication across sources
- 10 sources: LinkedIn, Remotive, Arbeitnow, Himalayas, WeWorkRemotely,
               Internshala, AngelList/Wellfound, Instahyre, Freshersworld, Shine
"""

import requests
import feedparser
import hashlib
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from bs4 import BeautifulSoup
from rapidfuzz import fuzz

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

ALL_SOURCES = [
    # Global / Remote
    "LinkedIn", "Remotive", "Arbeitnow", "Himalayas", "WeWorkRemotely",
    # Free APIs (no key needed)
    "Jobicy", "NaukriRSS",
    # Free tier APIs (key required — set in .env)
    "JSearch", "Adzuna",
    # India-specific scrapers
    "Internshala", "AngelList", "Instahyre", "Freshersworld", "Shine",
]


def _delay(a=0.5, b=1.5):
    time.sleep(random.uniform(a, b))


def _cache_key(keywords: list, sources: list, locations: str) -> str:
    raw = f"{sorted(keywords)}|{sorted(sources)}|{locations}"
    return hashlib.md5(raw.encode()).hexdigest()


# ─── LinkedIn ─────────────────────────────────────────────────────────────────

def search_linkedin(keywords: list, locations: str = "India",
                    remote: bool = False, experience_level: str = "mid",
                    limit: int = 30) -> list:
    """LinkedIn guest public API — paginated, with remote + experience filters."""
    jobs = []
    keyword_str = "%20".join(keywords[:3])
    loc_list = [l.strip() for l in locations.split(",") if l.strip()]
    loc_str = "%20".join((loc_list[0] if loc_list else "India").split())
    geo_id = "102713980"  # India

    # Experience level mapping
    exp_map = {"entry": "2", "mid": "3", "senior": "4", "lead": "5"}
    exp_code = exp_map.get(experience_level.lower().split("-")[0], "3")

    for start in range(0, min(limit, 50), 10):
        try:
            params = (
                f"?keywords={keyword_str}&location={loc_str}&geoId={geo_id}"
                f"&f_E={exp_code}&start={start}"
            )
            if remote:
                params += "&f_WT=2"
            url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search{params}"
            resp = requests.get(url, headers=HEADERS, timeout=12)
            if resp.status_code != 200:
                break

            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.find_all("li")
            if not cards:
                break

            for card in cards:
                t = card.find("h3", class_="base-search-card__title")
                c = card.find("h4", class_="base-search-card__subtitle")
                l = card.find("span", class_="job-search-card__location")
                a = card.find("a", class_="base-card__full-link")
                tm = card.find("time")
                if not (t and a):
                    continue
                company = ""
                if c:
                    ca = c.find("a")
                    company = ca.get_text(strip=True) if ca else c.get_text(strip=True)
                title = t.get_text(strip=True)
                location = l.get_text(strip=True) if l else loc_list[0] if loc_list else "India"
                job_url = a["href"].split("?")[0]
                posted = tm.get("datetime", "") if tm else ""
                jobs.append({
                    "title": title, "company": company, "location": location,
                    "job_type": "Remote" if remote else "Full-time", "salary": "",
                    "description": f"Title: {title}\nCompany: {company}\nLocation: {location}\nPosted: {posted}",
                    "url": job_url, "source": "LinkedIn",
                    "discovered_at": datetime.now().isoformat(),
                })
            _delay(0.8, 1.5)
        except Exception as e:
            print(f"[LinkedIn] Error at start={start}: {e}")
            break

    return jobs[:limit]


# ─── Remotive ─────────────────────────────────────────────────────────────────

def search_remotive(keywords: list, limit: int = 30) -> list:
    jobs = []
    keyword_str = "+".join(keywords[:3])
    try:
        feed = feedparser.parse(f"https://remotive.com/remote-jobs/feed?category={keyword_str}")
        for entry in feed.entries[:limit]:
            jobs.append({
                "title": entry.get("title", ""), "company": entry.get("author", "Unknown"),
                "location": "Remote", "job_type": "Full-time", "salary": "",
                "description": BeautifulSoup(entry.get("summary", ""), "html.parser").get_text()[:2000],
                "url": entry.get("link", ""), "source": "Remotive",
                "discovered_at": datetime.now().isoformat(),
            })
    except Exception as e:
        print(f"[Remotive] {e}")
    return jobs


# ─── Arbeitnow ────────────────────────────────────────────────────────────────

def search_arbeitnow(keywords: list, remote: bool = True, limit: int = 30) -> list:
    jobs = []
    try:
        params = {"search": " ".join(keywords[:3]), "remote": "true" if remote else "false"}
        resp = requests.get("https://www.arbeitnow.com/api/job-board-api",
                            params=params, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            for item in resp.json().get("data", [])[:limit]:
                jobs.append({
                    "title": item.get("title", ""), "company": item.get("company_name", "Unknown"),
                    "location": item.get("location", "Remote"),
                    "job_type": "Remote" if item.get("remote") else "On-site",
                    "salary": "", "source": "Arbeitnow",
                    "description": BeautifulSoup(item.get("description", ""), "html.parser").get_text()[:2000],
                    "url": item.get("url", ""),
                    "discovered_at": datetime.now().isoformat(),
                })
    except Exception as e:
        print(f"[Arbeitnow] {e}")
    return jobs


# ─── Himalayas ────────────────────────────────────────────────────────────────

def search_himalayas(keywords: list, limit: int = 20) -> list:
    jobs = []
    try:
        keyword_str = "%20".join(keywords[:3])
        feed = feedparser.parse(f"https://himalayas.app/jobs/rss?q={keyword_str}")
        for entry in feed.entries[:limit]:
            jobs.append({
                "title": entry.get("title", ""), "company": entry.get("author", "Unknown"),
                "location": "Remote", "job_type": "Full-time", "salary": "",
                "description": BeautifulSoup(entry.get("summary", ""), "html.parser").get_text()[:2000],
                "url": entry.get("link", ""), "source": "Himalayas",
                "discovered_at": datetime.now().isoformat(),
            })
    except Exception as e:
        print(f"[Himalayas] {e}")
    return jobs


# ─── We Work Remotely ─────────────────────────────────────────────────────────

def search_weworkremotely(limit: int = 20) -> list:
    jobs = []
    feeds = [
        "https://weworkremotely.com/categories/remote-programming-jobs.rss",
        "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss",
    ]
    try:
        for feed_url in feeds:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:limit // 2]:
                jobs.append({
                    "title": entry.get("title", ""), "company": "",
                    "location": "Remote", "job_type": "Full-time", "salary": "",
                    "description": BeautifulSoup(entry.get("summary", ""), "html.parser").get_text()[:2000],
                    "url": entry.get("link", ""), "source": "WeWorkRemotely",
                    "discovered_at": datetime.now().isoformat(),
                })
    except Exception as e:
        print(f"[WWR] {e}")
    return jobs


# ─── Internshala ──────────────────────────────────────────────────────────────

def search_internshala(keywords: list, limit: int = 20) -> list:
    """Scrape Internshala jobs (great for fresher/entry-level India roles)."""
    jobs = []
    try:
        keyword_str = "-".join(keywords[:2]).lower().replace(" ", "-")
        url = f"https://internshala.com/jobs/{keyword_str}-jobs"
        resp = requests.get(url, headers=HEADERS, timeout=12)
        if resp.status_code != 200:
            return jobs
        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.find_all("div", class_="individual_internship")[:limit]
        for card in cards:
            title_tag = card.find("h3", class_="job-internship-name")
            company_tag = card.find("h4", class_="company-name")
            loc_tag = card.find("div", id=lambda x: x and "location_names" in (x or ""))
            link_tag = card.find("a", class_="view_detail_button")
            if not (title_tag and link_tag):
                continue
            href = link_tag.get("href", "")
            if not href.startswith("http"):
                href = "https://internshala.com" + href
            jobs.append({
                "title": title_tag.get_text(strip=True),
                "company": company_tag.get_text(strip=True) if company_tag else "Unknown",
                "location": loc_tag.get_text(strip=True) if loc_tag else "India",
                "job_type": "Full-time", "salary": "",
                "description": f"Role: {title_tag.get_text(strip=True)} at {company_tag.get_text(strip=True) if company_tag else 'Company'}",
                "url": href, "source": "Internshala",
                "discovered_at": datetime.now().isoformat(),
            })
    except Exception as e:
        print(f"[Internshala] {e}")
    return jobs


# ─── AngelList / Wellfound ────────────────────────────────────────────────────

def search_angellist(keywords: list, limit: int = 20) -> list:
    """Search AngelList/Wellfound via public RSS (startup/tech roles)."""
    jobs = []
    try:
        keyword_str = "%20".join(keywords[:3])
        url = f"https://wellfound.com/jobs?q={keyword_str}&remote=true"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        # Wellfound serves JS-rendered content, grab JSON-LD if present
        scripts = soup.find_all("script", type="application/ld+json")
        count = 0
        for script in scripts:
            try:
                import json
                data = json.loads(script.string or "")
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if item.get("@type") == "JobPosting" and count < limit:
                        jobs.append({
                            "title": item.get("title", ""),
                            "company": item.get("hiringOrganization", {}).get("name", "Startup"),
                            "location": item.get("jobLocation", {}).get("address", {}).get("addressLocality", "Remote") if isinstance(item.get("jobLocation"), dict) else "Remote",
                            "job_type": item.get("employmentType", "Full-time"),
                            "salary": "", "source": "AngelList",
                            "description": BeautifulSoup(item.get("description", ""), "html.parser").get_text()[:2000],
                            "url": item.get("url", url),
                            "discovered_at": datetime.now().isoformat(),
                        })
                        count += 1
            except Exception:
                continue
    except Exception as e:
        print(f"[AngelList] {e}")
    return jobs


# ─── Instahyre ────────────────────────────────────────────────────────────────

def search_instahyre(keywords: list, limit: int = 15) -> list:
    """Search Instahyre (quality India tech jobs)."""
    jobs = []
    try:
        keyword_str = "+".join(keywords[:3])
        resp = requests.get(
            f"https://www.instahyre.com/api/v1/opportunity/?format=json&search={keyword_str}&limit={limit}",
            headers=HEADERS, timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            for item in (data.get("results") or data if isinstance(data, list) else [])[:limit]:
                company = item.get("company", {})
                jobs.append({
                    "title": item.get("designation", ""),
                    "company": company.get("name", "Unknown") if isinstance(company, dict) else str(company),
                    "location": item.get("location", "India"),
                    "job_type": "Full-time", "salary": str(item.get("ctc", "")),
                    "description": item.get("about", "")[:2000],
                    "url": f"https://www.instahyre.com/candidate/find-jobs/opportunity/{item.get('id','')}",
                    "source": "Instahyre",
                    "discovered_at": datetime.now().isoformat(),
                })
    except Exception as e:
        print(f"[Instahyre] {e}")
    return jobs


# ─── Freshersworld ────────────────────────────────────────────────────────────

def search_freshersworld(keywords: list, limit: int = 15) -> list:
    """Search Freshersworld (entry-level India jobs)."""
    jobs = []
    try:
        keyword_str = "+".join(keywords[:2])
        url = f"https://www.freshersworld.com/jobs/jobsearch/{keyword_str}-jobs?job_type=Jobs"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.find_all("li", class_="job-container")[:limit]
        for card in cards:
            title = card.find("a", class_="job-title-link")
            company = card.find("span", class_="company-name")
            location = card.find("span", class_="location-text")
            if not (title and title.get("href")):
                continue
            href = title["href"]
            if not href.startswith("http"):
                href = "https://www.freshersworld.com" + href
            jobs.append({
                "title": title.get_text(strip=True),
                "company": company.get_text(strip=True) if company else "Unknown",
                "location": location.get_text(strip=True) if location else "India",
                "job_type": "Full-time", "salary": "", "source": "Freshersworld",
                "description": f"Entry-level job: {title.get_text(strip=True)}",
                "url": href,
                "discovered_at": datetime.now().isoformat(),
            })
    except Exception as e:
        print(f"[Freshersworld] {e}")
    return jobs


# ─── Shine.com ────────────────────────────────────────────────────────────────

def search_shine(keywords: list, locations: str = "India", limit: int = 15) -> list:
    """Search Shine.com (popular Indian job board)."""
    jobs = []
    try:
        kw = "%20".join(keywords[:2])
        loc = locations.split(",")[0].strip().lower().replace(" ", "-")
        url = f"https://www.shine.com/job-search/{kw}-jobs-in-{loc}"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.find_all("article", class_="jsx-")[:limit]
        if not cards:
            cards = soup.select("div.jobCard, div[class*='jobListing'], li.jobItem")[:limit]
        for card in cards:
            title = card.find("h2") or card.find("h3")
            company = card.find(class_=lambda c: c and "company" in c.lower()) if card else None
            link = card.find("a")
            if not (title and link):
                continue
            href = link.get("href", "")
            if not href.startswith("http"):
                href = "https://www.shine.com" + href
            jobs.append({
                "title": title.get_text(strip=True),
                "company": company.get_text(strip=True) if company else "Unknown",
                "location": locations.split(",")[0].strip(),
                "job_type": "Full-time", "salary": "", "source": "Shine",
                "description": f"Job at Shine.com: {title.get_text(strip=True)}",
                "url": href,
                "discovered_at": datetime.now().isoformat(),
            })
    except Exception as e:
        print(f"[Shine] {e}")
    return jobs


# ─── Fuzzy Deduplication ──────────────────────────────────────────────────────

def _fuzzy_deduplicate(jobs: list, threshold: int = 85) -> list:
    """Remove duplicate jobs across sources using fuzzy title+company matching."""
    unique = []
    for job in jobs:
        key = f"{job.get('title','').lower()} {job.get('company','').lower()}"
        is_dup = False
        for seen in unique:
            seen_key = f"{seen.get('title','').lower()} {seen.get('company','').lower()}"
            if fuzz.ratio(key, seen_key) >= threshold:
                is_dup = True
                # Keep the one with a richer description
                if len(job.get("description", "")) > len(seen.get("description", "")):
                    unique.remove(seen)
                    unique.append(job)
                break
        if not is_dup:
            unique.append(job)
    return unique


# ─── Keyword Pre-filter ───────────────────────────────────────────────────────

def _keyword_filter(jobs: list, keywords: list) -> list:
    """Keep only jobs whose title or description contains at least one keyword token."""
    tokens = set()
    for kw in keywords:
        for token in kw.lower().split():
            if len(token) > 2:
                tokens.add(token)
    if not tokens:
        return jobs
    return [
        j for j in jobs
        if any(tok in (j.get("title", "") + " " + j.get("description", "")).lower() for tok in tokens)
    ]


# ─── Jobicy (100% Free Public API) ──────────────────────────────────────────

def search_jobicy(keywords: list, limit: int = 30) -> list:
    """Jobicy Remote Jobs API — completely free, no key needed."""
    jobs = []
    try:
        tag = keywords[0].replace(" ", "+") if keywords else "developer"
        resp = requests.get(
            f"https://jobicy.com/api/v2/remote-jobs?count={limit}&tag={tag}",
            headers=HEADERS, timeout=12
        )
        if resp.status_code == 200:
            for item in resp.json().get("jobs", [])[:limit]:
                jobs.append({
                    "title": item.get("jobTitle", ""),
                    "company": item.get("companyName", "Unknown"),
                    "location": item.get("jobGeo", "Remote"),
                    "job_type": item.get("jobType", "Full-time"),
                    "salary": item.get("annualSalaryMin", ""),
                    "description": item.get("jobDescription", "")[:2000],
                    "url": item.get("url", ""),
                    "source": "Jobicy",
                    "discovered_at": datetime.now().isoformat(),
                })
    except Exception as e:
        print(f"[Jobicy] {e}")
    return jobs


# ─── Naukri RSS Feed (100% Free) ─────────────────────────────────────────────

def search_naukri_rss(keywords: list, locations: str = "India", limit: int = 30) -> list:
    """
    Naukri.com publishes undocumented but public RSS feeds.
    URL pattern: https://www.naukri.com/rss/jobsearch/it-jobs?k=<keyword>&l=<location>
    """
    jobs = []
    kw = keywords[0].replace(" ", "-").lower() if keywords else "software"
    loc = locations.split(",")[0].strip().lower().replace(" ", "-")
    try:
        rss_url = f"https://www.naukri.com/jobapi/v3/search?noOfResults={limit}&urlType=search_by_keyword&searchType=adv&keyword={'+'.join(keywords[:2])}&location={loc}&pageNo=1&seoKey={kw}-jobs-in-{loc}&src=jobsearchDesk&latLong="
        # Naukri also exposes a simplified RSS-like public feed:
        feed_url = f"https://www.naukri.com/rss/jobsearch/it-jobs?k={keywords[0]}&l={loc}"
        feed = feedparser.parse(feed_url)
        for entry in feed.entries[:limit]:
            title = entry.get("title", "")
            link = entry.get("link", "")
            summary = entry.get("summary", "")
            # Naukri RSS title is usually: "Job Title - Company Name"
            parts = title.split(" - ", 1)
            job_title = parts[0].strip() if parts else title
            company = parts[1].strip() if len(parts) > 1 else "Unknown"
            jobs.append({
                "title": job_title,
                "company": company,
                "location": loc.title(),
                "job_type": "Full-time",
                "salary": "",
                "description": BeautifulSoup(summary, "html.parser").get_text()[:2000],
                "url": link,
                "source": "NaukriRSS",
                "discovered_at": datetime.now().isoformat(),
            })
    except Exception as e:
        print(f"[NaukriRSS] {e}")
    return jobs


# ─── JSearch via RapidAPI (Free 200 req/month) ────────────────────────────────

def search_jsearch(keywords: list, locations: str = "India", remote: bool = False,
                   limit: int = 30, api_key: str = None) -> list:
    """
    JSearch on RapidAPI — aggregates LinkedIn + Indeed + Glassdoor.
    FREE tier: 200 requests/month. Pass api_key directly or set RAPIDAPI_KEY in .env.
    Sign up at: https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
    """
    import os
    key = api_key or os.getenv("RAPIDAPI_KEY", "")
    if not key:
        print("[JSearch] No API key set. Skipping. Get a free key at rapidapi.com")
        return []
    jobs = []
    query = " ".join(keywords[:2])
    loc = locations.split(",")[0].strip()
    try:
        url = "https://jsearch.p.rapidapi.com/search"
        params = {
            "query": f"{query} jobs in {loc}",
            "page": "1",
            "num_pages": "2",
            "date_posted": "week",
        }
        if remote:
            params["remote_jobs_only"] = "true"
        resp = requests.get(
            url,
            headers={
                **HEADERS,
                "X-RapidAPI-Key": key,
                "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
            },
            params=params,
            timeout=15,
        )
        if resp.status_code == 200:
            for item in resp.json().get("data", [])[:limit]:
                jobs.append({
                    "title": item.get("job_title", ""),
                    "company": item.get("employer_name", "Unknown"),
                    "location": item.get("job_city", loc) + ", " + item.get("job_country", ""),
                    "job_type": item.get("job_employment_type", "Full-time"),
                    "salary": f"{item.get('job_min_salary','')} - {item.get('job_max_salary','')}".strip(" - "),
                    "description": item.get("job_description", "")[:2000],
                    "url": item.get("job_apply_link", item.get("job_google_link", "")),
                    "source": f"JSearch ({item.get('job_publisher','')[:10]})",
                    "discovered_at": datetime.now().isoformat(),
                })
        elif resp.status_code == 429:
            print("[JSearch] Rate limit reached (200 req/month on free tier)")
        else:
            print(f"[JSearch] HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"[JSearch] {e}")
    return jobs


# ─── Adzuna India (Free 1000 req/month) ──────────────────────────────────────

def search_adzuna(keywords: list, locations: str = "India", limit: int = 30,
                  app_id: str = None, app_key: str = None) -> list:
    """
    Adzuna Jobs API — has India-specific data with salary info.
    FREE tier: 1000 requests/month. Pass keys directly or set ADZUNA_APP_ID + ADZUNA_APP_KEY in .env.
    Sign up at: https://developer.adzuna.com/
    """
    import os
    _app_id = app_id or os.getenv("ADZUNA_APP_ID", "")
    _app_key = app_key or os.getenv("ADZUNA_APP_KEY", "")
    if not _app_id or not _app_key:
        print("[Adzuna] No keys set. Skipping. Get free keys at developer.adzuna.com")
        return []
    jobs = []
    query = " ".join(keywords[:3])
    try:
        resp = requests.get(
            f"https://api.adzuna.com/v1/api/jobs/in/search/1",
            params={
                "app_id": _app_id,
                "app_key": _app_key,
                "results_per_page": min(limit, 50),
                "what": query,
                "content-type": "application/json",
                "sort_by": "date",
            },
            headers=HEADERS,
            timeout=12,
        )
        if resp.status_code == 200:
            for item in resp.json().get("results", [])[:limit]:
                jobs.append({
                    "title": item.get("title", ""),
                    "company": item.get("company", {}).get("display_name", "Unknown"),
                    "location": item.get("location", {}).get("display_name", "India"),
                    "job_type": item.get("contract_time", "full_time").replace("_", " ").title(),
                    "salary": f"\u20b9{item.get('salary_min',''):.0f} - \u20b9{item.get('salary_max',''):.0f}" if item.get('salary_min') else "",
                    "description": item.get("description", "")[:2000],
                    "url": item.get("redirect_url", ""),
                    "source": "Adzuna",
                    "discovered_at": datetime.now().isoformat(),
                })
        else:
            print(f"[Adzuna] HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"[Adzuna] {e}")
    return jobs


# ─── Main Search Orchestrator ─────────────────────────────────────────────────

SOURCE_FN_MAP = {
    # ── Global / Remote ───────────────────────────────────────────────────────
    "LinkedIn":       lambda kw, prefs, is_remote, loc, keys: search_linkedin(
        kw, locations=loc, remote=is_remote,
        experience_level=prefs.get("experience_level", "mid"), limit=30),
    "Remotive":       lambda kw, prefs, is_remote, loc, keys: search_remotive(kw, limit=30),
    "Arbeitnow":      lambda kw, prefs, is_remote, loc, keys: search_arbeitnow(kw, remote=is_remote, limit=30),
    "Himalayas":      lambda kw, prefs, is_remote, loc, keys: search_himalayas(kw, limit=20),
    "WeWorkRemotely": lambda kw, prefs, is_remote, loc, keys: search_weworkremotely(limit=20),
    # ── Free APIs (zero key needed) ───────────────────────────────────────────
    "Jobicy":         lambda kw, prefs, is_remote, loc, keys: search_jobicy(kw, limit=30),
    "NaukriRSS":      lambda kw, prefs, is_remote, loc, keys: search_naukri_rss(kw, locations=loc, limit=30),
    # ── Free-tier APIs (per-user key via session state) ───────────────────────
    "JSearch":        lambda kw, prefs, is_remote, loc, keys: search_jsearch(
        kw, locations=loc, remote=is_remote, limit=30,
        api_key=keys.get("rapidapi_key") if keys else None),
    "Adzuna":         lambda kw, prefs, is_remote, loc, keys: search_adzuna(
        kw, locations=loc, limit=30,
        app_id=keys.get("adzuna_app_id") if keys else None,
        app_key=keys.get("adzuna_app_key") if keys else None),
    # ── India-specific scrapers ───────────────────────────────────────────────
    "Internshala":    lambda kw, prefs, is_remote, loc, keys: search_internshala(kw, limit=20),
    "AngelList":      lambda kw, prefs, is_remote, loc, keys: search_angellist(kw, limit=20),
    "Instahyre":      lambda kw, prefs, is_remote, loc, keys: search_instahyre(kw, limit=15),
    "Freshersworld":  lambda kw, prefs, is_remote, loc, keys: search_freshersworld(kw, limit=15),
    "Shine":          lambda kw, prefs, is_remote, loc, keys: search_shine(kw, locations=loc, limit=15),
}


def search_all_sources(
    preferences: dict,
    log_fn=None,
    enabled_sources: list = None,
    use_cache: bool = True,
    api_keys: dict = None,
) -> list:
    """
    Parallel job search across all selected sources.
    - api_keys: per-user key dict from st.session_state — never uses os.environ directly
    - Checks 24-hr cache first
    - Runs all sources concurrently via ThreadPoolExecutor
    - Fuzzy-deduplicates cross-source duplicates
    - Keyword pre-filters irrelevant listings
    """
    def log(msg: str):
        print(msg)
        if log_fn:
            log_fn(msg)

    active = list(enabled_sources) if enabled_sources else list(ALL_SOURCES)
    keywords = [k.strip() for k in preferences.get("keywords", "Python").split(",") if k.strip()]
    is_remote = preferences.get("remote_preference", "any").lower() in ("remote", "hybrid", "both")
    pref_locations = preferences.get("locations", "India")

    # ── Cache check ───────────────────────────────────────────────────────────
    if use_cache:
        try:
            from database.db_manager import get_cached_search, save_search_cache
            key = _cache_key(keywords, active, pref_locations)
            cached = get_cached_search(key, ttl_hours=24)
            if cached:
                log(f"⚡ **Cache hit!** Returning {len(cached)} jobs from last 24h")
                return cached
        except Exception:
            pass

    log(f"🔍 Searching for: **{', '.join(keywords)}**")
    log(f"📌 Sources: **{', '.join(active)}** — running in parallel...")

    all_jobs = []
    source_results = {}
    keys = api_keys or {}

    # ── Parallel scraping ─────────────────────────────────────────────────────
    with ThreadPoolExecutor(max_workers=min(len(active), 6)) as executor:
        future_to_source = {
            executor.submit(SOURCE_FN_MAP[src], keywords, preferences, is_remote, pref_locations, keys): src
            for src in active if src in SOURCE_FN_MAP
        }
        for future in as_completed(future_to_source):
            src = future_to_source[future]
            try:
                jobs = future.result(timeout=20)
                source_results[src] = len(jobs)
                all_jobs.extend(jobs)
                log(f"  ✅ **{src}**: {len(jobs)} jobs")
            except Exception as e:
                log(f"  ⚠️ **{src}** failed: {e}")
                source_results[src] = 0

    raw_count = len(all_jobs)
    log(f"\n📦 Raw total: **{raw_count} jobs** — deduplicating...")

    # ── URL deduplication ─────────────────────────────────────────────────────
    seen_urls = set()
    url_unique = []
    for job in all_jobs:
        url = job.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            url_unique.append(job)

    # ── Fuzzy deduplication across sources ────────────────────────────────────
    deduped = _fuzzy_deduplicate(url_unique)
    log(f"🔄 After dedup: **{len(deduped)} unique jobs**")

    # ── Keyword relevance filter ───────────────────────────────────────────────
    relevant = _keyword_filter(deduped, keywords)
    filtered = len(deduped) - len(relevant)
    if filtered > 0:
        log(f"🔎 Keyword filter: removed **{filtered}** irrelevant jobs")
    log(f"🎯 **{len(relevant)} relevant jobs** ready for AI scoring")

    # ── Save to cache ─────────────────────────────────────────────────────────
    if use_cache and relevant:
        try:
            save_search_cache(key, relevant)
        except Exception:
            pass

    return relevant
