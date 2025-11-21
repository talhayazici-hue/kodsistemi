import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import re
import time

# --- AYARLAR ---
SHEET_NAME = "Kreatif_Sistem_DB"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
INITIAL_USERS = ["🦁 Talha", "🦅 Emir", "🌸 Aslı", "✨ Ilgın", "💎 Duru", "🎨 Ebru", "🎸 Özgün"]
INITIAL_COUNTRIES = ["ES", "PTBR", "VIE", "EN", "RU", "AR", "FR", "TR", "DE", "IT", "SR", "RO", "PL", "KR", "BG", "HE", "HU", "CZ"]

# --- GOOGLE BAĞLANTISI ---
@st.cache_resource
def get_connection():
    try:
        if "gcp_service_account" not in st.secrets: return None
        creds_dict = dict(st.secrets["gcp_service_account"])
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        client = gspread.authorize(creds)
        return client
    except Exception: return None

# --- VERİ OKUMA (HIZLANDIRILMIŞ & GÜVENLİ) ---
@st.cache_data(ttl=10) # 10 saniye cache
def get_data(worksheet_name):
    client = get_connection()
    if client:
        try:
            sheet = client.open(SHEET_NAME)
            try:
                worksheet = sheet.worksheet(worksheet_name)
            except:
                # Sayfa yoksa oluştur
                worksheet = sheet.add_worksheet(title=worksheet_name, rows="100", cols="20")
                if worksheet_name == "users": worksheet.append_row(["Isim"])
                elif worksheet_name == "countries": worksheet.append_row(["Kod"])
                elif worksheet_name == "creative_codes": worksheet.append_row(["Tarih", "Kullanici", "Prefix", "Senaryo", "Tam_Kod", "Tur"])
            
            data = worksheet.get_all_records()
            return pd.DataFrame(data)
        except: return pd.DataFrame()
    return pd.DataFrame()

# --- VERİ YAZMA ---
def append_row(worksheet_name, row_data_list):
    client = get_connection()
    if client:
        try:
            sheet = client.open(SHEET_NAME)
            worksheet = sheet.worksheet(worksheet_name)
            worksheet.append_row(row_data_list)
            get_data.clear() # İşlem bitince cache temizle
            return True
        except Exception as e: st.error(f"Kayıt hatası: {e}")
    return False

def update_cell_value(worksheet_name, col_name, old_val, new_val):
    client = get_connection()
    if client:
        try:
            sheet = client.open(SHEET_NAME)
            worksheet = sheet.worksheet(worksheet_name)
            cell = worksheet.find(old_val)
            if cell:
                worksheet.update_cell(cell.row, cell.col, new_val)
                get_data.clear()
                return True
        except Exception as e: st.error(f"Güncelleme hatası: {e}")
    return False

def delete_row_by_value(worksheet_name, value):
    client = get_connection()
    if client:
        try:
            sheet = client.open(SHEET_NAME)
            worksheet = sheet.worksheet(worksheet_name)
            cell = worksheet.find(value)
            if cell:
                worksheet.delete_rows(cell.row)
                get_data.clear()
                return True
        except Exception as e: st.error(f"Silme hatası: {e}")
    return False

# --- FONKSİYONLAR (DÖNGÜ ENGELLEYİCİ MOD) ---

def get_users():
    # HATA BURADAYDI: get_users içinde add_new_user çağırıyorduk, o da tekrar get_users çağırıyordu.
    # ARTIK: Eğer liste boşsa direkt statik listeyi dönüyoruz, yazmaya çalışmıyoruz.
    
    df = get_data("users")
    if not df.empty and "Isim" in df.columns:
        users_list = df['Isim'].tolist()
        # Boş satırları ve tekrarları temizle
        unique_users = sorted(list(set([u for u in users_list if str(u).strip() != ""])))
        if unique_users:
            return unique_users
            
    return INITIAL_USERS

def add_new_user(name):
    if name:
        name = name.strip().title()
        # Direkt ekle, kontrolü sheet tarafına bırak (Döngüyü kırmak için)
        return append_row("users", [name])
    return False

def update_user_name(old_name, new_name):
    if new_name:
        new_name = new_name.strip().title()
        return update_cell_value("users", "Isim", old_name, new_name)
    return False

def delete_user(name): return delete_row_by_value("users", name)

def get_countries():
    df = get_data("countries")
    if not df.empty and "Kod" in df.columns:
        c_list = df['Kod'].tolist()
        unique_c = sorted(list(set([c for c in c_list if str(c).strip() != ""])))
        if unique_c: return unique_c
    return INITIAL_COUNTRIES

def add_new_country(code):
    if code:
        code = code.upper()
        return append_row("countries", [code])
    return False

# --- KOD MANTIĞI ---
def get_scenario_number(scenario_str):
    if pd.isna(scenario_str): return None
    match = re.search(r'(\d+)$', str(scenario_str))
    if match: return match.group(1) 
    return None

def get_next_alt_info(scenario_input):
    df = get_data("creative_codes")
    target_num = get_scenario_number(scenario_input)
    max_alt = 0; found_orj = False
    
    if not target_num or df.empty: return 0, False
    
    for index, row in df.iterrows():
        db_scenario = str(row['Senaryo']); db_code = str(row['Tam_Kod'])
        db_num = get_scenario_number(db_scenario)
        
        if db_num == target_num and "TU" in scenario_input and "TU" in db_scenario:
             parts = db_code.split('_'); suffix = parts[-1]
             if suffix == 'ORJ': found_orj = True
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
        return df[df['Tur'] == record_type].sort_index(ascending=False)
    return pd.DataFrame()

# --- ARAYÜZ ---
st.set_page_config(page_title="Kreatif Kod Pro", page_icon="🔥", layout="wide")
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

with st.sidebar:
    st.title("👤 Profil Seç")
    current_users = get_users()
    
    # Seçim Kutusu
    default_selection = current_users[0] if current_users else None
    selected_user = st.pills("Ekip:", current_users, default=default_selection, selection_mode="single")
    
    if selected_user and get_connection():
        st.markdown("---"); st.caption("✏️ Seçili Profili Düzenle")
        c1, c2, c3 = st.columns([3, 1.5, 1.5])
        with c1: en = st.text_input("Edit", value=selected_user, label_visibility="collapsed", key=f"e_{selected_user}")
        with c2: 
            if st.button("Kaydet"): 
                if en != selected_user: update_user_name(selected_user, en); st.success("✅"); time.sleep(0.5); st.rerun()
        with c3:
            if st.button("🗑️ Sil", type="secondary"): delete_user(selected_user); st.warning("Silindi!"); time.sleep(0.5); st.rerun()
    
    st.markdown("---")
    if get_connection():
        with st.expander("➕ Yeni Kişi Ekle"):
            nn = st.text_input("İsim", placeholder="İsim Yaz")
            if st.button("Listeye Ekle"):
