import streamlit as st
import google.generativeai as genai
import json
import pandas as pd
import re
from docx import Document
from pypdf import PdfReader
from PIL import Image, ImageDraw, ImageFont
import io

# --- 1. KONFIGURASI API ---
API_KEY = "AIzaSyDqfdboe48QcfwcqsD61g3tNpZJo0fiwcc"

def init_ai():
    try:
        genai.configure(api_key=API_KEY)
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        target = next((m for m in models if '1.5-flash' in m), models[0] if models else None)
        return genai.GenerativeModel(target) if target else None
    except Exception as e:
        return None

model_ai = init_ai()

def clean_json_output(text):
    match = re.search(r'\[.*\]', text, re.DOTALL)
    return match.group(0) if match else text

def extract_text_from_file(uploaded_file):
    text = ""
    if uploaded_file.type == "text/plain":
        text = str(uploaded_file.read(), "utf-8")
    elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        doc = Document(uploaded_file)
        text = "\n".join([para.text for para in doc.paragraphs])
    elif uploaded_file.type == "application/pdf":
        reader = PdfReader(uploaded_file)
        for page in reader.pages:
            text += page.extract_text()
    return text

# --- FUNGSI GENERATE GAMBAR PREVIEW ---
def generate_preview_image(data, width, height, theme_style):
    img = Image.new('RGB', (width, height), color=theme_style['bg'])
    draw = ImageDraw.Draw(img)
    accent = theme_style['accent']
    margin = int(width * 0.05)
    y_pos = int(height * 0.1)
    draw.text((margin, y_pos), "INFOGRAPHIC PREVIEW", fill=accent)
    y_pos += int(height * 0.08)
    for item in data[:6]:
        h_text = item.get('h', '')
        d_text = item.get('d', '')
        draw.text((margin, y_pos), f"• {h_text}", fill=accent)
        y_pos += int(height * 0.04)
        draw.text((margin + 20, y_pos), f"{d_text[:45]}...", fill="#ffffff")
        y_pos += int(height * 0.08)
    draw.text((margin, height - 50), "Copyright © 2026 M. Husaeni", fill=accent)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def main():
    st.set_page_config(page_title="Pro Designer - M. Husaeni", layout="wide")
    
    st.markdown("""
        <style>
        .stButton>button { width: 100%; border-radius: 8px; height: 3.5em; background: linear-gradient(45deg, #d4af37, #aa8418); color: white; font-weight: bold; border: none; }
        .footer { position: fixed; left: 0; bottom: 0; width: 100%; background-color: #0a0a0a; color: #d4af37; text-align: center; padding: 10px; font-size: 14px; border-top: 1px solid #d4af37; z-index: 100; }
        .super-prompt { padding: 20px; background-color: #111; border-radius: 10px; border: 1px solid #d4af37; color: #eee; font-family: 'Courier New', monospace; white-space: pre-wrap; }
        .copyright-text { text-align: center; color: #d4af37; font-size: 16px; margin-top: -15px; margin-bottom: 20px; font-weight: 500; }
        .color-preview { width: 100%; height: 40px; border-radius: 5px; margin-bottom: 10px; border: 1px solid #555; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 12px; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<h1 style='text-align: center; color: #d4af37; margin-bottom: 0;'>🎨 VISUAL DESIGNER</h1>", unsafe_allow_html=True)
    st.markdown("<div style='text-align: center; color: #000000; font-size: 16px; margin-top: -15px; margin-bottom: 20px; font-weight: 500;'>Copyright © 2026 M. Husaeni</div>", unsafe_allow_html=True)
    st.write("---")

    # --- SIDEBAR: KONFIGURASI MEDIA ---
    st.sidebar.header("🎨 Konfigurasi Media")
    size_mode = st.sidebar.radio("Mode Ukuran", ["Pilih Preset", "Input Custom Pixel"])
    
    w, h = 1080, 1080
    final_ratio_desc = ""
    
    if size_mode == "Pilih Preset":
        media_size = st.sidebar.selectbox("Pilih Ukuran Target", [
            "Status WA / Reels (1080x1920)", "Instagram Portrait (1080x1350)", 
            "Instagram Feed (1080x1080)", "Flyer Cetak A4 (2480x3508)", "Slide Presentasi (1920x1080)"
        ])
        presets = {
            "Status WA / Reels (1080x1920)": (1080, 1920, "9:16 aspect ratio"),
            "Instagram Portrait (1080x1350)": (1080, 1350, "4:5 aspect ratio"),
            "Instagram Feed (1080x1080)": (1080, 1080, "1:1 aspect ratio"),
            "Flyer Cetak A4 (2480x3508)": (2480, 3508, "A4 format"),
            "Slide Presentasi (1920x1080)": (1920, 1080, "16:9 aspect ratio")
        }
        w, h, final_ratio_desc = presets[media_size]
    else:
        col_w, col_h = st.sidebar.columns(2)
        w = col_w.number_input("Lebar (px)", min_value=100, value=1080)
        h = col_h.number_input("Tinggi (px)", min_value=100, value=1080)
        final_ratio_desc = f"{w}x{h} px"

    st.sidebar.write("---")
    st.sidebar.header("🎨 Tema & Warna")
    
    layout_mode = st.sidebar.selectbox("Gaya Komposisi", ["Editorial Spread", "Floating Elements", "Cinematic Poster"])
    
    # Koleksi Tema yang Diperbanyak
    themes = {
        "Royal Gold": {"bg": "#0a0a0a", "accent": "#d4af37", "label": "Emas & Hitam"},
        "Emerald Silk": {"bg": "#062c21", "accent": "#fbbf24", "label": "Hijau & Kuning"},
        "Desert Sand": {"bg": "#2d1b10", "accent": "#e2b464", "label": "Coklat & Pasir"},
        "Midnight Silver": {"bg": "#021027", "accent": "#bdc3c7", "label": "Biru & Perak"},
        "Deep Purple": {"bg": "#1a0033", "accent": "#bf00ff", "label": "Ungu & Neon"},
        "Minimalist White": {"bg": "#ffffff", "accent": "#333333", "label": "Putih & Abu"},
        "Terracotta": {"bg": "#4a2c2a", "accent": "#f1c40f", "label": "Bata & Kuning"},
        "Oceanic": {"bg": "#0a3d62", "accent": "#60a3bc", "label": "Biru Laut"}
    }
    
    theme_choice = st.sidebar.selectbox("Pilih Tema Warna", list(themes.keys()))
    style = themes[theme_choice]
    
    # TAMPILAN PREVIEW WARNA DI SIDEBAR
    st.sidebar.markdown(f"""
        <div class='color-preview' style='background-color: {style["bg"]}; color: {style["accent"]}; border: 2px solid {style["accent"]}'>
            CONTOH TEKS AKSEN
        </div>
        <div style='display: flex; gap: 5px;'>
            <div style='flex: 1; height: 20px; background: {style["bg"]}; border: 1px solid #555; border-radius: 3px;'></div>
            <div style='flex: 1; height: 20px; background: {style["accent"]}; border: 1px solid #555; border-radius: 3px;'></div>
        </div>
        <p style='font-size: 11px; text-align: center; margin-top: 5px;'>Background vs Aksen ({style["label"]})</p>
    """, unsafe_allow_html=True)

    # --- MAIN PANEL ---
    tab1, tab2, tab3 = st.tabs(["🚀 Idea Corner (AI)", "✍️ Manual Craft (Copas)", "📂 Import File"])

    if 'data_final' not in st.session_state:
        st.session_state.data_final = []

    with tab1:
        col1, col2 = st.columns([1.5, 1])
        with col1:
            category = st.selectbox("Kategori:", ["Ramadhan", "Marketing", "Haji/Umroh", "Pendidikan", "Umum"])
            topic_ai = st.text_input("Topik Spesifik:", placeholder="Misal: Keutamaan Puasa", key="topic_ai")
            if st.button("Rancang Desain & Konten"):
                if topic_ai and model_ai:
                    with st.spinner("AI sedang merancang..."):
                        prompt = f"Art Director mode. Topic: '{topic_ai}' Category {category}. Return ONLY JSON array: [{{'v': 'Visual focus object', 'h': 'Header', 'd': 'Description (max 10 words)', 's': 'Source'}}]"
                        response = model_ai.generate_content(prompt)
                        st.session_state.data_final = json.loads(clean_json_output(response.text))
                        st.rerun()

    with tab2:
        user_text = st.text_area("Tempel Teks Anda:", height=200)
        if st.button("Konversi ke Visual Pro"):
            if user_text and model_ai:
                with st.spinner("Mengekstrak visual..."):
                    prompt = f"Extract points into dynamic visual JSON: [{{'v': 'Visual object', 'h': 'Header', 'd': 'Description', 's': 'User Content'}}]. Text: {user_text}"
                    response = model_ai.generate_content(prompt)
                    st.session_state.data_final = json.loads(clean_json_output(response.text))
                    st.rerun()

    with tab3:
        uploaded_file = st.file_uploader("Upload file", type=["pdf", "docx", "txt"])
        if st.button("Proses Dokumen"):
            if uploaded_file and model_ai:
                with st.spinner("Membaca dokumen..."):
                    try:
                        file_text = extract_text_from_file(uploaded_file)
                        prompt = f"Summarize doc into key visual points. Text: {file_text[:3500]}. Return ONLY JSON array: [{{'v': 'Visual object', 'h': 'Header', 'd': 'Description', 's': 'Source doc'}}]"
                        response = model_ai.generate_content(prompt)
                        st.session_state.data_final = json.loads(clean_json_output(response.text))
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

    # --- EDITOR ---
    st.write("---")
    st.subheader("🖋️ Editorial Editor (Tentukan Fokus Visual)")
    df_editor = pd.DataFrame(st.session_state.data_final) if st.session_state.data_final else pd.DataFrame([{"v": "Objek Visual", "h": "", "d": "", "s": ""}])
    final_df = st.data_editor(df_editor, num_rows="dynamic", use_container_width=True)

    # --- OUTPUT BRIEF ---
    st.write("---")
    col_brief, col_download = st.columns([1, 1])
    
    with col_brief:
        st.subheader("🎬 HIGH-END DESIGN BRIEF")
        super_prompt = f"""
[EXECUTIVE CREATIVE DIRECTION]
Target Specs: {final_ratio_desc}.
Style: Professional {layout_mode}, photorealistic, 8k resolution.
Theme: {theme_choice} (BG: {style['bg']}, Accent: {style['accent']}).

[ELEMENTS TO RENDER]:
{final_df.to_dict('records')}

[FINAL RULE]: Render as a high-end editorial masterpiece.
        """
        st.code(super_prompt, language="text")

    st.markdown("""<div class="footer">Copyright © 2026 M. Husaeni | Premium Design Engine</div>""", unsafe_allow_html=True)

if __name__ == "__main__":
    main()