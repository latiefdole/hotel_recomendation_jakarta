import pandas as pd
import pickle
from flask import Flask, render_template, request, jsonify # <-- Tambahkan jsonify

# Inisialisasi aplikasi Flask
app = Flask(__name__)

# --- MEMUAT MODEL SAAT APLIKASI DIMULAI ---
try:
    df = pickle.load(open('models/processed_hotels_df.pkl', 'rb'))
    cosine_sim = pickle.load(open('models/cosine_sim_matrix.pkl', 'rb'))
    print("Model berhasil dimuat.")
except FileNotFoundError:
    print("Model tidak ditemukan. Jalankan 'proc_and_export.py' terlebih dahulu.")
    exit()

indices = pd.Series(df.index, index=df['Nama Hotel']).drop_duplicates()
unique_locations = sorted(df['Lokasi'].unique().tolist()) # <-- Ambil daftar lokasi unik

# --- FUNGSI REKOMENDASI (Tidak berubah) ---
def get_recommendations(hotel_name, cosine_sim=cosine_sim):
    try:
        idx = indices[hotel_name]
    except KeyError:
        return None
    sim_scores = list(enumerate(cosine_sim[idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
    sim_scores = sim_scores[1:11]
    hotel_indices = [i[0] for i in sim_scores]
    return df.iloc[hotel_indices]

# --- ROUTING APLIKASI ---
@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        selected_hotel = request.form.get('hotel_name')
        recommendations = get_recommendations(selected_hotel)
        if recommendations is not None:
            recs_list = recommendations.to_dict(orient='records')
        else:
            recs_list = []
        return render_template('recommendations.html', 
                               hotel_name=selected_hotel, 
                               recommendations=recs_list)

    # Method GET: Kirim daftar lokasi unik ke template
    return render_template('index.html', locations=unique_locations)


# === ENDPOINT API BARU UNTUK JAVASCRIPT ===
@app.route('/get_hotels_by_location')
def get_hotels_by_location():
    # Ambil parameter lokasi dari request
    location = request.args.get('location', '')
    if not location:
        return jsonify([]) # Kirim list kosong jika tidak ada lokasi
    
    # Filter hotel berdasarkan lokasi
    hotels_in_location = df[df['Lokasi'] == location]['Nama Hotel'].unique().tolist()
    
    # Kembalikan sebagai JSON
    return jsonify(sorted(hotels_in_location))
# ============================================

# Menjalankan aplikasi
if __name__ == '__main__':
    app.run(debug=True)