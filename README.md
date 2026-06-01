# Academic Paper Recommendation System

A hybrid recommendation platform for academic papers using dense semantic search (IndoSBERT) + sparse keyword search (BM25), powered by Qdrant Vector Database and Streamlit.

## Key Features

- **Hybrid Search**: Combines dense semantic embeddings (IndoSBERT) + sparse BM25 keyword search with RRF (Reciprocal Rank Fusion) for better retrieval quality
- **Item-to-Item Recommendations**: Click on any paper to see 5 similar papers with detail pages
- **Trend Analysis**: Visualize paper distribution by academic major and publication year
- **Advanced Filtering**: Filter results by major and year
- **Interactive UI**: Browse papers with abstracts, metadata, and links to original documents
- **Heatmap Visualization**: Cross-tabulation of academic major vs publication year

## Tech Stack

- **Dense Embeddings**: IndoSBERT (firqaaa/indo-sentence-bert-base, 768-dim, COSINE distance)
- **Sparse Embeddings**: FastEmbed BM25 with IDF modifier
- **Vector Database**: Qdrant (local persistent storage with named vectors)
- **Retrieval Fusion**: Native RRF (Reciprocal Rank Fusion) via Qdrant Prefetch
- **Frontend**: Streamlit with session state management
- **Data Pipeline**: BeautifulSoup4 web scraper, pandas preprocessing
- **Visualization**: Plotly Express and Plotly Graph Objects

## Requirements

- Python 3.8+
- pip / conda
- 3-4GB disk space (models + embeddings + vector storage)
- Internet connection (for model downloads on first run)

## Installation & Setup

### 1. Setup Project Folder

```bash
cd "c:\Users\rifky\Downloads\Projects\PI - Sistem Rekomendasi"
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run Pipeline Orchestration

```bash
python main.py --pages 5 --test
```

**Common options:**
- `--pages 5`: Scrape 5 pages from Gunadarma repository (~100-150 papers)
- `--test`: Run test hybrid search after indexing
- `--skip-scrape`: Skip scraping, use existing CSV
- `--recreate-db`: Delete and recreate Qdrant collection
- `--collection hybrid_60`: Set custom collection name
- `--title-weight 0.6`: Use 60% title, 40% abstract for embeddings (default: combined)

**Output:**
- `papers_data.csv`: Scraped paper metadata
- `./qdrant_storage/`: Qdrant database with dense + sparse embeddings

First run takes 10-20 minutes depending on page count and internet speed.

### 4. Run Streamlit App

```bash
streamlit run app.py
```

Opens at `http://localhost:8501`

## Architecture

### Search Pipeline

```
User Query
    |
    +---> Dense Embedding (IndoSBERT)
    |           |
    |           v
    |     Qdrant Dense Search (30 results)
    |
    +---> Sparse Embedding (BM25)
                |
                v
          Qdrant Sparse Search (30 results)
                |
                v
          RRF Fusion (combine rankings)
                |
                v
          Final Results (10 papers)
```

### Vector Storage

Uses Qdrant named vectors:
- `dense`: COSINE distance, 768-dimensional (IndoSBERT)
- `sparse`: IDF modifier (BM25 keyword matching)

Deterministic point IDs (MD5 hash of title) prevent duplicates on upsert.

### Web Scraping with Scrapy

The system uses **Scrapy** framework for efficient, scalable web scraping from Gunadarma's institutional repository.

**Spider Architecture** (webscrape.py):

```
GunadarmaRepoSpider
├── start_requests()
│   └── Generate requests for all faculty + document type combinations
│
├── parse_listing()
│   ├── Extract paper cards from search results
│   ├── Follow detail links for each paper
│   └── Auto-paginate through results
│
└── parse_detail()
    ├── Extract abstract (ABSTRAKSI section)
    ├── Extract exam date (TANGGAL SIDANG)
    ├── Parse year from date
    └── Apply stop-gap logic (halt if old papers encountered)
```

**Multi-Faceted Crawling Strategy**:

The spider iterates through all combinations of:
- **Document Types** (Jenis): Skripsi, Penulisan Ilmiah
- **Faculties** (Fakultas): Ilmu Komputer, Ekonomi, Teknologi Industri

For each combination, it:
1. Fetches search results page by page
2. Extracts paper titles, faculties, majors, advisors
3. Follows detail links to extract abstracts and dates
4. Auto-increments pages until no more results

**Stop-Gap Logic**:

To avoid crawling thousands of old papers, the spider tracks consecutive papers below MIN_YEAR (2020):
- If 20 consecutive papers are older than 2020, the category is marked as complete
- This prevents unnecessary requests while ensuring coverage of recent papers

**Extending the Spider**:

To add new faculties or document types, edit the TARGET_JENIS and TARGET_FAKULTAS dictionaries in webscrape.py:

```python
TARGET_FAKULTAS = {
    "Ilmu Komputer dan Teknologi Informasi": "1",
    "Ekonomi": "2",
    "Teknologi Industri": "4",
    "Your Faculty Name": "5",  # Add new faculty
}
```

Then re-run the pipeline:
```bash
python main.py --pages 10 --recreate-db
```

The spider will automatically generate requests for all new combinations.

**Error Handling**:

- Failed detail page requests use errback handler and log warnings
- Missing fields default to empty strings or "-"
- Invalid year formats are skipped
- Duplicate titles are removed during preprocessing

**Performance**:

- Uses Scrapy's asynchronous requests for fast concurrent crawling
- Respects target website by limiting concurrent requests
- Typical throughput: 50-100 papers per minute

## Usage Guide

### Tab 1: Recommendations

1. Enter paper title or research topic
   - Example: "machine learning recommendation"
   - Example: "sentiment analysis"

2. (Optional) Set number of results (5-30)

3. (Optional) Filter by major and year

4. Click "Search Recommendations"

5. Browse results:
   - Similarity score percentage
   - Paper title (clickable for detail page)
   - Metadata: Type, Major, Year, Advisor
   - Abstract in expandable section
   - Links to original document

6. Click "View Details & Similar Papers" to:
   - See full paper metadata
   - Find 5 similar papers
   - Click through chains of similar papers

### Tab 2: Trend Analysis

Visualizations of paper data:
- **Distribution by Major**: Bar chart of papers per academic major
- **Trend by Year**: Line chart of publications over time
- **Heatmap**: Cross-tabulation of major vs year

Advanced statistics:
- Most common major
- Most productive year
- Average papers per major

## File Structure

```
.
├── main.py                # Pipeline orchestration (scrape -> embed -> index)
├── embedding.py           # EmbeddingManager class (hybrid search + Qdrant)
├── app.py                 # Streamlit UI (tabs, search, detail view, trends)
├── webscrape.py           # Scraper implementation
├── requirements.txt       # Python dependencies
├── papers_data.csv        # Output: paper metadata (generated)
├── qdrant_storage/        # Output: vector database (generated)
└── README.md              # This file
```

### Key Classes

**EmbeddingManager** (embedding.py):
- `__init__`: Load models (IndoSBERT + BM25)
- `create_collection()`: Setup Qdrant with dense + sparse vectors
- `ingest_papers()`: Generate embeddings and upsert to Qdrant
- `search_hybrid()`: Dense + sparse search with RRF fusion
- `search_similar_by_paper_id()`: Find similar papers for detail view
- `get_collection_stats()`: Metadata about indexed papers
- `analyze_trends()`: Distribution analysis

## Troubleshooting

### Error: "ModuleNotFoundError: No module named 'sentence_transformers'"

Reinstall dependencies:
```bash
pip install -r requirements.txt --upgrade
```

### Error: "Vector database not found"

Run the pipeline first:
```bash
python main.py
```

### Slow initial setup

- Model download (~600MB) takes 5-10 minutes on first run
- Embedding generation takes 5-15 minutes depending on paper count
- Do not interrupt the process

### Memory issues during embedding

Reduce batch size in embedding.py:
```python
embeddings = self.model.encode(texts, batch_size=16, ...)  # Reduce from 32
```

### Search results show duplicate papers

This indicates papers with identical titles (already filtered in preprocessing). If persisting, check paper_data.csv for duplicates.

## Advanced Configuration

### Custom collection name

```bash
python main.py --collection my_papers_hybrid
```

### Change embedding weighting

```bash
python main.py --title-weight 0.7  # 70% title, 30% abstract
python main.py --title-weight 1.0  # Title only
python main.py --title-weight 0.0  # Abstract only
python main.py                      # Combined (default)
```

### Use different model

```bash
python main.py --model indobenchmark/indobert-base-p1
```

### Ingest existing papers from CSV

```bash
python main.py --csv my_papers.csv --skip-scrape
```

CSV should have columns: jenis, fakultas, judul, dosen_pembimbing, jurusan, tahun, abstrak

## Security & Privacy

- All data stored locally in `./qdrant_storage/`
- No cloud connectivity
- Models from official Huggingface
- No external API calls during search

## Limitations & Future Work

- Currently search by title/abstract only (no full-text)
- Scraper tied to Gunadarma library structure (will break if website changes)
- No user authentication or multi-user support
- No explanation of why papers are similar

### Planned Features

- [ ] Fine-tune IndoSBERT on domain-specific academic papers
- [ ] Auto clustering and topic discovery
- [ ] Cloud deployment (AWS/GCP)
- [ ] Recommendation explanations
- [ ] Full-text search support
- [ ] Real-time ingestion pipeline
- [ ] User feedback for ranking refinement

## License

Personal project for PI Sistem Rekomendasi, Universitas Gunadarma

## Author

Rifky - Universitas Gunadarma

---

For detailed help:
```bash
python main.py --help
```
