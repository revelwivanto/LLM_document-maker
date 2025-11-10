import streamlit as st
import json
import os
import re
import io
import requests
from pypdf import PdfReader
from streamlit_pdf_viewer import pdf_viewer
import google.generativeai as genai
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from google.oauth2.service_account import Credentials
import ast

conn = st.connection("gsheets", type=GSheetsConnection)

TARGET_PDF_TEMPLATES_PENGADAAN_LESS_300 = [ 
    os.path.join("templates", "Nota dinas izin prinsip(SVP)", "Nota dinas Izin Prinsip Pengadaan(SVP).pdf"),
    os.path.join("templates", "Nota dinas izin prinsip", "Nota dinas Izin Prinsip Pengadaan_D.bidang.pdf"),
    os.path.join("templates", "RAB", "RAB", "RAB Pengadaan.pdf"),
    os.path.join("templates", "RAB", "RKS", "RKS Pengadaan.pdf")
    
]
TARGET_PDF_TEMPLATES_PENGADAAN_MORE_300 = [ 
    os.path.join("templates", "RAB", "RAB Dir. Bidang", "RAB Pengadaan.pdf"),
    os.path.join("templates", "RAB", "RKS Dir. Bidang", "RKS Pengadaan.pdf"),
    os.path.join("templates", "Review Pekerjaan", "Review Pengajuan Pekerjaan Pengadaan Barang.pdf") #done
]

TARGET_PDF_TEMPLATES_LISENSI_MORE_300 = [ # blm
    os.path.join("templates", "RAB", "RAB Dir. Bidang", "RAB Lisensi.pdf"),
    os.path.join("templates", "RAB", "RKS Dir. Bidang", "RKS Lisensi.pdf")
]
TARGET_PDF_TEMPLATES_LISENSI_LESS_300 = [
    os.path.join("templates", "Nota dinas izin prinsip(SVP)", "Nota dinas Izin Prinsip Pengadaan(SVP).pdf"),
    os.path.join("templates", "Nota dinas izin prinsip", "Nota dinas Izin Prinsip Pengadaan_D.bidang.pdf"),
    os.path.join("templates", "RAB", "RAB", "RAB Pengadaan.pdf"),
    os.path.join("templates", "RAB", "RKS Dir. Bidang", "RKS Lisensi.pdf")
]

# --- Konfigurasi & Inisialisasi ---
st.set_page_config(page_title="Generator Dokumen Cerdas", page_icon="📝", layout="wide")

# --- Custom Modern Styling (visual only, no functional changes) ---
st.markdown(
    '''
    <style>
    /* Background and container card */
    .stApp {
        background: linear-gradient(120deg, #f9fafc 0%, #f1f6fa 100%);
        color: #222;
    }
    section[data-testid="stSidebar"] {
        background-color: #f6fbff !important;
    }
    /* Card effect for forms and main panels */
    div[class*="stForm"] {
        background: #fff !important;
        border-radius: 18px;
        padding: 2rem 2.2rem;
        box-shadow: 0 6px 32px #19537515;
        border: 1.5px solid #ecf3fc;
        margin-bottom: 24px;
    }
    /* Headings */
    h1, h2, h3, h4 {
        color: #195375;
        letter-spacing: 0.5px;
    }
    /* Buttons */
    button[kind="primary"] {
        background: linear-gradient(90deg, #318af2 0%, #56c7ff 100%) !important;
        color: #fff !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 12px #318af236;
        border: none !important;
        font-weight: 600;
    }
    button[kind="secondary"] {
        background: #fff !important;
        border: 1.2px solid #56c7ff !important;
        border-radius: 8px !important;
        color: #318af2 !important;
    }
    /* Text Input and Text Area */
    input, textarea {
        background-color: #f7fafc !important;
        border-radius: 7px !important;
        border: 1px solid #cbdbfc !important;
        padding: 8px 12px !important;
        transition: box-shadow 0.18s;
        font-size: 1rem;
    }
    input:focus, textarea:focus {
        outline: none !important;
        border-color: #67c3f3 !important;
        box-shadow: 0 0 0 2px #67c3f342 !important;
    }
    /* File Uploader dropzone */
    div[data-testid="stFileDropzone"] {
        border: 2px dashed #318af2 !important;
        background-color: #f0f5fd !important;
        border-radius: 10px !important;
    }
    /* Expander panels */
    div[data-testid="stExpander"] > div:first-child {
        background: #f4fafd !important;
        border-radius: 8px;
        border: 1px solid #e2eefc;
    }
    /* Info/Warning boxes */
    div[data-testid="stAlertInfo"] {
        background-color: #e3f0fd !important;
        color: #153e5c !important;
    }
    div[data-testid="stAlertWarning"] {
        background-color: #fff7df !important;
        color: #9b5d06 !important;
    }
    .st-b5 {
        font-size: 1.16rem !important;
    }
    /* Secondary tweaks as needed */
    </style>
    ''', unsafe_allow_html=True)

# Konfigurasi API Key Gemini (PENTING: Gunakan Streamlit Secrets saat deploy)
try:
    # Coba muat API key dari secrets (untuk deployment)
    api_key =st.secrets.get("GEMINI_API") # GANTIKAN DENGAN st.secrets["GEMINI_API"] SAAT DEPLOY
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash') # Menggunakan model yang lebih baru jika tersedia
except (KeyError, FileNotFoundError):
    # Fallback jika secrets tidak ada (misalnya saat testing lokal)
    st.warning("GEMINI_API tidak ditemukan di Streamlit Secrets. Pastikan Anda telah mengkonfigurasinya untuk deployment.")
    st.error("Model AI tidak dapat dikonfigurasi. Aplikasi tidak dapat melanjutkan.")
    model = None # Set model ke None jika konfigurasi gagal

# Inisialisasi session state
if 'page' not in st.session_state: st.session_state.page = "initial_input"
if 'recipe' not in st.session_state: st.session_state.recipe = None
if 'initial_data' not in st.session_state: st.session_state.initial_data = {"prompt": "", "files": {}}
if 'ai_extracted_data' not in st.session_state: st.session_state.ai_extracted_data = None
if 'final_json' not in st.session_state: st.session_state.final_json = None
if 'gsheet_data' not in st.session_state: st.session_state.gsheet_data = None # To store the DataFrame
if 'ai_matches' not in st.session_state: st.session_state.ai_matches = None # To store matching titles
if 'budget' not in st.session_state: st.session_state.budget = None

# --- Fungsi-fungsi Inti ---

@st.cache_data

def analyze_budget_with_llm(text_description):
    """
    Menggunakan LLM (Gemini) untuk menganalisis deskripsi teks,
    menghitung total estimasi, dan mengembalikan HANYA ANGKA.
    """
    if not model or not text_description:
        return None

    prompt = f"""
    Analisis deskripsi berikut untuk menentukan total estimasi budget pengadaan utama dalam Rupiah.
    Fokus pada angka budget utama, bukan RKA P atau nilai kontrak lama.
    Lakukan perhitungan jika diperlukan (misal: harga per unit dikali jumlah unit).

    CONTOH:
    - Input: "budget 10jt untuk 20 users"
      Output: 200000000
    - Input: "total biaya sekitar 500 juta rupiah"
      Output: 500000000
    - Input: "harganya 500 ribu per lisensi, kami butuh 10"
      Output: 5000000
    - Input: "perpanjangan adobe 17.5 jt"
      Output: 17500000
    - Input: "proyek ini tidak ada budgetnya"
      Output: null

    Deskripsi Pengguna: "{text_description}"

    ATURAN OUTPUT SANGAT PENTING:
    1. Respon Anda HARUS salah satu dari ini: ANGKA total budget (misal: 17500000) atau kata 'null'.
    2. JANGAN sertakan teks penjelasan.
    3. JANGAN sertakan 'Rp', 'juta', 'ribu', titik, koma, atau format mata uang APAPUN.
    4. JANGAN jelaskan cara Anda menghitung.
    5. KEMBALIKAN HANYA ANGKA (sebagai string) ATAU 'null'.
    """

    try:
        response = model.generate_content(prompt)
        # Ambil teks mentah, hapus spasi, dan jadikan huruf kecil
        result_text = response.text.strip().lower()

        if result_text == 'null' or not result_text:
            return None
        else:
            # Coba konversi langsung. Jika gagal, berarti AI tidak mengikuti aturan.
            try:
                # Hapus spasi ekstra jika ada (misal: "17 500 000" -> "17500000")
                cleaned_num_str = re.sub(r'\s', '', result_text)
                return float(cleaned_num_str) # Langsung konversi
            except ValueError:
                # AI Gagal mengikuti aturan. Tampilkan error.
                st.error(f"Terjadi kesalahan saat analisis budget: AI mengembalikan teks yang tidak valid (bukan angka atau 'null'). Respons AI: '{result_text}'")
                return None

    except Exception as e:
        st.error(f"Terjadi kesalahan fatal saat memanggil AI budget: {e}")
        if 'response' in locals():
            st.text_area("Teks mentah dari AI (Budget Analysis):", value=response.text)
        return None

def load_recipe(template_path):
    """Memuat file resep .json berdasarkan path file template .pdf."""
    # Mengganti ekstensi .pdf (atau .PDF) dengan .json
    recipe_path = os.path.splitext(template_path)[0] + ".json"
    try:
        with open(recipe_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error(f"File resep tidak ditemukan di: {recipe_path}")
        return None
    except Exception as e:
        st.error(f"Gagal memuat file resep '{os.path.basename(recipe_path)}': {e}")
        return None

def run_ai_first_pass(initial_prompt, file_uploads, all_placeholders, all_examples):
    """
    Membangun prompt, memanggil AI, dan mengekstrak data JSON awal,
    dengan tambahan output debugging.
    """
    if not model:
        st.error("Model AI tidak dikonfigurasi.")
        return {"error": "MODEL_AI_TIDAK_TERKONFIGURASI"}

    # --- TAMBAHAN DEBUGGING: Periksa nilai initial_prompt ---
    st.warning(f"DEBUG: Nilai 'initial_prompt' yang diterima fungsi: '{initial_prompt}'")
    # --- AKHIR TAMBAHAN DEBUGGING ---

    # Pastikan initial_prompt adalah string, meskipun kosong
    prompt_text = initial_prompt if initial_prompt else ""

    # --- Bagian Konstruksi Prompt (Sama seperti sebelumnya, tapi gunakan prompt_text) ---
    json_format_string = json.dumps({key: "..." for key in all_placeholders if not key.endswith('_CALCULATED')}, indent=2)
    context_text = ""
    for upload_id, uploaded_file in file_uploads.items():
        if uploaded_file:
            file_content = get_text_from_file(uploaded_file)
            if file_content:
                 context_text += f"\n\n--- KONTEKS DARI DOKUMEN '{upload_id}' ---\n{file_content}"
            else:
                 st.warning(f"File '{upload_id}' diunggah tetapi tidak ada teks yang bisa diekstrak.")

    combined_examples_str = json.dumps(all_examples, indent=2)

    # --- PERUBAHAN: Pastikan f-string menggunakan variabel prompt_text ---
    prompt = f"""
    Anda adalah asisten AI yang sangat teliti, bertugas mengekstrak informasi sebanyak mungkin dari teks untuk mengisi beberapa dokumen resmi terkait.

    TUGAS UTAMA:
    Berdasarkan konteks utama dan dokumen pendukung, coba isi sebanyak mungkin field dalam format JSON di bawah ini. Field ini adalah gabungan dari beberapa dokumen yang akan dibuat.

    KONTEKS UTAMA DARI PENGGUNA:
    prompt utama: "{prompt_text}"
    context pendukung: {context_text}

    CONTOH LENGKAP OUTPUT YANG DIHARAPKAN (Ini adalah gabungan contoh, gunakan sebagai referensi gaya, panjang, dan format):
    ```json
    {combined_examples_str}
    ```

    ATURAN PENTING:
    1.  Fokus untuk mengisi field dalam format JSON ini: {json_format_string}.
    2.  Jika Anda benar-benar tidak dapat menemukan informasi untuk sebuah field, JANGAN sertakan field tersebut.
    3.  Output HARUS berupa objek JSON yang valid.
    4.  Jangan sertakan penjelasan atau markdown (seperti ```json). HANYA objek JSON.
    5.  Gunakan NAMA FIELD (key) persis seperti yang diminta.
    6.  Untuk field numerik, kembalikan ANGKA (integer/float), bukan string.
    7.  Untuk field "Bukti_BA" dan "Pembelian", HARUS berupa ARRAY (list) dari OBJECTS JSON [{{ "NO": ..., "OBJEK": ..., "JUMLAH": ..., "DETAIL": ... }}].
    8.  Jangan menggunakan kapital diawal kalimat, kecuali untuk singkatan
    9.  Jangan memberi '.' diakhir kalimat
    10. parafrase sebanyak mungkin untuk response kalimat, guna menghindari plagiasi dari konteks yang diberikan, kecuali untuk fileld yang memang meminta nomor, nama spesifik atau Title.
    11. Prompt utama adalah sumber informasi utama, gunakan konteks pendukung hanya jika informasi tidak ada di prompt utama.
    12. Apabila contoh ada '/n', maka itu line break yang dianjurkan ada disuatu placeholder.
    """

    # --- Bagian Debugging & Panggilan AI (Sama seperti sebelumnya) ---
    with st.expander("👀 Lihat Prompt Lengkap yang Dikirim ke AI"):
        st.code(prompt, language='markdown')

    raw_response_text = None
    try:
        response = model.generate_content(prompt)
        if response and response.parts:
            raw_response_text = response.parts[0].text
        elif response and hasattr(response, 'text'):
            raw_response_text = response.text
        elif response and response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            raw_response_text = response.candidates[0].content.parts[0].text
        else:
            raw_response_text = "Respons AI tidak memiliki teks yang dapat dibaca."

        with st.expander("👀 Lihat Respons Mentah dari AI"):
             st.text(raw_response_text if raw_response_text else "Tidak ada respons teks.")

        if not raw_response_text or raw_response_text == "Respons AI tidak memiliki teks yang dapat dibaca.":
             st.error("AI tidak mengembalikan teks respons.")
             return {"error": "AI tidak mengembalikan teks."}

        json_string = raw_response_text.strip().replace("```json", "").replace("```", "").strip()

        if not json_string:
             st.error("Setelah dibersihkan, respons AI kosong.")
             return {"error": "Respons AI kosong setelah dibersihkan."}

        parsed_json = json.loads(json_string)
        return parsed_json

    except json.JSONDecodeError as json_err:
        error_message = f"Gagal mem-parse JSON dari AI: {json_err}. Respons mentah ada di atas."
        st.error(error_message)
        return {"error": error_message}
    except Exception as e:
        error_message = f"Terjadi kesalahan saat memanggil atau memproses respons AI: {e}"
        st.error(error_message)
        return {"error": error_message}

def get_text_from_file(uploaded_file):
    if uploaded_file is None:
        return ""
    full_text = ""
    try:
        file_bytes = uploaded_file.getvalue()
        if uploaded_file.type == "application/pdf":
            reader = PdfReader(io.BytesIO(file_bytes))
            for page in reader.pages:
                if page.extract_text():
                    full_text += page.extract_text() + "\n"
        elif uploaded_file.type == "text/plain":
            full_text = file_bytes.decode("utf-8")
    except Exception as e:
        st.warning(f"Gagal membaca file {uploaded_file.name}: {e}")
    return full_text.strip()

def perform_calculations(recipe_placeholders, final_data):
    """
    Melakukan perhitungan matematis, membersihkan format mata uang,
    memberikan pesan error yang jelas, dan menangani dependensi antar kalkulasi.
    """
    def clean_currency(value):
        """Membersihkan string (termasuk format IDR,-) menjadi float, atau mengembalikan float/int asli."""
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            cleaned_value = re.sub(r'(IDR|\s|,-?$)', '', value)
            if cleaned_value.isdigit():
                return float(cleaned_value)
        st.warning(f"Nilai '{value}' tidak dapat dibersihkan menjadi angka.")
        return None

    # Iterasi melalui placeholder di resep
    for key, value in recipe_placeholders.items():
        if key.endswith("_CALCULATED"):
            base_key = key.replace("_CALCULATED", "") # Nama key hasil (misal: Sisa_anggaran_proyek)
            formula_string = value # value adalah string formula (misal: "Budget_2025 - Terpakai")
            local_vars = {} # Variabel lokal untuk eval()
            variables_needed = re.findall(r'\b([A-Za-z_][A-Za-z0-9_]*)\b', formula_string)
            valid_formula = True
            missing_vars_details = []

            # Periksa ketersediaan dan validitas setiap variabel yang dibutuhkan
            for var_name in variables_needed:
                # PENTING: Cek di final_data (yang diupdate terus menerus)
                if var_name in final_data:
                    numeric_value = clean_currency(final_data[var_name])
                    if numeric_value is not None:
                        local_vars[var_name] = numeric_value
                    else:
                        missing_vars_details.append(f"'{var_name}' (nilai '{final_data[var_name]}' tidak valid)")
                        valid_formula = False; break # Hentikan jika nilai tidak valid
                else:
                    missing_vars_details.append(f"'{var_name}' (tidak ditemukan)")
                    valid_formula = False; break # Hentikan jika variabel tidak ditemukan

            # Lakukan perhitungan hanya jika semua variabel valid
            if valid_formula:
                try:
                    result = eval(formula_string, {"__builtins__": None}, local_vars)
                    # --- PERUBAHAN KRUSIAL: Update final_data DI DALAM LOOP ---
                    final_data[base_key] = result # Simpan hasil langsung ke data utama
                except Exception as e:
                    st.error(f"Gagal melakukan kalkulasi untuk '{base_key}': {e}")
                    final_data[base_key] = f"ERROR_CALCULATION: {e}" # Simpan error ke data utama
            else:
                 # Simpan error missing vars ke data utama
                final_data[base_key] = f"ERROR_MISSING_VARS: {', '.join(missing_vars_details)}"

    # Fungsi sekarang langsung memodifikasi dan mengembalikan final_data
    return final_data

def format_for_gdocs(value):
    """
    Memformat angka menjadi string format Indonesia (misal: 1.000.000 atau 1.234,56).
    Membiarkan nilai non-numerik apa adanya.
    """
    if isinstance(value, int):
        # Format integer: 1000000 -> "1.000.000"
        return f"{value:,}".replace(",", ".")
    if isinstance(value, float):
        # Format float: 1234.56 -> "1.234,56" (format 2 desimal)
        # 1,234.56 (Inggris) -> 1X234.56 -> 1X234,56 -> 1.234,56 (Indonesia)
        return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    
    # Kembalikan nilai asli jika bukan int or float (misal: string, list, dll)
    return value

@st.cache_data(ttl=600) # Cache data for 10 minutes
def load_gsheet_data(sheet_url):
    """Membaca data dari Google Sheet menggunakan st.connection."""
    try:
        # PENTING: Pastikan Anda sudah menginisialisasi conn di awal script:
        # conn = st.connection("gsheets", type=GSheetsConnection)
        st.info(f"Mencoba membuka Google Sheet via st.connection: {sheet_url}")
        df = conn.read(
            spreadsheet=sheet_url,  # URL sheet Anda dari secrets
            worksheet=0,            # Mengambil sheet pertama
            ttl=600                 # Cache
        )
        if df.empty:
            st.warning("Google Sheet berhasil dimuat, tetapi tidak ada data.")
        else:
            st.success(f"Berhasil memuat {len(df)} baris data dari Google Sheet.")
        return df
    except Exception as e:
        st.error(f"Gagal memuat data dari Google Sheet via st.connection: {e}")
        # Periksa konfigurasi secrets.toml [connections.gsheets]
        st.error("Pastikan konfigurasi `[connections.gsheets]` di secrets.toml sudah benar "
                 "dan Service Account memiliki akses ke Sheet.")
        return None

def find_prompt_matches_with_llm(user_prompt, gsheet_titles):
    """Menggunakan LLM untuk mencocokkan prompt pengguna dengan judul dari GSheet."""
    if not model or not user_prompt or not gsheet_titles:
        return {"matches": []}

    titles_list_str = "\n".join([f"- {title}" for title in gsheet_titles])
    prompt = f"""
    Anda adalah asisten pencocokan proyek. Bandingkan permintaan pengguna dengan daftar judul proyek di bawah ini. Identifikasi judul proyek mana saja yang paling mungkin cocok.

    Permintaan Pengguna:
    "{user_prompt}"

    Daftar Judul Proyek dari Spreadsheet:
    {titles_list_str}

    ATURAN RESPON:
    1. Respon HANYA dengan objek JSON yang valid.
    2. Objek JSON harus memiliki satu key: "matches".
    3. Nilai dari "matches" harus berupa LIST (array) berisi string judul proyek yang cocok PERSIS seperti yang ada di daftar.
    4. Jika tidak ada kecocokan yang kuat, kembalikan list kosong: {{"matches": []}}.
    5. Jika ada beberapa kecocokan yang kuat, sertakan SEMUA judul yang cocok dalam list.
    6. Jangan sertakan penjelasan atau teks lain di luar objek JSON.
    """
    try:
        # ... (kode panggilan AI dan parsing JSON seperti di versi sebelumnya) ...
        response = model.generate_content(prompt)
        json_string = response.text.strip().replace("```json", "").replace("```", "")
        parsed_json = json.loads(json_string)
        if isinstance(parsed_json, dict) and "matches" in parsed_json and isinstance(parsed_json["matches"], list):
             valid_matches = [match for match in parsed_json["matches"] if match in gsheet_titles]
             return {"matches": valid_matches}
        else:
             st.warning("AI mengembalikan format JSON pencocokan yang tidak diharapkan.")
             return {"matches": []}
    except Exception as e:
        st.error(f"Error saat mencocokkan prompt dengan AI: {e}")
        return {"matches": []}

def augment_prompt_with_gsheet_data(original_prompt, selected_row_data):
    """Menambahkan data dari baris GSheet ke prompt asli."""
    augmented_prompt = original_prompt + "\n\n--- Data Tambahan dari Spreadsheet ---"
    for col, value in selected_row_data.items():
        if pd.notna(value) and value != '' and col.lower() != 'title':
            augmented_prompt += f"\n{col}: {value}"
    return augmented_prompt

# --- Tampilan & Logika Aplikasi (State Machine) ---
st.title("AI Document Generator")

# --- LANGKAH 1: INPUT AWAL & INTEGRASI GSHEET ---
if st.session_state.page == "initial_input":
    st.header("Langkah 1: Jelaskan Kebutuhan Anda")

    # Tombol untuk memuat data GSheet (di luar form)
    # st.info("Anda dapat memuat data proyek dari Google Sheet untuk membantu AI.")
    # use_gsheet = st.toggle("Aktifkan Pencarian Data Proyek di Google Sheet", value=True, key="use_gsheet_toggle")

    # if use_gsheet:
    #     # Tampilkan tombol load hanya jika GSheet belum dimuat atau ingin di-refresh
    #     if 'gsheet_data' not in st.session_state or st.session_state.gsheet_data is None:
    #     #     if st.button(" Muat/Refresh Data Proyek dari Google Sheet"):
    #     #         gsheet_url = st.secrets.get("GSHEET_URL")
    #     #         if not gsheet_url:
    #     #             st.error("URL Google Sheet (GSHEET_URL) tidak ditemukan di Streamlit Secrets.")
    #     #         else:
    #     #             with st.spinner("Mengambil data dari Google Sheet..."):
    #     #                 df = load_gsheet_data(gsheet_url)
    #     #                 st.session_state.gsheet_data = df # Simpan DataFrame ke session state
    #     #                 if df is not None:
    #     #                     st.success("Data Google Sheet berhasil dimuat.")
    #     # else: error sudah ditampilkan oleh load_gsheet_data

    #     # Tampilkan status data GSheet jika sudah dimuat
    #     elif st.session_state.gsheet_data is not None:
    #     #     st.success(f"Data Google Sheet ({len(st.session_state.gsheet_data)} baris) sudah dimuat.")
    #     #     if st.button("Refresh Data"): # Tombol refresh jika data sudah ada
    #     #         # Clear cache dan muat ulang
    #     #         load_gsheet_data.clear()
    #     #         gsheet_url = st.secrets.get("GSHEET_URL")
    #     #         if gsheet_url:
    #     #             with st.spinner("Memuat ulang data dari Google Sheet..."):
    #     #                 st.session_state.gsheet_data = load_gsheet_data(gsheet_url)

    # Form untuk input pengguna
    with st.form("initial_input_form", clear_on_submit=False): # Keep clear_on_submit=False
        st.info("Masukkan deskripsi kebutuhan Anda, termasuk estimasi budget.")
        # Berikan key unik ke text_area DAN simpan widget ke variabel
        initial_prompt_input = st.text_area( # <-- Simpan widget ke variabel ini
            "Deskripsi Kebutuhan:",
            height=150,
            placeholder="Contoh: pengadaan fasilitas perangkat laptop penunjang kinerja personil TI Prognosa 2025 100jt. Terpakai 0. Usulan anggaran 17,5jt. Anggaran kalimat tujuh belas koma lima juta. Pos Anggaran VI. 3 (Biaya Perbaikan Aplikasi Infrastruktur). Tanggal 10 Oktober 2025. Rkap 2025 26.401.000.000. Nilai Kontrak po 2025 20.850.959.696. pr 1.165.000.000. budget pembuatan rab & rks 1.628.894.000. harga pembelian 22 jt. pembatalan garansi dilakukan apabila terjadi kelalaian pegawai yang akan ditanggung oleh PT TPS. Contract execution 1 bulan",
            key="prompt_input_key" # Key tetap ada, berguna nanti
        )
        uploaded_files_list = st.file_uploader(
            "Unggah Dokumen Pendukung Apapun (Opsional, .pdf atau .txt)",
            type=['pdf', 'txt'], accept_multiple_files=True, key="initial_uploader"
        )
        submitted = st.form_submit_button("Analisis & Lanjut ke Pemrosesan Dokumen")

        if submitted:
            prompt_value_from_input = initial_prompt_input

            if not prompt_value_from_input: # Periksa nilai yang didapat dari widget
                st.warning("Harap isi deskripsi kebutuhan.")
            else:
                # Lakukan analisis budget dengan LLM menggunakan nilai yang benar
                with st.spinner("Menganalisis budget dengan AI..."):
                    budget = analyze_budget_with_llm(prompt_value_from_input) # Gunakan nilai dari widget
                st.session_state.budget = budget

                # Simpan data input awal (gunakan nilai yang sudah dibaca)
                uploaded_files_dict = {f.name: f for f in uploaded_files_list} if uploaded_files_list else {}
                st.session_state.initial_data = {
                    "prompt": prompt_value_from_input, # Simpan nilai yang benar
                    "files": uploaded_files_dict
                }

                # --- LOGIKA PENCOCOKAN GSHEET ---
                gsheet_enabled = st.session_state.get("use_gsheet_toggle", False)
                gsheet_df = st.session_state.get("gsheet_data")

                if gsheet_enabled and gsheet_df is not None and not gsheet_df.empty and 'Title' in gsheet_df.columns:
                    st.info("Fitur Google Sheet aktif, mencoba mencocokkan...") # Info tambahan
                    with st.spinner("AI sedang mencocokkan permintaan Anda dengan data proyek..."):
                        gsheet_titles = gsheet_df['Title'].dropna().astype(str).tolist()
                        
                        ai_match_response = find_prompt_matches_with_llm(prompt_value_from_input, gsheet_titles)
                    matches = ai_match_response.get("matches", [])
                    st.session_state.ai_matches = matches # Simpan hasil pencocokan

                    if matches:
                        st.session_state.page = "disambiguation" # Pindah ke halaman konfirmasi
                    else:
                        st.info("Tidak ditemukan data proyek yang cocok di Google Sheet.")
                        st.session_state.page = "load_recipes_and_process" # Lanjut tanpa konfirmasi
                else: # Lanjut tanpa pencocokan
                    if gsheet_enabled and (gsheet_df is None or gsheet_df.empty or 'Title' not in gsheet_df.columns):
                         st.warning("Pencarian Google Sheet diaktifkan, tetapi data belum dimuat/kosong/tidak valid.")
                    ## st.info("Melanjutkan tanpa menggunakan data dari Google Sheet.")
                    st.session_state.page = "load_recipes_and_process"

elif st.session_state.page == "disambiguation":
    st.header("Konfirmasi Proyek Terkait")
    st.info("AI menemukan kemungkinan proyek terkait di Google Sheet berdasarkan permintaan Anda.")
    
    matches = st.session_state.get("ai_matches", [])
    gsheet_df = st.session_state.get("gsheet_data")
    
    if not matches or gsheet_df is None:
        st.error("Data pencocokan tidak ditemukan. Kembali ke awal.")
        if st.button("Kembali"): st.session_state.page = "initial_input"; st.rerun()
        st.stop()

    # Tambahkan opsi "Bukan salah satu di atas"
    options = matches + ["Bukan salah satu di atas / Permintaan Baru"]
    
    # Gunakan radio button jika sedikit pilihan, selectbox jika banyak
    if len(options) <= 5:
        selected_title = st.radio("Manakah proyek yang Anda maksud?", options, index=0, key="match_selector")
    else:
        selected_title = st.selectbox("Manakah proyek yang Anda maksud?", options, index=0, key="match_selector")

    if st.button("Konfirmasi Pilihan & Lanjutkan"):
        augmented_prompt = st.session_state.initial_data["prompt"] # Mulai dengan prompt asli

        if selected_title != "Bukan salah satu di atas / Permintaan Baru":
            # Cari baris data yang sesuai di DataFrame
            selected_row = gsheet_df[gsheet_df['Title'] == selected_title].iloc[0]
            # Augmentasi prompt
            augmented_prompt = augment_prompt_with_gsheet_data(augmented_prompt, selected_row)
            st.success(f"Data dari proyek '{selected_title}' akan ditambahkan ke konteks.")
            # Tampilkan data yang ditambahkan (opsional)
            with st.expander("Lihat Data yang Ditambahkan"):
                 st.dataframe(selected_row.to_frame().T) # Tampilkan sebagai tabel kecil
        else:
            st.info("Melanjutkan hanya dengan deskripsi awal Anda.")

        # Update prompt di initial_data sebelum lanjut
        st.session_state.initial_data["prompt"] = augmented_prompt
        # Lanjut ke tahap pemuatan resep
        st.session_state.page = "load_recipes_and_process"
        st.rerun()

    st.write("---")
    if st.button("Batalkan & Kembali ke Input Awal"):
        st.session_state.page = "initial_input"
        # Reset state yang relevan
        st.session_state.ai_matches = None
        st.rerun()

# --- LANGKAH 1.8 (DIMODIFIKASI): Tentukan & Muat Resep yang Relevan ---
elif st.session_state.page == "load_recipes_and_process":
    
    # Ambil data yang dibutuhkan untuk membuat keputusan
    budget = st.session_state.get('budget')
    # Ambil prompt yang mungkin sudah di-augmentasi oleh GSheet
    prompt_text = st.session_state.initial_data.get("prompt", "").lower()

    target_templates_to_load = [] # List kosong untuk diisi
    
    st.info(f"Menganalisis kondisi...")
    st.caption(f"Budget terdeteksi: {budget}")
    st.caption(f"Prompt (awal): {prompt_text[:70]}...")

    # --- Logika Pemilihan Template Dinamis ---
    if budget is None:
        st.error("Budget tidak dapat terdeteksi dari deskripsi Anda. Tidak dapat melanjutkan.")
        if st.button("Kembali ke Input Awal"):
            st.session_state.page = "initial_input"; st.rerun()
        st.stop()
    
    elif budget >= 300_000_000:
        if "lisensi" in prompt_text:
            print("Kondisi terdeteksi: Budget >= 300jt, Tipe 'Lisensi'.")
            target_templates_to_load = TARGET_PDF_TEMPLATES_LISENSI_MORE_300
        elif "pengadaan" in prompt_text:
            print("Kondisi terdeteksi: Budget >= 300jt, Tipe 'Pengadaan'.")
            target_templates_to_load = TARGET_PDF_TEMPLATES_PENGADAAN_MORE_300
        else:
            print(f"Budget >= 300jt, tapi kata kunci 'lisensi'/'pengadaan' tidak ditemukan. Menggunakan default 'Pengadaan >= 300jt'.")
            target_templates_to_load = TARGET_PDF_TEMPLATES_PENGADAAN_MORE_300 # Default jika > 300jt
    
    else: # Budget < 300,000,000
        if "lisensi" in prompt_text:
            print("Kondisi terdeteksi: Budget < 300jt, Tipe 'Lisensi'. Menggunakan default 'Pengadaan < 300jt' (sebelum ada aturan spesifik).")
            # Default ke pengadaan < 300jt jika tidak ada aturan untuk lisensi < 300jt
            target_templates_to_load = TARGET_PDF_TEMPLATES_LISENSI_LESS_300
        elif "pengadaan" in prompt_text:
            print("Kondisi terdeteksi: Budget < 300jt, Tipe 'Pengadaan'.")
            target_templates_to_load = TARGET_PDF_TEMPLATES_PENGADAAN_LESS_300
        else:
            print("Budget < 300jt, tapi kata kunci tidak ditemukan. Menggunakan default 'Pengadaan < 300jt'.")
            target_templates_to_load = TARGET_PDF_TEMPLATES_PENGADAAN_LESS_300 # Default jika < 300jt

    if not target_templates_to_load:
         st.error("Tidak ada set template yang cocok dengan kondisi Anda. Proses dihentikan.")
         if st.button("Kembali"): st.session_state.page = "initial_input"; st.rerun()
         st.stop()

    # --- Loop Pemuatan Resep (Sekarang menggunakan list dinamis) ---
    loaded_recipes = {}
    all_recipes_valid = True
    with st.spinner(f"Memuat {len(target_templates_to_load)} resep dokumen yang dipilih..."):
        for pdf_path in target_templates_to_load: # Menggunakan variabel dinamis
            recipe_data = load_recipe(pdf_path)
            if recipe_data:
                loaded_recipes[pdf_path] = recipe_data
            else:
                st.error(f"Gagal memuat resep untuk {os.path.basename(pdf_path)}. Proses dihentikan.")
                all_recipes_valid = False
                break

    if all_recipes_valid:
        st.session_state.recipes_to_process = loaded_recipes
        st.session_state.page = "processing" # Lanjut ke pemrosesan AI
        # Reset state AI/JSON sebelumnya
        st.session_state.ai_extracted_data = None
        st.session_state.final_combined_data = None
        st.rerun()
    else:
        # Jika resep gagal dimuat, beri opsi kembali
        if st.button("Kembali ke Input Awal"):
             st.session_state.page = "initial_input"; st.rerun()
        st.stop()
        
# --- LANGKAH 2: PEMROSESAN AI & VERIFIKASI GABUNGAN ---
elif st.session_state.page == "processing":
    st.header("Verifikasi & Lengkapi Data Gabungan")

    # Pastikan resep sudah dimuat dari langkah sebelumnya
    if not st.session_state.get('recipes_to_process'):
        st.error("Resep dokumen tidak ditemukan. Kembali ke langkah awal.")
        if st.button("Kembali"): st.session_state.page = "initial_input"; st.rerun()
        st.stop()

    # --- Gabungkan Placeholders & Examples dari semua resep ---
    all_placeholders = {}
    all_examples = {}
    valid_recipes = True # Asumsikan valid karena sudah dicek saat load
    # Gabungkan placeholder unik dan contoh unik
    for pdf_path, recipe_data in st.session_state.recipes_to_process.items():
        # Validasi lagi untuk keamanan
        if not recipe_data or "placeholders" not in recipe_data or "examples" not in recipe_data:
             st.error(f"Struktur resep untuk {os.path.basename(pdf_path)} tidak valid saat diakses kembali.")
             valid_recipes = False; break
        # Gabungkan placeholder (ambil definisi dari resep pertama jika ada duplikat)
        for key, value in recipe_data["placeholders"].items():
            if key not in all_placeholders:
                all_placeholders[key] = value
        # Gabungkan contoh
        for key, value in recipe_data["examples"].items():
            if key not in all_examples:
                 all_examples[key] = value

    if not valid_recipes:
        if st.button("Kembali"): st.session_state.page = "initial_input"; st.rerun()
        st.stop() # Hentikan jika ada resep tidak valid

    # --- Tahap AI First Pass (jika belum dijalankan) ---
    if 'ai_pass_done' not in st.session_state or not st.session_state.ai_pass_done:
        with st.spinner("AI sedang menganalisis input Anda untuk ekstraksi awal..."):
            initial_data = st.session_state.initial_data
            # Panggil AI dengan gabungan placeholders & examples
            ai_result = run_ai_first_pass(
                initial_prompt=initial_data["prompt"],
                file_uploads=initial_data["files"],
                all_placeholders=all_placeholders, # Kirim gabungan
                all_examples=all_examples        # Kirim gabungan
            )
            # Simpan hasil AI (bahkan jika kosong atau error)
            st.session_state.ai_extracted_data = ai_result if ai_result else {}
            st.session_state.ai_pass_done = True
        st.rerun() # Muat ulang untuk menampilkan hasil AI dan form verifikasi

    # --- Tampilkan Hasil AI & Formulir Verifikasi ---
    ai_data = st.session_state.ai_extracted_data

    st.info("AI telah mencoba mengekstrak informasi berikut untuk semua dokumen. Silakan periksa, perbaiki, dan lengkapi.")
    with st.expander("Lihat Hasil Mentah Ekstraksi AI"):
        # Tampilkan error jika ada
        if isinstance(ai_data, dict) and "error" in ai_data:
             st.error(f"Ekstraksi AI gagal: {ai_data['error']}")
        elif not ai_data:
             st.warning("Tidak ada data yang berhasil diekstrak oleh AI.")
        else:
             st.json(ai_data)

    with st.form("verification_form_combined"):
        st.markdown("**Data Gabungan untuk Dokumen (Silakan Edit/Lengkapi):**")
        widget_keys = {}

        # Loop melalui GABUNGAN placeholder yang BUKAN kalkulasi
        for key, value_obj in all_placeholders.items():
            if not key.endswith("_CALCULATED"):
                label = f"{key.replace('_', ' ').title()}:"
                # Dapatkan nilai awal dari hasil AI jika ada
                ai_extracted_value = ai_data.get(key) if isinstance(ai_data, dict) else None # Handle jika ai_data error
                # Tentukan tipe input berdasarkan nilai default di resep (struktur baru)
                instruction_or_default = value_obj.get("instruction") if isinstance(value_obj, dict) else value_obj
                widget_key = f"input_{key}"
                widget_keys[key] = widget_key

                # Buat input teks atau angka (editable)
                if isinstance(instruction_or_default, str):
                    default_value_txt = str(ai_extracted_value) if ai_extracted_value is not None else ""
                    if key in ["Isi_BA", "Bukti_BA", "Alasan", "Alasan_detail"] or len(default_value_txt) > 80: # Heuristik untuk text area
                        st.text_area(label, value=default_value_txt, key=widget_key, height=100)
                    else:
                        st.text_input(label, value=default_value_txt, key=widget_key)
                elif instruction_or_default is None or isinstance(instruction_or_default, (int, float)):
                    default_value_num = None
                    if ai_extracted_value is not None:
                        try:
                            cleaned_val_str = re.sub(r'(IDR|\s|,-?$)', '', str(ai_extracted_value))
                            if cleaned_val_str: default_value_num = float(cleaned_val_str) if '.' in cleaned_val_str else int(cleaned_val_str)
                        except: default_value_num = None
                    st.number_input(label, value=default_value_num, format=None, key=widget_key)


        verification_submitted = st.form_submit_button("Verifikasi Selesai, Lanjutkan ke Pembuatan Dokumen")

        if verification_submitted:
            # Kumpulkan data yang diverifikasi pengguna dari state widget
            user_verified_data = {key: st.session_state[widget_skey] for key, widget_skey in widget_keys.items()}

            if "Bukti_BA" in user_verified_data and isinstance(user_verified_data["Bukti_BA"], str):
                bukti_ba_str = user_verified_data["Bukti_BA"].strip()
                # Hanya coba parse jika terlihat seperti list/array
                if bukti_ba_str.startswith('[') and bukti_ba_str.endswith(']'):
                    st.write("DEBUG: Mencoba mem-parsing string Bukti_BA...") # Debug message
                    try:
                        # Gunakan ast.literal_eval untuk parsing aman string Python
                        parsed_bukti_ba = ast.literal_eval(bukti_ba_str)
                        # Verifikasi hasilnya adalah list
                        if isinstance(parsed_bukti_ba, list):
                            user_verified_data["Bukti_BA"] = parsed_bukti_ba # Ganti string dengan list
                            st.write("DEBUG: Parsing Bukti_BA berhasil.")
                        else:
                            st.warning("Hasil parsing Bukti_BA bukan list. Mempertahankan string.")
                    except (ValueError, SyntaxError) as parse_error:
                        st.error(f"Gagal mem-parse input Bukti_BA sebagai list Python: {parse_error}")
                        st.warning("Pastikan format input untuk Bukti BA adalah list Python yang valid, contoh: [{'NO': '1', ...}]. Mempertahankan input string asli.")
                    except Exception as e:
                        st.error(f"Error tak terduga saat parsing Bukti_BA: {e}")
                else:
                    # Jika tidak terlihat seperti list, mungkin memang teks biasa
                    st.write("DEBUG: Bukti_BA adalah string tapi tidak terlihat seperti list, tidak di-parse.")
            
            if "Pembelian" in user_verified_data and isinstance(user_verified_data["Pembelian"], str):
                pembelian_str = user_verified_data["Pembelian"].strip()
                # Hanya coba parse jika terlihat seperti list/array
                if pembelian_str.startswith('[') and pembelian_str.endswith(']'):
                    st.write("DEBUG: Mencoba mem-parsing string Pembelian...") # Debug message
                    try:
                        # Gunakan ast.literal_eval untuk parsing aman string Python
                        parsed_pembelian = ast.literal_eval(pembelian_str)
                        # Verifikasi hasilnya adalah list
                        if isinstance(parsed_pembelian, list):
                            user_verified_data["Pembelian"] = parsed_pembelian # Ganti string dengan list
                            st.write("DEBUG: Parsing Pembelian berhasil.")
                        else:
                            st.warning("Hasil parsing Pembelian bukan list. Mempertahankan string.")
                    except (ValueError, SyntaxError) as parse_error:
                        st.error(f"Gagal mem-parse input Pembelian sebagai list Python: {parse_error}")
                        st.warning("Pastikan format input untuk Bukti BA adalah list Python yang valid, contoh: [{'NO': '1', ...}]. Mempertahankan input string asli.")
                    except Exception as e:
                        st.error(f"Error tak terduga saat parsing Pembelian: {e}")
                else:
                    # Jika tidak terlihat seperti list, mungkin memang teks biasa
                    st.write("DEBUG: Pembelian adalah string tapi tidak terlihat seperti list, tidak di-parse.")

            # Lakukan kalkulasi pada data gabungan yang sudah diverifikasi
            st.session_state.final_combined_data = perform_calculations(all_placeholders, user_verified_data)

            st.session_state.page = "results" # Pindah ke halaman hasil
            # Hapus state sementara
            if 'ai_pass_done' in st.session_state: del st.session_state['ai_pass_done']
            st.rerun() # Muat ulang untuk menampilkan hasil akhir

# --- LANGKAH 3: HASIL AKHIR & PENGIRIMAN BATCH ---
elif st.session_state.page == "results":
    st.header("Hasil Akhir & Pengiriman ke Google Docs")

    # Ambil data gabungan yang sudah final dan daftar resep
    final_combined_data = st.session_state.get('final_combined_data')
    recipes_to_process = st.session_state.get('recipes_to_process')

    if final_combined_data and recipes_to_process:
        st.success("Proses pengumpulan dan kalkulasi data selesai.")
        with st.expander("Lihat Data Final Gabungan (JSON)"):
            st.json(final_combined_data)

        st.write("---")
        st.subheader("Siapkan & Kirim Data Batch ke Google Docs")

        # Ambil URL Web App dari Secrets atau fallback
        # apps_script_url = st.secrets.get("APPS_SCRIPT_WEB_APP_URL")
        apps_script_url = "https://script.google.com/macros/s/AKfycbzly2uf47C9_6pknw9-VmY8n1OmpOmt2sAwqKgtTZSlBiwYF0MAla4DdbqULOhkrUUi/exec"
        if not apps_script_url:
            apps_script_url = "https://script.google.com/macros/s/AKfycbzly2uf47C9_6pknw9-VmY8n1OmpOmt2sAwqKgtTZSlBiwYF0MAla4DdbqULOhkrUUi/exec" # Fallback
            st.warning("URL Apps Script diambil dari kode (hardcoded).")

        if not apps_script_url:
            st.error("Error Konfigurasi: URL Web App Google Apps Script tidak ditemukan.")
        else:
            if st.button("Kirim Data & Buat Semua Dokumen di Google Docs"):
                with st.spinner("Mempersiapkan dan mengirim data batch ke Google Apps Script..."):
                    try:
                        # --- MEMBANGUN PAYLOAD BATCH ---
                        batch_payload = {"documents": []}
                        for pdf_path, recipe_data in recipes_to_process.items():
                            google_doc_id = recipe_data.get("google_doc_id")
                            placeholders_for_this_doc = recipe_data.get("placeholders", {}).keys()

                            # Validasi ketat: google_doc_id harus ada, tidak None, tidak kosong, dan bertipe string
                            if not google_doc_id or not isinstance(google_doc_id, str) or not google_doc_id.strip():
                                st.error(f"ID Google Doc tidak valid untuk {os.path.basename(pdf_path)}. Nilai: {repr(google_doc_id)}")
                                continue # Lanjut ke dokumen berikutnya jika ID tidak valid

                            # Pastikan google_doc_id adalah string yang sudah di-strip
                            google_doc_id = google_doc_id.strip()

                            # Filter data gabungan, hanya ambil yang relevan untuk dokumen ini
                            data_for_this_doc = {
                                key: format_for_gdocs(final_combined_data.get(key))
                                for key in placeholders_for_this_doc
                                if not key.endswith("_CALCULATED") # Jangan kirim key kalkulasi
                                and final_combined_data.get(key) is not None # Hanya kirim jika ada nilainya
                            }
                            # Tambahkan hasil kalkulasi (jika ada) dengan nama base key
                            for key in placeholders_for_this_doc:
                                 if key.endswith("_CALCULATED"):
                                      base_key = key.replace("_CALCULATED", "")
                                      if base_key in final_combined_data:
                                           data_for_this_doc[base_key] = format_for_gdocs(final_combined_data[base_key])


                            batch_payload["documents"].append({
                                "google_doc_id": google_doc_id,
                                "data_to_fill": data_for_this_doc
                            })
                        # --- AKHIR MEMBANGUN PAYLOAD ---

                        if not batch_payload["documents"]:
                             st.warning("Tidak ada dokumen valid yang bisa dikirim.")
                        else:
                             # Validasi akhir: Pastikan semua dokumen dalam payload memiliki google_doc_id yang valid
                             valid_documents = []
                             for doc in batch_payload["documents"]:
                                 doc_id = doc.get("google_doc_id")
                                 if doc_id and isinstance(doc_id, str) and doc_id.strip():
                                     valid_documents.append({
                                         "google_doc_id": doc_id.strip(),
                                         "data_to_fill": doc.get("data_to_fill", {})
                                     })
                                 else:
                                     st.error(f"Ditemukan dokumen dengan google_doc_id tidak valid: {repr(doc_id)}")
                             
                             if not valid_documents:
                                 st.error("Tidak ada dokumen dengan google_doc_id yang valid untuk dikirim.")
                             else:
                                 # Gunakan payload yang sudah divalidasi
                                 batch_payload["documents"] = valid_documents
                                 
                                 st.warning("DEBUG: Payload yang akan dikirim ke Apps Script:")
                                 st.json(batch_payload) # Tampilkan payload sebelum dikirim
                                 print(f"batch_payload: {batch_payload}")
                                 # Kirim payload batch
                                 response = requests.post(
                                    apps_script_url,
                                    headers={'Content-Type': 'application/json'},
                                    json=batch_payload
                                 )
                                 response.raise_for_status()
                                 result = response.json()

                                 # --- Tampilkan hasil batch ---
                                 st.subheader("Hasil Pembuatan Dokumen:")
                                 if result.get("status") == "completed":
                                     for doc_result in result.get("results", []):
                                         if doc_result.get("status") == "success":
                                             st.success(f"✅ Dokumen '{doc_result.get('fileName', 'N/A')}' berhasil dibuat.")
                                             st.markdown(f"   [🔗 Buka Dokumen]({doc_result.get('docUrl')})")
                                         else:
                                             st.error(f"❌ Gagal membuat dokumen dari template ID ...{doc_result.get('templateId', 'N/A')[-12:]}: {doc_result.get('message')}")
                                 elif result.get("status") == "error":
                                      st.error(f"Terjadi error global di Apps Script: {result.get('message')}")
                                 else:
                                      st.warning("Respons dari Apps Script tidak dikenali.")
                                      st.json(result)
                    except requests.exceptions.RequestException as req_e: # Specific exception first
                            st.error(f"Gagal mengirim data ke Apps Script (Request Error): {req_e}")
                            # Safely attempt to show response text if available
                            if 'response' in locals() and hasattr(response, 'text'):
                                st.text_area("Respons Server (jika ada):", value=response.text, height=100)

                    except json.JSONDecodeError as json_e: # Specific exception for JSON parsing
                            st.warning(f"Respons dari Apps Script bukan JSON valid: {json_e}")
                            # Show raw text since JSON parsing failed
                            if 'response' in locals() and hasattr(response, 'text'):
                                st.text_area("Respons Mentah Server:", value=response.text, height=100)
                    except Exception as e: # Generic catch-all last
                            st.error(f"Terjadi kesalahan tak terduga saat mengirim/memproses: {e}")
                            # Avoid accessing 'response' here as its state is unknown
                            st.exception(e) # Display full traceback for debugging
                    except Exception as e:
                        st.error(f"Gagal mengirim/memproses batch: {e}")
                        if 'response' in locals(): st.text_area("Respons Mentah:", response.text)

    else:
        st.error("Tidak ada hasil JSON atau resep. Terjadi kesalahan.")

    st.write("---")
    if st.button("Buat Permintaan Baru"):
        keys_to_reset = list(st.session_state.keys()) # Reset semua state
        for key in keys_to_reset:
             del st.session_state[key]
        st.rerun()