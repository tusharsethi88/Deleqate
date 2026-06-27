import os, time, threading, sqlite3, json, datetime
from pathlib import Path
from openai import OpenAI

from django.conf import settings
from werkzeug.utils import secure_filename
from core.database import DB_PATH, log_status

MODEL = "nvidia/nemotron-3-ultra-550b-a55b"
BASE_DIR = Path(settings.BASE_DIR)
# The md files are in d:\Deleqate (which is BASE_DIR's parent)
SYSTEM_PROMPT_FILE = BASE_DIR.parent / "Equity_Research_System.md"
HTML_PROMPT_FILE = BASE_DIR.parent / "Equity_Research_HTML_Report_Prompt.md"
COMPANIES_CSV = BASE_DIR.parent / "new_companies.csv"


# Corporate suffixes / filler words stripped before matching company names.
_NAME_STOPWORDS = {
    'ltd', 'limited', 'pvt', 'private', 'inc', 'incorporated', 'corp', 'corp.',
    'corporation', 'co', 'company', 'plc', 'llp', 'group', 'holdings', 'holding',
}


def _norm_tokens(s):
    """Lowercase, drop punctuation (incl. truncating dots) and corporate
    suffixes, and return a list of significant tokens."""
    import re
    s = (s or '').lower().replace('&', ' and ')
    s = re.sub(r'[^a-z0-9 ]+', ' ', s)
    return [t for t in s.split() if t and t not in _NAME_STOPWORDS]


def _token_match(a, b):
    """True if two tokens match, tolerating Screener's truncated names
    (e.g. 'wealth' vs 'wea.', 'electromechanics' vs 'electromech')."""
    if a == b:
        return True
    return len(a) >= 3 and len(b) >= 3 and (a.startswith(b) or b.startswith(a))


def _name_score(qtoks, ctoks):
    import difflib
    if not qtoks or not ctoks:
        return 0.0
    matched, used = 0, set()
    for qt in qtoks:
        for i, ct in enumerate(ctoks):
            if i in used:
                continue
            if _token_match(qt, ct):
                matched += 1
                used.add(i)
                break
    coverage = matched / max(len(qtoks), len(ctoks))
    seq = difflib.SequenceMatcher(None, ' '.join(qtoks), ' '.join(ctoks)).ratio()
    return 0.7 * coverage + 0.3 * seq


def _lookup_company_url(stock_name):
    """Resolve the exact Screener.in URL for a company from new_companies.csv.

    Tries, in order: exact ticker match, exact normalized-name match, then a
    fuzzy token-based score that tolerates truncated names and corporate
    suffixes. Returns the full URL string, or None if no confident match is
    found (caller then falls back to Screener's search API).
    """
    import csv
    if not stock_name:
        return None
    ql = stock_name.strip().lower()
    try:
        with open(COMPANIES_CSV, newline='', encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
    except Exception as e:
        print(f"[LLM Worker] Could not read {COMPANIES_CSV}: {e}", flush=True)
        return None

    def url_of(row):
        u = (row.get('url') or '').strip()
        return u.rstrip('/') + '/' if u else u

    # 1) exact ticker match (ignore the 'id' placeholder used by /company/id/ URLs)
    for r in rows:
        tk = (r.get('ticker') or '').strip().lower()
        if tk and tk != 'id' and tk == ql:
            return url_of(r)

    # 2) exact normalized-name match
    qtoks = _norm_tokens(stock_name)
    if qtoks:
        for r in rows:
            if _norm_tokens(r.get('name')) == qtoks:
                return url_of(r)

    # 3) best fuzzy match above a confidence threshold
    best, best_score = None, 0.0
    for r in rows:
        sc = _name_score(qtoks, _norm_tokens(r.get('name')))
        if sc > best_score:
            best, best_score = r, sc
    if best and best_score >= 0.55:
        print(f"[LLM Worker] Fuzzy-matched '{stock_name}' to '{best.get('name')}' "
              f"(score {best_score:.2f})", flush=True)
        return url_of(best)
    return None


def _num(s):
    """Parse a Screener cell ('70,698', '27%', '₹2,580', '-96', '-') to float/None."""
    import re
    if s is None:
        return None
    t = str(s).replace(',', '').replace('₹', '').replace('%', '').strip()
    if t in ('', '-', '—', 'NA', 'N/A'):
        return None
    try:
        return float(t)
    except ValueError:
        m = re.search(r'-?\d+\.?\d*', t)
        return float(m.group()) if m else None


def _parse_financial_tables(soup):
    """Parse Screener financial sections into {section_id: {'periods':[...],
    'rows': {row_label: {period: raw_value}}}}. Defensive: returns {} on any
    problem so report generation never breaks."""
    out = {}
    try:
        for section in soup.find_all('section', id=True):
            sid = section.get('id')
            if sid.lower() == 'insights':   # premium-gated, masked values — skip
                continue
            table = section.find('table')
            if not table:
                continue
            periods = []
            thead = table.find('thead')
            if thead:
                periods = [th.get_text(strip=True) for th in thead.find_all('th')]
            cols = periods[1:] if periods else []
            rows = {}
            tbody = table.find('tbody')
            if tbody:
                for tr in tbody.find_all('tr'):
                    cells = tr.find_all(['td', 'th'])
                    if not cells:
                        continue
                    label = cells[0].get_text(strip=True).rstrip('+').strip()
                    if not label:
                        continue
                    vals = [c.get_text(strip=True) for c in cells[1:]]
                    rows[label] = {cols[i]: vals[i] for i in range(min(len(cols), len(vals)))}
            out[sid] = {'periods': cols, 'rows': rows}
    except Exception as e:
        print(f"[LLM Worker] Financial-table parse failed: {e}", flush=True)
    return out


def _screener_verified_metrics(tables, ratios):
    """Build a deterministic 'use only these' block: Screener-reported headline
    ratios verbatim, plus ratios COMPUTED in code from the financial tables for
    items Screener doesn't publish. Every value carries its period + source so
    the model never has to (and must not) compute or recall a number."""
    lines = []

    def latest(sec):
        return (tables.get(sec, {}).get('periods') or [None])[-1]

    def val(sec, label_prefix, period=None):
        rows = tables.get(sec, {}).get('rows', {})
        for k, v in rows.items():
            if k.lower().startswith(label_prefix.lower()):
                per = period or latest(sec)
                return _num(v.get(per)) if per else None
        return None

    def prev(sec, label_prefix):
        pers = tables.get(sec, {}).get('periods') or []
        if len(pers) < 2:
            return None
        return val(sec, label_prefix, pers[-2])

    pl, bs, cf, rt = 'profit-loss', 'balance-sheet', 'cash-flow', 'ratios'
    fy = latest(pl)

    # --- Screener-REPORTED headline ratios (verbatim) ---
    if ratios:
        lines.append("REPORTED BY SCREENER (use verbatim):")
        for k in ['Current Price', 'Market Cap', 'High / Low', 'Stock P/E', 'Book Value',
                  'Dividend Yield', 'ROCE', 'ROE', 'Face Value']:
            if k in ratios:
                lines.append(f"  {k} = {ratios[k]}")

    # --- COMPUTED from Screener financial tables (annual, latest FY) ---
    sales = val(pl, 'Sales'); npft = val(pl, 'Net Profit'); op = val(pl, 'Operating Profit')
    pbt = val(pl, 'Profit before tax'); interest = val(pl, 'Interest'); eps = val(pl, 'EPS')
    payout = val(pl, 'Dividend Payout')
    eq_cap = val(bs, 'Equity Capital'); reserves = val(bs, 'Reserves')
    assets = val(bs, 'Total Assets'); borrow = val(bs, 'Borrowings'); invest = val(bs, 'Investments')
    cfo = val(cf, 'Cash from Operating'); fcf = val(cf, 'Free Cash Flow')
    equity = (eq_cap or 0) + (reserves or 0) if (eq_cap or reserves) else None
    mcap = _num(ratios.get('Market Cap')) if ratios else None

    comp = []

    def add(name, v, unit=''):
        if v is not None:
            comp.append(f"  {name} = {v}{unit}  [computed from Screener {fy}]")

    if sales and npft:
        add('Net Profit Margin', round(npft / sales * 100, 1), '%')
    if sales and assets:
        add('Asset Turnover', round(sales / assets, 2), 'x')
    if assets and equity:
        add('Financial Leverage (Assets/Equity)', round(assets / equity, 2), 'x')
    if borrow is not None and equity:
        add('Debt / Equity', round(borrow / equity, 2), 'x')
    if pbt and interest:
        add('Interest Coverage (EBIT/Int)', round((pbt + interest) / interest, 0), 'x')
    if cfo and npft:
        add('CFO / PAT', round(cfo / npft * 100, 0), '%')
    if fcf is not None:
        add('Free Cash Flow', f"{fcf:,.0f}", ' Cr')
    if sales and prev(pl, 'Sales'):
        add('Sales YoY', round((sales / prev(pl, 'Sales') - 1) * 100, 1), '%')
    if npft and prev(pl, 'Net Profit'):
        add('Net Profit YoY', round((npft / prev(pl, 'Net Profit') - 1) * 100, 1), '%')
    if mcap and borrow is not None and invest is not None and op:
        ev = mcap + borrow - invest
        add('EV/EBITDA (approx, MktCap+Debt-Investments)/OpProfit', round(ev / op, 1), 'x')
    # Working-capital / receivables straight from ratios section
    for lbl in ['Debtor Days', 'Working Capital Days', 'Cash Conversion Cycle']:
        v = val(rt, lbl)
        if v is not None:
            comp.append(f"  {lbl} = {v}  [Screener ratios {latest(rt)}]")

    if comp:
        lines.append("\nCOMPUTED RATIOS (do NOT recompute — use these exact values):")
        lines.extend(comp)

    if not lines:
        return ""
    return ("\n--- VERIFIED NUMBERS — USE ONLY THESE FOR ALL FINANCIAL FIGURES "
            "(every value is from Screener or computed from Screener tables) ---\n"
            + "\n".join(lines))


def _concall_label_for(a):
    t = a.get_text(strip=True).lower()
    if 'transcript' in t:
        return 'TRANSCRIPT'
    if 'ppt' in t or 'presentation' in t or 'fact' in t:
        return 'INVESTOR PRESENTATION / FACT SHEET'
    if 'note' in t:
        return 'CONCALL NOTES'
    return None


def _is_text_doc(href):
    if not href:
        return False
    h = href.lower()
    if any(x in h for x in ('youtu', '#type=overlay', 'overlay', '/login')):
        return False
    return h.endswith('.pdf') or 'annpdfopen' in h or 'attachlive' in h \
        or 'attachhis' in h or '.pdf?' in h


def _latest_concall_docs(soup, transcript_only=False):
    """Return (date_label, [(label, href), ...]) for the most recent quarter's
    concall on a Screener company page. Picks the first row that has a real
    Transcript link; optionally returns the transcript only."""
    docs, concall_date = [], None
    cc_sec = soup.find(id='concalls') or soup.find('div', class_='concalls')
    if cc_sec:
        for li in cc_sec.find_all('li'):
            links = li.find_all('a')
            has_transcript = any('transcript' in a.get_text(strip=True).lower()
                                 and _is_text_doc(a.get('href')) for a in links)
            if not has_transcript:
                continue
            label_el = li.find('div')
            concall_date = label_el.get_text(strip=True) if label_el else ''
            for a in links:
                lbl = _concall_label_for(a)
                href = a.get('href')
                if lbl and _is_text_doc(href):
                    if transcript_only and lbl != 'TRANSCRIPT':
                        continue
                    docs.append((lbl, href))
            break
    # Fallback: generic documents scan if no concalls section.
    if not docs:
        dd = soup.find('div', class_='documents')
        if dd:
            for a in dd.find_all('a'):
                text = a.text.strip().lower()
                if ('transcript' in text or 'concall' in text or 'earnings call' in text) \
                        and _is_text_doc(a.get('href')):
                    docs.append(('TRANSCRIPT', a.get('href')))
                    break
    return concall_date, docs


def _download_doc_texts(docs, headers, concall_date, label_prefix='LATEST QUARTER',
                        max_pages=40, max_chars=60000):
    """Download each (label, url) PDF and return (context_parts, found_any).
    Validates the response is actually a PDF (BSE often returns an HTML error
    page when throttled), retries once, and silences pypdf parser warnings."""
    import io
    import time
    import logging
    import requests
    try:
        from pypdf import PdfReader
    except ImportError:
        from PyPDF2 import PdfReader
    logging.getLogger('pypdf').setLevel(logging.ERROR)   # hush "wrong pointing object" noise

    def _get_pdf(url):
        h = dict(headers)
        if 'bseindia.com' in url:
            h['Referer'] = 'https://www.bseindia.com/'
            h['Accept'] = 'application/pdf,*/*'
        for attempt in range(2):                          # one retry on throttle/HTML
            try:
                r = requests.get(url, headers=h, timeout=25)
            except Exception as e:
                print(f"[LLM Worker] fetch error ({url}): {e}", flush=True)
                time.sleep(1.5)
                continue
            if r.status_code == 200 and r.content[:1024].lstrip()[:4] == b'%PDF':
                return r.content
            if attempt == 0:
                time.sleep(1.5)                           # back off then retry once
        return None

    parts, found = [], False
    for lbl, doc_url in docs:
        if doc_url.startswith('/'):
            doc_url = "https://www.screener.in" + doc_url
        print(f"[LLM Worker] Downloading {lbl} ({label_prefix}"
              f"{f', {concall_date}' if concall_date else ''}) from {doc_url}...", flush=True)
        data = _get_pdf(doc_url)
        if not data:
            print(f"[LLM Worker] {lbl} skipped — source did not return a valid PDF "
                  f"(likely blocked/throttled by BSE).", flush=True)
            continue
        try:
            reader = PdfReader(io.BytesIO(data))
            text = ""
            for i in range(min(max_pages, len(reader.pages))):
                text += (reader.pages[i].extract_text() or "") + "\n"
            if len(text.strip()) > 100:
                hdr = f"\n--- {label_prefix} {lbl}"
                hdr += f" — {concall_date}" if concall_date else ""
                hdr += f" (source: {doc_url}) ---"
                if lbl == 'TRANSCRIPT':
                    hdr += "\n(Management commentary — use for forward guidance.)"
                parts.append(hdr)
                parts.append(text[:max_chars])
                found = True
        except Exception as e:
            print(f"[LLM Worker] {lbl} extraction failed: {e}", flush=True)
        time.sleep(2)   # 2s gap between BSE downloads to avoid throttling
    return parts, found


def _fetch_peers_context(soup, headers, session=None):
    """Pull the peer-comparison table (loaded by Screener via a separate API)
    and enrich each peer with its key ratios. Returns a context string, or ''
    if peers could not be resolved. `session` carries the cookies set by the
    company page, which the peers AJAX endpoint requires."""
    import re
    import requests
    from bs4 import BeautifulSoup
    http = session or requests   # use the cookie-bearing session if provided

    # The peers table is lazy-loaded. Find the correct Screener company id from
    # ANY /api/company/<id>/... reference in the page HTML (chart, peers, etc.
    # all share the same id), then build the peers endpoint. This is far more
    # reliable than data-company-id, which can hold an index/section id.
    import re as _re
    from collections import Counter
    html = str(soup)

    # The peers endpoint uses Screener's WAREHOUSE id (e.g. 6599230), which is
    # DIFFERENT from the company id used by chart/search (e.g. 3365). Collect all
    # plausible id candidates from the page — preferring an explicit peers URL,
    # then warehouse-id attributes/JSON, then company ids — and try each until
    # the peers endpoint returns 200.
    candidates = []

    def _add(x):
        if x and x not in candidates:
            candidates.append(x)

    # 1) explicit peers URL already in HTML (best)
    m = _re.search(r'/api/company/(\d+)/peers', html, _re.I)
    if m:
        _add(m.group(1))
    # 2) warehouse id (what peers actually uses)
    for pat in (r'data-warehouse-id="?(\d+)', r'warehouse[_-]?id["\'\s:=]+(\d+)',
                r'"warehouse"\s*:\s*\{[^}]*?"id"\s*:\s*(\d+)'):
        for x in _re.findall(pat, html, _re.I):
            _add(x)
    # 3) any other /api/company/<id>/ ids, most-frequent first (company id, etc.)
    freq = Counter(_re.findall(r'/api/company/(\d+)/', html))
    for x, _c in freq.most_common():
        _add(x)
    for x in _re.findall(r'data-company-id="?(\d+)', html):
        _add(x)
    # 4) last resort: standalone 7-8 digit numbers (warehouse ids look like
    #    6599230) ranked by frequency — covers ids embedded only in inline JS.
    for x, _c in Counter(_re.findall(r'\b(\d{7,8})\b', html)).most_common():
        _add(x)

    if not candidates:
        print("[LLM Worker] No company/warehouse id candidates found for peers", flush=True)
        return ""

    # AJAX/session headers — Screener's peers endpoint needs these + cookies.
    ajax_headers = dict(headers)
    ajax_headers.update({
        'X-Requested-With': 'XMLHttpRequest',
        'HX-Request': 'true',
        'Referer': "https://www.screener.in/",
        'Accept': 'text/html, */*; q=0.01',
    })
    try:
        csrf = http.cookies.get('csrftoken') if hasattr(http, 'cookies') else None
        if csrf:
            ajax_headers['X-CSRFToken'] = csrf
    except Exception:
        pass

    psoup = None
    for wid in candidates[:12]:
        url = f"https://www.screener.in/api/company/{wid}/peers/"
        try:
            r = http.get(url, headers=ajax_headers, timeout=10)
            if r.status_code == 200 and r.text.strip():
                print(f"[LLM Worker] Peers endpoint resolved: {url}", flush=True)
                psoup = BeautifulSoup(r.text, 'html.parser')
                break
        except Exception as e:
            print(f"[LLM Worker] Peers fetch error for id {wid}: {e}", flush=True)
    if psoup is None:
        print(f"[LLM Worker] Peers not found; tried ids {candidates[:12]}", flush=True)
        return ""

    table = psoup.find('table')
    if not table:
        return ""

    parts = ["\n--- PEER COMPARISON (live from Screener.in) ---"]
    thead = table.find('thead')
    if thead:
        parts.append(" | ".join(th.get_text(strip=True) for th in thead.find_all('th')))

    peer_links = []
    tbody = table.find('tbody')
    if tbody:
        for tr in tbody.find_all('tr'):
            cols = [td.get_text(strip=True) or '-' for td in tr.find_all(['td', 'th'])]
            if any(c not in ('-', '') for c in cols):
                parts.append(" | ".join(cols))
            a = tr.find('a', href=True)
            if a and a['href'].startswith('/company/'):
                peer_links.append((a.get_text(strip=True), a['href']))

    # Enrich up to 5 peers with their headline ratios (ROE/ROCE/OPM/P-E/etc.).
    # Peer URLs are taken ONLY from new_companies.csv (resolved by ticker, then
    # name) — never constructed from the ticker, since some tickers are numeric
    # codes whose URL is not /company/<ticker>/. Peers absent from the CSV are
    # skipped rather than guessed.
    for name, href in peer_links[:8]:
        # ticker is the path segment right after /company/
        segs = [s for s in href.split('/') if s]
        ticker = segs[segs.index('company') + 1] if 'company' in segs else ''
        peer_url = _lookup_company_url(ticker) or _lookup_company_url(name)
        if not peer_url:
            print(f"[LLM Worker] Peer '{name}' ({ticker}) not in CSV — skipping detail", flush=True)
            continue
        try:
            rr = http.get(peer_url, headers=headers, timeout=8)
            ps = BeautifulSoup(rr.text, 'html.parser')
            rd = ps.find('div', class_='company-ratios')
            if not rd:
                continue
            kv = []
            for li in rd.find_all('li'):
                nm = li.find('span', class_='name')
                vv = li.find('span', class_='value')
                if nm and vv:
                    kv.append(f"{nm.get_text(strip=True)}: {vv.get_text(' ', strip=True)}")
            if kv:
                parts.append(f"\nPEER DETAIL — {name} ({peer_url}): " + "; ".join(kv))

            # Pull the peer's latest-quarter concall transcript (compact) for
            # operational guidance. Transcript only, fewer pages/chars to keep
            # the overall prompt size in check across multiple peers.
            try:
                p_date, p_docs = _latest_concall_docs(ps, transcript_only=True)
                if p_docs:
                    p_parts, _ = _download_doc_texts(
                        p_docs, headers, p_date,
                        label_prefix=f"PEER {name} — LATEST QUARTER",
                        max_pages=20, max_chars=20000)
                    parts.extend(p_parts)
            except Exception as e:
                print(f"[LLM Worker] Peer concall fetch failed for {name}: {e}", flush=True)
        except Exception as e:
            print(f"[LLM Worker] Peer detail fetch failed for {name}: {e}", flush=True)
            continue

    print(f"[LLM Worker] Pulled peer comparison ({len(peer_links)} peers)", flush=True)
    return "\n".join(parts)


def fetch_live_context(stock_name):
    import time
    import requests
    from bs4 import BeautifulSoup
    
    print(f"[LLM Worker] Fetching live internet context for {stock_name}...", flush=True)
    context_parts = []
    ratios = {}   # scraped headline metrics, returned for deterministic substitution

    # 1. Scrape strict live data from Screener.in
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}

        # Prefer the exact URL from new_companies.csv; fall back to search API.
        full_url = _lookup_company_url(stock_name)
        if full_url:
            print(f"[LLM Worker] Matched '{stock_name}' to CSV URL {full_url}", flush=True)
        else:
            print(f"[LLM Worker] '{stock_name}' not in CSV; using Screener search API", flush=True)
            search_url = f"https://www.screener.in/api/company/search/?q={requests.utils.quote(stock_name)}"
            resp = requests.get(search_url, timeout=5)
            if resp.status_code == 200 and len(resp.json()) > 0:
                full_url = f"https://www.screener.in{resp.json()[0]['url']}"

        if full_url:
            # Use a Session so cookies set by the company page (needed by the
            # peers AJAX endpoint) carry into subsequent requests.
            session = requests.Session()
            session.headers.update(headers)
            page_resp = session.get(full_url, timeout=8)
            soup = BeautifulSoup(page_resp.text, 'html.parser')
            
            import re as _re
            ratios_div = soup.find('div', class_='company-ratios')
            if ratios_div:
                context_parts.append(f"--- EXACT LIVE METRICS FROM SCREENER.IN ({full_url}) ---")
                ratios = {}
                for li in ratios_div.find_all('li'):
                    name = li.find('span', class_='name')
                    value = li.find('span', class_='value')
                    if name and value:
                        nm = _re.sub(r'\s+', ' ', name.get_text(' ', strip=True)).strip()
                        val_str = _re.sub(r'\s+', ' ', value.get_text(' ', strip=True)).strip()
                        ratios[nm] = val_str
                        context_parts.append(f"{nm}: {val_str}")
                # Headline quote — the report MUST use these verbatim.
                if ratios:
                    key_order = ['Current Price', 'Market Cap', 'High / Low', 'Stock P/E',
                                 'Book Value', 'Dividend Yield', 'ROCE', 'ROE', 'Face Value']
                    headline = [f"{k} = ₹{ratios[k]}" if k in ('Current Price',) and not ratios[k].startswith('₹')
                                else f"{k} = {ratios[k]}"
                                for k in key_order if k in ratios]
                    if headline:
                        context_parts.append(
                            "\n*** AUTHORITATIVE HEADLINE NUMBERS (from Screener, as of the "
                            "scrape date) — COPY THESE VERBATIM; DO NOT use any figure from "
                            "memory and DO NOT invent an 'as of' month/date ***\n"
                            + " | ".join(headline))
            
            # Extract tables (Quarters, P&L, Balance Sheet, Cash Flows, etc.).
            # Skip the 'Insights' section — it is premium-gated and its values
            # are masked ('xx.xx' / 'Requires Premium'), so it adds only noise.
            for section in soup.find_all('section', id=True):
                if section.get('id', '').lower() == 'insights':
                    continue
                title = section.find('h2')
                table = section.find('table')
                if not title or not table:
                    continue
                if 'insight' in title.get_text(strip=True).lower():
                    continue

                context_parts.append(f"\n--- {title.text.strip()} ---")
                thead = table.find('thead')
                if thead:
                    headers_list = [th.text.strip() for th in thead.find_all('th')]
                    context_parts.append(" | ".join(headers_list))
                    
                tbody = table.find('tbody')
                if tbody:
                    for tr in tbody.find_all('tr'):
                        cols = [td.text.strip() for td in tr.find_all(['td', 'th'])]
                        cols = [c if c else "-" for c in cols]
                        context_parts.append(" | ".join(cols))
            
            # Company profile + KEY POINTS (segment / vertical / revenue breakup).
            about = soup.find('div', class_='company-profile') or soup.find('div', class_='company-info')
            if about:
                prof = _re.sub(r'\n{2,}', '\n', about.get_text('\n', strip=True))
                context_parts.append("\n--- COMPANY PROFILE & KEY POINTS (segments / verticals / "
                                     "revenue breakup, from Screener) ---\n" + prof[:8000])
            # Explicitly grab a 'Key Points' block if it sits outside the profile div.
            for hdr in soup.find_all(['h2', 'h3', 'p', 'div']):
                if hdr.get_text(strip=True).lower().startswith('key point'):
                    blk = hdr.find_parent() or hdr
                    txt = _re.sub(r'\n{2,}', '\n', blk.get_text('\n', strip=True))
                    if len(txt) > 30:
                        context_parts.append("\n--- KEY POINTS ---\n" + txt[:4000])
                    break

            # 1a. Deterministic verified-numbers block (reported + computed).
            try:
                _tables = _parse_financial_tables(soup)
                verified = _screener_verified_metrics(_tables, ratios)
                if verified:
                    context_parts.append(verified)
            except Exception as e:
                print(f"[LLM Worker] Verified-metrics step failed: {e}", flush=True)

            # 1b. Pull the live peer-comparison table + each peer's key ratios.
            try:
                peers_ctx = _fetch_peers_context(soup, headers, session)
                if peers_ctx:
                    context_parts.append(peers_ctx)
            except Exception as e:
                print(f"[LLM Worker] Peer comparison step failed: {e}", flush=True)

            # 2. Pull ALL text documents (transcript, investor PPT / fact sheet,
            # notes) for the LATEST quarter's concall of the main company.
            global found_concall
            found_concall = False
            concall_date, docs_to_fetch = _latest_concall_docs(soup)
            if docs_to_fetch:
                parts, found = _download_doc_texts(docs_to_fetch, headers, concall_date,
                                                   label_prefix='LATEST QUARTER')
                context_parts.extend(parts)
                found_concall = found
    except Exception as e:
        print(f"[LLM Worker] Screener direct scrape failed: {e}", flush=True)
        found_concall = False
        
    # 3. Fallback to Moneycontrol/NSE ONLY if Screener was missing data (e.g. no concall)
    if not found_concall:
        print(f"[LLM Worker] Screener concall missing, falling back to Moneycontrol/NSE...", flush=True)
        fallback_queries = [
            f"{stock_name} management concall transcript guidance site:moneycontrol.com",
            f"{stock_name} announcement guidance site:nseindia.com"
        ]
        
        try:
            try:
                from ddgs import DDGS              # current package name
            except ImportError:
                try:
                    from duckduckgo_search import DDGS   # legacy name (deprecated)
                except ImportError:
                    DDGS = None
            if DDGS is None:
                print("[LLM Worker] duckduckgo_search not installed — skipping web fallback", flush=True)
                raise RuntimeError("no-ddgs")
            with DDGS() as ddgs:
                for q in fallback_queries:
                    try:
                        results = list(ddgs.text(q, max_results=2))
                        if results:
                            context_parts.append(f"\n--- Fallback Search: '{q}' ---")
                            for r in results:
                                context_parts.append(f"Title: {r.get('title')}\nSnippet: {r.get('body')}\n")
                        time.sleep(1)
                    except Exception as inner_e:
                        print(f"[LLM Worker] DDGS query failed '{q}': {inner_e}", flush=True)
                        continue
        except Exception as e:
            print(f"[LLM Worker] DDGS initialization failed: {e}", flush=True)
        
    return "\n".join(context_parts), ratios


# Maps display labels in the generated HTML to Screener ratio keys + a value
# formatter, used by _enforce_live_numbers for deterministic substitution.
def _fmt_money(v):
    v = v.replace('₹', '').strip()
    return '₹' + v

def _fmt_pct(v):
    return v.replace('₹', '').replace(' ', '').strip().rstrip('%') + '%'

def _fmt_plain(v):
    return v.replace('₹', '').strip()

def _fmt_high_low(v):
    parts = [p.strip().replace('₹', '') for p in v.split('/')]
    return ' / '.join('₹' + p for p in parts if p)


def _enforce_live_numbers(html, ratios):
    """Deterministically overwrite headline figures in the generated HTML with
    the exact Screener values, so the model cannot substitute stale numbers.
    Each rule replaces only the FIRST value token that follows its label
    (the headline card), within a bounded window, leaving the rest untouched."""
    import re
    if not html or not ratios:
        return html

    # (label_regex, value_regex, screener_key, formatter)
    NUM = r'[\d][\d,]*(?:\.\d+)?'
    rules = [
        (r'(?:CMP|Current\s*Price)', rf'₹?\s*{NUM}', 'Current Price', _fmt_money),
        (r'Market\s*Cap', rf'₹?\s*{NUM}\s*Cr\.?', 'Market Cap',
         lambda v: '₹' + _fmt_plain(v).replace('Cr.', 'Cr').strip()),
        (r'(?:52\s*W(?:eek)?\s*)?High\s*/\s*Low', rf'₹?\s*{NUM}\s*/\s*₹?\s*{NUM}', 'High / Low', _fmt_high_low),
        (r'(?:Stock\s*)?P\s*/\s*E(?:\s*\(TTM\))?', rf'{NUM}\s*x?', 'Stock P/E', lambda v: _fmt_plain(v).rstrip('xX') + 'x'),
        (r'Book\s*Value', rf'₹?\s*{NUM}', 'Book Value', _fmt_money),
        (r'Div(?:idend)?\.?\s*Yield', rf'{NUM}\s*%?', 'Dividend Yield', _fmt_pct),
    ]

    def sub_first(pattern_label, pattern_value, new_value):
        nonlocal html
        # capture: (label + any chars up to 160, before the value)(value)
        rx = re.compile(rf'({pattern_label}.{{0,160}}?)({pattern_value})', re.I | re.S)
        m = rx.search(html)
        if m:
            html = html[:m.start(2)] + new_value + html[m.end(2):]
            return True
        return False

    for lbl, valrx, key, fmt in rules:
        if key in ratios and ratios[key].strip():
            try:
                sub_first(lbl, valrx, fmt(ratios[key]))
            except Exception as e:
                print(f"[LLM Worker] substitution for {key} failed: {e}", flush=True)

    # ROE / ROCE — handle a combined "ROE / ROCE" cell and separate cells.
    roe = _fmt_pct(ratios['ROE']) if ratios.get('ROE') else None
    roce = _fmt_pct(ratios['ROCE']) if ratios.get('ROCE') else None
    if roe and roce:
        combo = re.compile(r'(ROE\s*/\s*ROCE.{0,160}?)(\d[\d.]*\s*%\s*/\s*\d[\d.]*\s*%)', re.I | re.S)
        m = combo.search(html)
        if m:
            html = html[:m.start(2)] + f"{roe} / {roce}" + html[m.end(2):]
    # Also enforce standalone ROE and ROCE labels (first occurrence each).
    for lbl, val in (('ROCE', roce), ('ROE', roe)):
        if not val:
            continue
        rx = re.compile(rf'(\b{lbl}\b(?!\s*/).{{0,120}}?)(\d[\d.]*\s*%)', re.I | re.S)
        m = rx.search(html)
        if m:
            html = html[:m.start(2)] + val + html[m.end(2):]

    print("[LLM Worker] Applied deterministic live-number substitution", flush=True)
    return html


_LAYOUT_FIX_CSS = """
<style id="deleqate-layout-fix">
  /* Deterministic layout fix. The model sometimes wraps the report in CSS
     multi-column layout, which fractures paragraphs into interleaved words and
     stretches the metric cards into tall narrow blocks. Force single-column
     flow and restore the intended grids. */
  html, body, body * {
    column-count: 1 !important; column-width: auto !important;
    columns: auto !important; -webkit-columns: auto !important; -moz-columns: auto !important;
  }
  .mgrid { display: grid !important;
           grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)) !important;
           gap: 10px !important; }
  .grid2 { display: grid !important; grid-template-columns: 1fr 1fr !important; gap: 12px !important; }
  table { width: 100% !important; table-layout: auto !important; }
</style>
"""


def _fix_report_layout(html):
    """Append the layout-fix stylesheet so it wins the cascade (inserted last,
    uses !important). Handles missing </body> defensively."""
    if not html:
        return html
    if '</body>' in html:
        return html.replace('</body>', _LAYOUT_FIX_CSS + '\n</body>', 1)
    return html + _LAYOUT_FIX_CSS


def _generate_report(stock_name, research_focus, report_type):
    api_key = os.environ.get("NVIDIA_API_KEY", "").strip()
    if not api_key:
        print("[LLM Worker] WARNING: NVIDIA_API_KEY is not set or empty! API call will likely fail.", flush=True)

    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key or "invalid_key", # Pass a dummy key if empty to prevent OpenAI SDK crash
        timeout=300.0,
    )
    
    # Use Equity_Research_HTML_Report_Prompt.md as the system instruction
    try:
        sys_prompt = HTML_PROMPT_FILE.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Error reading prompt file: {e}")
        sys_prompt = "You are an equity research analyst. Generate a complete HTML report based on the 6 pillar framework."
    
    # We also need the Equity_Research_System.md framework as context.
    try:
        framework = SYSTEM_PROMPT_FILE.read_text(encoding="utf-8")
        sys_prompt = framework + "\n\n" + sys_prompt
    except Exception as e:
        print(f"Error reading framework file: {e}")
        pass
        
    user_request = f"Report Type: {report_type}\nFocus on: {stock_name}"
    if research_focus:
        user_request += f"\nExtra focus: {research_focus}"
        
    live_context, live_ratios = fetch_live_context(stock_name)
    if live_context:
        user_request += f"\n\nLIVE INTERNET DATA CONTEXT (Use this to provide up-to-date figures and news):\n{live_context}"
        user_request += (
            "\n\nABSOLUTE RULE — NO MODEL-GENERATED NUMBERS. Every numeric value in EVERY "
            "pillar of the report (prices, ratios, growth rates, margins, DuPont components, "
            "cash-flow figures, working-capital days, EV/EBITDA, EPS, headcount, TCV, client "
            "counts, etc.) MUST come verbatim from the data blocks above: 'VERIFIED NUMBERS', "
            "'EXACT LIVE METRICS FROM SCREENER.IN', the financial tables, the PEER COMPARISON "
            "block, or the extracted concall transcript text. You must NOT compute, estimate, "
            "round differently, or recall ANY number from your own training knowledge. "
            "In particular: use the 'COMPUTED RATIOS' values as-is (do not recompute DuPont, "
            "margins, leverage, turnover, coverage). Do NOT invent an 'as of' date, an NSE/BSE "
            "rank, a sector average, or a '% from high' unless that exact value is in the data. "
            "Source priority is Screener first, then the Moneycontrol/NSE fallback snippets "
            "above if present. If a required number is NOT present in ANY provided block, OMIT "
            "that metric entirely — drop the row/cell/line from the report. Do NOT print a "
            "placeholder ('N/A', '[DATA NEEDED]', '—', 'TBD'), do NOT leave an empty cell, and "
            "NEVER fill the gap with a plausible-looking figure. A shorter report with only "
            "sourced numbers is required; an unsourced number is a failure."
        )
        user_request += (
            "\n\nSTRUCTURE — DO NOT CHANGE THE TEMPLATE. Produce the COMPLETE self-contained "
            "HTML report exactly per the template and styling in the system prompt, including "
            "ALL sections and ALL hand-built inline-SVG charts (Sales/Net-profit, EPS quarters, "
            "margin, ROE/DuPont, valuation, peer comparison, bear/base/bull). Build every chart "
            "whose data IS available in the provided blocks (quarterly results, P&L, ratios, peer "
            "table). The OMIT rule above applies ONLY to individual unsourced data values — it "
            "must NOT be used to drop charts, sections, or the overall report structure."
        )
        user_request += (
            "\n\nIMPORTANT — PEER COMPARISON: Use the 'PEER COMPARISON (live from Screener.in)' "
            "table and the 'PEER DETAIL' lines above to populate peer columns "
            "(market cap, P/E, ROE, ROCE, OPM, sales/profit growth, etc.). Use the PEER DETAIL "
            "lines and peer transcript blocks for each peer. Do NOT write '[DATA NEEDED]'. "
            "If a particular peer metric is not in the provided data, OMIT that row/column for "
            "that peer rather than printing a placeholder — never invent peer figures."
        )
        
    print(f"[LLM Worker] Sending prompt to NVIDIA API (Model: {MODEL})...", flush=True)
    print(f"[LLM Worker] (Generating the 6-pillar HTML report with {MODEL}. This may take 1-3 minutes. Please wait...)", flush=True)
    
    try:
        response_stream = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_request},
            ],
            temperature=0.6,        # lower temp → more faithful to sourced numbers
            top_p=0.9,
            max_tokens=32768,       # Llama 3.3 70B has a 128K context; allow a large completion
            stream=True,
        )
        
        print("[LLM Worker] Model response stream started: ", end="", flush=True)
        content_chunks = []
        for chunk in response_stream:
            if chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta.content
                if delta:
                    print(delta, end="", flush=True)
                    content_chunks.append(delta)
        
        print("\n[LLM Worker] Finished streaming response.", flush=True)
        content = "".join(content_chunks)
    except Exception as e:
        print(f"\n[LLM Worker] API Call Error: {e}", flush=True)
        raise e
        
    print(f"[LLM Worker] Received full response from NVIDIA API ({len(content)} characters)", flush=True)
    # Try to extract HTML if wrapped in markdown
    if "```html" in content:
        content = content.split("```html")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].strip()

    # Deterministic pass: force headline numbers to the exact Screener values.
    try:
        content = _enforce_live_numbers(content, live_ratios)
    except Exception as e:
        print(f"[LLM Worker] live-number enforcement skipped: {e}", flush=True)
    # Deterministic pass: fix multi-column/grid layout distortion.
    try:
        content = _fix_report_layout(content)
    except Exception as e:
        print(f"[LLM Worker] layout fix skipped: {e}", flush=True)
    return content

def _llm_worker_thread():
    while True:
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            conn.row_factory = sqlite3.Row

            # Release STALE claims: if a generation crashed/hung, its order stays
            # claimed + in_progress and would block the single-concurrency queue
            # forever. A report takes 1-3 min, so anything claimed >15 min ago is
            # presumed dead — release it so it retries and the queue moves on.
            conn.execute(
                "UPDATE orders SET assigned_pilot_id=NULL WHERE task='equity_research' "
                "AND status='in_progress' AND assigned_pilot_id IS NOT NULL "
                "AND assigned_at < datetime('now','-15 minutes')")
            conn.commit()

            # Find the OLDEST unclaimed in_progress equity research order (FIFO
            # queue). assigned_pilot_id IS NULL means no worker has claimed it.
            order = conn.execute(
                "SELECT id, intake_data, client_id FROM orders WHERE task='equity_research' "
                "AND status='in_progress' AND assigned_pilot_id IS NULL "
                "AND id NOT IN (SELECT order_id FROM deliverables) ORDER BY id ASC LIMIT 1"
            ).fetchone()

            if order:
                order_id = order['id']

                # Resolve the AI pilot id (used for both the claim and the deliverable).
                ap_email = os.environ.get('AUTOPILOT_EMAIL', 'deleqate@gmail.com')
                pilot = conn.execute("SELECT id FROM users WHERE email=? AND role='pilot'", (ap_email,)).fetchone()
                pilot_id = pilot['id'] if pilot else 1  # Fallback to 1 if no pilot found

                # ATOMIC CLAIM with GLOBAL SINGLE-CONCURRENCY: claim this order
                # only if (a) it's still unclaimed AND (b) no other equity-research
                # order is currently generating (status='in_progress' AND already
                # claimed). SQLite serializes writes, so only one worker — across
                # all gunicorn processes — can ever be generating at a time; the
                # rest stay queued (unclaimed, in_progress) for later loops.
                claim = conn.execute(
                    "UPDATE orders SET assigned_pilot_id=?, assigned_at=CURRENT_TIMESTAMP "
                    "WHERE id=? AND status='in_progress' AND assigned_pilot_id IS NULL "
                    "AND NOT EXISTS (SELECT 1 FROM orders WHERE task='equity_research' "
                    "                AND status='in_progress' AND assigned_pilot_id IS NOT NULL)",
                    (pilot_id, order_id))
                conn.commit()
                if claim.rowcount != 1:
                    conn.close()
                    time.sleep(5)
                    continue  # another report is generating, or order already taken — wait

                intake = json.loads(order['intake_data'] or "{}")
                stock_name = intake.get("stock_name", "")
                research_focus = intake.get("research_focus", "")
                report_type = intake.get("report_type", "Single-Stock Deep-Dive")

                print(f"[LLM Worker] Claimed Order #{order_id} for '{stock_name}'", flush=True)

                try:
                    html_content = _generate_report(stock_name, research_focus, report_type)

                    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                    safe_stock = secure_filename(stock_name.replace(' ', '_'))
                    filename = f"order_{order_id}_{safe_stock}_{timestamp}.pdf"
                    filepath = os.path.join(settings.DELIVERABLES_FOLDER, filename)

                    from playwright.sync_api import sync_playwright
                    print(f"[LLM Worker] Rendering HTML to PDF...", flush=True)
                    with sync_playwright() as p:
                        browser = p.chromium.launch()
                        page = browser.new_page()
                        page.set_content(html_content)
                        page.pdf(path=filepath, format="A4", print_background=True)
                        browser.close()

                    conn.execute(
                        "INSERT INTO deliverables (order_id, pilot_id, filename, original_name) VALUES (?,?,?,?)",
                        (order_id, pilot_id, filename, f"{stock_name} Research Report.pdf")
                    )

                    # Update status to delivered
                    conn.execute("UPDATE orders SET status='delivered', completed_at=? WHERE id=?",
                                 (datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'), order_id))

                    log_status(conn, order_id, 'in_progress', 'delivered', None, "AI Pilot completed equity research report")
                    print(f"[LLM Worker] Order #{order_id} successfully marked as delivered!", flush=True)
                except Exception as e:
                    print(f"[LLM Worker] Error generating report for order {order_id}: {e}", flush=True)
                    # Release the claim so it retries on a later loop.
                    conn.execute("UPDATE orders SET assigned_pilot_id=NULL WHERE id=?", (order_id,))

                conn.commit()
            conn.close()
        except Exception as e:
            print(f"[LLM Worker] loop error: {e}", flush=True)
            
        time.sleep(10)

_llm_thread = None
def start_llm_worker():
    global _llm_thread
    if _llm_thread is None or not _llm_thread.is_alive():
        _llm_thread = threading.Thread(target=_llm_worker_thread, daemon=True, name='llm-research')
        _llm_thread.start()
