import streamlit as st
import re
import os
import base64
from streamlit_pdf_viewer import pdf_viewer
from PyPDF2 import PdfReader

# --- Core Logic (Tidak ada perubahan di sini) ---

def extract_budget(text):
    """Mengekstrak nilai budget dari string."""
    cleaned_text = text.lower()
    cleaned_text = re.sub(r',[\d]+', '', cleaned_text)
    cleaned_text = re.sub(r'(rp|\s|\.)', '', cleaned_text)
    patterns = [
        r'(\d+)(m|miliar)', r'(\d+)(jt|juta|million)',
        r'(\d+)(k|ribu)', r'(\d+)'
    ]
    for pattern in patterns:
        match = re.search(pattern, cleaned_text)
        if match:
            value_str = match.group(1)
            unit = match.group(2) if len(match.groups()) > 1 else ""
            value = int(value_str)
            if unit in ['jt', 'juta', 'million']: return value * 1_000_000
            if unit in ['k', 'ribu']: return value * 1_000
            if unit in ['m', 'miliar']: return value * 1_000_000_000
            return value
    return None

# --- Helper Function untuk Menampilkan Contoh Dokumen ---

def display_document_examples(doc_folder):
    """Menampilkan file PDF di dalam folder sebagai tombol yang bisa diklik."""
    st.subheader(f"Contoh Template untuk: {doc_folder}")
    if not os.path.isdir(doc_folder):
        st.warning(f"Folder '{doc_folder}' tidak ditemukan.")
        return
    try:
        pdf_files = [f for f in os.listdir(doc_folder) if f.lower().endswith('.pdf')]
        if not pdf_files:
            st.info(f"Tidak ada file contoh PDF yang ditemukan di folder '{doc_folder}'.")
            return
        st.write("Klik pada salah satu template untuk melihat pratinjau di bawah:")
        for file in pdf_files:
            if st.button(file, key=file):
                file_path = os.path.join(doc_folder, file)
                with open(file_path, "rb") as f:
                    st.session_state.pdf_binary_data = f.read()
                    # Re-open the binary stream for PdfReader
                    f.seek(0)
                    reader = PdfReader(f)
                    st.session_state.total_pages = len(reader.pages)
                st.session_state.selected_pdf_path = file_path
                st.session_state.current_page = 1 # Reset ke halaman pertama
    except Exception as e:
        st.error(f"Terjadi kesalahan saat mengakses folder '{doc_folder}': {e}")

# --- Antarmuka Pengguna Streamlit ---

st.set_page_config(page_title="Document Generator", page_icon=":pencil:", layout="wide")

# Inisialisasi session state
if 'analysis_done' not in st.session_state: st.session_state.analysis_done = False
if 'required_docs' not in st.session_state: st.session_state.required_docs = []
if 'budget' not in st.session_state: st.session_state.budget = None
if 'selected_pdf_path' not in st.session_state: st.session_state.selected_pdf_path = None
if 'current_page' not in st.session_state: st.session_state.current_page = 1
if 'total_pages' not in st.session_state: st.session_state.total_pages = 0
if 'pdf_binary_data' not in st.session_state: st.session_state.pdf_binary_data = None

# --- Bagian Atas: Antarmuka Chat & Analisis ---
st.write("# Document Generator")

with st.form(key='analysis_form'):
    input_text = st.text_area("Deskripsi Kebutuhan:", height=150, placeholder="Contoh: Saya ingin memperpanjang lisensi Adobe dengan budget sekitar 300jt rupiah...")
    submitted = st.form_submit_button("Analisis Deskripsi")

if submitted:
    st.session_state.selected_pdf_path = None
    if input_text:
        st.session_state.budget = extract_budget(input_text)
        st.session_state.analysis_done = True
        if st.session_state.budget is not None:
            if st.session_state.budget >= 300_000_000:
                st.session_state.required_docs = ["BAP", "Review Pekerjaan", "RAB (D. Bidang)", "RKS(D. Bidang)"]
            else:
                st.session_state.required_docs = ["BAP", "Draf nota dinas izin prinsip(SVP)", "RAB", "RKS", "Nota Dina izin Prinsip"]
        else:
            st.session_state.required_docs = []
    else:
        st.error("Silakan masukkan deskripsi terlebih dahulu.")
        st.session_state.analysis_done = False

if st.session_state.analysis_done:
    st.write("---")
    budget = st.session_state.budget
    if budget is None:
        st.warning("Tidak ada budget yang ditemukan.")
    else:
        formatted_budget = f"Rp {budget:,.0f}".replace(",", ".")
        st.info(f"**Budget yang terdeteksi:** {formatted_budget}")
        decision_text = "**Keputusan:** b (Budget >= Rp 300.000.000)" if budget >= 300_000_000 else "**Keputusan:** a (Budget < Rp 300.000.000)"
        st.success(decision_text)
        st.write("**Dokumen yang dibutuhkan:**")
        for doc in st.session_state.required_docs:
            st.markdown(f"- {doc}")
        if st.session_state.required_docs:
            st.write("---")
            doc_choice = st.text_input("Dokumen apa yang ingin saya bantu buat?", key="doc_choice_input")
            if doc_choice:
                chosen_doc = next((doc for doc in st.session_state.required_docs if doc_choice.lower() in doc.lower()), None)
                if chosen_doc:
                    display_document_examples(chosen_doc)
                else:
                    st.warning(f"Tidak ada dokumen yang cocok dengan '{doc_choice}'.")

# --- Bagian Bawah: Penampil PDF (hanya muncul jika PDF dipilih) ---
if st.session_state.selected_pdf_path:
    st.write("---")
    st.subheader("Pratinjau Dokumen")

    # Definisikan callback untuk memperbarui halaman dari input angka
    def jump_to_page():
        st.session_state.current_page = st.session_state.page_jumper

    nav_cols = st.columns([2, 2, 3, 5])

    # Tombol "Sebelumnya"
    if nav_cols[0].button('⬅️ Sebelumnya', use_container_width=True):
        if st.session_state.current_page > 1:
            st.session_state.current_page -= 1

    # Tombol "Berikutnya"
    if nav_cols[1].button('Berikutnya ➡️', use_container_width=True):
        if st.session_state.current_page < st.session_state.total_pages:
            st.session_state.current_page += 1

    # Input Halaman
    nav_cols[2].number_input(
        f'Halaman (dari {st.session_state.total_pages})',
        min_value=1,
        max_value=st.session_state.total_pages,
        key='page_jumper',
        on_change=jump_to_page # Gunakan callback untuk penanganan yang lebih baik
    )
    
    # --- Tampilkan PDF ---
    pdf_viewer(
        input=st.session_state.pdf_binary_data,
        width=700,
        pages_to_render=[st.session_state.current_page],
        # --- DIPERBAIKI: Key sekarang dinamis untuk memaksa render ulang saat halaman berubah ---
        key=f"pdf_viewer_{st.session_state.selected_pdf_path}_{st.session_state.current_page}"
    )

