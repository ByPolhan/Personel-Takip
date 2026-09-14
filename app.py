import streamlit as st
import sqlite3
import pandas as pd
import hashlib
import datetime
import io
import matplotlib.pyplot as plt
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor

# ==========================================
# 1. SAYFA YAPILANDIRMASI VE SABİTLER
# ==========================================
st.set_page_config(
    page_title="Tabur Personel Performans Takip Sistemi",
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
    st.title("🛡️ Tabur Personel Performans Takip Sistemi")
    st.subheader("Giriş Paneli")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        username = st.text_input("Kullanıcı Adı")
        password = st.text_input("Şifre", type='password')
        if st.button("Giriş Yap", type="primary"):
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

st.sidebar.title("🛡️ Tabur Takip Paneli")
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

menu_options.append("📝 Veri Girişi")

if role in ["Admin", "Destek Takım Komutanı", "Bölük Yetkilisi", "Tim Komutanı"]:
    menu_options.append("👤 Personel Yönetimi")

if role in ["Admin", "Reporter"]:
    menu_options.append("📄 Sunum ve Rapor Alma")

if role == "Admin":
    menu_options.append("⚙️ Yönetici Paneli")

if st.sidebar.button("Güvenli Çıkış"):
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
        SELECT p.tarih, p.periyot, per.sicil_no, per.ad_soyad, per.birlik, per.tim,
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

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            secilen_periyot = st.selectbox("Periyot Seçin", ["Tümü"] + PERIYOTLAR)
        with col_f2:
            secilen_birlik = st.selectbox("Birlik Filtresi", ["Tümü"] + BIRLIK_LISTESI)

        if secilen_periyot != "Tümü":
            df = df[df["periyot"] == secilen_periyot]
        if secilen_birlik != "Tümü":
            df = df[df["birlik"] == secilen_birlik]

        st.subheader("📈 Genel Ortalamalar")
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Şınav (Ort.)", f"{df['sinav'].mean():.1f}")
        m2.metric("Mekik (Ort.)", f"{df['mekik'].mean():.1f}")
        m3.metric("Barfiks (Ort.)", f"{df['barfiks'].mean():.1f}")
        
        avg_kosu_sn = df['kosu_3000m_sn'].dropna().mean() if not df['kosu_3000m_sn'].dropna().empty else 0
        m4.metric("3000m Koşu (Ort.)", format_kosu_saniye(avg_kosu_sn))
        m5.metric("Yazılı Sınav (Ort.)", f"{df['yazili_sinav'].mean():.1f}")

        st.divider()

        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.subheader("🏆 Bölük Bazlı Genel Başarı Ortalamaları")
            boluk_grp = df.groupby("birlik")[["sinav", "mekik", "barfiks", "yazili_sinav"]].mean()
            st.bar_chart(boluk_grp)

        with col_g2:
            st.subheader("🏃‍♂️ Bölük Bazlı 3000m Koşu Ortalamaları (Saniye)")
            kosu_grp = df.groupby("birlik")["kosu_3000m_sn"].mean()
            st.bar_chart(kosu_grp)

        st.subheader("🎖️ En Yüksek Başarı Gösteren İlk 10 Personel")
        df["Genel_Skor"] = (
            df["sinav"].fillna(0) + 
            df["mekik"].fillna(0) + 
            (df["barfiks"].fillna(0) * 2) + 
            df["yazili_sinav"].fillna(0) - 
            (df["kosu_3000m_sn"].fillna(1200) / 10)
        )
        top10 = df.sort_values(by="Genel_Skor", ascending=False).head(10).copy()
        top10["3000m Koşu"] = top10["kosu_3000m_sn"].apply(format_kosu_saniye)
        
        st.dataframe(top10[["ad_soyad", "birlik", "tim", "sinav", "mekik", "barfiks", "3000m Koşu", "yazili_sinav"]], use_container_width=True)

# ==========================================
# MENÜ 2: VERİ GİRİŞİ
# ==========================================
elif choice == "📝 Veri Girişi":
    st.header("📝 Performans Veri Girişi")

    conn = get_db()
    
    if role in ["Admin", "Reporter"]:
        allowed_birlikler = BIRLIK_LISTESI
    elif role == "Destek Takım Komutanı":
        allowed_birlikler = ["Destek Bölüğü"]
    else:
        allowed_birlikler = [user["birlik"]]

    col1, col2, col3 = st.columns(3)
    
    with col1:
        secilen_birlik = st.selectbox("Birlik", allowed_birlikler)
    
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
            secilen_tim = st.selectbox("Tim / Unvan", allowed_timler)

    with col3:
        secilen_periyot = st.selectbox("Periyot", PERIYOTLAR)

    if secilen_birlik in ["Karargah", "Destek Bölüğü"]:
        personel_df = pd.read_sql_query("SELECT id, sicil_no, ad_soyad FROM personel WHERE birlik=?", 
                                        conn, params=(secilen_birlik,))
    else:
        personel_df = pd.read_sql_query("SELECT id, sicil_no, ad_soyad FROM personel WHERE birlik=? AND tim=?", 
                                        conn, params=(secilen_birlik, secilen_tim))
    
    if personel_df.empty:
        st.warning("Seçilen birlikte kayıtlı personel bulunamadı.")
    else:
        secilen_personel_id = st.selectbox("Personel Seçin", 
                                           options=personel_df["id"].tolist(), 
                                           format_func=lambda x: f"{personel_df[personel_df['id']==x]['sicil_no'].values[0]} - {personel_df[personel_df['id']==x]['ad_soyad'].values[0]}")
        
        st.divider()
        tab_spor, tab_yazili = st.tabs(["🏃‍♂️ Spor Testi Girişi", "📝 Yazılı Sınav Girişi"])

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
        st.dataframe(display_rep[["PBİK", "ad_soyad", "rutbe", "birlik", "tim", "periyot", "sinav", "mekik", "barfiks", "3000m Koşu", "yazili_sinav"]], use_container_width=True)

        col_d1, col_d2 = st.columns(2)

        with col_d1:
            def create_pptx():
                prs = Presentation()
                prs.slide_width = Inches(13.333)
                prs.slide_height = Inches(7.5)
                blank_layout = prs.slide_layouts[6]

                slide1 = prs.slides.add_slide(blank_layout)
                title_box = slide1.shapes.add_textbox(Inches(1), Inches(2), Inches(11.333), Inches(3.5))
                tf1 = title_box.text_frame
                tf1.word_wrap = True
                
                p1 = tf1.paragraphs[0]
                p1.text = "🛡️ TABUR PERSONEL PERFORMANS SUNUMU"
                p1.font.size = Pt(32)
                p1.font.bold = True
                p1.font.color.rgb = RGBColor(30, 58, 138)
                p1.alignment = PP_ALIGN.CENTER
                
                kapsam_metni = f"{kapsam_tipi}"
                if kapsam_tipi == "Belirli Bölük":
                    kapsam_metni += f" ({secilen_b})"
                elif kapsam_tipi == "Belirli Tim":
                    kapsam_metni += f" ({secilen_b} / {secilen_t})"

                p2 = tf1.add_paragraph()
                p2.text = f"\nKapsam: {kapsam_metni}\nPeriyot: {periyot_filtre}\nTarih: {datetime.date.today().strftime('%d.%m.%Y')}"
                p2.font.size = Pt(20)
                p2.font.color.rgb = RGBColor(71, 85, 105)
                p2.alignment = PP_ALIGN.CENTER

                slide2 = prs.slides.add_slide(blank_layout)
                header_box2 = slide2.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.733), Inches(0.8))
                p_h2 = header_box2.text_frame.paragraphs[0]
                p_h2.text = "📊 En Başarılı Personeller ve Performans Tablosu"
                p_h2.font.size = Pt(24)
                p_h2.font.bold = True
                p_h2.font.color.rgb = RGBColor(30, 58, 138)

                df_top = report_df.copy()
                df_top["Genel_Skor"] = (
                    df_top["sinav"].fillna(0) + 
                    df_top["mekik"].fillna(0) + 
                    (df_top["barfiks"].fillna(0) * 2) + 
                    df_top["yazili_sinav"].fillna(0) - 
                    (df_top["kosu_3000m_sn"].fillna(1200) / 10)
                )
                df_top5 = df_top.sort_values(by="Genel_Skor", ascending=False).head(5)

                rows, cols = len(df_top5) + 1, 7
                table_shape = slide2.shapes.add_table(rows, cols, Inches(0.8), Inches(1.5), Inches(11.733), Inches(4.5))
                table = table_shape.table

                headers = ["PBİK", "Ad Soyad", "Birlik", "Şınav", "Mekik", "Barfiks", "3000m Koşu"]
                for c_idx, h_text in enumerate(headers):
                    cell = table.cell(0, c_idx)
                    cell.text = h_text
                    for p in cell.text_frame.paragraphs:
                        p.font.bold = True
                        p.font.size = Pt(13)
                        p.font.color.rgb = RGBColor(255, 255, 255)
                        p.alignment = PP_ALIGN.CENTER
                    cell.fill.solid()
                    cell.fill.fore_color.rgb = RGBColor(30, 58, 138)

                for r_idx, (_, r_data) in enumerate(df_top5.iterrows(), start=1):
                    vals = [
                        str(r_data["PBİK"]), str(r_data["ad_soyad"]), str(r_data["birlik"]),
                        str(int(r_data["sinav"])) if pd.notna(r_data["sinav"]) else "-",
                        str(int(r_data["mekik"])) if pd.notna(r_data["mekik"]) else "-",
                        str(int(r_data["barfiks"])) if pd.notna(r_data["barfiks"]) else "-",
                        format_kosu_saniye(r_data["kosu_3000m_sn"])
                    ]
                    for c_idx, val in enumerate(vals):
                        cell = table.cell(r_idx, c_idx)
                        cell.text = val
                        for p in cell.text_frame.paragraphs:
                            p.font.size = Pt(12)
                            p.alignment = PP_ALIGN.CENTER

                slide3 = prs.slides.add_slide(blank_layout)
                header_box3 = slide3.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.733), Inches(0.8))
                p_h3 = header_box3.text_frame.paragraphs[0]
                p_h3.text = "📈 Grafiksel Performans ve Dağılım Analizi"
                p_h3.font.size = Pt(24)
                p_h3.font.bold = True
                p_h3.font.color.rgb = RGBColor(30, 58, 138)

                fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.8))
                plt.subplots_adjust(wspace=0.3)

                grp = report_df.groupby("birlik")[["sinav", "mekik", "barfiks"]].mean()
                if not grp.empty:
                    grp.plot(kind="bar", ax=ax1, color=["#2563EB", "#16A34A", "#EA580C"])
                    ax1.set_title("Bölük Bazlı Spor Ortalamaları", fontsize=11, fontweight="bold")
                    ax1.set_ylabel("Tekrar")
                    ax1.grid(axis="y", linestyle="--", alpha=0.6)
                    ax1.tick_params(axis='x', rotation=20)

                data_box = [
                    report_df["sinav"].dropna(),
                    report_df["mekik"].dropna(),
                    report_df["barfiks"].dropna(),
                    report_df["yazili_sinav"].dropna()
                ]
                if any(len(d) > 0 for d in data_box):
                    bp = ax2.boxplot([d for d in data_box if len(d)>0], patch_artist=True)
                    colors = ['#93C5FD', '#86EFAC', '#FDBA74', '#FCA5A5']
                    for patch, color in zip(bp['boxes'], colors[:len(bp['boxes'])]):
                        patch.set_facecolor(color)
                    ax2.set_title("Performans Dağılımı (Mum / Boxplot)", fontsize=11, fontweight="bold")
                    ax2.grid(axis="y", linestyle="--", alpha=0.6)

                img_buf = io.BytesIO()
                plt.savefig(img_buf, format="png", dpi=150, bbox_inches="tight")
                plt.close(fig)
                img_buf.seek(0)

                slide3.shapes.add_picture(img_buf, Inches(0.8), Inches(1.3), width=Inches(11.733))

                pptx_out = io.BytesIO()
                prs.save(pptx_out)
                pptx_out.seek(0)
                return pptx_out

            pptx_file = create_pptx()
            st.download_button(
                label="🖥️ Profesyonel PowerPoint Sunumunu İndir (.pptx)",
                data=pptx_file,
                file_name=f"Tabur_Performans_Sunumu_{datetime.date.today()}.pptx",
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
                file_name=f"Tabur_Performans_Raporu_{datetime.date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

# ==========================================
# MENÜ 5: YÖNETİCİ PANELİ (GÜNCELLENDİ)
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

        # Ana admin ve oturum acan kendi kullanicisini silme listesinden haric tut
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
