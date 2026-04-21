# 🚀 QUICKSTART - Sistem Rekomendasi Karya Ilmiah

Panduan tercepat untuk get the system up and running dalam 5 langkah!

## ✅ Prerequisites Check

```bash
# Check Python version (pastikan 3.8+)
python --version

# Check pip
pip --version
```

Jika Python belum terinstall, download dari https://www.python.org/

---

## 🎯 5-Minute Setup

### Step 1: Install Dependencies (2 menit)

**Windows:**
```bash
pip install -r requirements.txt
```

**Mac/Linux:**
```bash
pip3 install -r requirements.txt
```

### Step 2: Run Orchestration Pipeline (5-10 menit)

**Windows:**
```bash
python main.py --pages 5 --test
```

**Mac/Linux:**
```bash
python3 main.py --pages 5 --test
```

Ini akan:
- ✅ Scrape ~100-150 papers dari repository Gunadarma
- ✅ Generate embeddings menggunakan IndoBERT
- ✅ Index semua papers ke Qdrant
- ✅ Run test search untuk verify setup

**Output:**
```
============================================================
  PHASE 1: SCRAPING DATA
============================================================
[Page 1] Status: 200
[Page 1] Extracted 24 papers
...

============================================================
  PHASE 2-3: EMBEDDING & INDEXING
============================================================
Loading model: indobenchmark/indobert-lite-base-p1...
Model loaded. Embedding dimension: 384
Initializing Qdrant at ./qdrant_storage...
Creating collection: papers
Generating embeddings for 120 texts...
✅ Embedding & indexing complete

============================================================
  TEST: SIMILARITY SEARCH
============================================================
[TEST] Query: "sistem rekomendasi machine learning"
1. [0.875] Sistem Rekomendasi Menggunakan Collaborative Filtering...
2. [0.842] Machine Learning untuk Prediksi Data...
...
```

### Step 3: Start Streamlit App

**Windows:**
```bash
streamlit run app.py
```

**Mac/Linux:**
```bash
streamlit run app.py
```

Akan automatically buka browser ke `http://localhost:8501`

### Step 4: Test Pencarian

1. Buka tab "🔍 Rekomendasi"
2. Masukkan query: `"sistem rekomendasi machine learning"`
3. Klik "🚀 Cari Rekomendasi"
4. Lihat hasil dengan similarity scores

### Step 5: Explore Tren Analytics

1. Buka tab "📊 Tren Analisis"
2. Lihat:
   - 📌 Distribusi per Jurusan (bar chart)
   - 📅 Tren per Tahun (line chart)
   - 🔥 Heatmap Jurusan vs Tahun

---

## 🎬 Using Setup Scripts (Alternative)

Jika tidak ingin run commands satu-satu, gunakan setup script:

**Windows:**
```bash
setup.bat
```

**Mac/Linux:**
```bash
chmod +x setup.sh
./setup.sh
```

Script ini akan automatic:
1. Install dependencies
2. Run orchestration pipeline
3. Start Streamlit app

---

## 💡 Common Queries untuk Testing

### Rekomendasi
- `"sistem rekomendasi machine learning"`
- `"analisis sentimen media sosial"`
- `"deep learning image recognition"`
- `"natural language processing"`
- `"database optimization"`

### Tips
- Gunakan bahasa Indonesia untuk hasil terbaik
- Bisa search dengan judul, topik, atau keywords
- Filter dengan jurusan/tahun untuk hasil lebih spesifik

---

## ⚠️ Troubleshooting

### ❌ "Python not found"
```bash
# Install Python dari https://www.python.org/
# Pastikan "Add Python to PATH" di-check saat install
```

### ❌ "No module named 'streamlit'"
```bash
pip install -r requirements.txt --upgrade
```

### ❌ "Vector database not found"
Pastikan sudah menjalankan `main.py` terlebih dahulu:
```bash
python main.py --pages 5
```

### ❌ "Model download lambat"
Model IndoBERT (~300MB) only download once. Tunggu 5-10 menit.

### ❌ "Streamlit port 8501 already in use"
```bash
# Use different port
streamlit run app.py --server.port 8502
```

---

## 🎛️ Advanced Options

### Scrape lebih banyak papers
```bash
python main.py --pages 20  # ~400-500 papers
```

### Skip scraping (gunakan existing data)
```bash
python main.py --skip-scrape
```

### Custom CSV
```bash
# Siapkan CSV dengan columns: judul, penulis, jurusan, jenis, tahun, link
python main.py --csv your_data.csv --skip-scrape
```

---

## 📊 Expected Results

Setelah setup, Anda akan memiliki:

```
.
├── papers_data.csv                 # ~100-150 papers dengan metadata
├── qdrant_storage/
│   ├── collection/
│   ├── snapshots/
│   └── config.json
├── app.py                          # Streamlit app running di :8501
└── [logs & cache files]
```

**Database Stats:**
- Total papers: ~100-500
- Vector dimension: 384 (IndoBERT output)
- Vector DB: Qdrant (local)
- Average search time: ~100ms

---

## 🎉 You're All Set!

```
✅ Setup Complete
✅ Database Indexed
✅ Streamlit Running at http://localhost:8501
✅ Ready to Search & Analyze!
```

---

## 📚 Next Steps

1. **Explore recommendations** - Try different queries
2. **Analyze trends** - Check distribution charts
3. **Read README.md** - Learn advanced features
4. **Customize** - Modify colors, add filters, etc. in `app.py`

---

## 🆘 Still Having Issues?

1. Check `README.md` untuk detailed docs
2. Run dengan `--help` flag untuk options:
   ```bash
   python main.py --help
   ```
3. Check error messages di terminal
4. Verify all dependencies: `pip list`

---

**Happy Recommending! 🎓📚**
