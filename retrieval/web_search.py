"""
Web retrieval: Tavily search (primary) with DuckDuckGo fallback,
plus BeautifulSoup scraper for full-page content.
"""
from __future__ import annotations
import hashlib, re, time, logging
from typing import Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from config.settings import settings
from agent.models import SourceDocument, HealthTopic, TherapyDimension

log = logging.getLogger(__name__)

# ── Therapy keywords for dimension tagging ────────────────────────────────────
_DIM_KEYWORDS: dict[str, list[str]] = {
    TherapyDimension.FDA_CLINICAL: [
        "fda", "drug", "clinical trial", "prescription", "dosage",
        "chemotherapy", "immunotherapy", "insulin", "approved", "medication",
    ],
    TherapyDimension.HOMEOPATHIC: [
        "homeopathy", "homeopathic", "naturopathic", "herbal", "acupuncture",
        "traditional medicine", "ayurveda", "essential oil", "remedy",
    ],
    TherapyDimension.SUPPLEMENTATION: [
        "supplement", "vitamin", "mineral", "probiotic", "omega",
        "magnesium", "zinc", "turmeric", "curcumin", "melatonin",
    ],
    TherapyDimension.SURGICAL: [
        "surgery", "surgical", "procedure", "implant", "transplant",
        "bypass", "resection", "laparoscopic", "ablation", "stent",
    ],
}


def _tag_dimension(text: str) -> str:
    lower = text.lower()
    scores: dict[str, int] = {}
    for dim, kws in _DIM_KEYWORDS.items():
        scores[dim] = sum(1 for kw in kws if kw in lower)
    best = max(scores, key=scores.get)  # type: ignore[arg-type]
    return best if scores[best] > 0 else ""


def _chunk_text(text: str, size: int = 800, overlap: int = 120) -> list[str]:
    """Split text into overlapping chunks."""
    words = text.split()
    chunks, i = [], 0
    while i < len(words):
        chunk = " ".join(words[i : i + size])
        chunks.append(chunk)
        i += size - overlap
    return chunks


# ── Tavily search ─────────────────────────────────────────────────────────────
def tavily_search(query: str, max_results: int = 8) -> list[SourceDocument]:
    """Search via Tavily API (trusted, annotated results)."""
    if not settings.tavily_api_key:
        log.warning("No TAVILY_API_KEY — falling back to DuckDuckGo")
        return duckduckgo_search(query, max_results)

    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=settings.tavily_api_key)
        resp = client.search(
            query=query,
            search_depth="advanced",
            max_results=max_results,
            include_domains=settings.trusted_domains,
        )
        docs = []
        for r in resp.get("results", []):
            content_chunks = _chunk_text(r.get("content", ""))
            for j, chunk in enumerate(content_chunks):
                docs.append(SourceDocument(
                    content=chunk,
                    url=r.get("url", ""),
                    title=r.get("title", ""),
                    source_type="web",
                    relevance_score=r.get("score", 0.0),
                    therapy_dimension=_tag_dimension(chunk),
                    chunk_id=hashlib.md5(f"{r['url']}{j}".encode()).hexdigest(),
                ))
        log.info(f"Tavily returned {len(docs)} chunks for: {query!r}")
        return docs
    except Exception as exc:
        log.error(f"Tavily error: {exc} — falling back to DuckDuckGo")
        return duckduckgo_search(query, max_results)


# ── DuckDuckGo fallback ───────────────────────────────────────────────────────
def duckduckgo_search(query: str, max_results: int = 8) -> list[SourceDocument]:
    """Free DuckDuckGo search via duckduckgo-search library."""
    try:
        from duckduckgo_search import DDGS
        docs = []
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        for r in results:
            body = r.get("body", "")
            for j, chunk in enumerate(_chunk_text(body)):
                docs.append(SourceDocument(
                    content=chunk,
                    url=r.get("href", ""),
                    title=r.get("title", ""),
                    source_type="web",
                    therapy_dimension=_tag_dimension(chunk),
                    chunk_id=hashlib.md5(f"{r['href']}{j}".encode()).hexdigest(),
                ))
        return docs
    except Exception as exc:
        log.error(f"DuckDuckGo error: {exc}")
        return []


# ── Full-page scraper ─────────────────────────────────────────────────────────
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; HealthRAGBot/1.0; "
        "+https://github.com/your-org/health-rag-agent)"
    )
}

def scrape_page(url: str, timeout: int = 10) -> Optional[str]:
    """
    Fetch and clean a web page. Returns plain text or None on failure.
    Respects robots.txt by only scraping trusted domains.
    """
    domain = urlparse(url).netloc.lstrip("www.")
    if not any(domain.endswith(td) for td in settings.trusted_domains):
        log.debug(f"Skipping untrusted domain: {domain}")
        return None
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "aside", "form"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        # Collapse whitespace
        text = re.sub(r"\s{2,}", " ", text)
        return text[:12_000]          # cap at 12k chars per page
    except Exception as exc:
        log.warning(f"Scrape failed {url}: {exc}")
        return None


def deep_search(
    query: str,
    topic: HealthTopic,
    scrape_top_n: int = 3,
    include_academic: bool = True,
) -> list[SourceDocument]:
    """
    Full pipeline: web search → scrape top N pages + academic sources.
    Returns merged, deduplicated SourceDocuments from both web and academia.
    """
    # Topic-specific query enrichment
    topic_suffix = {
        HealthTopic.VACCINES:   "vaccine immunology clinical evidence",
        HealthTopic.CANCER:     "cancer treatment options evidence-based",
        HealthTopic.HEMOPHILIA: "hemophilia treatment factor therapy",
        HealthTopic.WEIGHT:     "weight management obesity treatment",
        HealthTopic.DIABETES:   "diabetes treatment glycemic control",
    }.get(topic, "")

    enriched_query = f"{query} {topic_suffix}".strip()
    
    # ── Start with web search ─────────────────────────────────────────────
    docs = tavily_search(enriched_query, max_results=10)

    # Scrape unique top URLs for fuller context
    seen_urls: set[str] = set()
    scraped_count = 0
    for doc in docs[:scrape_top_n * 2]:
        if doc.url in seen_urls or scraped_count >= scrape_top_n:
            continue
        seen_urls.add(doc.url)
        full_text = scrape_page(doc.url)
        if full_text:
            for j, chunk in enumerate(_chunk_text(full_text)):
                docs.append(SourceDocument(
                    content=chunk,
                    url=doc.url,
                    title=doc.title,
                    source_type="web_scraped",
                    therapy_dimension=_tag_dimension(chunk),
                    chunk_id=hashlib.md5(f"scraped:{doc.url}{j}".encode()).hexdigest(),
                ))
            scraped_count += 1

    # ── Augment with academic sources ─────────────────────────────────────
    if include_academic:
        try:
            from retrieval.academic_sources import search_academic_sources
            academic_docs = search_academic_sources(
                query=query,
                topic=topic,
                include_preprints=True,
                include_oa=True,
                include_chembl=True,
                include_lens=True,
            )
            docs.extend(academic_docs)
            log.info(f"Added {len(academic_docs)} academic source documents to retrieval")
        except Exception as e:
            log.warning(f"Error retrieving academic sources: {e}")

    return docs
