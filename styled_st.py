import streamlit as st
import re
import os
import base64
from streamlit_pdf_viewer import pdf_viewer
from PyPDF2 import PdfReader

# --- Custom CSS Styling ---
def load_custom_css():
    st.markdown("""
    <style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@400;600;700&family=Poppins:wght@400;600;700&display=swap');
    
    /* Main background with pattern */
    .stApp {
        background: linear-gradient(135deg, #E8F4F8 0%, #D4E9F7 100%);
        font-family: 'Poppins', sans-serif;
    }
    
    /* Add decorative pattern overlay */
    .stApp::before {
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-image: 
            radial-gradient(circle at 20% 50%, rgba(173, 216, 230, 0.1) 0%, transparent 50%),
            radial-gradient(circle at 80% 80%, rgba(135, 206, 235, 0.1) 0%, transparent 50%);
        pointer-events: none;
        z-index: 0;
    }
    
    /* Main title styling */
    h1 {
        font-family: 'Fredoka', sans-serif !important;
        color: #2B4C7E !important;
        font-size: 3rem !important;
        font-weight: 700 !important;
        text-align: center !important;
        text-shadow: 3px 3px 6px rgba(0,0,0,0.1);
        margin-bottom: 2rem !important;
        letter-spacing: 2px !important;
    }
    
    /* Subheader styling */
    h2, h3 {
        font-family: 'Fredoka', sans-serif !important;
        color: #2B4C7E !important;
        font-weight: 600 !important;
    }
    
    /* Form container styling */
    .stForm {
        background: white;
        padding: 2rem;
        border-radius: 20px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        border: 3px solid #87CEEB;
        position: relative;
    }
    
    /* Text area styling */
    .stTextArea textarea {
        border-radius: 15px !important;
        border: 2px solid #87CEEB !important;
        font-family: 'Poppins', sans-serif !important;
        padding: 1rem !important;
        background: #F8FCFF !important;
    }
    
    .stTextArea textarea:focus {
        border-color: #567EBB !important;
        box-shadow: 0 0 0 2px rgba(86, 126, 187, 0.2) !important;
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, #567EBB 0%, #2B4C7E 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 15px !important;
        padding: 0.75rem 2rem !important;
        font-weight: 600 !important;
        font-family: 'Fredoka', sans-serif !important;
        font-size: 1.1rem !important;
        box-shadow: 0 4px 15px rgba(43, 76, 126, 0.3) !important;
        transition: all 0.3s ease !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(43, 76, 126, 0.4) !important;
    }
    
    /* Info, success, warning boxes */
    .stAlert {
        border-radius: 15px !important;
        border: 2px solid !important;
        padding: 1rem !important;
        margin: 1rem 0 !important;
    }
    
    div[data-baseweb="notification"] {
        border-radius: 15px !important;
        background: white !important;
        border: 2px solid #87CEEB !important;
    }
    
    /* Info box - blue */
    .stAlert[kind="info"], div.stMarkdown > div > div[data-testid="stNotificationContentInfo"] {
        background: linear-gradient(135deg, #E3F2FD 0%, #BBDEFB 100%) !important;
        border-color: #567EBB !important;
    }
    
    /* Success box - green */
    .stAlert[kind="success"], div.stMarkdown > div > div[data-testid="stNotificationContentSuccess"] {
        background: linear-gradient(135deg, #E8F5E9 0%, #C8E6C9 100%) !important;
        border-color: #66BB6A !important;
    }
    
    /* Warning box - orange */
    .stAlert[kind="warning"], div.stMarkdown > div > div[data-testid="stNotificationContentWarning"] {
        background: linear-gradient(135deg, #FFF3E0 0%, #FFE0B2 100%) !important;
        border-color: #FFA726 !important;
    }
    
    /* Document list styling */
    .stMarkdown ul {
        list-style: none !important;
        padding-left: 0 !important;
    }
    
    .stMarkdown ul li {
        background: white;
        margin: 0.5rem 0;
        padding: 1rem;
        border-radius: 12px;
        border-left: 5px solid #567EBB;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        font-weight: 500;
    }
    
    .stMarkdown ul li::before {
        content: "📄 ";
        margin-right: 0.5rem;
    }
    
    /* Text input styling */
    .stTextInput input {
        border-radius: 12px !important;
        border: 2px solid #87CEEB !important;
        padding: 0.75rem !important;
        font-family: 'Poppins', sans-serif !important;
        background: white !important;
    }
    
    .stTextInput input:focus {
        border-color: #567EBB !important;
        box-shadow: 0 0 0 2px rgba(86, 126, 187, 0.2) !important;
    }
    
    /* Number input styling */
    .stNumberInput input {
        border-radius: 12px !important;
        border: 2px solid #87CEEB !important;
        background: white !important;
    }
    
    /* Navigation buttons */
    div[data-testid="column"] .stButton > button {
        width: 100% !important;
        background: white !important;
        color: #2B4C7E !important;
        border: 2px solid #567EBB !important;
        font-size: 0.9rem !important;
    }
    
    div[data-testid="column"] .stButton > button:hover {
        background: #567EBB !important;
        color: white !important;
    }
    
    /* PDF viewer container */
    .stMarkdown h3 {
        color: #2B4C7E !important;
        border-bottom: 3px solid #87CEEB;
        padding-bottom: 0.5rem;
        margin-bottom: 1rem;
    }
    
    /* Divider styling */
    hr {
        border: none !important;
        height: 3px !important;
        background: linear-gradient(90deg, transparent, #87CEEB, transparent) !important;
        margin: 2rem 0 !important;
    }
    
    h1::before {
        content: url('C:/Users/revel/Desktop/code/pelindo/Document_Maker/elements/danantara.png');
        display: inline-block;
        width: 24px;
        height: 24px;
        margin-right: 0.5rem;
    }

    h1::after {
        content: url('elements/petikemas.png');
        display: inline-block;
        width: 24px;
        height: 24px;
        margin-left: 0.5rem;
    }
    
    /* Scrollbar styling */
    ::-webkit-scrollbar {
        width: 12px;
    }
    
    ::-webkit-scrollbar-track {
        background: #E8F4F8;
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(180deg, #567EBB, #2B4C7E);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #2B4C7E;
    }
    
    /* Add floating decorative elements */
    @keyframes float {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-10px); }
    }
    
    /* Strong text styling */
    strong {
        color: #2B4C7E !important;
        font-weight: 600 !important;
    }
    </style>
    """, unsafe_allow_html=True)

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

st.set_page_config(page_title="Document Generator", page_icon="", layout="wide")

# Load custom CSS
load_custom_css()

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
                st.session_state.required_docs = ["BAP", "Draf nota dinas izin prinsip (SVP)", "RAB", "RKS", "Nota Dina izin Prinsip"]
        else:
            st.session_state.required_docs = []
    else:
        st.error("Silakan masukan deskripsi terlebih dahulu.")
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
    if nav_cols[0].button('Sebelumnya', use_container_width=True):
        if st.session_state.current_page > 1:
            st.session_state.current_page -= 1

    # Tombol "Berikutnya"
    if nav_cols[1].button('Berikutnya', use_container_width=True):
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
        width=500,
        pages_to_render=[st.session_state.current_page],
        # --- DIPERBAIKI: Key sekarang dinamis untuk memaksa render ulang saat halaman berubah ---
        key=f"pdf_viewer_{st.session_state.selected_pdf_path}_{st.session_state.current_page}"
    )
