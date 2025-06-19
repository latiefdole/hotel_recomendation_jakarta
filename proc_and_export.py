import pandas as pd
import numpy as np
import re
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import os
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory 


print("Memulai proses...")

# === 1. MEMUAT & MEMBERSIHKAN DATA (Sama seperti di notebook) ===
try:
    NAMA_FILE_CSV = 'data_hotel_lengkap_final.csv' 
    df = pd.read_csv(NAMA_FILE_CSV)
    print(f"Berhasil memuat {len(df)} data.")
except FileNotFoundError:
    print(f"Error: File '{NAMA_FILE_CSV}' tidak ditemukan.")
    exit()

def parse_rating(rating_str):
    if not isinstance(rating_str, str) or '(' not in rating_str: return None, None
    skor_match = re.search(r'^\s*([\d.]+)', rating_str)
    skor = float(skor_match.group(1)) if skor_match else None
    jumlah_match = re.search(r'\((\d+)', rating_str)
    jumlah = int(jumlah_match.group(1)) if jumlah_match else None
    return skor, jumlah

df[['Skor Rating', 'Jumlah Ulasan']] = df['Rating'].apply(parse_rating).apply(pd.Series)
df.dropna(subset=['Skor Rating', 'Jumlah Ulasan', 'Tipe Properti'], inplace=True)
df['Jumlah Ulasan'] = df['Jumlah Ulasan'].astype(int)
df['Bintang Hotel'] = df['Bintang Hotel'].astype(int)
print("Data berhasil dibersihkan.")

# === 2. MEMBUAT FITUR & MODEL (Sama seperti di notebook) ===
df['features'] = (
    df['Lokasi'].fillna('').str.lower().str.replace(',', ' ') + ' ' + 
    df['Fasilitas'].fillna('').str.lower().str.replace('; ', ' ') + ' ' + 
    df['Tipe Properti'].fillna('').str.lower()
)
factory = StopWordRemoverFactory()
stop_words_sastrawi = factory.get_stop_words()
tfidf = TfidfVectorizer(stop_words=stop_words_sastrawi)
tfidf_matrix = tfidf.fit_transform(df['features'])
cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)
print("Model Cosine Similarity berhasil dibuat.")

# === 3. EKSPOR MODEL & DATA KE FILE ===
# Buat folder 'models' jika belum ada
if not os.path.exists('models'):
    os.makedirs('models')

# Kita hanya perlu menyimpan DataFrame yang sudah diproses dan matriks similarity
pickle.dump(df, open('models/processed_hotels_df.pkl', 'wb'))
pickle.dump(cosine_sim, open('models/cosine_sim_matrix.pkl', 'wb'))

print("\nProses selesai!")
print("File-file berikut telah berhasil diekspor ke folder /models:")
print("1. processed_hotels_df.pkl (Data hotel yang sudah bersih)")
print("2. cosine_sim_matrix.pkl (Matriks kemiripan hotel)")