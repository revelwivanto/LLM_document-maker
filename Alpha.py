import streamlit as st
import json
import os
import re
import io
import requests
from pypdf import PdfReader
from streamlit_pdf_viewer import pdf_viewer
import google.generativeai as genai

# --- Konstanta Baru: Definisikan path ke template PDF yang akan selalu dibuat ---
TARGET_PDF_TEMPLATES = [
    os.path.join("templates", "Nota dinas izin prinsip(SVP)", "Nota dinas Izin Prinsip Pengadaan.pdf"),
    os.path.join("templates", "RAB", "RAB", "RAB Pengadaan.pdf"),
    os.path.join("templates", "RKS", "Review Pengajuan Pekerjaan Pengadaan Barang.pdf")
]

# --- Konfigurasi & Inisialisasi ---
st.set_page_config(page_title="Generator Dokumen Cerdas", page_icon="📝", layout="wide")

# Konfigurasi API Key Gemini (PENTING: Gunakan Streamlit Secrets saat deploy)
try:
    # Coba muat API key dari secrets (untuk deployment)
    api_key ="AIzaSyDwpv0KP6FezXRfhQiR3rJ6jsErfDN7M_0" # GANTIKAN DENGAN st.secrets["GEMINI_API"] SAAT DEPLOY
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

# --- Fungsi-fungsi Inti ---

# FUNGSI get_document_types DAN get_templates_for_type DIHAPUS KARENA TIDAK DIPERLUKAN LAGI

@st.cache_data
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

# GANTI FUNGSI run_ai_first_pass LAMA ANDA DENGAN INI

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
    "{prompt_text}"
    {context_text}

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
    7.  Untuk field "Bukti_BA", HARUS berupa ARRAY (list) dari OBJECTS JSON [{{ "NO": ..., "OBJEK": ..., "JUMLAH": ..., "DETAIL": ... }}].

    """
    # --- AKHIR PERUBAHAN ---

    # --- Bagian Debugging & Panggilan AI (Sama seperti sebelumnya) ---
    with st.expander("👀 Lihat Prompt Lengkap yang Dikirim ke AI"):
        st.code(prompt, language='markdown')

    raw_response_text = None
    try:
        response = model.generate_content(prompt)
        # ... (sisa kode try...except untuk memproses respons) ...
        # (Salin sisa blok try...except dari versi sebelumnya di sini)
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

# --- Tampilan & Logika Aplikasi (State Machine) ---
st.title("AI Document Generator")
# GANTI SELURUH BLOK elif st.session_state.page == "initial_input": DENGAN INI

# --- LANGKAH 1: INPUT AWAL DARI PENGGUNA ---
if st.session_state.page == "initial_input":
    st.header("Jelaskan Kebutuhan Anda")
    with st.form("initial_input_form", clear_on_submit=False): # clear_on_submit=False might help retain value
        st.info("Masukkan deskripsi kebutuhan Anda, termasuk estimasi budget.")
        # Berikan key unik ke text_area
        initial_prompt_input = st.text_area(
            "Deskripsi Kebutuhan:",
            height=150,
            placeholder="Contoh: Saya ingin mengajukan pengadaan Laptop Lenovo Yoga 7i 2in1 untuk Direktur Operasi yang baru karena pergantian pejabat. Budget per unit sekitar 17,5jt, butuh 1 unit. Mohon diproses segera, target tanggal 16/06/2025, RKAP 2025 sebesar 1,5 miliar, sudah terpakai 200juta, PR 1.165.000.000, budget pembuatan dokumen 1.628.894.000, nilai kontrak 2025 20.850.959.696, POS anggaran20jt Terlampir BA pemeriksaan kebutuhan nomor SI.02/18/6/2/D4.3.2/D/TPSS-25.(Sertakan: Nama Proyek/Barang, Alasan Kebutuhan, Jumlah, Estimasi Budget/Harga Satuan, Tanggal Target, No. Dokumen Referensi jika ada)",
            key="prompt_input_key" # Tambahkan key di sini
        )
        uploaded_files_list = st.file_uploader(
            "Unggah Dokumen Pendukung Apapun (Opsional, .pdf atau .txt)",
            type=['pdf', 'txt'], accept_multiple_files=True, key="initial_uploader"
        )
        submitted = st.form_submit_button("Analisis & Lanjut ke Pemrosesan Dokumen")

        if submitted:
            # --- PERBAIKAN: Baca nilai dari session_state menggunakan key ---
            prompt_value_from_state = st.session_state.prompt_input_key
            # -----------------------------------------------------------

            if not prompt_value_from_state: # Periksa nilai yang dibaca
                st.warning("Harap isi deskripsi kebutuhan.")
            else:
                # Lakukan analisis budget dengan LLM menggunakan nilai yang benar
                with st.spinner("Menganalisis budget dengan AI..."):
                    budget = analyze_budget_with_llm(prompt_value_from_state)
                st.session_state.budget = budget

                # Simpan data input awal (gunakan nilai yang sudah dibaca)
                uploaded_files_dict = {f.name: f for f in uploaded_files_list} if uploaded_files_list else {}
                st.session_state.initial_data = {
                    "prompt": prompt_value_from_state, # Simpan nilai yang benar
                    "files": uploaded_files_dict
                }

                # Muat resep (logika ini dipindahkan ke sini agar hanya berjalan saat submit valid)
                loaded_recipes = {}
                all_recipes_valid = True
                with st.spinner("Memuat resep dokumen yang dibutuhkan..."):
                    for pdf_path in TARGET_PDF_TEMPLATES:
                        recipe_data = load_recipe(pdf_path)
                        if recipe_data:
                            loaded_recipes[pdf_path] = recipe_data
                        else:
                            st.error(f"Gagal memuat resep untuk {os.path.basename(pdf_path)}. Proses dihentikan.")
                            all_recipes_valid = False
                            break

                if all_recipes_valid:
                    st.session_state.recipes_to_process = loaded_recipes
                    st.session_state.page = "processing" # Pindah halaman
                    # Reset state AI/JSON
                    st.session_state.ai_extracted_data = None
                    st.session_state.final_json_batch = None
                    # Jangan panggil rerun() di dalam form, Streamlit akan otomatis rerun setelah submit
                # else: Error sudah ditampilkan

    # Logika rerun dipindahkan ke luar form jika diperlukan, tapi biasanya tidak perlu setelah submit form
    # if st.session_state.page == "processing":
    #    st.rerun() # Pindah halaman setelah form selesai diproses

# --- LANGKAH 2 (BARU): PEMROSESAN AI & VERIFIKASI GABUNGAN ---
elif st.session_state.page == "processing":
    st.header("Langkah 2: Verifikasi & Lengkapi Data Gabungan")

    # Pastikan resep sudah dimuat
    if not st.session_state.get('recipes_to_process'):
        st.error("Resep dokumen tidak ditemukan. Kembali ke langkah awal.")
        if st.button("Kembali"): st.session_state.page = "initial_input"; st.rerun()
        st.stop()

    # --- Gabungkan Placeholders & Examples dari semua resep ---
    all_placeholders = {}
    all_examples = {}
    valid_recipes = True
    for pdf_path, recipe_data in st.session_state.recipes_to_process.items():
        if "placeholders" not in recipe_data or "examples" not in recipe_data:
            st.error(f"Struktur resep untuk {os.path.basename(pdf_path)} tidak valid.")
            valid_recipes = False; break
        # Gabungkan placeholder (ambil definisi dari resep pertama jika ada duplikat)
        for key, value in recipe_data["placeholders"].items():
            if key not in all_placeholders:
                all_placeholders[key] = value
        # Gabungkan contoh (ambil contoh dari resep pertama jika ada duplikat)
        for key, value in recipe_data["examples"].items():
            if key not in all_examples:
                 all_examples[key] = value

    if not valid_recipes: st.stop() # Hentikan jika ada resep tidak valid

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
            st.session_state.ai_extracted_data = ai_result if ai_result and "error" not in ai_result else {}
            st.session_state.ai_pass_done = True
        st.rerun()

    # --- Tampilkan Hasil AI & Formulir Verifikasi ---
    ai_data = st.session_state.ai_extracted_data

    st.info("AI telah mencoba mengekstrak informasi berikut untuk semua dokumen. Silakan periksa, perbaiki, dan lengkapi.")
    with st.expander("Lihat Hasil Mentah Ekstraksi AI"):
        st.json(ai_data if ai_data else {"Info": "Tidak ada data yang diekstrak AI."})

    with st.form("verification_form_combined"):
        st.markdown("**Data Gabungan untuk Dokumen (Silakan Edit/Lengkapi):**")
        widget_keys = {}

        # Loop melalui GABUNGAN placeholder yang BUKAN kalkulasi
        for key, value_obj in all_placeholders.items():
            if not key.endswith("_CALCULATED"):
                label = f"{key.replace('_', ' ').title()}:"
                ai_extracted_value = ai_data.get(key)
                instruction_or_default = value_obj.get("instruction") if isinstance(value_obj, dict) else value_obj
                widget_key = f"input_{key}"
                widget_keys[key] = widget_key

                # Buat input teks atau angka (editable)
                if isinstance(instruction_or_default, str):
                    default_value_txt = str(ai_extracted_value) if ai_extracted_value is not None else ""
                    if key in ["Isi_BA", "Bukti_BA", "Alasan", "Alasan_detail"] or len(default_value_txt) > 100:
                         st.text_area(label, value=default_value_txt, key=widget_key, height=100) # Tinggi dikurangi
                    else:
                         st.text_input(label, value=default_value_txt, key=widget_key)
                elif instruction_or_default is None or isinstance(instruction_or_default, (int, float)):
                    default_value_num = None
                    if ai_extracted_value is not None:
                        try:
                            cleaned_val_str = re.sub(r'(IDR|\s|\.|,-?$)', '', str(ai_extracted_value))
                            if cleaned_val_str: default_value_num = float(cleaned_val_str) if '.' in cleaned_val_str else int(cleaned_val_str)
                        except: default_value_num = None
                    st.number_input(label, value=default_value_num, format=None, key=widget_key)

        verification_submitted = st.form_submit_button("Verifikasi Selesai, Lanjutkan ke Pembuatan Dokumen")

        if verification_submitted:
            # Kumpulkan data yang diverifikasi pengguna
            user_verified_data = {key: st.session_state[widget_skey] for key, widget_skey in widget_keys.items()}

            # Lakukan kalkulasi (fungsi perform_calculations tidak perlu diubah)
            # Kita lakukan kalkulasi pada data gabungan
            st.session_state.final_combined_data = perform_calculations(all_placeholders, user_verified_data)

            st.session_state.page = "results"
            # Hapus state sementara
            if 'ai_pass_done' in st.session_state: del st.session_state['ai_pass_done']
            st.rerun()

# GANTI SELURUH BLOK elif st.session_state.page == "results": DENGAN INI

# --- LANGKAH 3 (BARU): HASIL AKHIR & PENGIRIMAN BATCH ---
elif st.session_state.page == "results":
    st.header("Langkah 3: Hasil Akhir & Pengiriman ke Google Docs")

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

                            if not google_doc_id:
                                st.error(f"ID Google Doc tidak ditemukan untuk {os.path.basename(pdf_path)}.")
                                continue # Lanjut ke dokumen berikutnya jika ID hilang

                            # Filter data gabungan, hanya ambil yang relevan untuk dokumen ini
                            data_for_this_doc = {
                                key: final_combined_data.get(key)
                                for key in placeholders_for_this_doc
                                if not key.endswith("_CALCULATED") # Jangan kirim key kalkulasi
                                and final_combined_data.get(key) is not None # Hanya kirim jika ada nilainya
                            }
                            # Tambahkan hasil kalkulasi (jika ada) dengan nama base key
                            for key in placeholders_for_this_doc:
                                 if key.endswith("_CALCULATED"):
                                      base_key = key.replace("_CALCULATED", "")
                                      if base_key in final_combined_data:
                                           data_for_this_doc[base_key] = final_combined_data[base_key]


                            batch_payload["documents"].append({
                                "google_doc_id": google_doc_id,
                                "data_to_fill": data_for_this_doc
                            })
                        # --- AKHIR MEMBANGUN PAYLOAD ---

                        if not batch_payload["documents"]:
                             st.warning("Tidak ada dokumen valid yang bisa dikirim.")
                        else:
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