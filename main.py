#!/usr/bin/env python
"""
Main orchestration script untuk sistem rekomendasi karya ilmiah
Flow: Scrape -> Preprocess -> Generate Embeddings -> Index Qdrant -> Ready for Inference
"""

import os
import sys
import argparse
from urllib.parse import quote_plus
from datetime import datetime
from webscrape import GunadarmaRepositoryScraper
from embedding import EmbeddingManager

def print_section(title):
    """Print section header"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def scrape_papers(output_csv: str = 'papers_data.csv', max_pages: int = 5):
    """Phase 1: Scrape papers dari Gunadarma"""
    print_section("PHASE 1: SCRAPING DATA")
    
    base_url = 'https://library.gunadarma.ac.id/repository'
    
    scraper = GunadarmaRepositoryScraper(
        base_url=base_url,
        output_csv=output_csv,
        max_pages=max_pages
    )
    
    print(f'\n[INFO] Starting scrape ({max_pages} pages max)...')
    scraper.scrape_all_pages()
    scraper.save_to_csv()
    
    print(f'\n✅ Scraping complete: {output_csv}')
    return output_csv

def generate_paper_link(title: str) -> str:
        base_url = "https://library.gunadarma.ac.id/deposit-system/epaper"

        encoded_title = quote_plus(title)

        return (
            f"{base_url}"
            f"?pembimbing=&penulis=&tahun=&jurusan=&judul={encoded_title}"
        )

def generate_embeddings_and_index(csv_path: str = 'all_papers_data.csv',
                                   qdrant_path: str = './qdrant_storage',
                                   model_name: str = 'firqaaa/indo-sentence-bert-base',
                                   recreate: bool = True):
    """Phase 2 & 3: Generate embeddings dan index ke Qdrant"""
    print_section("PHASE 2-3: EMBEDDING & INDEXING")
    
    if not os.path.exists(csv_path):
        print(f'❌ ERROR: CSV file not found: {csv_path}')
        return None
    
    print(f'\n[INFO] Initializing embedding manager...')
    em = EmbeddingManager(model_name=model_name, qdrant_path=qdrant_path)
    
    print(f'\n[INFO] Ingesting papers to Qdrant...')
    num_papers = em.ingest_papers(csv_path, recreate=recreate)
    
    # Print stats
    stats = em.get_collection_stats()
    print(f'\n[STATS]')
    print(f'  - Papers indexed: {stats["points_count"]}')
    print(f'  - Vector dimension: {stats["vector_size"]}')
    print(f'  - Distance metric: {stats["distance"]}')
    
    print(f'\n✅ Embedding & indexing complete')
    return em

def analyze_trends(em: EmbeddingManager):
    """Phase 4: Analyze trends"""
    print_section("PHASE 4: TREND ANALYSIS")
    
    trends = em.analyze_trends()
    
    print(f'\n[TRENDS]')
    print(f'  - Total papers: {trends["total_papers"]}')
    print(f'  - Jurusan: {len(trends["jurusan_distribution"])} unique')
    print(f'  - Tahun: {len(trends["tahun_distribution"])} years')
    
    print(f'\n  Top 5 Jurusan:')
    sorted_jurusan = sorted(trends['jurusan_distribution'].items(), 
                            key=lambda x: x[1], reverse=True)[:5]
    for jurusan, count in sorted_jurusan:
        print(f'    - {jurusan}: {count}')
    
    print(f'\n  Top 5 Tahun:')
    sorted_tahun = sorted(trends['tahun_distribution'].items(),
                          key=lambda x: x[1], reverse=True)[:5]
    for tahun, count in sorted_tahun:
        print(f'    - {tahun}: {count}')

def test_search(em: EmbeddingManager, query: str = "sistem rekomendasi machine learning"):
    """Test search functionality"""
    print_section("TEST: SIMILARITY SEARCH")
    
    print(f'\n[TEST] Query: "{query}"')
    print(f'[TEST] Searching for 5 similar papers...\n')
    
    results = em.search_similar(query, limit=5)
    
    for idx, result in enumerate(results, 1):
        print(f'{idx}. [{result["score"]:.3f}] {result["judul"][:80]}...')
        print(f'   - Jurusan: {result["jurusan"]}')
        print(f'   - Tahun: {result["tahun"]}')

def main():
    parser = argparse.ArgumentParser(
        description='Orchestrate paper scraping and embedding pipeline'
    )
    parser.add_argument('--csv', type=str, default='papers_data.csv',
                        help='Output CSV file for papers')
    parser.add_argument('--pages', type=int, default=5,
                        help='Max pages to scrape')
    parser.add_argument('--qdrant-path', type=str, default='./qdrant_storage',
                        help='Path for Qdrant storage')
    parser.add_argument('--model', type=str, default='firqaaa/indo-sentence-bert-base',
                        help='IndoBERT model name')
    parser.add_argument('--skip-scrape', action='store_true',
                        help='Skip scraping, use existing CSV')
    parser.add_argument('--recreate-db', action='store_true',
                        help='Delete and recreate Qdrant collection')
    parser.add_argument('--test', action='store_true',
                        help='Run test search after pipeline')
    
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("  SISTEM REKOMENDASI KARYA ILMIAH")
    print("  Orchestration Pipeline")
    print("="*60)
    print(f"\n[START TIME] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Phase 1: Scrape
        if not args.skip_scrape:
            csv_path = scrape_papers(
                output_csv=args.csv,
                max_pages=args.pages
            )
        else:
            csv_path = args.csv
            if not os.path.exists(csv_path):
                print(f'❌ ERROR: CSV file not found: {csv_path}')
                print('Please run without --skip-scrape or provide existing CSV')
                return
            print(f'\n[INFO] Using existing CSV: {csv_path}')
        
        # Phase 2-3: Embedding & Indexing
        em = generate_embeddings_and_index(
            csv_path=csv_path,
            qdrant_path=args.qdrant_path,
            model_name=args.model,
            recreate=args.recreate_db
        )
        
        if em is None:
            print('❌ ERROR during embedding phase')
            return
        
        # Phase 4: Analyze trends
        analyze_trends(em)
        
        # Optional: Test search
        if args.test:
            test_search(em)
        
        # Success
        print_section("PIPELINE COMPLETE")
        print(f'\n✅ All phases completed successfully!')
        print(f'\n[NEXT STEP] Run Streamlit app:')
        print(f'  streamlit run app.py')
        print(f'\n[END TIME] {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        
    except Exception as e:
        print(f'\n❌ FATAL ERROR: {str(e)}')
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
