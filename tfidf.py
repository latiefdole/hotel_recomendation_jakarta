import pandas as pd
import numpy as np
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ==============================================================================
# === LANGKAH 1: MEMUAT DATA ===================================================
# ==============================================================================
try:
    # Ganti nama file jika Anda menyimpannya dengan nama lain
    NAMA_FILE_CSV = 'data_hotel_lengkap_final.csv' 
    df = pd.read_csv(NAMA_FILE_CSV)
    print(f"Berhasil memuat {len(df)} data dari '{NAMA_FILE_CSV}'")
except FileNotFoundError:
    print(f"Error: File '{NAMA_FILE_CSV}' tidak ditemukan.")
    print("Pastikan Anda sudah menjalankan skrip scraping dan nama filenya benar.")
    exit()

# ==============================================================================
# === LANGKAH 2: PEMBERSIHAN & PERSIAPAN DATA ==================================
# ==============================================================================
print("\nMemulai pembersihan dan persiapan data...")

# --- 2a. Membersihkan Harga ---
# Mengubah 'Rp 1.500.000' menjadi angka 1500000
def clean_price(price):
    if isinstance(price, str) and 'Rp' in price:
        return int(price.replace('Rp ', '').replace('.', ''))
    return np.nan # Beri nilai NaN jika format tidak sesuai

df['Harga Numerik'] = df['Harga Diskon'].apply(clean_price)

# --- 2b. Memisahkan Skor Rating dan Jumlah Ulasan ---
def parse_rating(rating_str):
    if not isinstance(rating_str, str) or '(' not in rating_str:
        return None, None
    
    skor_match = re.search(r'^\s*([\d.]+)', rating_str)
    skor = float(skor_match.group(1)) if skor_match else None
    
    jumlah_match = re.search(r'\((\d+)', rating_str)
    jumlah = int(jumlah_match.group(1)) if jumlah_match else None
    
    return skor, jumlah

df[['Skor Rating', 'Jumlah Ulasan']] = df['Rating'].apply(parse_rating).apply(pd.Series)

# Hapus baris yang datanya tidak lengkap setelah diproses
df.dropna(subset=['Skor Rating', 'Jumlah Ulasan', 'Harga Numerik'], inplace=True)
df['Jumlah Ulasan'] = df['Jumlah Ulasan'].astype(int)
df['Bintang Hotel'] = df['Bintang Hotel'].astype(int)

print("Pembersihan data selesai. Contoh data yang sudah bersih:")
print(df[['Nama Hotel', 'Skor Rating', 'Jumlah Ulasan', 'Harga Numerik']].head())


# ==============================================================================
# === LANGKAH 3: REKAYASA FITUR (FEATURE ENGINEERING) ==========================
# ==============================================================================
print("\nMembuat fitur 'Skor Popularitas' dan 'Features' untuk model...")

# --- 3a. Menghitung Skor Popularitas (Weighted Rating) ---
C = df['Skor Rating'].mean()
# Kita gunakan persentil 75, artinya hotel harus lebih populer dari 75% hotel lain
m = df['Jumlah Ulasan'].quantile(0.75) 

def calculate_weighted_rating(row, m=m, C=C):
    v = row['Jumlah Ulasan']
    R = row['Skor Rating']
    return (v / (v + m)) * R + (m / (v + m)) * C

df['Skor Popularitas'] = df.apply(calculate_weighted_rating, axis=1)

# --- 3b. Menggabungkan Fitur untuk Content-Based Filtering ---
# Kita gabungkan fitur-fitur terpenting menjadi satu string
# .fillna('') untuk mengatasi jika ada data yang kosong
df['features'] = (
    df['Lokasi'].fillna('').str.lower().str.replace(',', ' ') + ' ' +
    df['Fasilitas'].fillna('').str.lower().str.replace('; ', ' ') + ' ' +
    df['Tipe Properti'].fillna('').str.lower()
)

print("Fitur berhasil dibuat. Contoh fitur untuk satu hotel:")
print(df['features'].iloc[0])


# ==============================================================================
# === LANGKAH 4: PEMBANGUNAN MODEL REKOMENDASI =================================
# ==============================================================================
print("\nMembangun model rekomendasi dengan TF-IDF dan Cosine Similarity...")

# Inisialisasi TfidfVectorizer
# stop_words untuk mengabaikan kata umum (misal: 'dan', 'di', 'the', 'a')
tfidf = TfidfVectorizer(stop_words='english')

# Membuat matriks TF-IDF
tfidf_matrix = tfidf.fit_transform(df['features'])

# Menghitung matriks cosine similarity
cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)

print("Model berhasil dibangun!")

# ==============================================================================
# === LANGKAH 5: FUNGSI REKOMENDASI & DEMONSTRASI ==============================
# ==============================================================================

# Membuat mapping antara nama hotel dan indeks DataFrame untuk pencarian cepat
indices = pd.Series(df.index, index=df['Nama Hotel']).drop_duplicates()

def recommend_hotel(hotel_name, cosine_sim=cosine_sim):
    try:
        # Dapatkan indeks dari hotel yang cocok dengan nama
        idx = indices[hotel_name]
    except KeyError:
        return f"Hotel dengan nama '{hotel_name}' tidak ditemukan di dalam dataset."

    # Dapatkan skor kesamaan dari semua hotel dengan hotel tersebut
    sim_scores = list(enumerate(cosine_sim[idx]))

    # Urutkan hotel berdasarkan skor kesamaan
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)

    # Ambil skor dari 10 hotel paling mirip (indeks 0 adalah hotel itu sendiri)
    sim_scores = sim_scores[1:11]

    # Dapatkan indeks dari hotel-hotel yang direkomendasikan
    hotel_indices = [i[0] for i in sim_scores]

    # Kembalikan DataFrame kecil berisi hotel yang direkomendasikan
    return df.iloc[hotel_indices]

# --- DEMONSTRASI ---
print("\n--- CONTOH REKOMENDASI ---")

# Ganti dengan nama hotel yang ada di file CSV Anda
NAMA_HOTEL_CONTOH = df['Nama Hotel'].iloc[0] 

# Cek apakah hotel ada di dataset
if NAMA_HOTEL_CONTOH not in indices:
    print(f"'{NAMA_HOTEL_CONTOH}' tidak ditemukan di dataset.")
else:
    print(f"Rekomendasi untuk hotel: '{NAMA_HOTEL_CONTOH}'")
    
    # Dapatkan rekomendasi
    rekomendasi = recommend_hotel(NAMA_HOTEL_CONTOH)
    
    # --- Tampilan 1: Rekomendasi Murni Berdasarkan Kemiripan Konten ---
    print("\nTop 10 Rekomendasi (berdasarkan kemiripan fasilitas & lokasi):")
    print(rekomendasi[['Nama Hotel', 'Lokasi', 'Fasilitas', 'Tipe Properti']])
    
    # --- Tampilan 2: Rekomendasi yang Diurutkan Berdasarkan Popularitas ---
    print("\nTop 10 Rekomendasi (diurutkan berdasarkan SKOR POPULARITAS):")
    rekomendasi_sorted = rekomendasi.sort_values('Skor Popularitas', ascending=False)
    print(rekomendasi_sorted[['Nama Hotel', 'Skor Rating', 'Jumlah Ulasan', 'Skor Popularitas']])