import streamlit as st
import pandas as pd
import os
import re

# --- AYARLAR ve DOSYA İSİMLERİ ---
DATA_FILE = 'creative_codes_db.csv'
USER_FILE = 'users_db.csv'
COUNTRY_FILE = 'countries_db.csv' 

# Emojili Varsayılan Kullanıcılar
INITIAL_USERS = [
    "🦁 Talha", "🦅 Emir", "🌸 Aslı", "✨ Ilgın", "💎 Duru", 
    "🎨 Ebru", "🎸 Özgün"
]

# Varsayılan Ülkeler
INITIAL_COUNTRIES = [
    "ES", "PTBR", "VIE", "EN", "RU", "AR", "FR", "TR", "DE", "IT", 
    "SR", "RO", "PL", "KR", "BG", "HE", "HU", "CZ"
]

# --- DOSYA KONTROLLERİ ---
if not os.path.exists(DATA_FILE):
    df = pd.DataFrame(columns=['Tarih', 'Kullanici', 'Prefix', 'Senaryo', 'Tam_Kod', 'Tur'])
    df.to_csv(DATA_FILE, index=False)
else:
    df_check = pd.read_csv(DATA_FILE)
    if 'Tur' not in df_check.columns:
        df_check['Tur'] = 'YENI'
        df_check.to_csv(DATA_FILE, index=False)

# --- KULLANICI LİSTESİ KONTROLÜ ---
reset_users = False
if not os.path.exists(USER_FILE):
    reset_users = True
else:
    existing_users = pd.read_csv(USER_FILE)['Isim'].tolist()
    if not any("Özgün" in str(u) for u in existing_users):
         reset_users = True

if reset_users:
    df_users = pd.DataFrame({'Isim': INITIAL_USERS})
    df_users.to_csv(USER_FILE, index=False)

if not os.path.exists(COUNTRY_FILE):
    df_countries = pd.DataFrame({'Kod': INITIAL_COUNTRIES})
    df_countries.to_csv(COUNTRY_FILE, index=False)

# --- FONKSİYONLAR ---

def get_users():
    if os.path.exists(USER_FILE):
        return pd.read_csv(USER_FILE)['Isim'].tolist()
    return INITIAL_USERS

def add_new_user(name):
    if name:
        name = name.strip().title()
        df_users = pd.read_csv(USER_FILE)
        if name not in df_users['Isim'].values:
            new_row = pd.DataFrame({'Isim': [name]})
            df_users = pd.concat([df_users, new_row], ignore_index=True)
            df_users.to_csv(USER_FILE, index=False)
            return True
    return False

def update_user_name(old_name, new_name):
    if os.path.exists(USER_FILE) and new_name:
        new_name = new_name.strip().title() 
        df = pd.read_csv(USER_FILE)
        if old_name in df['Isim'].values:
            df.loc[df['Isim'] == old_name, 'Isim'] = new_name
            df.to_csv(USER_FILE, index=False)
            return True
    return False

def delete_user(name_to_delete):
    if os.path.exists(USER_FILE):
        df = pd.read_csv(USER_FILE)
        df = df[df['Isim'] != name_to_delete]
        df.to_csv(USER_FILE, index=False)
        return True
    return False

def get_countries():
    if os.path.exists(COUNTRY_FILE):
        return pd.read_csv(COUNTRY_FILE)['Kod'].tolist()
    return INITIAL_COUNTRIES

def add_new_country(code):
    if code:
        code = code.upper()
        df_c = pd.read_csv(COUNTRY_FILE)
        if code not in df_c['Kod'].values:
            new_row = pd.DataFrame({'Kod': [code]})
            df_c = pd.concat([df_c, new_row], ignore_index=True)
            df_c.to_csv(COUNTRY_FILE, index=False)

# --- DÜZELTİLEN MANTIK (ORJ -> ALT1 GEÇİŞİ) ---
def get_scenario_number(scenario_str):
    if pd.isna(scenario_str): return None
    match = re.search(r'(\d+)$', str(scenario_str))
    if match:
        return match.group(1) 
    return None

def get_next_alt_info(scenario_input):
    """
    Hem en büyük ALT numarasını hem de ORJ var mı bilgisini döndürür.
    """
    df = pd.read_csv(DATA_FILE)
    target_num = get_scenario_number(scenario_input)
    
    max_alt = 0
    found_orj = False # ORJ bulduk mu bayrağı
    
    if not target_num:
        return 0, False
    
    for index, row in df.iterrows():
        db_scenario = str(row['Senaryo'])
        db_code = str(row['Tam_Kod'])
        db_num = get_scenario_number(db_scenario)
        
        # Aynı numara ailesinden mi? (TU02 == TUES02)
        if db_num == target_num and "TU" in scenario_input and "TU" in db_scenario:
             parts = db_code.split('_')
             suffix = parts[-1]
             
             if suffix == 'ORJ':
                 found_orj = True
             elif suffix.startswith('ALT'):
                try:
                    num = int(suffix.replace('ALT', ''))
                    if num > max_alt:
                        max_alt = num
                except:
                    pass
                    
    return max_alt, found_orj

def generate_single_code(prefix, scenario):
    current_max, found_orj = get_next_alt_info(scenario)
    df = pd.read_csv(DATA_FILE)
    
    # Durum 1: Zaten ALT'lı bir şeyler var (Örn: ALT2), bir fazlasını ver.
    if current_max > 0:
        return f"{prefix}_{scenario}_ALT{current_max + 1}"
    
    # Durum 2: Hiç ALT yok ama ORJ var. O zaman sıra ALT1'de.
    if found_orj:
        return f"{prefix}_{scenario}_ALT1"
    
    # Durum 3: Ne ALT var ne ORJ. O zaman bu ilk kayıt.
    return f"{prefix}_{scenario}_ORJ"

def save_code(user, prefix, scenario, full_code, record_type):
    new_data = {
        'Tarih': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M'),
        'Kullanici': user,
        'Prefix': prefix,
        'Senaryo': scenario,
        'Tam_Kod': full_code,
        'Tur': record_type
    }
    df = pd.read_csv(DATA_FILE)
    new_row = pd.DataFrame([new_data])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(DATA_FILE, index=False)

def get_data_by_type(record_type):
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        if 'Tur' not in df.columns:
            return pd.DataFrame()
        filtered_df = df[df['Tur'] == record_type]
        return filtered_df.sort_index(ascending=False)
    return pd.DataFrame()

# --- ARAYÜZ TASARIMI ---
st.set_page_config(page_title="Kreatif Kod Pro", page_icon="🔥", layout="wide")

# CSS
st.markdown("""
<style>
    .stPills { justify-content: center; }
    [data-testid="stSidebar"] { 
        background-color: #262730; 
        border-right: 1px solid #4b5563;
    }
    div[data-testid="stPills"] button[aria-selected="true"] {
        background-color: #4b5563 !important;
        color: white !important;
        border-color: #4b5563 !important;
    }
    div[data-testid="stPills"] button:hover {
        border-color: #6b7280 !important;
        color: #e5e7eb !important;
    }
    div[data-testid="stPills"] button[aria-selected="true"]:hover {
        color: white !important;
    }
    div.stButton > button[kind="primary"] {
        background-color: #374151 !important;
        border-color: #374151 !important;
    }
    div.stButton > button[kind="secondary"] {
        border-color: #ef4444 !important;
        color: #ef4444 !important;
    }
    div.stButton > button[kind="secondary"]:hover {
        background-color: #ef4444 !important;
        color: white !important;
    }
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
                        st.rerun()
        
        with col_del:
            if st.button("🗑️ Sil", type="secondary"):
                delete_user(selected_user)
                st.warning("Silindi!")
                st.rerun()
    
    st.markdown("---")
    
    with st.expander("➕ Yeni Kişi Ekle"):
        new_user_name = st.text_input("İsim", placeholder="İsim Yaz")
        if st.button("Listeye Ekle"):
            if new_user_name:
                if add_new_user(new_user_name):
                    st.success("Eklendi!")
                    st.rerun()

# --- ANA EKRAN ---
st.title("🔥 Kreatif Kod Yönetimi")

if not selected_user:
    st.warning("⚠️ Lütfen sol menüden bir profil seçiniz veya yeni ekleyiniz!")
    st.stop()

st.caption(f"Aktif Kullanıcı: **{selected_user}**")

tab1, tab2, tab3 = st.tabs(["🆕 Yeni Kreatif", "🌍 Lokalizasyon", "📝 Manuel / Geçmiş Giriş"])

# --- TAB 1: YENİ KOD ---
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
            if custom_input:
                final_prefix = custom_input
    with c2:
        st.subheader("2. Senaryo")
        t1_scenario = st.text_input("Senaryo Kodu", value="TU02", help="TU02, TUES02 vb.").upper()
        st.write("") 
        st.write("") 
        if st.button("🚀 KODU ÜRET", type="primary", use_container_width=True):
            if final_prefix and t1_scenario and final_prefix != "CUSTOM":
                if selected_pill == "CUSTOM":
                    add_new_country(final_prefix)
                
                new_code = generate_single_code(final_prefix, t1_scenario)
                save_code(selected_user, final_prefix, t1_scenario, new_code, "YENI")
                st.success("✅ Kod Oluşturuldu!")
                st.header(f"`{new_code}`")
                if selected_pill == "CUSTOM":
                    st.rerun()
            else:
                st.error("Eksik bilgi.")

    st.markdown("---")
    st.subheader("📜 Yeni Kod Geçmişi")
    st.dataframe(get_data_by_type("YENI"), use_container_width=True, hide_index=True)

# --- TAB 2: LOKALİZASYON ---
with tab2:
    st.info("Mevcut bir kodu referans alarak diğer ülkelere kopyala.")
    c_ref, c_dum = st.columns([1, 2])
    with c_ref:
        source_code_input = st.text_input("Referans Kod (Örn: EN_TU02_ALT2)")
    
    target_scenario = ""
    target_suffix = ""
    
    if source_code_input:
        try:
            parts = source_code_input.split('_')
            if len(parts) >= 3:
                target_scenario = parts[1]
                target_suffix = parts[-1]
                st.caption(f"Algılanan: **{target_scenario}** | **{target_suffix}**")
        except:
            st.warning("Format algılanamadı.")
    
    st.divider()
    st.subheader("Hedef Ülkeleri Seç")
    current_countries_loc = get_countries()
    selected_targets_pills = st.pills("Ülkeler", current_countries_loc, selection_mode="multi")
    
    col_cust, col_btn = st.columns([1, 1])
    with col_cust:
        custom_target = st.text_input("Listede olmayan ülke?", placeholder="Örn: JP")
    with col_btn:
        st.write("") 
        st.write("") 
        if st.button("🌍 LOKALİZASYONLARI KAYDET", type="primary", use_container_width=True):
            if target_scenario and target_suffix:
                final_targets = []
                if selected_targets_pills:
                    final_targets = list(selected_targets_pills)
                if custom_target:
                    custom_code_clean = custom_target.upper()
                    final_targets.append(custom_code_clean)
                    add_new_country(custom_code_clean)
                
                if not final_targets:
                    st.error("Hiç ülke seçmedin!")
                else:
                    saved_list = []
                    for country in final_targets:
                        final_code = f"{country}_{target_scenario}_{target_suffix}"
                        save_code(selected_user, country, target_scenario, final_code, "LOKAL")
                        saved_list.append(final_code)
                    st.success(f"✅ {len(saved_list)} kod sisteme girildi.")
                    st.write(saved_list)
                    if custom_target:
                        st.rerun()
            else:
                st.error("Referans kod girilmedi.")
    st.markdown("---")
    st.subheader("🌍 Lokalizasyon Geçmişi")
    st.dataframe(get_data_by_type("LOKAL"), use_container_width=True, hide_index=True)

# --- TAB 3: MANUEL / GEÇMİŞ GİRİŞ ---
with tab3:
    st.warning("⚠️ Burası geçmiş verileri girmek veya özel bir kod oluşturmak içindir.")
    col_man_1, col_man_2 = st.columns([2, 1])
    with col_man_1:
        manual_code_entry = st.text_input("Tam Kod (Yapıştır)", placeholder="Örn: ES_TU81_ALT22")
    with col_man_2:
        st.write("")
        st.write("")
        if st.button("💾 VERİTABANINA EKLE", type="primary", use_container_width=True):
            if manual_code_entry:
                try:
                    parts = manual_code_entry.split('_')
                    if len(parts) >= 3:
                        man_prefix = parts[0].upper()
                        man_scenario = parts[1].upper()
                        man_full = manual_code_entry.upper()
                        add_new_country(man_prefix)
                        save_code(selected_user, man_prefix, man_scenario, man_full, "MANUEL")
                        st.success(f"✅ {man_full} eklendi!")
                        st.info(f"Sistem güncellendi. {man_scenario} için sayaç buradan devam edecek.")
                    else:
                        st.error("Hatalı format!")
                except Exception as e:
                    st.error(f"Hata: {e}")
            else:
                st.error("Kod girmediniz.")

    st.markdown("---")
    st.subheader("📝 Manuel Giriş Geçmişi")
    st.dataframe(get_data_by_type("MANUEL"), use_container_width=True, hide_index=True)
