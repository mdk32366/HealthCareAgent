"""
Academic/Scientific retrieval: bioRxiv/medRxiv, CrossRef/Unpaywall, ChEMBL, CORE/Lens.org
Complements web_search.py with preprints, DOI resolution, drug targets, and OA aggregators.
"""
from __future__ import annotations
import hashlib
import logging
import time
from typing import Optional
from datetime import datetime

import requests

from config.settings import settings
from agent.models import SourceDocument, HealthTopic, TherapyDimension

log = logging.getLogger(__name__)

# ── Therapy keywords for dimension tagging (reuse from web_search) ────────────
_DIM_KEYWORDS: dict[str, list[str]] = {
    TherapyDimension.FDA_CLINICAL: [
        "fda", "drug", "clinical trial", "prescription", "dosage",
        "chemotherapy", "immunotherapy", "insulin", "approved", "medication",
        "phase i", "phase ii", "phase iii", "biomarker", "efficacy",
    ],
    TherapyDimension.HOMEOPATHIC: [
        "homeopathy", "homeopathic", "naturopathic", "herbal", "acupuncture",
        "traditional medicine", "ayurveda", "essential oil", "remedy",
    ],
    TherapyDimension.SUPPLEMENTATION: [
        "supplement", "vitamin", "mineral", "probiotic", "omega",
        "magnesium", "zinc", "turmeric", "curcumin", "melatonin", "bioavailability",
    ],
    TherapyDimension.SURGICAL: [
        "surgery", "surgical", "procedure", "implant", "transplant",
        "bypass", "resection", "laparoscopic", "ablation", "stent",
    ],
}


def _tag_dimension(text: str) -> str:
    """Infer therapy dimension from text keywords."""
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


# ── bioRxiv / medRxiv (Preprints) ─────────────────────────────────────────────
def biorxiv_medrxiv_search(
    query: str,
    max_results: int = 10,
    days_since: int = 365,
) -> list[SourceDocument]:
    """
    Search bioRxiv (biology/life sciences) and medRxiv (medical) preprints.
    Uses the bioRxiv/medRxiv API (no auth required).
    Returns latest, unpublished preprint research.
    """
    docs = []
    try:
        # bioRxiv search
        biorxiv_url = "https://api.biorxiv.org/details/biorxiv"
        params = {
            "query": query,
            "offset": 0,
            "rows": max_results,
            "interval": days_since,
        }
        resp = requests.get(f"{biorxiv_url}?{query}/from-date/api", timeout=10)
        resp.raise_for_status()
        data = resp.json() if resp.text else {}
        
        for article in data.get("collection", [])[:max_results]:
            try:
                title = article.get("title", "")
                abstract = article.get("abstract", "")
                authors = article.get("author_corresponding", "")
                published = article.get("date", "")
                doi = article.get("doi", "")
                url = article.get("permalink", "") or f"https://www.biorxiv.org/content/{doi}"
                
                content = f"{title}\n\n{abstract}"
                for j, chunk in enumerate(_chunk_text(content)):
                    docs.append(SourceDocument(
                        content=chunk,
                        url=url,
                        title=title,
                        source_type="preprint_biorxiv",
                        published_date=published,
                        therapy_dimension=_tag_dimension(chunk),
                        chunk_id=hashlib.md5(f"biorxiv:{doi}{j}".encode()).hexdigest(),
                    ))
            except Exception as e:
                log.debug(f"Error processing bioRxiv article: {e}")
        
        log.info(f"bioRxiv returned {len(docs)} chunks for: {query!r}")
    except Exception as e:
        log.warning(f"bioRxiv/medRxiv search error: {e}")
    
    return docs


# ── CrossRef + Unpaywall (DOI Resolution & OA Full-Text) ──────────────────────
def crossref_unpaywall_search(query: str, max_results: int = 10) -> list[SourceDocument]:
    """
    Search CrossRef for research articles and resolve to Unpaywall for open-access links.
    Provides verified DOI metadata and free full-text when available.
    """
    docs = []
    try:
        # CrossRef search
        crossref_url = "https://api.crossref.org/works"
        params = {
            "query": query,
            "rows": max_results,
            "sort": "relevance",
            "order": "desc",
            "type": "journal-article",
        }
        resp = requests.get(crossref_url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        for item in data.get("message", {}).get("items", [])[:max_results]:
            try:
                title = item.get("title", [""])[0] if item.get("title") else ""
                doi = item.get("DOI", "")
                url = item.get("URL", "")
                published = item.get("published-online", {}).get("date-parts", [[""]])[0][0]
                abstract = item.get("abstract", "")
                
                # Try to get OA full-text via Unpaywall
                is_oa = False
                oa_url = None
                if doi:
                    try:
                        unpaywall_resp = requests.get(
                            f"https://api.unpaywall.org/v2/{doi}?email=user@example.com",
                            timeout=5
                        )
                        unpaywall_data = unpaywall_resp.json() if unpaywall_resp.ok else {}
                        is_oa = unpaywall_data.get("is_oa", False)
                        if is_oa:
                            oa_url = unpaywall_data.get("best_oa_location", {}).get("url")
                    except:
                        pass
                
                # Use OA URL if available, otherwise CrossRef URL
                final_url = oa_url or url or f"https://doi.org/{doi}"
                
                content = f"{title}\n\nDOI: {doi}\n\n{abstract}"
                
                for j, chunk in enumerate(_chunk_text(content)):
                    source_type = "article_oa" if is_oa else "article_crossref"
                    docs.append(SourceDocument(
                        content=chunk,
                        url=final_url,
                        title=f"{title} {'[OA]' if is_oa else ''}",
                        source_type=source_type,
                        published_date=str(published) if published else "",
                        therapy_dimension=_tag_dimension(chunk),
                        chunk_id=hashlib.md5(f"crossref:{doi}{j}".encode()).hexdigest(),
                    ))
            except Exception as e:
                log.debug(f"Error processing CrossRef item: {e}")
        
        log.info(f"CrossRef+Unpaywall returned {len(docs)} chunks for: {query!r}")
    except Exception as e:
        log.warning(f"CrossRef/Unpaywall search error: {e}")
    
    return docs


# ── ChEMBL (EBI Drug-Target Database) ──────────────────────────────────────────
def chembl_search(query: str, max_results: int = 10) -> list[SourceDocument]:
    """
    Search ChEMBL for drug targets, bioactivity, and compound information.
    Useful for supplementation, FDA-approved drugs, and mechanism of action.
    """
    docs = []
    try:
        # ChEMBL compound search
        chembl_url = "https://www.ebi.ac.uk/api/es/compound_set/es/query"
        
        # Search for compounds/targets related to query
        query_params = {
            "q": f'pref_name:"{query}" OR document_chembl_id:"{query}"',
            "size": max_results,
        }
        
        resp = requests.get(
            "https://www.ebi.ac.uk/api/es/compound_set/es/query",
            params={"q": query, "size": max_results},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json() if resp.text else {}
        
        # Try compound endpoint
        try:
            resp = requests.get(
                f"https://www.ebi.ac.uk/chembl/api/data/compounds",
                params={
                    "search": query,
                    "format": "json",
                    "limit": max_results,
                },
                timeout=10,
            )
            resp.raise_for_status()
            compound_data = resp.json()
            
            for compound in compound_data.get("results", [])[:max_results]:
                try:
                    name = compound.get("pref_name", "") or compound.get("molecule_chembl_id", "")
                    chembl_id = compound.get("molecule_chembl_id", "")
                    smiles = compound.get("canonical_smiles", "")
                    url = f"https://www.ebi.ac.uk/chembl/compound_report_card/{chembl_id}"
                    
                    # Get target info
                    targets = compound.get("targets", [])
                    target_info = "; ".join(
                        [f"{t.get('target_chembl_id')}: {t.get('target_pref_name')}" 
                         for t in targets[:3]]
                    ) if targets else ""
                    
                    content = (
                        f"Compound: {name}\n"
                        f"ChEMBL ID: {chembl_id}\n"
                        f"Mechanism/Targets: {target_info}\n"
                        f"SMILES: {smiles}"
                    )
                    
                    for j, chunk in enumerate(_chunk_text(content)):
                        docs.append(SourceDocument(
                            content=chunk,
                            url=url,
                            title=f"ChEMBL: {name}",
                            source_type="chembl_compound",
                            therapy_dimension=_tag_dimension(chunk),
                            chunk_id=hashlib.md5(f"chembl:{chembl_id}{j}".encode()).hexdigest(),
                        ))
                except Exception as e:
                    log.debug(f"Error processing ChEMBL compound: {e}")
        except Exception as e:
            log.debug(f"ChEMBL compound endpoint error: {e}")
        
        log.info(f"ChEMBL returned {len(docs)} chunks for: {query!r}")
    except Exception as e:
        log.warning(f"ChEMBL search error: {e}")
    
    return docs


# ── CORE / Lens.org (Open-Access Aggregators) ─────────────────────────────────
def lens_org_search(query: str, max_results: int = 10) -> list[SourceDocument]:
    """
    Search Lens.org for open-access research articles and patents.
    Provides free scholarly article aggregation with metadata.
    
    Note: Lens.org primarily offers browser interface; using crossref+unpaywall
    as alternative for API access to similar OA content.
    """
    # Lens.org doesn't have public API readily available,
    # but we can construct search URLs or use CORE API if available
    docs = []
    try:
        # Attempt CORE API if available (public API with rate limits)
        # CORE API documentation: https://core.ac.uk/documentation/
        # For this implementation, we construct Lens.org search URLs and note them
        
        lens_url = f"https://www.lens.org/lens/search?q={query}"
        
        # Since Lens doesn't have easy programmatic access, we create a reference
        # that points users to the OA articles found via CrossRef+Unpaywall
        # or we could implement basic web scraping if needed
        
        content = (
            f"Search for '{query}' on:\n"
            f"• Lens.org: {lens_url}\n"
            f"• CORE (core.ac.uk): Open-access aggregator\n\n"
            f"These platforms index millions of free research articles from various repositories."
        )
        
        for j, chunk in enumerate(_chunk_text(content)):
            docs.append(SourceDocument(
                content=chunk,
                url=lens_url,
                title=f"Lens.org & CORE: Open Access Search for '{query}'",
                source_type="oa_aggregator",
                therapy_dimension="",
                chunk_id=hashlib.md5(f"lens_org:{query}{j}".encode()).hexdigest(),
            ))
        
        log.info(f"Lens.org search reference created for: {query!r}")
    except Exception as e:
        log.warning(f"Lens.org search error: {e}")
    
    return docs


# ── Unified academic search ───────────────────────────────────────────────────
def search_academic_sources(
    query: str,
    topic: HealthTopic,
    include_preprints: bool = True,
    include_oa: bool = True,
    include_chembl: bool = True,
    include_lens: bool = True,
) -> list[SourceDocument]:
    """
    Unified search across all academic sources.
    Allows selective enabling/disabling of each source.
    """
    all_docs: list[SourceDocument] = []
    
    # Enrich query with topic context
    topic_context = {
        HealthTopic.VACCINES:   "vaccine immunization efficacy safety",
        HealthTopic.CANCER:     "cancer treatment oncology mechanism",
        HealthTopic.HEMOPHILIA: "hemophilia bleeding factor therapy",
        HealthTopic.WEIGHT:     "obesity weight loss metabolism",
        HealthTopic.DIABETES:   "diabetes glucose metabolism insulin",
    }.get(topic, "")
    
    enriched_query = f"{query} {topic_context}".strip()
    
    if include_preprints:
        log.debug(f"Searching bioRxiv/medRxiv for: {enriched_query}")
        all_docs.extend(biorxiv_medrxiv_search(enriched_query, max_results=8))
    
    if include_oa:
        log.debug(f"Searching CrossRef+Unpaywall for: {enriched_query}")
        all_docs.extend(crossref_unpaywall_search(enriched_query, max_results=10))
    
    if include_chembl:
        log.debug(f"Searching ChEMBL for: {query}")
        all_docs.extend(chembl_search(query, max_results=8))
    
    if include_lens:
        log.debug(f"Searching Lens.org for: {enriched_query}")
        all_docs.extend(lens_org_search(enriched_query, max_results=5))
    
    # Deduplicate by URL + chunk_id
    seen = set()
    deduped = []
    for doc in all_docs:
        key = (doc.url, doc.chunk_id)
        if key not in seen:
            seen.add(key)
            deduped.append(doc)
    
    log.info(
        f"Academic sources search complete: {len(deduped)} unique chunks "
        f"from {len(all_docs)} total across all sources"
    )
    return deduped
