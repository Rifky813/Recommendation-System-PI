import os
import re
import urllib.parse
import scrapy
from scrapy.crawler import CrawlerProcess

# ─── Konstanta ────────────────────────────────────────────────────────────────
BASE_URL       = "https://library.gunadarma.ac.id/repository"
MIN_YEAR       = 2020   # tahun minimum inklusif
STOP_GAP_LIMIT = 20     # max paper berturut-turut < MIN_YEAR sebelum berhenti

TARGET_JENIS = {
    "Skripsi": "skripsi", 
    "Penulisan Ilmiah": "ssm"
}

TARGET_FAKULTAS = {
    "Ilmu Komputer dan Teknologi Informasi": "1",
    "Ekonomi": "2",
    "Teknologi Industri": "4"
}

# ─── Helper ───────────────────────────────────────────────────────────────────
def _extract_year(text: str) -> int | None:
    """Ekstrak tahun 4-digit (20xx) dari string, return None jika tidak ada."""
    match = re.search(r"\b(20\d{2})\b", text)
    return int(match.group(1)) if match else None

# ─── Spider Scrapy ────────────────────────────────────────────────────────────
class GunadarmaRepoSpider(scrapy.Spider):
    name = "gunadarma_repo"
    # custom_settings dihapus dari sini dan dipindahkan ke CrawlerProcess 
    # agar nama output CSV bisa dinamis mengikuti main.py

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.combo_state = {}
        for j_label in TARGET_JENIS.keys():
            for f_label in TARGET_FAKULTAS.keys():
                key = f"{j_label}|{f_label}"
                self.combo_state[key] = {"counter": 0, "stop": False}

    def start_requests(self):
        for j_label, j_val in TARGET_JENIS.items():
            for f_label, f_val in TARGET_FAKULTAS.items():
                yield self._make_request(
                    j_label=j_label, j_val=j_val, 
                    f_label=f_label, f_val=f_val, 
                    page=1
                )

    def _make_request(self, j_label: str, j_val: str, f_label: str, f_val: str, page: int) -> scrapy.Request:
        params = {
            "jenis": j_val, "fakultas": f_val, "judul": "", "keyword": "",
            "nomoranggota": "", "penulis": "", "nomorinduk": "", "pembimbing": "", "page": page
        }
        query_string = urllib.parse.urlencode(params)
        url = f"{BASE_URL}?{query_string}"
        combo_key = f"{j_label}|{f_label}"

        return scrapy.Request(
            url=url,
            callback=self.parse_listing,
            meta={
                "page": page, "combo_key": combo_key,
                "jenis_label": j_label, "fak_label": f_label,
                "jenis_val": j_val, "fak_val": f_val
            },
        )

    def parse_listing(self, response):
        page = response.meta["page"]
        combo_key = response.meta["combo_key"]
        j_label, f_label = response.meta["jenis_label"], response.meta["fak_label"]
        j_val, f_val = response.meta["jenis_val"], response.meta["fak_val"]

        if self.combo_state[combo_key]["stop"]:
            return

        cards = response.css("div.card.shadow")

        if not cards:
            self.logger.info(f"[{combo_key} | Page {page}] Kosong — pagination berhenti.")
            return

        self.logger.info(f"[{combo_key} | Page {page}] Ditemukan {len(cards)} card.")

        for card in cards:
            try:
                item = self._extract_card(card)
                item["jenis"] = j_label
                item["fakultas"] = f_label
            except Exception as exc:
                self.logger.warning(f"[{combo_key} | Page {page}] Gagal extract card: {exc}")
                continue

            link = card.css("a.stretched-link::attr(href)").get()
            if link:
                yield response.follow(
                    link, callback=self.parse_detail,
                    cb_kwargs={"item": item, "combo_key": combo_key},
                    errback=self._errback_detail, priority=10
                )
            else:
                yield item

        if not self.combo_state[combo_key]["stop"]:
            yield self._make_request(
                j_label=j_label, j_val=j_val, 
                f_label=f_label, f_val=f_val, page=page + 1
            )

    def parse_detail(self, response, item: dict, combo_key: str):
        item["url_sumber"] = response.url

        try:
            raw = response.xpath("//h5[contains(., 'ABSTRAKSI')]/../following-sibling::div[1]//text()").getall()
            item["abstrak"] = " ".join(t.strip() for t in raw if t.strip())
        except Exception:
            item.setdefault("abstrak", "")

        try:
            tgl_raw = response.xpath("//h5[contains(., 'TANGGAL SIDANG')]/../following-sibling::div[1]//text()").get()
            tgl_sidang = tgl_raw.strip() if tgl_raw else ""
        except Exception:
            tgl_sidang = ""

        year = _extract_year(tgl_sidang)
        item["tahun"] = year if year is not None else (tgl_sidang or "-")

        if year is not None and year < MIN_YEAR:
            self.combo_state[combo_key]["counter"] += 1
            if self.combo_state[combo_key]["counter"] >= STOP_GAP_LIMIT:
                self.combo_state[combo_key]["stop"] = True
                self.logger.info(f"[{combo_key}] Stop-gap tercapai! Selesai mengambil data kategori ini.")
            return 
        elif year is not None:
            self.combo_state[combo_key]["counter"] = 0

        yield item

    def _errback_detail(self, failure):
        self.logger.warning(f"[Detail] Request gagal: {failure.request.url} — {failure.value}")

    @staticmethod
    def _extract_card(card) -> dict:
        judul = card.css("h5.card-title.font-weight-bold.text-purple ::text").get(default="").strip()
        parts = [p.strip() for p in card.css("h6.card-subtitle *::text").getall() if p.strip()]

        dosen_pembimbing = jurusan = "-"
        if parts:
            cols = parts[0].split("|")
            jurusan = cols[2].strip() if len(cols) >= 3 else "-"
        if len(parts) >= 2:
            dosen_pembimbing = parts[1].replace("Pembimbing:", "").strip()

        return {
            "judul": judul, "dosen_pembimbing": dosen_pembimbing,
            "jurusan": jurusan, "tahun": "-", "abstrak": ""
        }

# ─── Wrapper Class untuk Pipeline ─────────────────────────────────────────────
class GunadarmaRepositoryScraper:
    """Wrapper Scrapy CrawlerProcess agar sinkron dengan struktur main.py lama"""
    
    def __init__(self, base_url=None, output_csv='papers_data.csv', max_pages=None):
        # Kita abaikan base_url dan max_pages karena Scrapy Spider yang baru 
        # sudah punya aturan crawling dan target URL yang lebih cerdas (stop-gap limit).
        self.output_csv = output_csv
        
    def scrape_all(self):
        """Menjalankan Scrapy engine secara synchronous dari dalam script"""
        
        # Hapus file lama jika ada agar FEEDS tidak melakukan append data ganda
        if os.path.exists(self.output_csv):
            os.remove(self.output_csv)

        # Setting dinamis dipindahkan ke sini
        settings = {
            "DOWNLOAD_DELAY": 1.0,
            "RANDOMIZE_DOWNLOAD_DELAY": True,
            "CONCURRENT_REQUESTS": 4,
            "CONCURRENT_REQUESTS_PER_DOMAIN": 4,
            "RETRY_TIMES": 3,
            "RETRY_HTTP_CODES": [500, 502, 503, 504, 408, 429],
            "LOG_LEVEL": "INFO",
            "FEEDS": {
                self.output_csv: {
                    "format": "csv",
                    "encoding": "utf-8",
                    "overwrite": False,
                    "fields": ["jenis", "fakultas", "judul", "dosen_pembimbing", "jurusan", "tahun", "abstrak"],
                }
            }
        }

        # Eksekusi blocking
        process = CrawlerProcess(settings)
        process.crawl(GunadarmaRepoSpider)
        process.start() 

    def save_to_csv(self):
        """Method dummy karena Scrapy sudah otomatis menyimpan CSV via FEEDS"""
        pass

if __name__ == '__main__':
    print("Memulai proses scraping mandiri...")
    scraper = GunadarmaRepositoryScraper(output_csv='papers_data.csv')
    scraper.scrape_all()
    print("Scraping selesai! Data tersimpan di papers_data.csv")