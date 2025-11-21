import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import re
import time

# --- AYARLAR ---
SHEET_NAME = "Kreatif_Sistem_DB"  # Google Sheet dosyanın adı
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# --- GOOGLE SHEETS BAĞLANTISI ---
@st.cache_resource
def get_connection():
    """Google Sheets'e bağlanır (Secrets kullanarak)."""
    try:
        # Streamlit Secrets'tan bilgileri al
        creds_dict = dict(st.secrets["gcp_service_account"])
        
        # private_key içindeki \n karakterlerini düzelt (Burası çok önemli)
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"Google Bağlantı Hatası: {e}")
        return None

def get_data(worksheet_name):
    """Belirtilen sekmedeki verileri çeker."""
    client = get_connection()
    if client:
        try:
            sheet = client.open(SHEET_NAME)
            worksheet = sheet.worksheet(worksheet_name)
            data = worksheet.get_all_records()
            return pd.DataFrame(data)
        except Exception as e:
            # Hata vermeden önce boş dataframe dön, belki sayfa boştur
            return pd.DataFrame()
    return pd.DataFrame()

def append_row(worksheet_name, row_data_list):
    """Belirtilen sekmeye yeni satır ekler."""
    client = get_connection()
    if client:
        try:
            sheet = client.open(SHEET_NAME)
            worksheet = sheet.worksheet(worksheet_name)
            worksheet.append_row(row_data_list)
            return True
        except Exception as e:
            st.error(f"Kayıt Hatası ({worksheet_name}): {e}")
            return False
    return False

def update_cell_value(worksheet_name, col_name, old_val, new_val):
    """Hücre güncelleme."""
    client = get_connection()
    if client:
        try:
            sheet = client.open(SHEET_NAME)
            worksheet = sheet.worksheet(worksheet_name)
            cell = worksheet.find(old_val)
            if cell:
                worksheet.update_cell(cell.row, cell.col, new_val)
                return True
        except Exception as e:
            st.error(f"Güncelleme Hatası: {e}")
    return False

def delete_row_by_value(worksheet_name, value):
    """Satır silme."""
    client = get_connection()
    if client:
        try:
            sheet = client.open(SHEET_NAME)
            worksheet = sheet.worksheet(worksheet_name)
            cell = worksheet.find(value)
            if cell:
                worksheet.delete_rows(cell.row)
                return True
        except Exception as e:
            st.error(f"Silme Hatası: {e}")
    return False

# --- USER VE COUNTRY FONKSİYONLARI ---

def get_users():
    df = get_data("users")
    if not df.empty and "Isim" in df.columns:
        return df['Isim'].tolist()
    # Varsayılanlar (Eğer sheet boşsa burayı doldurur)
    defaults = ["🦁 Talha", "🦅 Emir", "🌸 Aslı", "✨ Ilgın", "💎 Duru", "🎨 Ebru", "🎸 Özgün"]
    if df.empty:
        for name in defaults:
            add_new_user(name)
        return defaults
    return []

def add_new_user(name):
    if name:
        name = name.strip().title()
        current_list = get_users()
        if name not in current_list:
            return append_row("users", [name])
    return False

def update_user_name(old_name, new_name):
    if new_name:
        new_name = new_name.strip().title()
        return update_cell_value("users", "Isim", old_name, new_name)
    return False

def delete_user(name):
    return delete_row_by_value("users", name)

def get_countries():
    df = get_data("countries")
    if not df.empty and "Kod" in df.columns:
        return df['Kod'].tolist()
    defaults = ["ES", "PTBR", "VIE", "EN", "RU", "AR", "FR", "TR", "DE", "IT", "SR", "RO", "PL", "KR", "BG", "HE", "HU", "CZ"]
    if df.empty:
        for code in defaults:
            add_new_country(code)
        return defaults
    return []

def add_new_country(code):
    if code:
        code = code.upper()
        current = get_countries()
        if code not in current:
            return append_row("countries", [code])
    return False

# --- KOD ÜRETME MANTIĞI ---
def get_scenario_number(scenario_str):
    if pd.isna(scenario_str): return None
    match = re.search(r'(\d+)$', str(scenario_str))
    if match: return match.group(1) 
    return None

def get_next_alt_info(scenario_input):
    df = get_data("creative_codes")
    target_num = get_scenario_number(scenario_input)
    
    max_alt = 0
    found_orj = False
    
    if not target_num or df.empty:
        return 0, False
    
    for index, row in df.iterrows():
        db_scenario = str(row['Senaryo'])
        db_code = str(row['Tam_Kod'])
        db_num = get_scenario_number(db_scenario)
        
        if db_num == target_num and "TU" in scenario_input and "TU" in db_scenario:
             parts = db_code.split('_')
             suffix = parts[-1]
             if suffix == 'ORJ':
                 found_orj = True
             elif suffix.startswith('ALT'):
                try:
                    num = int(suffix.replace('ALT', ''))
                    if num > max_alt: max_alt = num
                except: pass
    return max_alt, found_orj

def generate_single_code(prefix, scenario):
    current_max, found_orj = get_next_alt_info(scenario)
    if current_max > 0: return f"{prefix}_{scenario}_ALT{current_max + 1}"
    if found_orj: return f"{prefix}_{scenario}_ALT1"
    return f"{prefix}_{scenario}_ORJ"

def save_code(user, prefix, scenario, full_code, record_type):
    tarih = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')
    return append_row("creative_codes", [tarih, user, prefix, scenario, full_code, record_type])

def get_data_by_type(record_type):
    df = get_data("creative_codes")
    if not df.empty and 'Tur' in df.columns:
        filtered_df = df[df['Tur'] == record_type]
        return filtered_df.sort_index(ascending=False)
    return pd.DataFrame()

# --- ARAYÜZ (UI) ---
st.set_page_config(page_title="Kreatif Kod Pro", page_icon="🔥", layout="wide")

# CSS
st.markdown("""
<style>
    .stPills { justify-content: center; }
    [data-testid="stSidebar"] { background-color: #262730; border-right: 1px solid #4b5563; }
    div[data-testid="stPills"] button[aria-selected="true"] { background-color: #4b5563 !important; color: white !important; border-color: #4b5563 !important; }
    div[data-testid="stPills"] button:hover { border-color: #6b7280 !important; color: #e5e7eb !important; }
    div[data-testid="stPills"] button[aria-selected="true"]:hover { color: white !important; }
    div.stButton > button[kind="primary"] { background-color: #374151 !important; border-color: #374151 !important; }
    div.stButton > button[kind="secondary"] { border-color: #ef4444 !important; color: #ef4444 !important; }
    div.stButton > button[kind="secondary"]:hover { background-color: #ef4444 !important; color: white !important; }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.title("👤 Profil Seç")
    current_users = get_users()
    default_selection = current_users[0] if current_users else None
    selected_user = st.pills("Ekip:", current_users, default=default_selection, selection_mode="single")
    
    if selected_user:
        st.markdown("---")
        st.caption("✏️ Seçili Profili Düzenle")
        col_edit, col_save, col_del = st.columns([3, 1.5, 1.5])
        
        with col_edit:
            edit_new_name = st.text_input("Edit", value=selected_user, label_visibility="collapsed", key=f"edit_{selected_user}")
        with col_save:
            if st.button("Kaydet"):
                if edit_new_name and edit_new_name != selected_user:
                    if update_user_name(selected_user, edit_new_name):
                        st.success("✅")
                        time.sleep(1)
                        st.rerun()
        with col_del:
            if st.button("🗑️ Sil", type="secondary"):
                if delete_user(selected_user):
                    st.warning("Silindi!")
                    time.sleep(1)
                    st.rerun()
    
    st.markdown("---")
    with st.expander("➕ Yeni Kişi Ekle"):
        new_user_name = st.text_input("İsim", placeholder="İsim Yaz")
        if st.button("Listeye Ekle"):
            if new_user_name:
                if add_new_user(new_user_name):
                    st.success("Eklendi!")
                    time.sleep(1)
                    st.rerun()

# --- ANA EKRAN ---
st.title("🔥 Kreatif Kod Yönetimi (Google Sheets ☁️)")

if not selected_user:
    st.warning("⚠️ Lütfen sol menüden bir profil seçiniz veya yeni ekleyiniz!")
    st.stop()

st.caption(f"Aktif Kullanıcı: **{selected_user}**")

tab1, tab2, tab3 = st.tabs(["🆕 Yeni Kreatif", "🌍 Lokalizasyon", "📝 Manuel / Geçmiş Giriş"])

# TAB 1
with tab1:
    c1, c2 = st.columns([2, 1])
    with c1:
        st.subheader("1. Ülke Seç")
        current_countries = get_countries()
        options = current_countries + ["CUSTOM"]
        selected_pill = st.pills("Ülke Kodları", options, default="ES", selection_mode="single")
        
        final_prefix = selected_pill
        if selected_pill == "CUSTOM":
            custom_input = st.text_input("Yeni Ülke Kodu (Örn: KZ)").upper()
            if custom_input: final_prefix = custom_input
    with c2:
        st.subheader("2. Senaryo")
        t1_scenario = st.text_input("Senaryo Kodu", value="TU02", help="TU02, TUES02 vb.").upper()
        st.write("") 
        st.write("") 
        if st.button("🚀 KODU ÜRET", type="primary", use_container_width=True):
            if final_prefix and t1_scenario and final_prefix != "CUSTOM":
                if selected_pill == "CUSTOM": add_new_country(final_prefix)
                
                new_code = generate_single_code(final_prefix, t1_scenario)
                save_code(selected_user, final_prefix, t1_scenario, new_code, "YENI")
                st.success(f"✅ Oluşturuldu: {new_code}")
                st.header(f"`{new_code}`")
                if selected_pill == "CUSTOM": 
                    time.sleep(1)
                    st.rerun()
            else:
                st.error("Eksik bilgi.")
    st.markdown("---")
    st.subheader("📜 Yeni Kod Geçmişi (Sheet)")
    st.dataframe(get_data_by_type("YENI"), use_container_width=True, hide_index=True)

# TAB 2
with tab2:
    st.info("Mevcut bir kodu referans alarak diğer ülkelere kopyala.")
    c_ref, c_dum = st.columns([1, 2])
    with c_ref:
        source_code_input = st.text_input("Referans Kod (Örn: EN_TU02_ALT2)")
    
    target_scenario, target_suffix = "", ""
    if source_code_input:
        try:
            parts = source_code_input.split('_')
            if len(parts) >= 3:
                target_scenario, target_suffix = parts[1], parts[-1]
                st.caption(f"Algılanan: **{target_scenario}** | **{target_suffix}**")
        except: st.warning("Format algılanamadı.")
    
    st.divider()
    st.subheader("Hedef Ülkeleri Seç")
    current_countries_loc = get_countries()
    selected_targets_pills = st.pills("Ülkeler", current_countries_loc, selection_mode="multi")
    
    col_cust, col_btn = st.columns([1, 1])
    with col_cust: custom_target = st.text_input("Listede olmayan ülke?", placeholder="Örn: JP")
    with col_btn:
        st.write("") 
        st.write("") 
        if st.button("🌍 LOKALİZASYONLARI KAYDET", type="primary", use_container_width=True):
            if target_scenario and target_suffix:
                final_targets = list(selected_targets_pills) if selected_targets_pills else []
                if custom_target:
                    custom_clean = custom_target.upper()
                    final_targets.append(custom_clean)
                    add_new_country(custom_clean)
                
                if not final_targets: st.error("Hiç ülke seçmedin!")
                else:
                    saved_count = 0
                    for country in final_targets:
                        final_code = f"{country}_{target_scenario}_{target_suffix}"
                        if save_code(selected_user, country, target_scenario, final_code, "LOKAL"):
                            saved_count += 1
                    st.success(f"✅ {saved_count} kod Sheet'e girildi.")
                    if custom_target: 
                        time.sleep(1)
                        st.rerun()
            else: st.error("Referans kod girilmedi.")
    st.markdown("---")
    st.subheader("🌍 Lokalizasyon Geçmişi")
    st.dataframe(get_data_by_type("LOKAL"), use_container_width=True, hide_index=True)

# TAB 3
with tab3:
    st.warning("⚠️ Geçmiş verileri girmek veya özel kod oluşturmak için.")
    col_man_1, col_man_2 = st.columns([2, 1])
    with col_man_1: manual_code_entry = st.text_input("Tam Kod (Yapıştır)", placeholder="Örn: ES_TU81_ALT22")
    with col_man_2:
        st.write("")
        st.write("")
        if st.button("💾 VERİTABANINA EKLE", type="primary", use_container_width=True):
            if manual_code_entry:
                try:
                    parts = manual_code_entry.split('_')
                    if len(parts) >= 3:
                        m_pref, m_scen, m_full = parts[0].upper(), parts[1].upper(), manual_code_entry.upper()
                        add_new_country(m_pref)
                        save_code(selected_user, m_pref, m_scen, m_full, "MANUEL")
                        st.success(f"✅ {m_full} eklendi!")
                        time.sleep(1)
                        st.rerun()
                    else: st.error("Hatalı format!")
                except Exception as e: st.error(f"Hata: {e}")
            else: st.error("Kod girmediniz.")
    st.markdown("---")
    st.subheader("📝 Manuel Giriş Geçmişi")
    st.dataframe(get_data_by_type("MANUEL"), use_container_width=True, hide_index=True)
