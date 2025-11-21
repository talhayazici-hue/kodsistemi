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
# Varsayılan kullanıcılar (Bağlantı kopsa bile bunlar görünsün)
INITIAL_USERS = ["🦁 Talha", "🦅 Emir", "🌸 Aslı", "✨ Ilgın", "💎 Duru", "🎨 Ebru", "🎸 Özgün"]
INITIAL_COUNTRIES = ["ES", "PTBR", "VIE", "EN", "RU", "AR", "FR", "TR", "DE", "IT", "SR", "RO", "PL", "KR", "BG", "HE", "HU", "CZ"]

# --- GOOGLE BAĞLANTISI ---
@st.cache_resource
def get_connection():
    try:
        if "gcp_service_account" not in st.secrets:
            st.error("Secrets ayarları bulunamadı!")
            return None
            
        creds_dict = dict(st.secrets["gcp_service_account"])
        
        # Private key düzeltme
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        # Hata varsa ekrana basma (sonsuz döngü olmasın diye), sadece None dön
        return None

def get_data(worksheet_name):
    client = get_connection()
    if client:
        try:
            sheet = client.open(SHEET_NAME)
            worksheet = sheet.worksheet(worksheet_name)
            data = worksheet.get_all_records()
            return pd.DataFrame(data)
        except Exception:
            return pd.DataFrame() # Hata varsa boş dön
    return pd.DataFrame() # Bağlantı yoksa boş dön

def append_row(worksheet_name, row_data_list):
    client = get_connection()
    if client:
        try:
            sheet = client.open(SHEET_NAME)
            worksheet = sheet.worksheet(worksheet_name)
            worksheet.append_row(row_data_list)
            return True
        except Exception as e:
            st.error(f"Kayıt hatası: {e}")
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
                return True
        except Exception as e:
            st.error(f"Güncelleme hatası: {e}")
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
                return True
        except Exception as e:
            st.error(f"Silme hatası: {e}")
    return False

# --- DATA YÖNETİMİ (DÖNGÜ KORUMALI) ---

def get_users():
    df = get_data("users")
    if not df.empty and "Isim" in df.columns:
        return df['Isim'].tolist()
    
    # Eğer veritabanı boşsa veya BAĞLANTI HATASI varsa
    # Sadece statik listeyi döndür, yazmaya çalışma (Döngüyü engeller)
    return INITIAL_USERS

def add_new_user(name):
    if name:
        name = name.strip().title()
        # Mevcut listeyi kontrol etmeden direkt eklemeyi dene
        # (Duplicate kontrolünü sheet tarafında yapamıyorsak visual yaparız)
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
    div.stButton > button[kind="secondary"]:hover { background
