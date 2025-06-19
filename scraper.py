import time
import pandas as pd
import random
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException

# -- PENGATURAN --
URL = "https://www.traveloka.com/id-id/hotel/search?spec=19-06-2025.20-06-2025.1.1.HOTEL_GEO.102813.Jakarta.2"
NAMA_FILE_CSV = 'data_hotel_lengkap_final.csv'

options = webdriver.ChromeOptions()
options.add_experimental_option('excludeSwitches', ['enable-logging'])

print("Menginisialisasi browser Chrome...")
driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
driver.maximize_window()
driver.get(URL)

print("Memberi waktu 5 detik untuk halaman awal termuat...")
time.sleep(5)

try:
    close_button = driver.find_element(By.XPATH, "//div[@aria-label='Tutup']")
    if close_button.is_displayed():
        print("Menutup pop-up awal...")
        close_button.click()
        time.sleep(2)
except NoSuchElementException:
    print("Tidak ada pop-up awal yang terdeteksi.")
    pass

semua_hotel_data = []
processed_hotel_names = set()
html = driver.find_element(By.TAG_NAME, 'html')

print("Memulai proses scrolling dan parsing...")
last_height = driver.execute_script("return document.body.scrollHeight")
scroll_attempts = 0

while scroll_attempts < 4:
    # (Penanganan CAPTCHA tetap ada di sini)
    try:
        captcha_iframe = driver.find_element("xpath", "//iframe[contains(@title, 'CAPTCHA') or contains(@title, 'captcha')]")
        if captcha_iframe.is_displayed():
            print("\n=======================================================")
            print("  !!! CAPTCHA TERDETEKSI !!!")
            input("  Setelah selesai, tekan [Enter] di sini untuk melanjutkan...")
            print("  Melanjutkan scraping...")
            print("=======================================================\n")
            time.sleep(5)
    except NoSuchElementException:
        pass
        
    page_source = driver.page_source
    soup = BeautifulSoup(page_source, 'html.parser')
    current_hotels = soup.find_all('div', attrs={'data-testid': 'tvat-searchListItem'})
    
    new_data_found_in_this_pass = False
    for hotel_element in current_hotels:
        nama_element = hotel_element.find('h3', attrs={'data-testid': 'tvat-hotelName'})
        if not nama_element: continue
        hotel_name = nama_element.text.strip()
        
        if hotel_name not in processed_hotel_names:
            new_data_found_in_this_pass = True
            hotel_data = {}
            hotel_data['Nama Hotel'] = hotel_name

            # ... (Logika parsing nama, rating, lokasi) ...
            rating_element = hotel_element.find(attrs={'data-testid': 'tvat-ratingScore'})
            if rating_element:
                rating_text = rating_element.get_text(separator=" ", strip=True)
                hotel_data['Rating'] = rating_text
            else:
                hotel_data['Rating'] = 'N/A'

            lokasi_element = hotel_element.find(attrs={'data-testid': 'tvat-hotelLocation'})
            hotel_data['Lokasi'] = lokasi_element.text.strip() if lokasi_element else 'N/A'
            
            # === PENAMBAHAN BARU 1: TIPE PROPERTI ===
            # Mencari div yang berisi jenis properti (Hotel, Apartemen, dll.)
            properti_element = hotel_element.select_one("div.r-1vvnge1 div.r-1w9mtv9")
            hotel_data['Tipe Properti'] = properti_element.text.strip() if properti_element else 'N/A'

            # === PENAMBAHAN BARU 2: BINTANG HOTEL ===
            # Menemukan kontainer bintang dan menghitung jumlah ikon SVG di dalamnya
            bintang_container = hotel_element.find('div', attrs={'data-id': 'tvat-starRating'})
            if bintang_container:
                bintang_list = bintang_container.find_all('svg')
                hotel_data['Bintang Hotel'] = len(bintang_list)
            else:
                hotel_data['Bintang Hotel'] = 0

            # ... (Logika parsing gambar, harga, fasilitas) ...
            gambar_element = hotel_element.find('img', attrs={'data-testid': 'list-view-card-main-image'})
            hotel_data['URL Gambar'] = gambar_element.get('src', 'N/A') if gambar_element else 'N/A'
            harga_asli_element = hotel_element.find(attrs={'data-testid': 'tvat-originalPrice'})
            hotel_data['Harga Asli'] = harga_asli_element.text.strip() if harga_asli_element else 'N/A'
            harga_diskon_element = hotel_element.find(attrs={'data-testid': 'tvat-hotelPrice'})
            hotel_data['Harga Diskon'] = harga_diskon_element.text.strip() if harga_diskon_element else 'N/A'
            feature_elements = hotel_element.find_all('div', attrs={'data-testid': lambda x: x and x.startswith('hotel-feature-badge')})
            list_fasilitas = [feature.text.strip() for feature in feature_elements]
            hotel_data['Fasilitas'] = '; '.join(list_fasilitas)
            
            semua_hotel_data.append(hotel_data)
            processed_hotel_names.add(hotel_name)
    
    if new_data_found_in_this_pass:
        print(f"   -> Data baru ditemukan. Total hotel unik terkumpul: {len(semua_hotel_data)}")

    html.send_keys(Keys.END)
    time.sleep(random.uniform(3, 5))
    
    new_height = driver.execute_script("return document.body.scrollHeight")
    if new_height == last_height:
        scroll_attempts += 1
        print(f"   Tinggi halaman tidak berubah. Percobaan {scroll_attempts}/4...")
    else:
        scroll_attempts = 0
    last_height = new_height

print("\nScrolling selesai.")
driver.quit()

if semua_hotel_data:
    # Atur urutan kolom agar lebih rapi
    kolom = ['Nama Hotel', 'Tipe Properti', 'Bintang Hotel', 'Rating', 'Lokasi', 'Harga Diskon', 'Harga Asli', 'Fasilitas', 'URL Gambar']
    df = pd.DataFrame(semua_hotel_data, columns=kolom)
    df.to_csv(NAMA_FILE_CSV, index=False, encoding='utf-8')
    print(f"\nProses selesai! Data telah berhasil disimpan ke dalam file '{NAMA_FILE_CSV}'")
    print("\nContoh 5 data pertama:")
    print(df.head())
else:
    print("Tidak ada data hotel yang bisa diproses.")