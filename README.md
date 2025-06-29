# 🧠 SQL Server Performance Optimizer (Prototype)

Aplikasi berbasis Flask untuk membantu mengoptimasi performa SQL Server. Sistem ini dirancang sebagai prototipe yang dapat mendeteksi fragmentasi index, memberikan rekomendasi perbaikan (REBUILD/REORGANIZE), serta menyarankan index baru berdasarkan isi stored procedure dengan bantuan AI.

---

## 🚀 Fitur Utama

- 🔍 Deteksi fragmentasi index secara otomatis
- 🧠 Rekomendasi index tambahan dari AI (berbasis isi SP & struktur tabel)
- 📜 Hasil rekomendasi digabung dalam satu Stored Procedure: `recommendation_index`
- 🛠️ Eksekusi manual melalui SQL Server atau UI Flask
- 🗂 Logging ke file SQL untuk dokumentasi

---

## 📦 Instalasi

### 1. Clone repository

```bash
git clone https://github.com/username/sql-server-optimizer.git
cd sql-server-optimizer
```

### 2. Buat virtual environment

```bash
python -m venv venv
```
# Windows:
```bash
venv\Scripts\activate
```
# Linux/macOS:
```bash
source venv/bin/activate
```

### 3. Install dependensi
```bash
pip install -r requirements.txt
```

## ⚙️ Konfigurasi Database
Buat file .env di root folder:
```bash
SQL_SERVER=localhost
SQL_DATABASE=AdventureWorks2019
SQL_USERNAME=your_username
SQL_PASSWORD=your_password
```
Gantilah dengan kredensial sesuai environment kamu.

## ▶️ Menjalankan Aplikasi
```bash
python run_web.py
```

Akses melalui browser:
```bash
http://127.0.0.1:5000
```

## 🧪 Alur Penggunaan
1. Klik Analisa Index untuk mendeteksi fragmentasi
2. (Opsional) Klik Ambil Rekomendasi AI untuk melihat saran index tambahan
3. Klik Buat Stored Procedure untuk menyimpan semua perintah sebagai dbo.recommendation_index
4. Jalankan secara manual:
```bash
EXEC dbo.recommendation_index;
```

## 🗃️ Struktur Folder
├── app/
│   ├── indexing/
│   	├── __init__.py
│   	├── fragmentation_analyzer.py
│   	├── index_ai.py
│   	├── index_recommender.py
│   	├── recommendation_builder.py
│   	└── sql_executor.py
│   ├── optimization/
│   	├── __init__.py
│   	├── sp_loader.py
│   	├── sp_optimizer.py
│   	└── sp_saver.py
│   └── utils/
│   	├── __init__.py
│   	├── loggerloader.py
│   	└── utilssaver.py
├── outputs/
├── templates/ 
│   ├── execution_result.html
│   ├── index.html
│   ├── index_resultresult.html
│   ├── optimize.html
│   ├── result.html
│   ├── save_result.html
│   └── save_result_optimize.html
├── run_web.py                   
├── requirements.txt
├── .env                         
└──  README.md

## ⚠️ Catatan
- Pastikan sudah mengaktifkan Full Text Search jika SP mengandung FREETEXTTABLE / CONTAINSTABLE
- Rekomendasi AI tidak mengubah SP dan hanya memberi saran index tambahan
- Eksekusi tetap manual dan tidak diaktifkan otomatis

## 📜 Lisensi
MIT License – Bebas digunakan untuk pembelajaran, eksperimen, dan pengembangan internal.