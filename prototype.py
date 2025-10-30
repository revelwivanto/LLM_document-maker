import streamlit as st
import json
import os
import re
import io
import requests
from pypdf import PdfReader
from streamlit_pdf_viewer import pdf_viewer
import google.generativeai as genai

# --- Konfigurasi & Inisialisasi ---
st.set_page_config(page_title="Generator Dokumen Cerdas", page_icon="📝", layout="wide")

# Konfigurasi API Key Gemini (PENTING: Gunakan Streamlit Secrets saat deploy)
try:
    # Coba muat API key dari secrets (untuk deployment)
    api_key =st.secrets.get("GEMINI_API")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')
except (KeyError, FileNotFoundError):
    # Fallback jika secrets tidak ada (misalnya saat testing lokal)
    st.warning("GEMINI_API tidak ditemukan di Streamlit Secrets. Pastikan Anda telah mengkonfigurasinya untuk deployment.")
    # Anda bisa menambahkan cara lain untuk memuat API key di sini jika perlu untuk testing lokal,
    # misalnya dari environment variable atau input manual (tidak aman untuk produksi)
    # api_key_local = os.environ.get("GEMINI_API_LOCAL") # Contoh
    # if api_key_local:
    #     genai.configure(api_key=api_key_local)
    #     model = genai.GenerativeModel('gemini-pro')
    # else:
    st.error("Model AI tidak dapat dikonfigurasi. Aplikasi tidak dapat melanjutkan.")
    model = None # Set model ke None jika konfigurasi gagal

# Inisialisasi session state
if 'page' not in st.session_state: st.session_state.page = "initial_input"
# ---------------------------------------------------
if 'recipe' not in st.session_state: st.session_state.recipe = None
# --- PERUBAHAN: initial_data sekarang menyimpan prompt & semua file ---
if 'initial_data' not in st.session_state: st.session_state.initial_data = {"prompt": "", "files": {}}
# ----------------------------------------------------------------------
if 'ai_extracted_data' not in st.session_state: st.session_state.ai_extracted_data = None
if 'missing_manual_keys' not in st.session_state: st.session_state.missing_manual_keys = None
if 'final_json' not in st.session_state: st.session_state.final_json = None

# --- Fungsi-fungsi Inti ---
@st.cache_data # Cache hasil agar lebih cepat saat tidak ada perubahan
def get_document_types(base_folder="templates"):
    """Mencari semua tipe dokumen (sub-folder) di dalam folder 'templates'."""
    try:
        if not os.path.isdir(base_folder): return []
        # Pastikan hanya mengembalikan nama folder
        return [d for d in os.listdir(base_folder) if os.path.isdir(os.path.join(base_folder, d))]
    except Exception as e:
        st.error(f"Gagal membaca folder templates: {e}")
        return []

@st.cache_data
def get_templates_for_type(doc_type_folder):
    """Mencari semua file .pdf di dalam folder tipe dokumen yang dipilih."""
    try:
        if not os.path.isdir(doc_type_folder): return []
        # Pastikan hanya mengembalikan nama file PDF
        return [f for f in os.listdir(doc_type_folder) if f.lower().endswith('.pdf')]
    except Exception as e:
        st.error(f"Gagal membaca folder template {doc_type_folder}: {e}")
        return []
    
@st.cache_data
def load_recipe(template_path):
    recipe_path = os.path.splitext(template_path)[0] + ".json"
    try:
        with open(recipe_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Gagal memuat file resep '{os.path.basename(recipe_path)}': {e}")
        return None

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

def run_ai_first_pass(initial_prompt, file_uploads, recipe):
    if not model: return {"error": "MODEL_AI_TIDAK_TERKONFIGURASI"}

    placeholders_to_extract = recipe.get("placeholders", {})
    json_format_string = json.dumps({key: "..." for key in placeholders_to_extract if not key.endswith('_CALCULATED')}, indent=2)

    context_text = ""
    for upload_id, uploaded_file in file_uploads.items():
        if uploaded_file:
            context_text += f"\n\n--- KONTEKS DARI DOKUMEN '{upload_id}' ---\n{get_text_from_file(uploaded_file)}"

    full_example_json = json.dumps(recipe.get("examples", {}), indent=2)

    prompt = f"""
    Anda adalah asisten AI yang sangat teliti, bertugas mengekstrak informasi sebanyak mungkin dari teks untuk mengisi dokumen.

    TUGAS UTAMA:
    Berdasarkan konteks utama dan dokumen pendukung, coba isi sebanyak mungkin field dalam format JSON di bawah ini.

    KONTEKS UTAMA DARI PENGGUNA:
    "{initial_prompt}"
    {context_text}

    CONTOH LENGKAP OUTPUT YANG DIHARAPKAN (Gunakan ini sebagai referensi kuat untuk gaya, panjang, dan format):
    ```json
    {full_example_json}
    ```

    ATURAN PENTING:
    1.  Fokus untuk mengisi field dalam format JSON ini: {json_format_string}.
    2.  Jika Anda benar-benar tidak dapat menemukan informasi untuk sebuah field, JANGAN sertakan field tersebut di dalam output JSON Anda.
    3.  Output Anda HARUS berupa objek JSON yang valid, hanya berisi field-field yang berhasil Anda temukan.
    4.  Jangan menyertakan penjelasan atau format markdown. HANYA objek JSON.
    5.  Gunakan NAMA FIELD (key) persis seperti yang ada di format JSON yang diminta.
    6.  Untuk field numerik (seperti Budget_2025, Usulan_anggaran, dll.), pastikan Anda mengembalikan nilainya sebagai ANGKA (integer atau float), bukan string. Jika tidak ditemukan, jangan sertakan field tersebut.
    7.  **KHUSUS UNTUK FIELD "Bukti_BA": Nilainya HARUS berupa ARRAY (list) dari OBJECTS JSON, di mana setiap object memiliki keys "NO", "OBJEK", "JUMLAH", dan "DETAIL", persis seperti dalam CONTOH OUTPUT YANG DIHARAPKAN. Jika hanya ada satu item bukti, tetap buat array dengan satu object di dalamnya. Jika tidak ada bukti yang ditemukan, jangan sertakan field "Bukti_BA".**

    """
    try:
        response = model.generate_content(prompt)
        json_string = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(json_string)
    except Exception as e:
        error_message = f"Gagal mem-parse JSON dari AI: {e}"
        if 'response' in locals():
            st.text_area("Teks mentah dari AI untuk debugging:", value=response.text, height=200)
        return {"error": error_message}

# TAMBAHKAN FUNGSI BARU INI

def analyze_budget_with_llm(text_description):
    """
    Menggunakan LLM (Gemini) untuk menganalisis deskripsi teks,
    mengidentifikasi detail budget (harga, kuantitas), menghitung total estimasi,
    dan mengembalikan hasilnya sebagai angka (float) atau None.
    """
    if not model or not text_description:
        return None

    # Prompt yang spesifik untuk analisis dan kalkulasi budget
    prompt = f"""
    Analisis deskripsi berikut untuk menentukan total estimasi budget dalam Rupiah.
    Fokus pada angka yang berhubungan dengan biaya, harga, kuantitas (seperti jumlah user, item, dll.).
    Lakukan perhitungan jika diperlukan (misalnya, harga per unit dikali jumlah unit).

    CONTOH:
    - Input: "budget 10jt untuk 20 users" -> Output: 200000000
    - Input: "total biaya sekitar 500 juta rupiah" -> Output: 500000000
    - Input: "harganya 500 ribu per lisensi, kami butuh 10" -> Output: 5000000
    - Input: "perpanjangan adobe 17.5 jt" -> Output: 17500000
    - Input: "belum ada info budget" -> Output: null

    Deskripsi: "{text_description}"

    ATURAN OUTPUT PENTING:
    1. Kembalikan HANYA total estimasi budget sebagai ANGKA (integer atau float).
    2. Jika tidak ada informasi budget yang bisa dihitung atau ditemukan, kembalikan 'null'.
    3. Jangan sertakan 'Rp', 'juta', 'ribu', koma, titik, atau teks penjelasan lainnya. HANYA ANGKA atau 'null'.
    """

    try:
        response = model.generate_content(prompt)
        result_text = response.text.strip().lower()

        if result_text == 'null' or not result_text:
            return None
        else:
            # Coba konversi hasil teks (yang seharusnya hanya angka) ke float
            # Lakukan pembersihan minimal jika AI masih menyertakan pemisah
            cleaned_num_str = re.sub(r'[^\d.]', '', result_text.replace(',', '.')) # Standardisasi ke titik desimal
            if cleaned_num_str:
                return float(cleaned_num_str)
            else:
                st.warning(f"AI mengembalikan '{result_text}' yang tidak bisa diinterpretasikan sebagai budget.")
                return None # Gagal konversi

    except Exception as e:
        st.error(f"Terjadi kesalahan saat analisis budget dengan AI: {e}")
        if 'response' in locals():
            st.text_area("Teks mentah dari AI (Budget Analysis):", value=response.text)
        return None
    
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
            cleaned_value = re.sub(r'(IDR|\s|\.|,-?$)', '', value)
            if cleaned_value.isdigit():
                return float(cleaned_value)
        st.warning(f"Nilai '{value}' tidak dapat dibersihkan menjadi angka.")
        return None

    # --- PERUBAHAN LOGIKA UTAMA DIMULAI DI SINI ---
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
    # --- PERUBAHAN LOGIKA UTAMA SELESAI ---

# --- Tampilan & Logika Aplikasi (State Machine) ---
st.title("AI Document Generator")

# --- LANGKAH 1 (BARU): INPUT AWAL DARI PENGGUNA ---
if st.session_state.page == "initial_input":
    st.header("Jelaskan Kebutuhan Anda")
    with st.form("initial_input_form"):
        st.info("Masukkan deskripsi kebutuhan Anda, termasuk estimasi budget.")
        initial_prompt = st.text_area(
            "Deskripsi Kebutuhan:",
            height=150,
            placeholder="Contoh: Saya ingin memperpanjang lisensi Adobe untuk 100 user seharga 1jt per user, berikut terlampir BA pemeriksaan sebelumnya..."
        )
        uploaded_files_list = st.file_uploader(
            "Unggah Dokumen Pendukung Apapun (Opsional, .pdf atau .txt)",
            type=['pdf', 'txt'], accept_multiple_files=True, key="initial_uploader"
        )
        submitted = st.form_submit_button("Analisis & Lanjut ke Pemilihan Dokumen")

        if submitted:
            if not initial_prompt:
                st.warning("Harap isi deskripsi kebutuhan.")
            else:
                # --- PERUBAHAN: Lakukan analisis budget dengan LLM ---
                with st.spinner("Menganalisis budget dengan AI..."):
                    budget = analyze_budget_with_llm(initial_prompt)
                st.session_state.budget = budget # Simpan hasil (bisa berupa float atau None)
                # ---------------------------------------------------

                uploaded_files_dict = {f.name: f for f in uploaded_files_list} if uploaded_files_list else {}
                st.session_state.initial_data = {
                    "prompt": initial_prompt,
                    "files": uploaded_files_dict
                }
                st.session_state.page = "selection" # Pindah ke halaman pemilihan
                st.rerun()

# --- LANGKAH 2: PEMILIHAN TEMPLATE ---
elif st.session_state.page == "selection":
    st.header("Pilih Template Dokumen yang Ingin Anda Buat")

    # --- Logika Filter Dokumen Berdasarkan Budget ---
    budget = st.session_state.get('budget')
    if budget is not None:
        formatted_budget = f"Rp {budget:,.0f}".replace(",", ".")
        st.info(f"**Budget terdeteksi:** {formatted_budget}")
        if budget >= 300_000_000:
            st.success("**Rekomendasi:** Dokumen untuk budget >= 300 Juta ditampilkan.")
            # Daftar folder untuk budget besar
            allowed_doctypes = ["BAP", "Review Pekerjaan", "RAB", "RKS"]
        else:
            st.success("**Rekomendasi:** Dokumen untuk budget < 300 Juta ditampilkan.")
            # Daftar folder untuk budget kecil
            allowed_doctypes = ["BAP", "Nota dinas izin prinsip(SVP)", "RAB", "RKS"]
    else:
        st.warning("Budget tidak terdeteksi dari deskripsi Anda. Semua tipe dokumen ditampilkan.")
        allowed_doctypes = get_document_types() # Tampilkan semua jika tidak ada budget

    # Filter tipe dokumen yang akan ditampilkan
    available_doctypes = get_document_types()
    doc_types_to_show = [dt for dt in available_doctypes if dt in allowed_doctypes]

    st.write("---")

    # --- Tata Letak Dua Kolom ---
    col_selection, col_preview = st.columns([0.5, 0.5])

    # --- Kolom Kiri: Opsi Pemilihan ---
    with col_selection:
        if not doc_types_to_show:
            st.warning("Tidak ada tipe dokumen yang cocok dengan kriteria budget Anda.")
        else:
            selected_type = st.radio("Pilih tipe dokumen:", doc_types_to_show, horizontal=True, key="doc_type_selector")
            if selected_type:
                template_folder_path = os.path.join("templates", selected_type)
                pdf_templates = get_templates_for_type(template_folder_path)
                if not pdf_templates:
                    st.info(f"Tidak ada template PDF di folder '{selected_type}'.")
                else:
                    st.write("**Template yang tersedia:**")
                    for pdf_file in pdf_templates:
                        # Tombol ini sekarang hanya untuk memilih Preview
                        if st.button(f"{pdf_file}", key=f"btn_preview_{pdf_file}"):
                            # Simpan path file yang dipilih untuk Preview
                            st.session_state.pdf_to_preview = os.path.join(template_folder_path, pdf_file)
                            # Reset pilihan sebelumnya jika ada
                            st.session_state.final_json = None
                            st.rerun()

    # --- Kolom Kanan: Preview PDF & Tombol Lanjut ---
    with col_preview:
        st.subheader("Preview Dokumen")
        if st.session_state.get("pdf_to_preview"):
            pdf_path = st.session_state.pdf_to_preview
            try:
                # Baca file biner untuk ditampilkan
                with open(pdf_path, "rb") as f:
                    pdf_binary_data = f.read()
                
                # Tampilkan PDF Viewer
                pdf_viewer(pdf_binary_data, height=800) # Batasi tinggi agar tidak terlalu besar
                
                st.write("---")
                # Tombol konfirmasi untuk melanjutkan ke langkah berikutnya
                if st.button("✅ Lanjutkan & Isi Data untuk Template Ini"):
                    # Muat resep dari file yang dipilih untuk Preview
                    recipe_data = load_recipe(pdf_path)
                    if recipe_data:
                        st.session_state.recipe = recipe_data
                        st.session_state.page = "processing" # Lanjut ke pemrosesan AI
                        # Reset state Preview
                        st.session_state.pdf_to_preview = None 
                        st.rerun()
                    else:
                        st.error("Gagal memuat file resep (.json) yang terkait dengan template ini.")

            except FileNotFoundError:
                st.error(f"File Preview tidak ditemukan di: {pdf_path}")
            except Exception as e:
                st.error(f"Gagal menampilkan Preview PDF: {e}")
        else:
            st.info("Klik salah satu tombol 'Pilih Template Ini' di sebelah kiri untuk melihat Preview di sini.")

    # Tombol kembali ke input awal
    st.write("---")
    if st.button("Kembali ke Input Awal"):
        st.session_state.page = "initial_input"
        # Reset state yang relevan
        st.session_state.budget = None
        st.session_state.pdf_to_preview = None
        st.rerun()

# --- LANGKAH 3: PEMROSESAN AI DIIKUTI VERIFIKASI & PENGISIAN PENGGUNA ---
elif st.session_state.page == "processing":
    # Tahap 3A: AI First Pass (hanya dijalankan sekali)
    # Pastikan AI pass hanya berjalan jika belum ada hasilnya
    if 'ai_pass_done' not in st.session_state or not st.session_state.ai_pass_done:
        with st.spinner("AI sedang menganalisis input Anda untuk ekstraksi awal..."):
            initial_data = st.session_state.initial_data
            ai_result = run_ai_first_pass(
                initial_prompt=initial_data["prompt"],
                file_uploads=initial_data["files"],
                recipe=st.session_state.recipe
            )
            # Simpan hasil AI (bahkan jika kosong atau error untuk ditampilkan)
            st.session_state.ai_extracted_data = ai_result if ai_result else {}
            # Tandai bahwa AI sudah berjalan
            st.session_state.ai_pass_done = True
        st.rerun() # Muat ulang untuk menampilkan hasil AI dan form verifikasi

    # Tahap 3B: Tampilkan hasil AI dan formulir untuk verifikasi/pengisian pengguna
    st.header("Verifikasi & Lengkapi Data")

    ai_data = st.session_state.ai_extracted_data
    # Pastikan recipe dan placeholders ada
    if not st.session_state.recipe or "placeholders" not in st.session_state.recipe:
        st.error("Resep tidak valid atau tidak ditemukan. Kembali ke pemilihan.")
        if st.button("Kembali"): st.session_state.page = "selection"; st.rerun()
        st.stop()

    recipe_placeholders = st.session_state.recipe["placeholders"]

    st.info("AI telah mencoba mengekstrak informasi berikut. Silakan periksa, perbaiki jika perlu, dan lengkapi data yang kosong.")

    with st.expander("Lihat Hasil Mentah Ekstraksi AI"):
        st.json(ai_data if ai_data else {"Info": "Tidak ada data yang diekstrak AI atau terjadi error."})

    # --- Formulir Verifikasi & Pengisian Kesenjangan (SEMUA FIELD EDITABLE) ---
    with st.form("verification_form"):
        st.markdown("**Data untuk Dokumen (Silakan Edit/Lengkapi):**")

        # Dictionary untuk menyimpan key widget agar bisa dibaca setelah submit
        widget_keys = {}

        # Loop melalui SEMUA placeholder yang BUKAN kalkulasi
        for key, value_obj in recipe_placeholders.items():
            if not key.endswith("_CALCULATED"):
                label = f"{key.replace('_', ' ').title()}:"
                # Dapatkan nilai awal dari hasil AI jika ada
                ai_extracted_value = ai_data.get(key)
                # Tentukan tipe input (teks atau angka) berdasarkan nilai default di resep
                instruction_or_default = value_obj.get("instruction") if isinstance(value_obj, dict) else value_obj
                widget_key = f"input_{key}" # Key unik untuk widget Streamlit
                widget_keys[key] = widget_key # Simpan key widget untuk dibaca nanti

                # Buat input teks jika instruksi adalah string (termasuk instruksi AI)
                # atau jika nilai default adalah string kosong
                if isinstance(instruction_or_default, str):
                    default_value_txt = str(ai_extracted_value) if ai_extracted_value is not None else ""
                    # Tampilkan sebagai text_area jika kemungkinan isinya panjang (heuristic)
                    if key in ["Isi_BA", "Bukti_BA", "Alasan", "Alasan_detail"] or len(default_value_txt) > 100:
                         st.text_area(label, value=default_value_txt, key=widget_key, height=150)
                    else:
                         st.text_input(label, value=default_value_txt, key=widget_key)

                # Buat input angka jika instruksi/nilai default adalah null atau angka
                elif instruction_or_default is None or isinstance(instruction_or_default, (int, float)):
                    default_value_num = None
                    if ai_extracted_value is not None:
                        try:
                            # Coba bersihkan format mata uang sebelum konversi
                            cleaned_val_str = re.sub(r'(IDR|\s|\.|,-?$)', '', str(ai_extracted_value))
                            if cleaned_val_str:
                                default_value_num = float(cleaned_val_str) if '.' in cleaned_val_str else int(cleaned_val_str)
                        except (ValueError, TypeError):
                            st.warning(f"AI mengembalikan '{ai_extracted_value}' untuk '{key}'. Harap perbaiki menjadi angka.")
                            default_value_num = None
                    # Tampilkan number_input
                    st.number_input(label, value=default_value_num, format=None, key=widget_key)


        verification_submitted = st.form_submit_button("Verifikasi Selesai, Lanjutkan ke Kalkulasi")

        if verification_submitted:
            # --- PENGUMPULAN DATA SETELAH SUBMIT ---
            # Ambil nilai aktual dari semua widget Streamlit menggunakan key yang disimpan
            user_verified_data = {}
            for original_key, widget_skey in widget_keys.items():
                 user_verified_data[original_key] = st.session_state[widget_skey] # Baca dari session_state
            # ----------------------------------------

            # Lakukan kalkulasi dengan data yang sudah diverifikasi/dilengkapi pengguna
            st.session_state.final_json = perform_calculations(recipe_placeholders, user_verified_data)

            st.session_state.page = "results"
            # Hapus state sementara agar form tidak muncul lagi jika user kembali
            # Kita biarkan ai_extracted_data untuk perbandingan jika perlu, tapi hapus flag
            if 'ai_pass_done' in st.session_state: del st.session_state['ai_pass_done']
            # if 'missing_manual_keys' in st.session_state: del st.session_state['missing_manual_keys'] # Tidak dipakai lagi

            st.rerun()

# --- LANGKAH 4: TAMPILAN HASIL AKHIR ---
elif st.session_state.page == "results":
    # (Bagian ini tidak perlu diubah, tetap sama)
    st.header("Hasil Akhir & Pengiriman ke Google Docs")
    final_json = st.session_state.get('final_json')
    recipe = st.session_state.get('recipe')

    if final_json and recipe:
        st.success("Proses selesai! Objek JSON di bawah ini siap dikirim.")
        st.json(final_json, expanded=True) # Tampilkan secara default agar mudah dicek

        st.write("---")
        st.subheader("Kirim Data ke Google Docs")

        google_doc_id = recipe.get("google_doc_id")

        if not google_doc_id:
            st.error("Error: 'google_doc_id' tidak ditemukan dalam file resep JSON.")
        else:
            apps_script_url = "https://script.google.com/macros/s/AKfycbzly2uf47C9_6pknw9-VmY8n1OmpOmt2sAwqKgtTZSlBiwYF0MAla4DdbqULOhkrUUi/exec"
            if not apps_script_url:
                 apps_script_url = "https://script.google.com/macros/s/AKfycbzly2uf47C9_6pknw9-VmY8n1OmpOmt2sAwqKgtTZSlBiwYF0MAla4DdbqULOhkrUUi/exec" # Fallback
                 st.warning("URL Apps Script diambil dari kode (hardcoded).")

            if not apps_script_url:
                st.error("Error Konfigurasi: URL Web App Google Apps Script tidak ditemukan.")
            else:
                st.info(f"Dokumen akan dibuat menggunakan template Google Doc ID: ...{google_doc_id[-12:]}")

                if st.button("🚀 Kirim Data & Buat Dokumen di Google Docs"):
                    with st.spinner("Mengirim data ke Google Apps Script..."):
                        try:
                            payload_to_send = {
                                "google_doc_id": google_doc_id,
                                "data_to_fill": final_json
                            }
                            response = requests.post(
                                apps_script_url,
                                headers={'Content-Type': 'application/json'},
                                json=payload_to_send
                            )
                            response.raise_for_status()
                            result = response.json()
                            if result.get("status") == "success":
                                st.success(f"Berhasil! Dokumen baru telah dibuat.")
                                doc_url = result.get("docUrl")
                                if doc_url:
                                    st.markdown(f"**[🔗 Buka Dokumen yang Dihasilkan]({doc_url})**")
                            else:
                                st.error(f"Apps Script Error: {result.get('message', 'Unknown error')}")
                        except Exception as e:
                            st.error(f"Gagal mengirim/memproses: {e}")
                            if 'response' in locals(): st.text_area("Respons Mentah:", response.text)
    else:
        st.error("Tidak ada hasil JSON atau resep. Terjadi kesalahan.")

    st.write("---")
    if st.button("Buat Dokumen Baru"):
        keys_to_reset = ['page', 'recipe', 'initial_data', 'ai_extracted_data', 'missing_manual_keys', 'final_json', 'ai_pass_done']
        for key in keys_to_reset:
             if key in st.session_state: del st.session_state[key]
        st.rerun()