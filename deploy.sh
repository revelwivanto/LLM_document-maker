# Update daftar paket server
sudo apt update

# Instal Python 3, manajer paket pip, venv (wajib), Nginx, dan Git
sudo apt install python3 python3-pip python3-venv nginx git

#### Langkah 2.2: Dapatkan Kode dan Siapkan Folder

```bash
# Buat folder untuk aplikasi Anda di /var/www (lokasi umum untuk web)
sudo mkdir -p /var/www/doc-generator
sudo chown $USER:$USER /var/www/doc-generator # Beri izin ke user Anda

# Clone repositori Anda (ganti dengan URL repo Anda)
git clone [https://github.com/username/repo-anda.git] /var/www/doc-generator

# Masuk ke folder aplikasi
cd /var/www/doc-generator

#### Langkah 2.3: Siapkan Lingkungan Python (Venv)

```bash
# Buat lingkungan virtual bernama 'venv'
python3 -m venv venv

# Aktifkan lingkungan tersebut
source venv/bin/activate

# Instal semua dependensi dari file requirements.txt
pip install -r requirements.txt

# Nonaktifkan (opsional, hanya untuk kembali ke shell utama)
deactivate

---

### Bagian 3: Menjalankan Aplikasi 24/7 (Service & Nginx)

# Ini adalah bagian paling penting. Kita akan memberi tahu server cara menjalankan aplikasi Anda secara otomatis dan cara menampilkannya ke pengguna.

#### Langkah 3.1: Buat `systemd` Service (Agar Tetap Berjalan)

#Ini adalah file yang akan menyimpan **rahasia (environment variables)** Anda dan menjalankan aplikasi Anda.

#Buat file service baru:
`sudo nano /etc/systemd/system/docgen.service`

Salin dan tempel konten berikut. **ANDA HARUS MENGEDIT BAGIAN `Environment=`!**

```ini
[Unit]
Description=Streamlit Document Generator App
After=network.target

[Service]
User=root # Ganti dengan username Anda jika Anda tidak menjalankan sebagai root
WorkingDirectory=/var/www/doc-generator # Path ke folder proyek Anda

# --- PENTING: SET RAHASIA ANDA DI SINI ---
Environment="STREAMLIT_SERVER_PORT=8501"
Environment="GEMINI_API_KEY=AIzaSyDwpv0KP6FezXRfhQiR3rJ6jsErfDN7M_0"
Environment="APPS_SCRIPT_WEB_APP_URL=https://script.google.com/macros/s/AKfy.../exec"
Environment="GSHEET_URL=https://docs.google.com/spreadsheets/d/..."
# Ini adalah bagian yang rumit. Anda perlu mengubah kredensial GSheet JSON Anda menjadi SATU BARIS string
# Gunakan alat online "JSON minifier" untuk mengubah file JSON kredensial Anda menjadi satu baris
Environment="GCP_SERVICE_ACCOUNT_JSON={\"type\": \"service_account\", \"project_id\": \"...\", ...}"

# Perintah untuk menjalankan aplikasi di dalam venv
ExecStart=/var/www/doc-generator/venv/bin/streamlit run streamlit_app.py --server.runOnSave false --server.headless true

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target

#### Langkah 3.2: Konfigurasi `Nginx` (Agar Bisa Diakses)

Buat file konfigurasi Nginx baru:
`sudo nano /etc/nginx/sites-available/doc-generator`

Salin dan tempel konten berikut. Ganti `your_server_ip_or_domain` dengan alamat IP server Anda.

```nginx
server {
    listen 80;
    server_name your_server_ip_or_domain; # Ganti ini

    location / {
        proxy_pass http://127.0.0.1:8501; # Arahkan ke Streamlit
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Host $host;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade"; # Wajib untuk Streamlit
        proxy_read_timeout 86400;
    }
}

#### Langkah 3.3: Aktifkan Semuanya

```bash
# 1. Aktifkan situs Nginx baru
sudo ln -s /etc/nginx/sites-available/doc-generator /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default # Hapus situs default jika ada

# 2. Muat ulang konfigurasi
sudo systemctl daemon-reload

# 3. Mulai aplikasi Anda
sudo systemctl start docgen.service

# 4. Atur agar aplikasi berjalan saat startup
sudo systemctl enable docgen.service

# 5. Restart Nginx untuk menerapkan perubahan
sudo systemctl restart nginx

Selesai! Sekarang Anda seharusnya bisa membuka browser dan mengetik alamat IP server Anda (`http://your_server_ip_or_domain`) dan melihat aplikasi Streamlit Anda berjalan.