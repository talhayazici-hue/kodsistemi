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

# --- GOOGLE BAĞLANTISI (KORUMALI MOD) ---
@st.cache_resource
def get_connection():
    try:
        if "gcp_service_account" not in st.secrets:
            return None
            
        # Secrets nesnesini sözlüğe çevir
        creds_dict = dict(st.secrets["gcp_service_account"])
        
        # ANAHTAR DÜZELTME: \n karakterleri bazen bozuk gelir, kodla düzeltiyoruz
        if "private_key" in creds_dict:
            # Eğer string içinde \\n varsa onu gerçek \n yap
            raw_key = creds_dict["private_key"]
            creds_dict["private_key"] = raw_key.replace("\\n", "\n").replace("\\n", "\n")
            
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        # Hata detayını loglara yaz ama siteyi çökertme
        print(f"Bağlantı Hatası Detayı: {e}")
        return None

def get_data(worksheet_name):
    client = get_connection()
    if client:
        try:
            sheet = client.open(SHEET_NAME)
            try:
                worksheet = sheet.worksheet(worksheet_name)
            except:
                # Sayfa yoksa oluşturmayı dene (Otomatik tamir)
                worksheet = sheet.add_worksheet(title=worksheet_name, rows="100", cols="20")
                if worksheet_name == "users": worksheet.append_row(["Isim"])
                elif worksheet_name == "countries": worksheet.append_row(["Kod"])
                elif worksheet_name == "creative_codes": worksheet.append_row(["Tarih", "Kullanici", "Prefix", "Senaryo", "Tam_Kod", "Tur"])
            
            data = worksheet.get_all_records()
            return pd.DataFrame(data)
        except Exception as e:
            print(f"Veri okuma hatası: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

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

# --- DATA YÖNETİMİ (SONSUZ DÖNGÜ ENGELLEYİCİ) ---

def get_users():
    # Önce bağlantıyı kontrol et, yoksa direkt varsayılanı dön (DÖNGÜYÜ KIRAR)
    if get_connection() is None:
        return INITIAL_USERS

    df = get_data("users")
    if not df.empty and "Isim" in df.columns:
        return df['Isim'].tolist()
    
    # Tablo boşsa varsayılanları ekle
    for name in INITIAL_USERS:
        add_new_user(name)
    return INITIAL_USERS

def add_new_user(name):
    if name:
        name = name.strip().title()
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
    if get_connection() is None:
        return INITIAL_COUNTRIES
        
    df = get_data("countries")
    if not df.empty and "Kod" in df.columns:
        return df['Kod'].tolist()
    
    for code in INITIAL_COUNTRIES:
        add_new_country(code)
    return INITIAL_COUNTRIES

def add
