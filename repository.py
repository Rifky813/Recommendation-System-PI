import requests
from bs4 import BeautifulSoup
import csv
import time
from urllib.parse import urljoin, urlparse

class GunadarmaRepositoryScraper:
    """Scraper untuk repository karya ilmiah Gunadarma dengan metadata lengkap"""
    
    def __init__(self, base_url, output_csv='papers_data.csv', max_pages=10):
        self.base_url = base_url
        self.output_csv = output_csv
        self.max_pages = max_pages
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.papers = []
    
    def scrape_page(self, page_num=1):
        """Scrape satu halaman dengan metadata lengkap"""
        params = {
            'page': page_num,
            'jenis': '',
            'fakultas': '',
            'judul': 'vclass',
            'keyword': '',
            'nomoranggota': '',
            'penulis': '',
            'nomorinduk': '',
            'pembimbing': ''
        }
        
        try:
            response = self.session.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            print(f'[Page {page_num}] Status: {response.status_code}')
            
            soup = BeautifulSoup(response.text, 'html.parser')
            list_judul = soup.find_all('div', class_='card shadow')
            
            if not list_judul:
                print(f'[Page {page_num}] Tidak ada hasil')
                return 0
            
            count = 0
            for card in list_judul:
                try:
                    paper_data = self._extract_paper_data(card)
                    if paper_data:
                        self.papers.append(paper_data)
                        count += 1
                except Exception as e:
                    print(f'  [ERROR] Gagal extract paper: {e}')
            
            print(f'[Page {page_num}] Extracted {count} papers')
            time.sleep(1)  # Rate limiting
            return count
        
        except Exception as e:
            print(f'[Page {page_num}] ERROR: {e}')
            return 0
    
    def _extract_paper_data(self, card):
        """Extract metadata dari card element"""
        try:
            # Judul
            judul_elem = card.find('h5', class_='card-title font-weight-bold text-purple')
            judul = judul_elem.text.strip() if judul_elem else None
            
            # Metadata dari subtitle
            subtitle_elem = card.find('h6', class_='card-subtitle')
            if not subtitle_elem:
                return None
            
            subtitle_parts = subtitle_elem.text.split('|')
            
            # Parse subtitle: [Penulis | Jurusan | Jenis | Tahun]
            penulis = subtitle_parts[0].strip() if len(subtitle_parts) > 0 else None
            jurusan = subtitle_parts[2].strip() if len(subtitle_parts) > 2 else None
            jenis = subtitle_parts[1].strip() if len(subtitle_parts) > 1 else None
            tahun = subtitle_parts[3].strip() if len(subtitle_parts) > 3 else None
            
            # Link detail (jika ada)
            link_elem = card.find('a')
            link = link_elem.get('href') if link_elem else None
            if link:
                link = urljoin(self.base_url, link)
            
            return {
                'judul': judul,
                'penulis': penulis,
                'jurusan': jurusan,
                'jenis': jenis,
                'tahun': tahun,
                'link': link
            }
        
        except Exception as e:
            print(f'  [ERROR] Extract data: {e}')
            return None
    
    def scrape_all_pages(self):
        """Scrape semua halaman"""
        total = 0
        for page in range(1, self.max_pages + 1):
            count = self.scrape_page(page)
            if count == 0:
                print(f'No more results at page {page}, stopping...')
                break
            total += count
        
        print(f'\n[DONE] Total papers scraped: {total}')
        return total
    
    def save_to_csv(self):
        """Simpan hasil ke CSV"""
        if not self.papers:
            print('No papers to save')
            return
        
        try:
            with open(self.output_csv, 'w', newline='', encoding='utf-8') as f:
                fieldnames = ['judul', 'penulis', 'jurusan', 'jenis', 'tahun', 'link']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.papers)
            
            print(f'[SAVED] {len(self.papers)} papers -> {self.output_csv}')
        except Exception as e:
            print(f'[ERROR] Failed to save CSV: {e}')


# Main execution
if __name__ == '__main__':
    base_url = 'https://library.gunadarma.ac.id/repository'
    
    scraper = GunadarmaRepositoryScraper(
        base_url=base_url,
        output_csv='papers_data.csv',
        max_pages=5  # Start dengan 5 halaman untuk testing
    )
    
    print('Starting scrape...\n')
    scraper.scrape_all_pages()
    scraper.save_to_csv()