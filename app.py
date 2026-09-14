import streamlit as st
import sqlite3
import pandas as pd
import hashlib
import datetime
import io

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

TIM_LISTESI = ["1. Tim", "2. Tim", "3. Tim", "4. Tim"]
PERIYOTLAR = ["Günlük", "Haftalık", "Aylık"]

ROLLER = [
    "Admin",
    "Reporter",
    "Destek Takım Komutanı",
    "Bölük Yetkilisi",
    "Tim Komutanı"
]

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
                    kosu_3000m REAL,
                    yazili_sinav REAL,
                    kaydeden TEXT,
                    FOREIGN KEY(personel_id) REFERENCES personel(id)
                )''')
    
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

menu_options = [
    "📊 Tabur Performans Dashboard",
    "📝 Veri Girişi",
    "👤 Personel Yönetimi"
]

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
               p.sinav, p.mekik, p.barfiks, p.kosu_3000m, p.yazili_sinav
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
        m1.metric("Şınav (Ort.)", f"{df['sinav'].mean():.1f} tk")
        m2.metric("Mekik (Ort.)", f"{df['mekik'].mean():.1f} tk")
        m3.metric("Barfiks (Ort.)", f"{df['barfiks'].mean():.1f} tk")
        m4.metric("3000m Koşu (Ort.)", f"{df['kosu_3000m'].mean():.1f} dk")
        m5.metric("Yazılı Sınav (Ort.)", f"{df['yazili_sinav'].mean():.1f} Pn")

        st.divider()

        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.subheader("🏆 Bölük Bazlı Genel Başarı Ortalama")
            boluk_grp = df.groupby("birlik")[["sinav", "mekik", "barfiks", "yazili_sinav"]].mean()
            st.bar_chart(boluk_grp)

        with col_g2:
            st.subheader("🏃‍♂️ Bölük Bazlı 3000m Koşu Dereceleri")
            kosu_grp = df.groupby("birlik")["kosu_3000m"].mean()
            st.bar_chart(kosu_grp)

        st.subheader("🎖️ En Yüksek Başarı Gösteren İlk 10 Personel")
        df["Genel_Skor"] = df["sinav"] + df["mekik"] + (df["barfiks"] * 2) + df["yazili_sinav"] - (df["kosu_3000m"] * 2)
        top10 = df.sort_values(by="Genel_Skor", ascending=False).head(10)
        st.dataframe(top10[["ad_soyad", "birlik", "tim", "sinav", "mekik", "barfiks", "kosu_3000m", "yazili_sinav"]], use_container_width=True)

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
        # Karargah ve Destek Bölüğünde tim seçimi yapılmaz
        if secilen_birlik in ["Karargah", "Destek Bölüğü"]:
            secilen_tim = "-"
            st.info("💡 Bu birlikte tim seçimi yoktur.")
        else:
            if role == "Tim Komutanı":
                allowed_timler = [user["tim"]]
            else:
                allowed_timler = TIM_LISTESI
            secilen_tim = st.selectbox("Tim", allowed_timler)

    with col3:
        secilen_periyot = st.selectbox("Periyot", PERIYOTLAR)

    tarih = st.date_input("Test Tarihi", datetime.date.today())

    # Personel Getirme Sorgusu
    if secilen_birlik in ["Karargah", "Destek Bölüğü"]:
        personel_df = pd.read_sql_query("SELECT id, sicil_no, ad_soyad FROM personel WHERE birlik=?", 
                                        conn, params=(secilen_birlik,))
    else:
        personel_df = pd.read_sql_query("SELECT id, sicil_no, ad_soyad FROM personel WHERE birlik=? AND tim=?", 
                                        conn, params=(secilen_birlik, secilen_tim))
    
    if personel_df.empty:
        st.warning("Seçilen birlikte kayıtlı personel bulunamadı. Lütfen önce Personel Yönetimi menüsünden personel ekleyin.")
    else:
        secilen_personel_id = st.selectbox("Personel Seçin", 
                                           options=personel_df["id"].tolist(), 
                                           format_func=lambda x: f"{personel_df[personel_df['id']==x]['sicil_no'].values[0]} - {personel_df[personel_df['id']==x]['ad_soyad'].values[0]}")
        
        st.subheader("📋 Test ve Performans Değerleri")
        c1, c2, c3 = st.columns(3)
        with c1:
            sinav = st.number_input("Şınav (Tekrar)", min_value=0, max_value=200, value=30)
            mekik = st.number_input("Mekik (Tekrar)", min_value=0, max_value=200, value=35)
        with c2:
            barfiks = st.number_input("Barfiks (Tekrar)", min_value=0, max_value=100, value=10)
            kosu = st.number_input("3.000 Metre Koşu (Dakika.Saniye - Örn: 13.5)", min_value=0.0, max_value=60.0, value=14.0, step=0.1)
        with c3:
            yazili = st.number_input("Yazılı Sınav Notu (0 - 100)", min_value=0.0, max_value=100.0, value=75.0)

        if st.button("Kaydet", type="primary"):
            cur = conn.cursor()
            cur.execute('''INSERT INTO performans 
                          (personel_id, tarih, periyot, sinav, mekik, barfiks, kosu_3000m, yazili_sinav, kaydeden)
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                       (secilen_personel_id, str(tarih), secilen_periyot, sinav, mekik, barfiks, kosu, yazili, user["username"]))
            conn.commit()
            st.success("Performans verisi başarıyla kaydedildi!")
    
    conn.close()

# ==========================================
# MENÜ 3: PERSONEL YÖNETİMİ
# ==========================================
elif choice == "👤 Personel Yönetimi":
    st.header("👤 Tabur Personel Kayıt ve Yönetimi")

    tab1, tab2 = st.tabs(["Yeni Personel Ekle", "Personel Listesi"])

    conn = get_db()

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
            sicil_no = st.text_input("Sicil / T.C. No")
            ad_soyad = st.text_input("Ad Soyad")
            rutbe = st.text_input("Rütbe (Örn: Uzm.Çvş., Astsb., Tğm.)")
        with col2:
            p_birlik = st.selectbox("Atandığı Birlik", p_birlikler)
            
            # Karargah ve Destek Bölüğü için Tim Yok
            if p_birlik in ["Karargah", "Destek Bölüğü"]:
                p_tim = "-"
                st.info("💡 Bu birlikte tim ayrımı bulunmamaktadır.")
            else:
                if role == "Tim Komutanı":
                    p_timler = [user["tim"]]
                else:
                    p_timler = TIM_LISTESI
                p_tim = st.selectbox("Atandığı Tim", p_timler)

        if st.button("Personel Kaydet"):
            if sicil_no and ad_soyad:
                try:
                    cur = conn.cursor()
                    cur.execute("INSERT INTO personel (sicil_no, ad_soyad, rutbe, birlik, tim) VALUES (?, ?, ?, ?, ?)",
                                (sicil_no, ad_soyad, rutbe, p_birlik, p_tim))
                    conn.commit()
                    st.success(f"{ad_soyad} başarıyla sisteme eklendi.")
                except sqlite3.IntegrityError:
                    st.error("Bu Sicil/T.C. No ile kayıtlı bir personel zaten var!")
            else:
                st.warning("Lütfen Sicil ve Ad Soyad alanlarını doldurun.")

    with tab2:
        st.subheader("Mevcut Personel Listesi")
        p_df = pd.read_sql_query("SELECT sicil_no, ad_soyad, rutbe, birlik, tim FROM personel", conn)
        
        if role == "Destek Takım Komutanı":
            p_df = p_df[p_df["birlik"] == "Destek Bölüğü"]
        elif role == "Bölük Yetkilisi":
            p_df = p_df[p_df["birlik"] == user["birlik"]]
        elif role == "Tim Komutanı":
            p_df = p_df[(p_df["birlik"] == user["birlik"]) & (p_df["tim"] == user["tim"])]

        st.dataframe(p_df, use_container_width=True)

    conn.close()

# ==========================================
# MENÜ 4: SUNUM VE RAPOR ALMA
# ==========================================
elif choice == "📄 Sunum ve Rapor Alma":
    st.header("📄 Komutanlık Sunum ve Rapor Dosyası Oluşturucu")
    st.info("Bu modül sadece **Reporter** ve **Admin** yetkisine sahip kullanıcılar tarafından erişilebilir.")

    conn = get_db()
    query = '''
        SELECT p.tarih, p.periyot, per.sicil_no, per.ad_soyad, per.rutbe, per.birlik, per.tim,
               p.sinav, p.mekik, p.barfiks, p.kosu_3000m, p.yazili_sinav, p.kaydeden
        FROM performans p
        JOIN personel per ON p.personel_id = per.id
    '''
    report_df = pd.read_sql_query(query, conn)
    conn.close()

    if report_df.empty:
        st.warning("Raporlanacak veri bulunamadı.")
    else:
        st.subheader("📊 Rapor Önizleme")
        st.dataframe(report_df, use_container_width=True)

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            report_df.to_excel(writer, sheet_name='Tabur Performans Raporu', index=False)
            ozet = report_df.groupby("birlik")[["sinav", "mekik", "barfiks", "kosu_3000m", "yazili_sinav"]].mean()
            ozet.to_excel(writer, sheet_name='Bölük Ortalamaları Özet')

        buffer.seek(0)

        st.download_button(
            label="📥 Sunum ve Excel Raporunu İndir (.xlsx)",
            data=buffer,
            file_name=f"Tabur_Performans_Raporu_{datetime.date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# ==========================================
# MENÜ 5: YÖNETİCİ PANELİ
# ==========================================
elif choice == "⚙️ Yönetici Paneli":
    st.header("⚙️ Admin Kullanıcı Yönetimi & Şifre Sıfırlama")
    
    tab1, tab2 = st.tabs(["Yeni Kullanıcı / Yetkili Tanımla", "Şifre Sıfırlama ve Kullanıcı Listesi"])

    conn = get_db()

    with tab1:
        st.subheader("Sisteme Yeni Yetkili Ekle")
        u_col1, u_col2 = st.columns(2)
        
        with u_col1:
            new_username = st.text_input("Kullanıcı Adı")
            new_password = st.text_input("Şifre", type="password")
            new_role = st.selectbox("Atanacak Rol", ROLLER)

        with u_col2:
            if new_role in ["Admin", "Reporter"]:
                assigned_birlik = "Tüm Tabur"
                assigned_tim = "-"
                st.info("Admin ve Reporter tüm taburdan sorumludur.")
            elif new_role == "Destek Takım Komutanı":
                assigned_birlik = "Destek Bölüğü"
                assigned_tim = "-"
                st.info("Destek Takım Komutanı sadece Destek Bölüğünden sorumludur.")
            else:
                assigned_birlik = st.selectbox("Sorumlu Olduğu Birlik", [b for b in BIRLIK_LISTESI if b not in ["Karargah", "Destek Bölüğü"]])
                if new_role == "Bölük Yetkilisi":
                    assigned_tim = "-"
                else:
                    assigned_tim = st.selectbox("Sorumlu Olduğu Tim", TIM_LISTESI)

        if st.button("Kullanıcıyı Kaydet", type="primary"):
            if new_username and new_password:
                try:
                    cur = conn.cursor()
                    hashed_p = make_hashes(new_password)
                    cur.execute("INSERT INTO kullanicilar (kullanici_adi, sifre, rol, birlik, tim) VALUES (?, ?, ?, ?, ?)",
                                (new_username, hashed_p, new_role, assigned_birlik, assigned_tim))
                    conn.commit()
                    st.success(f"'{new_username}' kullanıcısı {new_role} olarak eklendi.")
                except sqlite3.IntegrityError:
                    st.error("Bu kullanıcı adı zaten alınmış!")
            else:
                st.warning("Lütfen kullanıcı adı ve şifre girin.")

    with tab2:
        st.subheader("Mevcut Kullanıcılar ve Şifre Sıfırlama")
        users_df = pd.read_sql_query("SELECT id, kullanici_adi, rol, birlik, tim FROM kullanicilar", conn)
        st.dataframe(users_df, use_container_width=True)

        st.divider()
        st.subheader("Şifre Sıfırla")
        selected_user_id = st.selectbox("Şifresi Değiştirilecek Kullanıcı", users_df["id"].tolist(), format_func=lambda x: users_df[users_df['id']==x]['kullanici_adi'].values[0])
        reset_pass = st.text_input("Yeni Şifre Belirle", type="password")
        
        if st.button("Şifreyi Güncelle"):
            if reset_pass:
                cur = conn.cursor()
                cur.execute("UPDATE kullanicilar SET sifre = ? WHERE id = ?", (make_hashes(reset_pass), selected_user_id))
                conn.commit()
                st.success("Kullanıcı şifresi başarıyla yenilendi.")
            else:
                st.warning("Lütfen yeni şifreyi giriniz.")

    conn.close()
