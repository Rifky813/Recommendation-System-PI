# 📚 Sistem Rekomendasi Karya Ilmiah

Platform rekomendasi karya ilmiah berbasis **IndoBERT**, **Qdrant Vector Database**, dan **Streamlit**.

## 🎯 Fitur Utama

- **🔍 Pencarian Rekomendasi**: Cari karya ilmiah berdasarkan judul/topik dengan semantic similarity
- **🎯 Hybrid Search**: Kombinasi similarity search + filtering (jurusan, tahun publikasi)
- **📊 Analisis Tren**: Visualisasi distribusi karya per jurusan dan per tahun
- **🔥 Heatmap**: Distribusi karya ilmiah berdasarkan jurusan vs tahun publikasi
- **📈 Advanced Analytics**: Statistik tren dan insights data

## 🛠️ Tech Stack

- **Model Embedding**: IndoBERT Lite (indobenchmark/indobert-lite-base-p1)
- **Vector Database**: Qdrant (local storage)
- **Frontend**: Streamlit
- **Data Scraping**: BeautifulSoup4
- **Visualization**: Plotly

## 📋 Prasyarat

- Python 3.8+
- pip / conda
- ~2GB disk space (untuk model + data)
- Internet connection (untuk download model pertama kali)

## 🚀 Instalasi & Setup

### 1. Clone / Setup Folder

```bash
cd "c:\Users\rifky\Downloads\Projects\PI - Sistem Rekomendasi"
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

**Note**: Instalasi pertama kali akan download IndoBERT model (~300MB). Tunggu beberapa menit.

### 3. Jalankan Pipeline Orchestration

```bash
python main.py --pages 5 --test
```

**Parameter:**
- `--pages 5`: Scrape 5 halaman dari repository Gunadarma (~100-150 papers)
- `--test`: Jalankan test search setelah indexing selesai
- `--skip-scrape`: Skip scraping, gunakan CSV yang sudah ada

**Output:**
- `papers_data.csv`: Data papers yang di-scrape
- `./qdrant_storage/`: Vector database dengan indexed embeddings

Proses ini memakan waktu ~5-15 menit tergantung jumlah papers dan kecepatan internet.

### 4. Jalankan Streamlit App

```bash
streamlit run app.py
```

App akan buka di `http://localhost:8501`

## 📖 Penggunaan

### Tab 1: Rekomendasi 🔍

1. Masukkan judul atau topik karya ilmiah di search box
   - Contoh: "sistem rekomendasi machine learning"
   - Contoh: "analisis sentimen media sosial"

2. (Opsional) Pilih jurusan dan tahun untuk filter hasil

3. Klik "Cari Rekomendasi"

4. Lihat hasil dengan:
   - Similarity score (%)
   - Metadata: Penulis, Jurusan, Tahun, Jenis
   - Link ke dokumen original

### Tab 2: Analisis Tren 📊

Visualisasi tren karya ilmiah:
- **Distribusi per Jurusan**: Bar chart jumlah karya per jurusan
- **Tren per Tahun**: Line chart publikasi seiring waktu
- **Heatmap**: Jurusan vs Tahun untuk insight komprehensif

## 📁 File Structure

```
.
├── repository.py          # Web scraper (Gunadarma library)
├── embedding.py           # Embedding manager + Qdrant integration
├── app.py                 # Streamlit interface
├── main.py                # Orchestration pipeline
├── requirements.txt       # Dependencies
├── papers_data.csv        # Output data (generated)
├── qdrant_storage/        # Vector DB (generated)
└── README.md              # This file
```

## 🔧 Troubleshooting

### ❌ "ModuleNotFoundError: No module named 'sentence_transformers'"

Jalankan install ulang:
```bash
pip install -r requirements.txt --upgrade
```

### ❌ "Vector database tidak ditemukan"

Jalankan pipeline orchestration terlebih dahulu:
```bash
python main.py
```

### ❌ Model download lambat

Model IndoBERT (~300MB) hanya download sekali saat pertama kali digunakan. Proses ini memakan waktu 5-10 menit tergantung koneksi internet. Bersabar dan jangan stop process.

### ❌ Memory error saat embedding

Jika device Anda memory-limited, reduce batch size di `embedding.py`:
```python
embeddings = self.model.encode(texts, batch_size=16, ...)  # Ubah dari 32 ke 16
```

### ❌ Scraping error / Gunadarma website berubah

Jika selector HTML berubah, update class names di `repository.py`:
- `div`, `class_='card shadow'` → main paper card
- `h5`, `class_='card-title font-weight-bold text-purple'` → judul
- `h6`, `class_='card-subtitle'` → metadata

## 🎛️ Advanced Configuration

### Mengubah jumlah pages yang di-scrape

```bash
python main.py --pages 10  # Scrape 10 pages (~200-300 papers)
```

### Menggunakan model IndoBERT yang berbeda

```bash
python main.py --model indobenchmark/indobert-base-p1  # Model lebih besar, lebih baik tapi lebih lambat
```

### Recreate database

```bash
python main.py --skip-scrape --recreate-db
```

### Streaming dengan custom CSV

```bash
# 1. Siapkan CSV dengan columns: judul, penulis, jurusan, jenis, tahun, link
python main.py --csv custom_data.csv --skip-scrape
```

## 📊 Performance Tips

1. **Search Speed**: Qdrant local sangat cepat (~100ms per query)
2. **Memory**: Streamlit cache model, jadi tidak reload setiap kali
3. **Scale**: Untuk 1000+ papers, pertimbangkan gunakan Qdrant server mode

## 🔐 Security & Privacy

- All data local di folder `./qdrant_storage/`
- Tidak ada data sent ke cloud
- Model IndoBERT di-download dari Huggingface official

## 🚀 Next Steps (Phase 2)

- [ ] Fine-tune IndoBERT dengan domain-specific Indonesian academic papers
- [ ] Implementasi clustering untuk auto-topic discovery
- [ ] Deploy ke cloud (AWS, GCP, Heroku)
- [ ] Add user authentication & session management
- [ ] Real-time ingestion pipeline dengan database
- [ ] Recommendation explanation (why this paper?)

## 📝 License

Project pribadi untuk PI Sistem Rekomendasi Gunadarma

## 👤 Author

Rifky | Universitas Gunadarma

---

**Questions?** Check `embedding.py` docstrings atau run:
```bash
python main.py --help
```
