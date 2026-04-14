# Academic & Scientific Sources Integration

## Overview

The Healthcare RAG Agent now incorporates multiple academic and scientific data sources to complement traditional web search with current research and open-access publications. This significantly enhances the evidence base for health recommendations.

## Supported Sources

### 1. **bioRxiv/medRxiv (Preprints)**
- **Type**: Preprint server with open API
- **Coverage**: Peer-reviewed preprints before formal publication
- **Use Case**: Latest research findings, clinical trial protocols, unpublished studies
- **API**: Free, no authentication required
- **Dimensions**: All therapy dimensions (via keyword analysis)

### 2. **CrossRef + Unpaywall (DOI Resolution & Open Access)**
- **Type**: DOI metadata provider + OA aggregator
- **Coverage**: Millions of scholarly articles with resolved DOI metadata
- **Use Case**: Verified citations, full-text access when open-access available
- **API**: Free, public API (rate-limited)
- **Features**:
  - Full bibliographic metadata
  - Automatic detection of open-access versions
  - Links to free full-text PDFs
- **Dimensions**: Evidence-based, FDA clinical, mechanism of action

### 3. **ChEMBL (EBI Drug-Target Database)**
- **Type**: Bioactivity and compound database
- **Coverage**: 2M+ bioactive compounds, drug targets, mechanisms
- **Use Case**: Drug mechanisms, target interactions, supplementation research
- **API**: Free REST API (no authentication)
- **Features**:
  - Chemical structure information (SMILES)
  - Drug-target interactions
  - Bioactivity data
- **Dimensions**: Primarily FDA-clinical & supplementation

### 4. **Lens.org & CORE (Open-Access Aggregators)**
- **Type**: OA article aggregators + discovery
- **Coverage**: 500M+ open-access documents from institutional repositories
- **Use Case**: Broad open-access research discovery
- **API**: Limited public API (CORE offers broader programmatic access)
- **Features**:
  - Patent & scholarly article integration (Lens)
  - Institutional repository indexing (CORE)
- **Dimensions**: All dimensions, broad coverage

### 5. **OpenAlex (Comprehensive Scholarly Catalog)**
- **Type**: Free, open, comprehensive catalog of scholarly communication
- **Coverage**: 200M+ papers, authors, institutions, and research topics
- **Use Case**: Comprehensive article discovery with citation context
- **API**: Free, public API (no authentication required)
- **Features**:
  - Citation count and relevance ranking
  - Research topic classification
  - Open-access status detection
  - Author and institutional metadata
  - Covers all research disciplines
- **Dimensions**: All therapy dimensions, high citation relevance

## Integration Architecture

```
deep_search()
  ├── Tavily Search (existing web search)
  ├── Page Scraping (existing)
  └── Search Academic Sources (NEW)
      ├── bioRxiv/medRxiv
      ├── CrossRef + Unpaywall
      ├── ChEMBL
      ├── Lens.org/CORE
      └── OpenAlex
```

## Source Selection & Quality

Each source adds distinct value:

| Source | Strength | Best For |
|--------|----------|----------|
| bioRxiv/medRxiv | Latest research | Current findings, emerging evidence |
| CrossRef+Unpaywall | Verified citations | Peer-reviewed articles, OA full-text |
| ChEMBL | Drug/mechanism data | Specific drug/supplement information |
| Lens.org/CORE | Broad coverage | Comprehensive discovery |
| OpenAlex | Citation relevance | Highly-cited research, comprehensive discovery |

## API Rate Limits & Performance

| Source | Rate Limit | Typical Response |
|--------|-----------|------------------|
| bioRxiv | ~5 req/min | 1-3 seconds |
| CrossRef | 1 req/second | 0.5-1 second |
| Unpaywall | 1 req/second | 0.2-0.5 second |
| ChEMBL | Reasonable | 1-2 seconds |
| Lens/CORE | Variable | 1-5 seconds |
| OpenAlex | 100k/month (free) | 0.5-1 second |

All queries include timeout handling and graceful fallback.

## Configuration

Enable/disable sources in `deep_search()` or `search_academic_sources()`:

```python
# In web_search.py deep_search():
include_academic=True  # Toggle all academic sources

# In academic_sources.py search_academic_sources():
include_preprints=True      # bioRxiv/medRxiv
include_oa=True             # CrossRef+Unpaywall
include_chembl=True         # ChEMBL
include_lens=True           # Lens/CORE
include_openalex=True       # OpenAlex
```

## Citation & Attribution

All retrieved documents include:
- ✅ Direct source URL
- ✅ DOI (when available)
- ✅ Publication date
- ✅ Source type indicator (preprint, OA, etc.)

## Future Enhancements

- [ ] ORCID integration for researcher profiles
- [ ] PubMed Centralized search (PMC Open Access subset)
- [ ] WHO/NIH clinical trial registry integration
- [ ] FDA adverse event reporting (FAERS) integration
- [ ] Real-time preprint alerts for specific topics
- [ ] Semantic Scholar API for citation context

## Troubleshooting

**No results from academic sources?**
- Check internet connectivity
- Verify API endpoints are accessible
- Check logs for specific API error messages

**Performance degradation?**
- Academic sources are fetched in parallel where possible
- Reduce `max_results` in source functions
- Disable specific sources if not needed for your use case

**OA links not found?**
- Not all articles have open-access versions
- Unpaywall coverage improves over time
- Consider institutional access or interlibrary loan
