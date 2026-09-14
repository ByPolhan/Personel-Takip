import streamlit as st
import sqlite3
import pandas as pd
import hashlib
import datetime
import io
import os

# Sunucu modunda grafik kilitlenmelerini önlemek için Agg backend kullanımı
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor

# ==========================================
# 1. SAYFA YAPILANDIRMASI VE SABİTLER
# ==========================================
st.set_page_config(
    page_title="Arnavutköy 5'inci J.Komd.Tb.K.liği - Performans Takip Sistemi",
    page_icon="🛡️",
    layout="wide"
)

BIRLIK_LISTESI = [
    "Karargah",
    "Destek Bölüğü",
    "1. Bölük",
    "2. Bölük",
    "3. Bölük",
    "4. Bölük"
]

TIM_LISTESI = ["Bölük Karargahı", "1. Tim", "2. Tim", "3. Tim", "4. Tim"]

RUTBE_LISTESI = [
    "Subay",
    "Astsubay",
    "Uzman Jandarma",
    "Uzman Çavuş"
]

PERIYOTLAR = ["Günlük", "Haftalık", "Aylık"]

ROLLER = [
    "Admin",
    "Reporter",
    "Destek Takım Komutanı",
    "Bölük Yetkilisi",
    "Tim Komutanı"
]

def format_kosu_saniye(saniye):
    if pd.isna(saniye) or saniye is None or saniye == 0:
        return "-"
    saniye = int(saniye)
    dk = saniye // 60
    sn = saniye % 60
    return f"{dk:02d}:{sn:02d}"

# ==========================================
# 2. VERİTABANI İŞLEMLERİ (SQLite)
# ==========================================
def get_db():
    conn = sqlite3.connect("personel_takip.db", check_same_thread=False)
    return conn

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return hashed_text
    return False

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS kullanicilar (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kullanici_adi TEXT UNIQUE,
                    sifre TEXT,
                    rol TEXT,
                    birlik TEXT,
                    tim TEXT
                )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS personel (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sicil_no TEXT UNIQUE,
                    ad_soyad TEXT,
                    rutbe TEXT,
                    birlik TEXT,
                    tim TEXT
                )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS performans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    personel_id INTEGER,
                    tarih TEXT,
                    periyot TEXT,
                    sinav INTEGER,
                    mekik INTEGER,
                    barfiks INTEGER,
                    kosu_3000m_sn INTEGER,
                    yazili_sinav REAL,
                    kaydeden TEXT,
                    FOREIGN KEY(personel_id) REFERENCES personel(id)
                )''')
    
    c.execute("PRAGMA table_info(performans)")
    cols = [col[1] for col in c.fetchall()]
    if "kosu_3000m" in cols and "kosu_3000m_sn" not in cols:
        c.execute("ALTER TABLE performans RENAME COLUMN kosu_3000m TO kosu_3000m_sn")

    c.execute("SELECT * FROM kullanicilar WHERE kullanici_adi = 'admin'")
    if not c.fetchone():
        admin_pass = make_hashes("admin123")
        c.execute("INSERT INTO kullanicilar (kullanici_adi, sifre, rol, birlik, tim) VALUES (?, ?, ?, ?, ?)",
                  ('admin', admin_pass, 'Admin', 'Tüm Tabur', '-'))
        
    c.execute("SELECT * FROM kullanicilar WHERE kullanici_adi = 'reporter'")
    if not c.fetchone():
        rep_pass = make_hashes("reporter123")
        c.execute("INSERT INTO kullanicilar (kullanici_adi, sifre, rol, birlik, tim) VALUES (?, ?, ?, ?, ?)",
                  ('reporter', rep_pass, 'Reporter', 'Tüm Tabur', '-'))

    conn.commit()
    conn.close()

init_db()

# ==========================================
# 3. OTURUM VE GİRİŞ YÖNETİMİ
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "user_info" not in st.session_state:
    st.session_state["user_info"] = {}

def login_user(username, password):
    conn = get_db()
    c = conn.cursor()
    hashed_pswd = make_hashes(password)
    c.execute('SELECT kullanici_adi, rol, birlik, tim FROM kullanicilar WHERE kullanici_adi =? AND sifre = ?', (username, hashed_pswd))
    data = c.fetchone()
    conn.close()
    return data

if not st.session_state["logged_in"]:
    col_a, col_b, col_c = st.columns([1, 2, 1])
    with col_b:
        if os.path.exists("logo.png"):
            st.image("logo.png", width=220)
        else:
            st.title("🛡️")
        st.title("ARNAVUTKÖY 5'İNCİ J.KOMD.TB.K.LİĞİ")
        st.subheader("Kasırgalar - Personel Performans Takip Sistemi")
        st.write("---")
        
        username = st.text_input("Kullanıcı Adı")
        password = st.text_input("Şifre", type='password')
        if st.button("Giriş Yap", type="primary", use_container_width=True):
            user_data = login_user(username, password)
            if user_data:
                st.session_state["logged_in"] = True
                st.session_state["user_info"] = {
                    "username": user_data[0],
                    "rol": user_data[1],
                    "birlik": user_data[2],
                    "tim": user_data[3]
                }
                st.success(f"Hoş geldiniz, {user_data[0]} ({user_data[1]})")
                st.rerun()
            else:
                st.error("Hatalı kullanıcı adı veya şifre!")
    st.stop()

# ==========================================
# 4. MENÜ VE YETKİLENDİRME
# ==========================================
user = st.session_state["user_info"]
role = user["rol"]

if os.path.exists("logo.png"):
    st.sidebar.image("logo.png", width=140)

st.sidebar.title("KASIRGALAR")
st.sidebar.caption("5'inci J.Komd.Tb.K.lığı")
st.sidebar.write(f"**Kullanıcı:** {user['username']}")
st.sidebar.write(f"**Rol:** {role}")
if user['birlik'] != "Tüm Tabur":
    st.sidebar.write(f"**Birlik:** {user['birlik']}")
if user['tim'] != "-" and user['tim'] != "Tüm Timler":
    st.sidebar.write(f"**Tim:** {user['tim']}")

with st.sidebar.expander("🔑 Şifremi Değiştir"):
    eski_sifre = st.text_input("Mevcut Şifre", type="password", key="pwd_old")
    yeni_sifre = st.text_input("Yeni Şifre", type="password", key="pwd_new")
    yeni_sifre_tekrar = st.text_input("Yeni Şifre (Tekrar)", type="password", key="pwd_new2")
    if st.button("Şifremi Güncelle", key="btn_change_pwd"):
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT sifre FROM kullanicilar WHERE kullanici_adi = ?", (user["username"],))
        curr_p = c.fetchone()
        if curr_p and check_hashes(eski_sifre, curr_p[0]):
            if yeni_sifre and yeni_sifre == yeni_sifre_tekrar:
                c.execute("UPDATE kullanicilar SET sifre = ? WHERE kullanici_adi = ?", (make_hashes(yeni_sifre), user["username"]))
                conn.commit()
                st.success("Şifreniz başarıyla değiştirildi!")
            else:
                st.error("Yeni şifreler uyuşmuyor veya boş!")
        else:
            st.error("Mevcut şifreniz hatalı!")
        conn.close()

st.sidebar.divider()

menu_options = []

if role in ["Admin", "Destek Takım Komutanı", "Bölük Yetkilisi", "Tim Komutanı"]:
    menu_options.append("📊 Tabur Performans Dashboard")

menu_options.append("📝 Veri Girişi & Geçmiş Veri Düzenleme")

if role in ["Admin", "Destek Takım Komutanı", "Bölük Yetkilisi", "Tim Komutanı"]:
    menu_options.append("👤 Personel Yönetimi")

if role in ["Admin", "Reporter"]:
    menu_options.append("📄 Sunum ve Rapor Alma")

if role == "Admin":
    menu_options.append("⚙️ Yönetici Paneli")

if st.sidebar.button("Güvenli Çıkış", use_container_width=True):
    st.session_state["logged_in"] = False
    st.session_state["user_info"] = {}
    st.rerun()

choice = st.sidebar.radio("Menü", menu_options)

# ==========================================
# MENÜ 1: DASHBOARD
# ==========================================
if choice == "📊 Tabur Performans Dashboard":
    st.header("📊 Tabur İçi Performans ve Sıralama Analizi")
    
    conn = get_db()
    query = '''
        SELECT p.id AS perf_id, p.tarih, p.periyot, per.id AS personel_id, per.sicil_no, per.ad_soyad, per.rutbe, per.birlik, per.tim,
               p.sinav, p.mekik, p.barfiks, p.kosu_3000m_sn, p.yazili_sinav
        FROM performans p
        JOIN personel per ON p.personel_id = per.id
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        st.info("Henüz veritabanında girilmiş performans kaydı bulunmamaktadır.")
    else:
        if role == "Destek Takım Komutanı":
            df = df[df["birlik"] == "Destek Bölüğü"]
        elif role == "Bölük Yetkilisi":
            df = df[df["birlik"] == user["birlik"]]
        elif role == "Tim Komutanı":
            df = df[(df["birlik"] == user["birlik"]) & (df["tim"] == user["tim"])]

        dash_tab1, dash_tab2 = st.tabs(["📊 Genellik & Sıralama", "📈 Personel Bireysel Geçmiş Takibi"])

        with dash_tab1:
            if role in ["Admin", "Reporter"]:
                dash_birlikler = ["Tümü"] + BIRLIK_LISTESI
            elif role == "Destek Takım Komutanı":
                dash_birlikler = ["Destek Bölüğü"]
            else:
                dash_birlikler = [user["birlik"]]

            col_f1, col_f2 = st.columns(2)
            with col_f1:
                secilen_periyot = st.selectbox("Periyot Seçin", ["Tümü"] + PERIYOTLAR, key="dash_p_filter")
            with col_f2:
                secilen_birlik = st.selectbox("Birlik Filtresi", dash_birlikler, key="dash_b_filter")

            filtered_df = df.copy()
            if secilen_periyot != "Tümü":
                filtered_df = filtered_df[filtered_df["periyot"] == secilen_periyot]
            if secilen_birlik != "Tümü":
                filtered_df = filtered_df[filtered_df["birlik"] == secilen_birlik]

            st.subheader("📈 Genel Ortalamalar")
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Şınav (Ort.)", f"{filtered_df['sinav'].mean():.1f}" if not filtered_df['sinav'].dropna().empty else "0")
            m2.metric("Mekik (Ort.)", f"{filtered_df['mekik'].mean():.1f}" if not filtered_df['mekik'].dropna().empty else "0")
            m3.metric("Barfiks (Ort.)", f"{filtered_df['barfiks'].mean():.1f}" if not filtered_df['barfiks'].dropna().empty else "0")
            
            avg_kosu_sn = filtered_df['kosu_3000m_sn'].dropna().mean() if not filtered_df['kosu_3000m_sn'].dropna().empty else 0
            m4.metric("3000m Koşu (Ort.)", format_kosu_saniye(avg_kosu_sn))
            m5.metric("Yazılı Sınav (Ort.)", f"{filtered_df['yazili_sinav'].mean():.1f}" if not filtered_df['yazili_sinav'].dropna().empty else "0")

            st.divider()

            col_g1, col_g2 = st.columns(2)
            with col_g1:
                st.subheader("🏆 Bölük Bazlı Genel Başarı Ortalamaları")
                boluk_grp = filtered_df.groupby("birlik")[["sinav", "mekik", "barfiks", "yazili_sinav"]].mean()
                st.bar_chart(boluk_grp)

            with col_g2:
                st.subheader("🏃‍♂️ Bölük Bazlı 3000m Koşu Ortalamaları (Saniye)")
                kosu_grp = filtered_df.groupby("birlik")["kosu_3000m_sn"].mean()
                st.bar_chart(kosu_grp)

            st.subheader("🎖️ En Yüksek Başarı Gösteren İlk 10 Personel Kaydı")
            filtered_df["Genel_Skor"] = (
                filtered_df["sinav"].fillna(0) + 
                filtered_df["mekik"].fillna(0) + 
                (filtered_df["barfiks"].fillna(0) * 2) + 
                filtered_df["yazili_sinav"].fillna(0) - 
                (filtered_df["kosu_3000m_sn"].fillna(1200) / 10)
            )
            top10 = filtered_df.sort_values(by="Genel_Skor", ascending=False).head(10).copy()
            top10["3000m Koşu"] = top10["kosu_3000m_sn"].apply(format_kosu_saniye)
            
            st.dataframe(top10[["tarih", "sicil_no", "rutbe", "ad_soyad", "birlik", "tim", "sinav", "mekik", "barfiks", "3000m Koşu", "yazili_sinav"]], use_container_width=True)

        with dash_tab2:
            st.subheader("👤 Personel Bazlı Tarihsel Gelişim Grafiği")
            unique_personel = df[["personel_id", "sicil_no", "rutbe", "ad_soyad"]].drop_duplicates()
            
            selected_p_hist_id = st.selectbox(
                "Tarihsel Gelişimini İncelemek İstediğiniz Personeli Seçin",
                options=unique_personel["personel_id"].tolist(),
                format_func=lambda x: f"{unique_personel[unique_personel['personel_id']==x]['sicil_no'].values[0]} - {unique_personel[unique_personel['personel_id']==x]['rutbe'].values[0]} {unique_personel[unique_personel['personel_id']==x]['ad_soyad'].values[0]}",
                key="select_p_hist_dash"
            )

            p_hist_df = df[df["personel_id"] == selected_p_hist_id].sort_values(by="tarih").copy()

            if p_hist_df.empty:
                st.info("Seçilen personele ait veri bulunamadı.")
            else:
                p_hist_df["3000m Koşu"] = p_hist_df["kosu_3000m_sn"].apply(format_kosu_saniye)
                st.write("**📜 Personelin Tarihsel Kayıt Listesi**")
                st.dataframe(p_hist_df[["tarih", "periyot", "sinav", "mekik", "barfiks", "3000m Koşu", "yazili_sinav"]], use_container_width=True)

                st.write("**📈 Zaman İçindeki Değişim Grafiği**")
                chart_df = p_hist_df.set_index("tarih")[["sinav", "mekik", "barfiks", "yazili_sinav"]]
                st.line_chart(chart_df)

# ==========================================
# MENÜ 2: VERİ GİRİŞİ VE GEÇMİŞ DÜZENLEME
# ==========================================
elif choice == "📝 Veri Girişi & Geçmiş Veri Düzenleme":
    st.header("📝 Performans Veri Girişi & Geçmiş Veri Düzenleme")

    conn = get_db()
    
    if role in ["Admin", "Reporter"]:
        allowed_birlikler = BIRLIK_LISTESI
    elif role == "Destek Takım Komutanı":
        allowed_birlikler = ["Destek Bölüğü"]
    else:
        allowed_birlikler = [user["birlik"]]

    col1, col2, col3 = st.columns(3)
    
    with col1:
        secilen_birlik = st.selectbox("Birlik", allowed_birlikler, key="vg_birlik")
    
    with col2:
        if secilen_birlik in ["Karargah", "Destek Bölüğü"]:
            secilen_tim = "-"
            st.info("💡 Bu birlikte tim seçimi yoktur.")
        else:
            if role in ["Admin", "Reporter"]:
                allowed_timler = TIM_LISTESI
            elif role == "Tim Komutanı":
                allowed_timler = [user["tim"]]
            else:
                allowed_timler = TIM_LISTESI
            secilen_tim = st.selectbox("Tim / Unvan", allowed_timler, key="vg_tim")

    with col3:
        secilen_periyot = st.selectbox("Periyot", PERIYOTLAR, key="vg_periyot")

    if secilen_birlik in ["Karargah", "Destek Bölüğü"]:
        personel_df = pd.read_sql_query("SELECT id, sicil_no, ad_soyad FROM personel WHERE birlik=?", 
                                        conn, params=(secilen_birlik,))
    else:
        personel_df = pd.read_sql_query("SELECT id, sicil_no, ad_soyad FROM personel WHERE birlik=? AND tim=?", 
                                        conn, params=(secilen_birlik, secilen_tim))
    
    if personel_df.empty:
        st.warning("⚠️ Seçilen birlikte kayıtlı personel bulunamadı. Lütfen önce Personel Yönetimi menüsünden personel ekleyin.")
    else:
        secilen_personel_id = st.selectbox("Personel Seçin", 
                                           options=personel_df["id"].tolist(), 
                                           format_func=lambda x: f"{personel_df[personel_df['id']==x]['sicil_no'].values[0]} - {personel_df[personel_df['id']==x]['ad_soyad'].values[0]}",
                                           key="vg_personel_select")
        
        st.divider()
        tab_spor, tab_yazili, tab_gecmis = st.tabs(["🏃‍♂️ Yeni Spor Testi Girişi", "📝 Yeni Yazılı Sınav Girişi", "📜 Geçmiş Kayıtlar & Düzenle / Sil"])

        with tab_spor:
            st.subheader("🏃‍♂️ Fiziki Yeterlilik ve Spor Testi")
            spor_tarih = st.date_input("Spor Test Tarihi", datetime.date.today(), key="spor_tarih")
            
            c1, c2 = st.columns(2)
            with c1:
                sinav = st.number_input("Şınav (Tekrar)", min_value=0, max_value=200, value=30, key="spor_sinav")
                mekik = st.number_input("Mekik (Tekrar)", min_value=0, max_value=200, value=35, key="spor_mekik")
                barfiks = st.number_input("Barfiks (Tekrar)", min_value=0, max_value=100, value=10, key="spor_barfiks")
            
            with c2:
                st.write("**3.000 Metre Koşu Süresi**")
                k_col1, k_col2 = st.columns(2)
                with k_col1:
                    kosu_dk = st.number_input("Dakika", min_value=0, max_value=60, value=14, key="spor_kosu_dk")
                with k_col2:
                    kosu_sn = st.number_input("Saniye (0-59)", min_value=0, max_value=59, value=0, key="spor_kosu_sn")
                
                toplam_kosu_saniye = (kosu_dk * 60) + kosu_sn

            if st.button("Spor Testini Kaydet", type="primary", key="btn_spor"):
                cur = conn.cursor()
                cur.execute("SELECT id FROM performans WHERE personel_id=? AND tarih=? AND periyot=?",
                            (secilen_personel_id, str(spor_tarih), secilen_periyot))
                existing = cur.fetchone()
                
                if existing:
                    cur.execute('''UPDATE performans 
                                   SET sinav=?, mekik=?, barfiks=?, kosu_3000m_sn=?, kaydeden=?
                                   WHERE id=?''',
                                (sinav, mekik, barfiks, toplam_kosu_saniye, user["username"], existing[0]))
                else:
                    cur.execute('''INSERT INTO performans 
                                  (personel_id, tarih, periyot, sinav, mekik, barfiks, kosu_3000m_sn, yazili_sinav, kaydeden)
                                  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                               (secilen_personel_id, str(spor_tarih), secilen_periyot, sinav, mekik, barfiks, toplam_kosu_saniye, None, user["username"]))
                conn.commit()
                st.success(f"Spor testi verileri ({kosu_dk:02d}:{kosu_sn:02d}) başarıyla kaydedildi/güncellendi!")
                st.rerun()

        with tab_yazili:
            st.subheader("📝 Yazılı Sınav Notu Girişi")
            yazili_tarih = st.date_input("Yazılı Sınav Tarihi", datetime.date.today(), key="yazili_tarih")
            yazili = st.number_input("Yazılı Sınav Notu (0 - 100)", min_value=0.0, max_value=100.0, value=75.0, key="yazili_not")

            if st.button("Yazılı Sınav Notunu Kaydet", type="primary", key="btn_yazili"):
                cur = conn.cursor()
                cur.execute("SELECT id FROM performans WHERE personel_id=? AND tarih=? AND periyot=?",
                            (secilen_personel_id, str(yazili_tarih), secilen_periyot))
                existing = cur.fetchone()
                
                if existing:
                    cur.execute('''UPDATE performans 
                                   SET yazili_sinav=?, kaydeden=?
                                   WHERE id=?''',
                                (yazili, user["username"], existing[0]))
                else:
                    cur.execute('''INSERT INTO performans 
                                  (personel_id, tarih, periyot, sinav, mekik, barfiks, kosu_3000m_sn, yazili_sinav, kaydeden)
                                  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                               (secilen_personel_id, str(yazili_tarih), secilen_periyot, None, None, None, None, yazili, user["username"]))
                conn.commit()
                st.success("Yazılı sınav notu başarıyla kaydedildi/güncellendi!")
                st.rerun()

        with tab_gecmis:
            st.subheader("📜 Seçilen Personelin Geçmiş Performans Kayıtları")
            
            perf_df = pd.read_sql_query('''
                SELECT p.id, p.tarih, p.periyot, p.sinav, p.mekik, p.barfiks,
                       p.kosu_3000m_sn, p.yazili_sinav, p.kaydeden
                FROM performans p
                WHERE p.personel_id = ?
                ORDER BY p.tarih DESC, p.id DESC
            ''', conn, params=(secilen_personel_id,))

            if perf_df.empty:
                st.info("Bu personele ait daha önce girilmiş bir performans kaydı bulunmamaktadır.")
            else:
                display_p = perf_df.copy()
                display_p["3000m Koşu"] = display_p["kosu_3000m_sn"].apply(format_kosu_saniye)
                display_p_view = display_p[["tarih", "periyot", "sinav", "mekik", "barfiks", "3000m Koşu", "yazili_sinav", "kaydeden"]]
                display_p_view.columns = ["Tarih", "Periyot", "Şınav", "Mekik", "Barfiks", "3000m Koşu", "Yazılı Notu", "Kaydeden"]
                st.dataframe(display_p_view, use_container_width=True)

                st.divider()
                st.subheader("✏️ Geçmiş Kayıt Düzenle veya Sil")

                record_id = st.selectbox(
                    "Düzenlenecek / Silinecek Performans Kaydını Seçin",
                    options=perf_df["id"].tolist(),
                    format_func=lambda x: f"Tarih: {perf_df[perf_df['id']==x]['tarih'].values[0]} | Periyot: {perf_df[perf_df['id']==x]['periyot'].values[0]} | Kaydeden: {perf_df[perf_df['id']==x]['kaydeden'].values[0]}",
                    key="select_perf_record"
                )

                rec = perf_df[perf_df['id'] == record_id].iloc[0]

                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    try:
                        parsed_date = datetime.datetime.strptime(str(rec['tarih']), "%Y-%m-%d").date()
                    except:
                        parsed_date = datetime.date.today()

                    edit_tarih = st.date_input("Kayıt Tarihi", parsed_date, key=f"rec_tarih_{record_id}")
                    edit_periyot = st.selectbox("Periyot", PERIYOTLAR, index=PERIYOTLAR.index(rec['periyot']) if rec['periyot'] in PERIYOTLAR else 0, key=f"rec_periyot_{record_id}")
                    edit_sinav = st.number_input("Şınav (Tekrar)", min_value=0, max_value=200, value=int(rec['sinav']) if pd.notna(rec['sinav']) else 0, key=f"rec_sinav_{record_id}")
                    edit_mekik = st.number_input("Mekik (Tekrar)", min_value=0, max_value=200, value=int(rec['mekik']) if pd.notna(rec['mekik']) else 0, key=f"rec_mekik_{record_id}")

                with col_e2:
                    edit_barfiks = st.number_input("Barfiks (Tekrar)", min_value=0, max_value=100, value=int(rec['barfiks']) if pd.notna(rec['barfiks']) else 0, key=f"rec_barfiks_{record_id}")
                    
                    curr_sn = int(rec['kosu_3000m_sn']) if pd.notna(rec['kosu_3000m_sn']) else 0
                    c_dk = curr_sn // 60
                    c_sn = curr_sn % 60
                    
                    st.write("**3.000 Metre Koşu Süresi**")
                    e_k_col1, e_k_col2 = st.columns(2)
                    with e_k_col1:
                        edit_kosu_dk = st.number_input("Dakika", min_value=0, max_value=60, value=c_dk, key=f"rec_kdk_{record_id}")
                    with e_k_col2:
                        edit_kosu_sn = st.number_input("Saniye", min_value=0, max_value=59, value=c_sn, key=f"rec_ksn_{record_id}")
                    
                    edit_yazili = st.number_input("Yazılı Sınav Notu (0-100)", min_value=0.0, max_value=100.0, value=float(rec['yazili_sinav']) if pd.notna(rec['yazili_sinav']) else 0.0, key=f"rec_yazili_{record_id}")

                btn_p1, btn_p2 = st.columns(2)
                with btn_p1:
                    if st.button("Kaydı Güncelle", type="primary", key=f"btn_upd_perf_{record_id}"):
                        tot_sn = (edit_kosu_dk * 60) + edit_kosu_sn
                        cur = conn.cursor()
                        cur.execute('''UPDATE performans 
                                       SET tarih=?, periyot=?, sinav=?, mekik=?, barfiks=?, kosu_3000m_sn=?, yazili_sinav=?, kaydeden=?
                                       WHERE id=?''',
                                    (str(edit_tarih), edit_periyot, edit_sinav, edit_mekik, edit_barfiks, tot_sn, edit_yazili, user["username"], record_id))
                        conn.commit()
                        st.success("Performans kaydı başarıyla güncellendi!")
                        st.rerun()

                with btn_p2:
                    chk_del_p = st.checkbox("Bu geçmiş kaydı tamamen silmeyi onaylıyorum", key=f"chk_del_p_{record_id}")
                    if st.button("Kaydı Sil", type="secondary", key=f"btn_del_perf_{record_id}"):
                        if chk_del_p:
                            cur = conn.cursor()
                            cur.execute("DELETE FROM performans WHERE id=?", (record_id,))
                            conn.commit()
                            st.warning("Performans kaydı silindi!")
                            st.rerun()
                        else:
                            st.error("Lütfen önce silme onay kutusunu işaretleyin.")
    
    conn.close()

# ==========================================
# MENÜ 3: PERSONEL YÖNETİMİ
# ==========================================
elif choice == "👤 Personel Yönetimi":
    st.header("👤 Tabur Personel Kayıt ve Yetkilendirme Yönetimi")

    conn = get_db()

    if role == "Admin":
        tab1, tab2, tab3, tab4 = st.tabs(["Yeni Personel Ekle", "Personel Listesi", "Mevcut Personele Yetki Tanımla", "✏️ Personel Güncelle / Sil"])
    else:
        tab1, tab2, tab3 = st.tabs(["Yeni Personel Ekle", "Personel Listesi", "Mevcut Personele Yetki Tanımla"])

    with tab1:
        st.subheader("Yeni Personel Tanımla")
        
        if role in ["Admin", "Reporter"]:
            p_birlikler = BIRLIK_LISTESI
        elif role == "Destek Takım Komutanı":
            p_birlikler = ["Destek Bölüğü"]
        else:
            p_birlikler = [user["birlik"]]

        col1, col2 = st.columns(2)
        with col1:
            sicil_no = st.text_input("PBİK")
            ad_soyad = st.text_input("Ad Soyad")
            rutbe = st.selectbox("Rütbe Seçin", RUTBE_LISTESI)
        with col2:
            p_birlik = st.selectbox("Atandığı Birlik", p_birlikler)
            
            if p_birlik in ["Karargah", "Destek Bölüğü"]:
                p_tim = "-"
                st.info("💡 Bu birlikte tim ayrımı bulunmamaktadır.")
            else:
                if role == "Tim Komutanı":
                    p_timler = [user["tim"]]
                else:
                    p_timler = TIM_LISTESI
                p_tim = st.selectbox("Atandığı Tim / Unvan", p_timler)

        st.divider()
        yetki_ver = st.checkbox("🔑 Bu personele sisteme giriş / veri giriş yetkisi (Kullanıcı Hesabı) tanımla")
        
        if yetki_ver:
            st.info(f"Sisteme giriş hesabı açılıyor. Birlik: **{p_birlik}**, Tim/Unvan: **{p_tim}** olarak atanacaktır.")
            u_col1, u_col2 = st.columns(2)
            with u_col1:
                new_username = st.text_input("Kullanıcı Adı (Sisteme Giriş)", value=sicil_no if sicil_no else "")
                new_password = st.text_input("Giriş Şifresi", type="password")
            with u_col2:
                new_role = st.selectbox("Atanacak Rol / Yetki", ROLLER, index=4 if p_tim != "-" else 3)

        if st.button("Personeli Kaydet", type="primary"):
            if sicil_no and ad_soyad:
                try:
                    cur = conn.cursor()
                    cur.execute("INSERT INTO personel (sicil_no, ad_soyad, rutbe, birlik, tim) VALUES (?, ?, ?, ?, ?)",
                                (str(sicil_no).strip(), ad_soyad.strip(), rutbe, p_birlik, p_tim))
                    
                    if yetki_ver:
                        if new_username and new_password:
                            hashed_p = make_hashes(new_password)
                            cur.execute("INSERT INTO kullanicilar (kullanici_adi, sifre, rol, birlik, tim) VALUES (?, ?, ?, ?, ?)",
                                        (new_username.strip(), hashed_p, new_role, p_birlik, p_tim))
                            st.success(f"{rutbe} {ad_soyad} eklendi ve '{new_username}' kullanıcı adı ile giriş yetkisi verildi!")
                        else:
                            st.warning("Personel eklendi fakat kullanıcı adı veya şifre boş bırakıldığı için yetki hesabı açılamadı!")
                    else:
                        st.success(f"{rutbe} {ad_soyad} başarıyla sisteme eklendi.")
                    
                    conn.commit()
                    st.rerun()
                except sqlite3.IntegrityError:
                    conn.rollback()
                    st.error("Bu PBİK veya Kullanıcı Adı zaten sistemde kayıtlı!")
            else:
                st.warning("Lütfen PBİK ve Ad Soyad alanlarını doldurun.")

    with tab2:
        st.subheader("Mevcut Personel Listesi")
        p_df = pd.read_sql_query("SELECT sicil_no AS PBİK, ad_soyad AS Ad_Soyad, rutbe AS Rütbe, birlik AS Birlik, tim AS Tim FROM personel ORDER BY id DESC", conn)
        
        if role == "Destek Takım Komutanı":
            p_df = p_df[p_df["Birlik"] == "Destek Bölüğü"]
        elif role == "Bölük Yetkilisi":
            p_df = p_df[p_df["Birlik"] == user["birlik"]]
        elif role == "Tim Komutanı":
            p_df = p_df[(p_df["Birlik"] == user["birlik"]) & (p_df["Tim"] == user["tim"])]

        st.dataframe(p_df, use_container_width=True)

    with tab3:
        st.subheader("Mevcut Personele Veri Giriş Yetkilisi (Kullanıcı) Yap")
        p_df_all = pd.read_sql_query("SELECT id, sicil_no, ad_soyad, rutbe, birlik, tim FROM personel ORDER BY id DESC", conn)
        
        if role == "Destek Takım Komutanı":
            p_df_all = p_df_all[p_df_all["birlik"] == "Destek Bölüğü"]
        elif role == "Bölük Yetkilisi":
            p_df_all = p_df_all[p_df_all["birlik"] == user["birlik"]]
        elif role == "Tim Komutanı":
            p_df_all = p_df_all[(p_df_all["birlik"] == user["birlik"]) & (p_df_all["tim"] == user["tim"])]

        if p_df_all.empty:
            st.info("Kayıtlı personel bulunmamaktadır.")
        else:
            selected_p_id = st.selectbox("Personele Yetki Tanımlamak İçin Seçin",
                                         options=p_df_all["id"].tolist(),
                                         format_func=lambda x: f"{p_df_all[p_df_all['id']==x]['rutbe'].values[0]} {p_df_all[p_df_all['id']==x]['ad_soyad'].values[0]} ({p_df_all[p_df_all['id']==x]['birlik'].values[0]} / {p_df_all[p_df_all['id']==x]['tim'].values[0]})")
            
            sel_p = p_df_all[p_df_all['id'] == selected_p_id].iloc[0]
            
            c1, c2 = st.columns(2)
            with c1:
                y_username = st.text_input("Giriş Kullanıcı Adı", value=str(sel_p['sicil_no']), key="exist_u")
                y_password = st.text_input("Şifre", type="password", key="exist_p")
            with c2:
                y_role = st.selectbox("Yetki / Rol", ROLLER, key="exist_r")
                st.info(f"📍 Otomatik Birlik/Tim: **{sel_p['birlik']} / {sel_p['tim']}**")

            if st.button("Yetkili Hesabını Oluştur", type="primary"):
                if y_username and y_password:
                    try:
                        cur = conn.cursor()
                        hashed_p = make_hashes(y_password)
                        cur.execute("INSERT INTO kullanicilar (kullanici_adi, sifre, rol, birlik, tim) VALUES (?, ?, ?, ?, ?)",
                                    (y_username.strip(), hashed_p, y_role, sel_p['birlik'], sel_p['tim']))
                        conn.commit()
                        st.success(f"'{sel_p['ad_soyad']}' için {y_role} yetkili hesabı başarıyla oluşturuldu.")
                    except sqlite3.IntegrityError:
                        conn.rollback()
                        st.error("Bu kullanıcı adı zaten kullanılmaktadır!")
                else:
                    st.warning("Lütfen kullanıcı adı ve şifre girin.")

    if role == "Admin":
        with tab4:
            st.subheader("✏️ Personel Bilgilerini Güncelle veya Sil (Sadece Admin)")
            all_p_df = pd.read_sql_query("SELECT * FROM personel ORDER BY id DESC", conn)
            
            if all_p_df.empty:
                st.info("Kayıtlı personel bulunmamaktadır.")
            else:
                edit_p_id = st.selectbox("Düzenlenecek / Silinecek Personel",
                                         options=all_p_df["id"].tolist(),
                                         format_func=lambda x: f"PBİK: {all_p_df[all_p_df['id']==x]['sicil_no'].values[0]} - {all_p_df[all_p_df['id']==x]['rutbe'].values[0]} {all_p_df[all_p_df['id']==x]['ad_soyad'].values[0]} ({all_p_df[all_p_df['id']==x]['birlik'].values[0]} / {all_p_df[all_p_df['id']==x]['tim'].values[0]})",
                                         key="select_edit_p_box")
                
                target_p = all_p_df[all_p_df['id'] == edit_p_id].iloc[0]
                
                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    edit_pbik = st.text_input("PBİK", value=str(target_p['sicil_no']), key=f"e_pbik_{edit_p_id}")
                    edit_ad_soyad = st.text_input("Ad Soyad", value=str(target_p['ad_soyad']), key=f"e_ad_{edit_p_id}")
                    edit_rutbe = st.selectbox("Rütbe", RUTBE_LISTESI, index=RUTBE_LISTESI.index(target_p['rutbe']) if target_p['rutbe'] in RUTBE_LISTESI else 0, key=f"e_rutbe_{edit_p_id}")
                with col_e2:
                    edit_birlik = st.selectbox("Birlik", BIRLIK_LISTESI, index=BIRLIK_LISTESI.index(target_p['birlik']) if target_p['birlik'] in BIRLIK_LISTESI else 0, key=f"e_birlik_{edit_p_id}")
                    
                    if edit_birlik in ["Karargah", "Destek Bölüğü"]:
                        edit_tim = "-"
                    else:
                        edit_tim = st.selectbox("Tim / Unvan", TIM_LISTESI, index=TIM_LISTESI.index(target_p['tim']) if target_p['tim'] in TIM_LISTESI else 0, key=f"e_tim_{edit_p_id}")

                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    if st.button("Bilgileri Güncelle", type="primary", key=f"btn_upd_{edit_p_id}"):
                        try:
                            cur = conn.cursor()
                            cur.execute("""UPDATE personel 
                                           SET sicil_no=?, ad_soyad=?, rutbe=?, birlik=?, tim=? 
                                           WHERE id=?""",
                                        (edit_pbik.strip(), edit_ad_soyad.strip(), edit_rutbe, edit_birlik, edit_tim, edit_p_id))
                            conn.commit()
                            st.success("Personel bilgileri başarıyla güncellendi!")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            conn.rollback()
                            st.error("Bu PBİK başka bir personele kayıtlı!")
                with btn_col2:
                    confirm_delete = st.checkbox("Silme işlemini onaylıyorum", key=f"del_chk_{edit_p_id}")
                    if st.button("Personeli Sil", type="secondary", key=f"btn_del_{edit_p_id}"):
                        if confirm_delete:
                            cur = conn.cursor()
                            cur.execute("SELECT sicil_no FROM personel WHERE id=?", (edit_p_id,))
                            p_row = cur.fetchone()
                            if p_row:
                                cur.execute("DELETE FROM kullanicilar WHERE kullanici_adi=?", (p_row[0],))
                            
                            cur.execute("DELETE FROM performans WHERE personel_id=?", (edit_p_id,))
                            cur.execute("DELETE FROM personel WHERE id=?", (edit_p_id,))
                            conn.commit()
                            st.warning("Personel, performans kayıtları ve yetkili hesabı silindi.")
                            st.rerun()
                        else:
                            st.error("Lütfen önce silme onay kutusunu işaretleyin.")

    conn.close()

# ==========================================
# MENÜ 4: SUNUM VE RAPOR ALMA
# ==========================================
elif choice == "📄 Sunum ve Rapor Alma":
    st.header("📄 Komutanlık Sunum ve Rapor Dosyası Oluşturucu")
    st.info("Bu modülden seçilen birim ve filtrelere uygun olarak **PowerPoint (.pptx)** sunumu veya **Excel (.xlsx)** raporu indirebilirsiniz.")

    st.subheader("🎯 Rapor ve Sunum Kapsamını Seçin")
    f_col1, f_col2, f_col3 = st.columns(3)
    
    with f_col1:
        kapsam_tipi = st.selectbox("Hedef Kapsam", ["Tüm Tabur", "Belirli Bölük", "Belirli Tim"])
    
    secilen_b = "Tüm Tabur"
    secilen_t = "-"
    
    with f_col2:
        if kapsam_tipi in ["Belirli Bölük", "Belirli Tim"]:
            secilen_b = st.selectbox("Bölük Seçin", BIRLIK_LISTESI)
    
    with f_col3:
        if kapsam_tipi == "Belirli Tim":
            secilen_t = st.selectbox("Tim Seçin", TIM_LISTESI)
            
    periyot_filtre = st.selectbox("Periyot Filtresi", ["Tümü"] + PERIYOTLAR)

    conn = get_db()
    query = '''
        SELECT p.tarih, p.periyot, per.sicil_no AS PBİK, per.ad_soyad, per.rutbe, per.birlik, per.tim,
               p.sinav, p.mekik, p.barfiks, p.kosu_3000m_sn, p.yazili_sinav, p.kaydeden
        FROM performans p
        JOIN personel per ON p.personel_id = per.id
    '''
    report_df = pd.read_sql_query(query, conn)
    conn.close()

    if kapsam_tipi == "Belirli Bölük":
        report_df = report_df[report_df["birlik"] == secilen_b]
    elif kapsam_tipi == "Belirli Tim":
        report_df = report_df[(report_df["birlik"] == secilen_b) & (report_df["tim"] == secilen_t)]

    if periyot_filtre != "Tümü":
        report_df = report_df[report_df["periyot"] == periyot_filtre]

    if report_df.empty:
        st.warning("Seçilen kriterlere uygun raporlanacak veri bulunamadı.")
    else:
        st.divider()
        st.subheader("📊 Rapor Önizleme")
        
        display_rep = report_df.copy()
        display_rep["3000m Koşu"] = display_rep["kosu_3000m_sn"].apply(format_kosu_saniye)
        st.dataframe(display_rep[["PBİK", "rutbe", "ad_soyad", "birlik", "tim", "periyot", "tarih", "sinav", "mekik", "barfiks", "3000m Koşu", "yazili_sinav"]], use_container_width=True)

        col_d1, col_d2 = st.columns(2)

        with col_d1:
            def create_pptx():
                prs = Presentation()
                prs.slide_width = Inches(13.333)
                prs.slide_height = Inches(7.5)
                blank_layout = prs.slide_layouts[6]

                min_tarih = report_df['tarih'].min() if not report_df.empty else "-"
                max_tarih = report_df['tarih'].max() if not report_df.empty else "-"
                tarih_araligi = f"{min_tarih} - {max_tarih}" if min_tarih != max_tarih else f"{min_tarih}"

                # ------------------------------------
                # SLAYT 1: KAPAK SLAYTI (KOMUTANLIK FORMATI)
                # ------------------------------------
                slide1 = prs.slides.add_slide(blank_layout)
                
                if os.path.exists("logo.png"):
                    slide1.shapes.add_picture("logo.png", Inches(1.2), Inches(1.8), width=Inches(3.2))

                text_left = Inches(4.8) if os.path.exists("logo.png") else Inches(1.5)
                text_width = Inches(7.5) if os.path.exists("logo.png") else Inches(10.333)

                title_box = slide1.shapes.add_textbox(text_left, Inches(1.8), text_width, Inches(4.5))
                tf1 = title_box.text_frame
                tf1.word_wrap = True
                
                p1 = tf1.paragraphs[0]
                p1.text = "ARNAVUTKÖY 5'İNCİ J.KOMD.TB.K.LİĞİ"
                p1.font.size = Pt(28)
                p1.font.bold = True
                p1.font.color.rgb = RGBColor(30, 58, 138)
                
                p_sub = tf1.add_paragraph()
                p_sub.text = "KASIRGALAR TABURU PERFORMANS DEĞERLENDİRME SUNUMU\n"
                p_sub.font.size = Pt(18)
                p_sub.font.bold = True
                p_sub.font.color.rgb = RGBColor(180, 83, 9)

                kapsam_metni = f"{kapsam_tipi}"
                if kapsam_tipi == "Belirli Bölük":
                    kapsam_metni += f" ({secilen_b})"
                elif kapsam_tipi == "Belirli Tim":
                    kapsam_metni += f" ({secilen_b} / {secilen_t})"

                p2 = tf1.add_paragraph()
                p2.text = f"📍 Kapsam: {kapsam_metni}\n" \
                          f"⏱️ Periyot: {periyot_filtre}\n" \
                          f"📅 Veri Tarih Aralığı: {tarih_araligi}\n" \
                          f"🗓️ Rapor Tarihi: {datetime.date.today().strftime('%d.%m.%Y')}"
                p2.font.size = Pt(15)
                p2.font.color.rgb = RGBColor(51, 65, 85)

                # ------------------------------------
                # SLAYT 2: TABUR GENEL İSTATİSTİKİ ÖZET
                # ------------------------------------
                slide2 = prs.slides.add_slide(blank_layout)
                
                h_box2 = slide2.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.733), Inches(0.8))
                p_h2 = h_box2.text_frame.paragraphs[0]
                p_h2.text = "📊 Genel Performans İstatistik Özeti"
                p_h2.font.size = Pt(24)
                p_h2.font.bold = True
                p_h2.font.color.rgb = RGBColor(30, 58, 138)

                table_shape2 = slide2.shapes.add_table(2, 6, Inches(0.8), Inches(1.8), Inches(11.733), Inches(2.2))
                t2 = table_shape2.table

                headers2 = ["Toplam Kayıt", "Şınav (Ort.)", "Mekik (Ort.)", "Barfiks (Ort.)", "3000m Koşu (Ort.)", "Yazılı Notu (Ort.)"]
                avg_kosu_sn = report_df['kosu_3000m_sn'].dropna().mean() if not report_df['kosu_3000m_sn'].dropna().empty else 0
                
                vals2 = [
                    str(len(report_df)),
                    f"{report_df['sinav'].mean():.1f}" if pd.notna(report_df['sinav'].mean()) else "-",
                    f"{report_df['mekik'].mean():.1f}" if pd.notna(report_df['mekik'].mean()) else "-",
                    f"{report_df['barfiks'].mean():.1f}" if pd.notna(report_df['barfiks'].mean()) else "-",
                    format_kosu_saniye(avg_kosu_sn),
                    f"{report_df['yazili_sinav'].mean():.1f}" if pd.notna(report_df['yazili_sinav'].mean()) else "-"
                ]

                for c_idx, text in enumerate(headers2):
                    cell = t2.cell(0, c_idx)
                    cell.text = text
                    for p in cell.text_frame.paragraphs:
                        p.font.bold = True
                        p.font.size = Pt(13)
                        p.font.color.rgb = RGBColor(255, 255, 255)
                        p.alignment = PP_ALIGN.CENTER
                    cell.fill.solid()
                    cell.fill.fore_color.rgb = RGBColor(30, 58, 138)

                for c_idx, text in enumerate(vals2):
                    cell = t2.cell(1, c_idx)
                    cell.text = text
                    for p in cell.text_frame.paragraphs:
                        p.font.bold = True
                        p.font.size = Pt(16)
                        p.font.color.rgb = RGBColor(15, 23, 42)
                        p.alignment = PP_ALIGN.CENTER
                    cell.fill.solid()
                    cell.fill.fore_color.rgb = RGBColor(241, 245, 249)

                # ------------------------------------
                # SLAYT 3: EN YÜKSEK BAŞARI GÖSTEREN İLK 10 PERSONEL
                # ------------------------------------
                slide3 = prs.slides.add_slide(blank_layout)
                
                h_box3 = slide3.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.733), Inches(0.8))
                p_h3 = h_box3.text_frame.paragraphs[0]
                p_h3.text = "🏆 En Yüksek Başarı Gösteren İlk 10 Personel Kaydı"
                p_h3.font.size = Pt(22)
                p_h3.font.bold = True
                p_h3.font.color.rgb = RGBColor(30, 58, 138)

                df_top = report_df.copy()
                df_top["Genel_Skor"] = (
                    df_top["sinav"].fillna(0) + 
                    df_top["mekik"].fillna(0) + 
                    (df_top["barfiks"].fillna(0) * 2) + 
                    df_top["yazili_sinav"].fillna(0) - 
                    (df_top["kosu_3000m_sn"].fillna(1200) / 10)
                )
                df_top10 = df_top.sort_values(by="Genel_Skor", ascending=False).head(10)

                rows, cols = len(df_top10) + 1, 9
                t3_shape = slide3.shapes.add_table(rows, cols, Inches(0.8), Inches(1.3), Inches(11.733), Inches(5.5))
                t3 = t3_shape.table

                headers3 = ["Test Tarihi", "PBİK", "Rütbe", "Ad Soyad", "Birlik", "Şınav", "Mekik", "Barfiks", "3000m Koşu"]
                for c_idx, h_text in enumerate(headers3):
                    cell = t3.cell(0, c_idx)
                    cell.text = h_text
                    for p in cell.text_frame.paragraphs:
                        p.font.bold = True
                        p.font.size = Pt(11)
                        p.font.color.rgb = RGBColor(255, 255, 255)
                        p.alignment = PP_ALIGN.CENTER
                    cell.fill.solid()
                    cell.fill.fore_color.rgb = RGBColor(30, 58, 138)

                for r_idx, (_, r_data) in enumerate(df_top10.iterrows(), start=1):
                    vals = [
                        str(r_data["tarih"]),
                        str(r_data["PBİK"]),
                        str(r_data["rutbe"]),
                        str(r_data["ad_soyad"]),
                        str(r_data["birlik"]),
                        str(int(r_data["sinav"])) if pd.notna(r_data["sinav"]) else "-",
                        str(int(r_data["mekik"])) if pd.notna(r_data["mekik"]) else "-",
                        str(int(r_data["barfiks"])) if pd.notna(r_data["barfiks"]) else "-",
                        format_kosu_saniye(r_data["kosu_3000m_sn"])
                    ]
                    for c_idx, val in enumerate(vals):
                        cell = t3.cell(r_idx, c_idx)
                        cell.text = val
                        for p in cell.text_frame.paragraphs:
                            p.font.size = Pt(10)
                            p.alignment = PP_ALIGN.CENTER

                # ------------------------------------
                # SLAYT 4: GÖRSEL VE TEMİZ SÜTUN GRAFİKLERİ
                # ------------------------------------
                slide4 = prs.slides.add_slide(blank_layout)
                
                h_box4 = slide4.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.733), Inches(0.8))
                p_h4 = h_box4.text_frame.paragraphs[0]
                p_h4.text = "📈 Bölük Bazlı Karşılaştırmalı Performans Grafiği"
                p_h4.font.size = Pt(22)
                p_h4.font.bold = True
                p_h4.font.color.rgb = RGBColor(30, 58, 138)

                fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.8))
                plt.subplots_adjust(wspace=0.35)

                # Grafik 1: Spor Ortalamaları
                grp_spor = report_df.groupby("birlik")[["sinav", "mekik", "barfiks"]].mean()
                if not grp_spor.empty:
                    grp_spor.plot(kind="bar", ax=ax1, color=["#1E3A8A", "#16A34A", "#D97706"], width=0.8)
                    ax1.set_title("Bölük Bazlı Spor Ortalamaları (Tekrar)", fontsize=11, fontweight="bold", pad=10)
                    ax1.set_ylabel("Tekrar Sayısı")
                    ax1.grid(axis="y", linestyle="--", alpha=0.5)
                    ax1.tick_params(axis='x', rotation=15)
                    
                    for p in ax1.patches:
                        height = p.get_height()
                        if height > 0:
                            ax1.annotate(f"{height:.1f}", (p.get_x() + p.get_width() / 2., height),
                                         ha='center', va='bottom', fontsize=8, xytext=(0, 2), textcoords='offset points')

                # Grafik 2: Yazılı Sınav Ortalamaları
                grp_yazili = report_df.groupby("birlik")["yazili_sinav"].mean()
                if not grp_yazili.empty:
                    bars = ax2.bar(grp_yazili.index, grp_yazili.values, color="#2563EB", width=0.5)
                    ax2.set_title("Bölük Bazlı Yazılı Sınav Ortalamaları (Puan)", fontsize=11, fontweight="bold", pad=10)
                    ax2.set_ylabel("Sınav Notu (0-100)")
                    ax2.set_ylim(0, 105)
                    ax2.grid(axis="y", linestyle="--", alpha=0.5)
                    ax2.tick_params(axis='x', rotation=15)
                    
                    for bar in bars:
                        yval = bar.get_height()
                        if pd.notna(yval) and yval > 0:
                            ax2.text(bar.get_x() + bar.get_width()/2.0, yval + 1, f"{yval:.1f}", ha='center', va='bottom', fontsize=9, fontweight='bold')

                img_buf = io.BytesIO()
                plt.savefig(img_buf, format="png", dpi=200, bbox_inches="tight")
                plt.close(fig)
                img_buf.seek(0)

                slide4.shapes.add_picture(img_buf, Inches(0.8), Inches(1.3), width=Inches(11.733))

                pptx_out = io.BytesIO()
                prs.save(pptx_out)
                pptx_out.seek(0)
                return pptx_out

            pptx_file = create_pptx()
            st.download_button(
                label="🖥️ Komutanlık PowerPoint Sunumunu İndir (.pptx)",
                data=pptx_file,
                file_name=f"Kasirgalar_Tabur_Performans_Sunumu_{datetime.date.today()}.pptx",
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                type="primary"
            )

        with col_d2:
            excel_buf = io.BytesIO()
            with pd.ExcelWriter(excel_buf, engine='openpyxl') as writer:
                display_rep.to_excel(writer, sheet_name='Performans Raporu', index=False)
                ozet = report_df.groupby("birlik")[["sinav", "mekik", "barfiks", "kosu_3000m_sn", "yazili_sinav"]].mean()
                ozet.to_excel(writer, sheet_name='Bölük Ortalamaları')

            excel_buf.seek(0)
            st.download_button(
                label="📊 Detaylı Excel Raporunu İndir (.xlsx)",
                data=excel_buf,
                file_name=f"Kasirgalar_Tabur_Performans_Raporu_{datetime.date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

# ==========================================
# MENÜ 5: YÖNETİCİ PANELİ
# ==========================================
elif choice == "⚙️ Yönetici Paneli":
    st.header("⚙️ Yönetici Paneli - Kullanıcı Hesabı Yönetimi")
    
    conn = get_db()

    st.subheader("📋 Mevcut Yetkili Kullanıcılar")
    users_df = pd.read_sql_query("SELECT id, kullanici_adi, rol, birlik, tim FROM kullanicilar", conn)
    st.dataframe(users_df, use_container_width=True)

    st.divider()
    tab_pwd, tab_del = st.tabs(["🔑 Şifre Sıfırla", "🗑️ Kullanıcı Sil / Hesabı Kaldır"])

    with tab_pwd:
        st.subheader("🔑 Kullanıcı Şifre Sıfırlama")
        if not users_df.empty:
            selected_user_id = st.selectbox(
                "Şifresi Değiştirilecek Kullanıcı",
                users_df["id"].tolist(),
                format_func=lambda x: f"{users_df[users_df['id']==x]['kullanici_adi'].values[0]} ({users_df[users_df['id']==x]['rol'].values[0]})",
                key="select_reset_user"
            )
            reset_pass = st.text_input("Yeni Şifre Belirle", type="password", key="reset_pass_input")
            
            if st.button("Şifreyi Güncelle", type="primary", key="btn_reset_pass"):
                if reset_pass:
                    cur = conn.cursor()
                    cur.execute("UPDATE kullanicilar SET sifre = ? WHERE id = ?", (make_hashes(reset_pass), selected_user_id))
                    conn.commit()
                    st.success("Kullanıcı şifresi başarıyla yenilendi.")
                else:
                    st.warning("Lütfen yeni şifreyi giriniz.")

    with tab_del:
        st.subheader("🗑️ Yetkili Kullanıcı Hesabını Sil")
        st.caption("Not: Buradan sildiğiniz kullanıcı hesaplarının sisteme giriş yetkisi tamamen kaldırılır. Ana 'admin' hesabı ve aktif olarak oturum açtığınız kendi hesabınız silinemez.")

        deletable_users = users_df[~users_df["kullanici_adi"].isin(["admin", user["username"]])]

        if deletable_users.empty:
            st.info("Silinebilir başka kullanıcı hesabı bulunmamaktadır.")
        else:
            del_user_id = st.selectbox(
                "Silinecek Kullanıcı Hesabı",
                deletable_users["id"].tolist(),
                format_func=lambda x: f"Kullanıcı Adı: {deletable_users[deletable_users['id']==x]['kullanici_adi'].values[0]} - Rol: {deletable_users[deletable_users['id']==x]['rol'].values[0]} ({deletable_users[deletable_users['id']==x]['birlik'].values[0]} / {deletable_users[deletable_users['id']==x]['tim'].values[0]})",
                key="select_del_user"
            )

            confirm_del = st.checkbox("Bu kullanıcı hesabını silmeyi onaylıyorum", key="chk_confirm_del_user")

            if st.button("Kullanıcı Hesabını Sil", type="primary", key="btn_del_user"):
                if confirm_del:
                    cur = conn.cursor()
                    cur.execute("DELETE FROM kullanicilar WHERE id = ?", (del_user_id,))
                    conn.commit()
                    st.success("Kullanıcı hesabı başarıyla silindi!")
                    st.rerun()
                else:
                    st.error("Lütfen önce silme onay kutusunu işaretleyin.")

    conn.close()
