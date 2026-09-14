import streamlit as st
import pandas as pd
import sqlite3
import datetime
import plotly.express as px
import io
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# ---------------------------------------------------------
# SAYFA AYARLARI
# ---------------------------------------------------------
st.set_page_config(
    page_title="Personel Takip & Performans Sistemi",
    page_icon="🎖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# VERİTABANI VERİ YAPISI VE BAĞLANTI
# ---------------------------------------------------------
DB_FILE = "personel_takip.db"

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    # Kullanıcılar tablosu (RBAC)
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            name TEXT NOT NULL
        )
    """)
    
    # Personel tablosu
    c.execute("""
        CREATE TABLE IF NOT EXISTS personnel (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name_surname TEXT NOT NULL,
            registration_no TEXT UNIQUE NOT NULL,
            unit TEXT,
            title TEXT
        )
    """)
    
    # Spor testleri tablosu
    c.execute("""
        CREATE TABLE IF NOT EXISTS sport_tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            personnel_id INTEGER NOT NULL,
            test_date DATE NOT NULL,
            pushups INTEGER DEFAULT 0,
            situps INTEGER DEFAULT 0,
            running_meters INTEGER DEFAULT 0,
            notes TEXT,
            FOREIGN KEY (personnel_id) REFERENCES personnel (id)
        )
    """)
    
    # Yazılı sınavlar tablosu
    c.execute("""
        CREATE TABLE IF NOT EXISTS written_exams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            personnel_id INTEGER NOT NULL,
            exam_date DATE NOT NULL,
            exam_name TEXT NOT NULL,
            score REAL NOT NULL,
            notes TEXT,
            FOREIGN KEY (personnel_id) REFERENCES personnel (id)
        )
    """)
    
    # Varsayılan Kullanıcıları Ekle (Eğer yoksa)
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        default_users = [
            ("admin", "admin123", "admin", "Sistem Yöneticisi (Admin)"),
            ("operator", "op123", "operator", "Veri Giriş Yöneticisi"),
            ("reporter", "rep123", "reporter", "Sunum & Rapor Yöneticisi")
        ]
        c.executemany("INSERT INTO users (username, password, role, name) VALUES (?, ?, ?, ?)", default_users)
    
    # Örnek Personel Verisi (Boş kalmasın diye)
    c.execute("SELECT COUNT(*) FROM personnel")
    if c.fetchone()[0] == 0:
        default_personnel = [
            ("Ahmet Yılmaz", "1001", "1. Bölük", "Uzman Çavuş"),
            ("Mehmet Demir", "1002", "1. Bölük", "Uzman Çavuş"),
            ("Mustafa Kaya", "1003", "2. Bölük", "Astsubay")
        ]
        c.executemany("INSERT INTO personnel (name_surname, registration_no, unit, title) VALUES (?, ?, ?, ?)", default_personnel)
        
        # Örnek Spor Verisi
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)
        prev_week = today - datetime.timedelta(days=7)
        
        c.execute("INSERT INTO sport_tests (personnel_id, test_date, pushups, situps, running_meters) VALUES (1, ?, 10, 20, 1000)", (yesterday,))
        c.execute("INSERT INTO sport_tests (personnel_id, test_date, pushups, situps, running_meters) VALUES (1, ?, 12, 22, 1050)", (today,))
        c.execute("INSERT INTO sport_tests (personnel_id, test_date, pushups, situps, running_meters) VALUES (2, ?, 15, 25, 1200)", (yesterday,))
        c.execute("INSERT INTO sport_tests (personnel_id, test_date, pushups, situps, running_meters) VALUES (2, ?, 18, 28, 1250)", (today,))
        
        # Örnek Sınav Verisi
        c.execute("INSERT INTO written_exams (personnel_id, exam_date, exam_name, score) VALUES (1, ?, 'Genel Mevzuat', 70)", (prev_week,))
        c.execute("INSERT INTO written_exams (personnel_id, exam_date, exam_name, score) VALUES (1, ?, 'Taktik Bilgisi', 85)", (today,))
        c.execute("INSERT INTO written_exams (personnel_id, exam_date, exam_name, score) VALUES (2, ?, 'Genel Mevzuat', 80)", (prev_week,))
        c.execute("INSERT INTO written_exams (personnel_id, exam_date, exam_name, score) VALUES (2, ?, 'Taktik Bilgisi', 90)", (today,))

    conn.commit()
    conn.close()

init_db()

# ---------------------------------------------------------
# OTURUM KONTROLÜ (SESSION STATE)
# ---------------------------------------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None

def login(username, password):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
    user = c.fetchone()
    conn.close()
    if user:
        st.session_state.logged_in = True
        st.session_state.user = dict(user)
        return True
    return False

def logout():
    st.session_state.logged_in = False
    st.session_state.user = None

# ---------------------------------------------------------
# GİRİŞ EKRANI (LOGIN PAGE)
# ---------------------------------------------------------
if not st.session_state.logged_in:
    st.title("🎖️ Personel Takip ve Performans Analiz Sistemi")
    st.subheader("Giriş Yapın")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        with st.form("login_form"):
            username = st.text_input("Kullanıcı Adı")
            password = st.text_input("Şifre", type="password")
            submit = st.form_submit_button("Giriş Yap", use_container_width=True)
            
            if submit:
                if login(username, password):
                    st.success("Giriş başarılı! Yönlendiriliyorsunuz...")
                    st.rerun()
                else:
                    st.error("Hatalı kullanıcı adı veya şifre!")
    
    with col2:
        st.info("""
        **Demo Hesap Bilgileri:**
        - **Admin (Tüm Yetkiler):** `admin` / `admin123`
        - **Veri Giriş Yöneticisi:** `operator` / `op123`
        - **Sunum / Rapor Yöneticisi:** `reporter` / `rep123`
        """)
    st.stop()

# ---------------------------------------------------------
# YAN MENÜ & GEZİNTİ (SIDEBAR & NAVIGATION)
# ---------------------------------------------------------
user = st.session_state.user
role = user["role"]

st.sidebar.title(f"👤 {user['name']}")
st.sidebar.caption(f"Rol: **{role.upper()}**")

# Rol tabanlı menü seçenekleri
menu_options = []
if role in ["admin", "reporter", "operator"]:
    menu_options.append("📊 Dashboard & Performans Analizi")
if role in ["admin", "operator"]:
    menu_options.append("📝 Veri Girişi (Spor & Sınav)")
    menu_options.append("👥 Personel Yönetimi")
if role in ["admin", "reporter"]:
    menu_options.append("📑 Sunum ve Rapor İndir")
if role == "admin":
    menu_options.append("⚙️ Yönetici Hesap Ayarları")

menu_options.append("Çıkış Yap")

choice = st.sidebar.radio("Sistem Menüsü", menu_options)

if choice == "Çıkış Yap":
    logout()
    st.rerun()

# ---------------------------------------------------------
# 1. DASHBOARD VE PERFORMANS ANALİZİ
# ---------------------------------------------------------
if choice == "📊 Dashboard & Performans Analizi":
    st.title("📊 Personel Gelişim ve Analiz Paneli")
    
    conn = get_connection()
    personnel_df = pd.read_sql_query("SELECT * FROM personnel", conn)
    
    if personnel_df.empty:
        st.warning("Sistemde henüz kayıtlı personel bulunmuyor.")
    else:
        # Personel Seçimi
        personnel_list = ["Tüm Personeller"] + list(personnel_df["name_surname"] + " (" + personnel_df["registration_no"] + ")")
        selected_p = st.selectbox("Analiz Edilecek Personeli Seçin:", personnel_list)
        
        if selected_p != "Tüm Personeller":
            p_id = int(selected_p.split("(")[1].replace(")", ""))
            selected_person = personnel_df[personnel_df["registration_no"] == str(p_id)].iloc[0]
            
            st.markdown(f"### 👤 {selected_person['name_surname']} - Gelişim Detayları")
            col_info1, col_info2, col_info3 = st.columns(3)
            col_info1.metric("Sicil No", selected_person['registration_no'])
            col_info2.metric("Birlik/Departman", selected_person['unit'])
            col_info3.metric("Rütbe/Unvan", selected_person['title'])
            
            st.divider()
            
            # Spor Verilerini Çek
            sport_df = pd.read_sql_query("SELECT * FROM sport_tests WHERE personnel_id = ? ORDER BY test_date ASC", conn, params=(selected_person['id'],))
            
            if not sport_df.empty:
                st.subheader("🏋️ Spor Testi Gelişim Metrikleri")
                
                # Yüzdelik Gelişim Hesaplama (Son iki test)
                if len(sport_df) >= 2:
                    last_test = sport_df.iloc[-1]
                    prev_test = sport_df.iloc[-2]
                    
                    pushup_diff = last_test['pushups'] - prev_test['pushups']
                    pushup_pct = (pushup_diff / prev_test['pushups'] * 100) if prev_test['pushups'] > 0 else 0
                    
                    situp_diff = last_test['situps'] - prev_test['situps']
                    situp_pct = (situp_diff / prev_test['situps'] * 100) if prev_test['situps'] > 0 else 0
                    
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Son Şınav Sayısı", f"{last_test['pushups']} Tekrar", delta=f"%{pushup_pct:+.1f} ({pushup_diff:+} Şınav)")
                    m2.metric("Son Mekik Sayısı", f"{last_test['situps']} Tekrar", delta=f"%{situp_pct:+.1f} ({situp_diff:+} Mekik)")
                    m3.metric("Son Koşu Mesafesi", f"{last_test['running_meters']} Metre", delta=f"{last_test['running_meters'] - prev_test['running_meters']:+} Metre")
                else:
                    last_test = sport_df.iloc[-1]
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Son Şınav Sayısı", f"{last_test['pushups']} Tekrar")
                    m2.metric("Son Mekik Sayısı", f"{last_test['situps']} Tekrar")
                    m3.metric("Son Koşu Mesafesi", f"{last_test['running_meters']} Metre")

                # Grafik Çiz
                fig_sport = px.line(sport_df, x="test_date", y=["pushups", "situps"], 
                                    labels={"value": "Tekrar Sayısı", "test_date": "Tarih", "variable": "Egzersiz"},
                                    title="Zaman İçindeki Şınav ve Mekik Gelişimi", markers=True)
                st.plotly_chart(fig_sport, use_container_width=True)
            else:
                st.info("Bu personele ait henüz spor testi kaydı bulunmuyor.")

            st.divider()

            # Yazılı Sınav Verileri
            exam_df = pd.read_sql_query("SELECT * FROM written_exams WHERE personnel_id = ? ORDER BY exam_date ASC", conn, params=(selected_person['id'],))
            if not exam_df.empty:
                st.subheader("📚 Yazılı Sınav Not Gelişimi")
                if len(exam_df) >= 2:
                    last_exam = exam_df.iloc[-1]
                    prev_exam = exam_df.iloc[-2]
                    score_diff = last_exam['score'] - prev_exam['score']
                    score_pct = (score_diff / prev_exam['score'] * 100) if prev_exam['score'] > 0 else 0
                    
                    st.metric("Son Sınav Notu", f"{last_exam['score']} Puan ({last_exam['exam_name']})", delta=f"%{score_pct:+.1f} ({score_diff:+} Puan)")
                
                fig_exam = px.bar(exam_df, x="exam_date", y="score", hover_data=["exam_name"], 
                                   labels={"score": "Puan (0-100)", "exam_date": "Tarih"},
                                   title="Yazılı Sınav Not Geçmişi", text="score")
                st.plotly_chart(fig_exam, use_container_width=True)
            else:
                st.info("Bu personele ait henüz yazılı sınav kaydı bulunmuyor.")

        else:
            # Tüm Personeller Genel Bakış
            st.subheader("🌐 Genel Birlik ve Takım Performans Özeti")
            all_sports = pd.read_sql_query("""
                SELECT p.name_surname, p.unit, s.test_date, s.pushups, s.situps, s.running_meters 
                FROM sport_tests s JOIN personnel p ON s.personnel_id = p.id
            """, conn)
            
            if not all_sports.empty:
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("##### 🏆 En Yüksek Şınav Performansları")
                    top_pushups = all_sports.groupby("name_surname")["pushups"].max().reset_index().sort_values(by="pushups", ascending=False)
                    st.dataframe(top_pushups, use_container_width=True)
                
                with col2:
                    st.markdown("##### 🏆 En Yüksek Mekik Performansları")
                    top_situps = all_sports.groupby("name_surname")["situps"].max().reset_index().sort_values(by="situps", ascending=False)
                    st.dataframe(top_situps, use_container_width=True)
            else:
                st.info("Henüz kaydedilmiş veri bulunmuyor.")
                
    conn.close()

# ---------------------------------------------------------
# 2. VERİ GİRİŞİ (SPOR & SINAV)
# ---------------------------------------------------------
elif choice == "📝 Veri Girişi (Spor & Sınav)":
    st.title("📝 Günlük ve Haftalık Veri Girişi")
    
    conn = get_connection()
    personnel_df = pd.read_sql_query("SELECT * FROM personnel", conn)
    
    if personnel_df.empty:
        st.error("Lütfen önce 'Personel Yönetimi' sekmesinden en az 1 personel ekleyin.")
    else:
        tab1, tab2 = st.tabs(["🏋️ Spor Testi Girişi", "📚 Yazılı Sınav Girişi"])
        
        with tab1:
            st.subheader("Yeni Spor Testi Kaydı")
            p_dict = {f"{row['name_surname']} ({row['registration_no']})": row['id'] for _, row in personnel_df.iterrows()}
            selected_p_name = st.selectbox("Personel Seçin:", list(p_dict.keys()), key="sport_p")
            selected_p_id = p_dict[selected_p_name]
            
            with st.form("sport_form"):
                test_date = st.date_input("Test Tarihi", datetime.date.today())
                col_s1, col_s2, col_s3 = st.columns(3)
                pushups = col_s1.number_input("Şınav Sayısı (Tekrar)", min_value=0, value=10)
                situps = col_s2.number_input("Mekik Sayısı (Tekrar)", min_value=0, value=20)
                running = col_s3.number_input("Koşu Mesafesi (Metre)", min_value=0, value=1000, step=50)
                notes = st.text_area("Notlar / Açıklama (İsteğe Bağlı)")
                
                submit_sport = st.form_submit_button("Spor Testini Kaydet", use_container_width=True)
                
                if submit_sport:
                    c = conn.cursor()
                    c.execute("""
                        INSERT INTO sport_tests (personnel_id, test_date, pushups, situps, running_meters, notes)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (selected_p_id, test_date, pushups, situps, running, notes))
                    conn.commit()
                    st.success(f"{selected_p_name} için spor testi başarıyla kaydedildi!")
        
        with tab2:
            st.subheader("Yeni Yazılı Sınav Kaydı")
            selected_p_name_exam = st.selectbox("Personel Seçin:", list(p_dict.keys()), key="exam_p")
            selected_p_id_exam = p_dict[selected_p_name_exam]
            
            with st.form("exam_form"):
                exam_date = st.date_input("Sınav Tarihi", datetime.date.today())
                exam_name = st.text_input("Sınav Adı / Konusu", "Genel Mevzuat Sınavı")
                score = st.number_input("Sınav Puanı (0 - 100)", min_value=0.0, max_value=100.0, value=75.0, step=0.5)
                exam_notes = st.text_area("Sınav Notları (İsteğe Bağlı)")
                
                submit_exam = st.form_submit_button("Sınav Notunu Kaydet", use_container_width=True)
                
                if submit_exam:
                    c = conn.cursor()
                    c.execute("""
                        INSERT INTO written_exams (personnel_id, exam_date, exam_name, score, notes)
                        VALUES (?, ?, ?, ?, ?)
                    """, (selected_p_id_exam, exam_date, exam_name, score, exam_notes))
                    conn.commit()
                    st.success(f"{selected_p_name_exam} için sınav notu kaydedildi!")

    conn.close()

# ---------------------------------------------------------
# 3. PERSONEL YÖNETİMİ
# ---------------------------------------------------------
elif choice == "👥 Personel Yönetimi":
    st.title("👥 Personel Kayıt ve Düzenleme")
    
    conn = get_connection()
    
    col_add, col_list = st.columns([1, 2])
    
    with col_add:
        st.subheader("➕ Yeni Personel Ekle")
        with st.form("add_personnel_form"):
            name_surname = st.text_input("Ad Soyad")
            reg_no = st.text_input("Sicil / ID No")
            unit = st.text_input("Birlik / Departman", "1. Bölük")
            title = st.text_input("Rütbe / Unvan", "Uzman Çavuş")
            
            save_btn = st.form_submit_button("Personeli Kaydet", use_container_width=True)
            if save_btn:
                if name_surname and reg_no:
                    try:
                        c = conn.cursor()
                        c.execute("INSERT INTO personnel (name_surname, registration_no, unit, title) VALUES (?, ?, ?, ?)",
                                  (name_surname, reg_no, unit, title))
                        conn.commit()
                        st.success(f"{name_surname} başarıyla eklendi!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Bu Sicil/ID Numarası zaten kayıtlı!")
                else:
                    st.error("Lütfen Ad Soyad ve Sicil No alanlarını doldurun.")

    with col_list:
        st.subheader("📋 Mevcut Personel Listesi")
        p_df = pd.read_sql_query("SELECT id, registration_no as 'Sicil No', name_surname as 'Ad Soyad', unit as 'Birlik', title as 'Unvan' FROM personnel", conn)
        st.dataframe(p_df, use_container_width=True)
        
        # Silme Bölümü
        if not p_df.empty:
            st.divider()
            st.caption("🗑️ Personel Sil")
            p_to_delete = st.selectbox("Silinecek Personel:", p_df["Ad Soyad"] + " (" + p_df["Sicil No"] + ")")
            if st.button("Seçili Personeli Sil", type="primary"):
                del_id = p_df[p_df["Ad Soyad"] + " (" + p_df["Sicil No"] + ")" == p_to_delete]["id"].values[0]
                c = conn.cursor()
                c.execute("DELETE FROM personnel WHERE id = ?", (del_id,))
                c.execute("DELETE FROM sport_tests WHERE personnel_id = ?", (del_id,))
                c.execute("DELETE FROM written_exams WHERE personnel_id = ?", (del_id,))
                conn.commit()
                st.success("Personel ve ilişkili tüm veriler silindi!")
                st.rerun()

    conn.close()

# ---------------------------------------------------------
# 4. SUNUM VE RAPOR İNDİR (LİDERLİK İÇİN)
# ---------------------------------------------------------
elif choice == "📑 Sunum ve Rapor İndir":
    st.title("📑 Liderlik Sunumu ve Rapor Çıktısı")
    st.write("Bu modül, girilen tüm verileri ve gelişim raporlarını amirlere/liderliğe sunmak üzere Excel ve PDF formatında indirmenizi sağlar.")
    
    conn = get_connection()
    
    # Verileri Birleştirilmiş Tabloya Dönüştür
    sports_df = pd.read_sql_query("""
        SELECT p.registration_no as 'Sicil No', p.name_surname as 'Ad Soyad', p.unit as 'Birlik',
               s.test_date as 'Tarih', s.pushups as 'Şınav', s.situps as 'Mekik', s.running_meters as 'Koşu (m)'
        FROM sport_tests s JOIN personnel p ON s.personnel_id = p.id
        ORDER BY s.test_date DESC
    """, conn)
    
    exams_df = pd.read_sql_query("""
        SELECT p.registration_no as 'Sicil No', p.name_surname as 'Ad Soyad', p.unit as 'Birlik',
               e.exam_date as 'Tarih', e.exam_name as 'Sınav Adı', e.score as 'Puan'
        FROM written_exams e JOIN personnel p ON e.personnel_id = p.id
        ORDER BY e.exam_date DESC
    """, conn)
    
    col_exp1, col_exp2 = st.columns(2)
    
    with col_exp1:
        st.subheader("📊 Excel Formatında Rapor")
        st.write("Tüm spor ve sınav verilerini ayrı sekmelerde Excel dosyası olarak indirin.")
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            sports_df.to_excel(writer, sheet_name='Spor Testleri', index=False)
            exams_df.to_excel(writer, sheet_name='Yazılı Sınavlar', index=False)
        excel_data = output.getvalue()
        
        st.download_button(
            label="📥 Excel Raporunu İndir (.xlsx)",
            data=excel_data,
            file_name=f"personel_gelisim_raporu_{datetime.date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    with col_exp2:
        st.subheader("📄 PDF Formatında Sunum Özeti")
        st.write("Liderlik sunumu için resmi özet raporu PDF olarak indirin.")
        
        def generate_pdf():
            pdf_buffer = io.BytesIO()
            doc = SimpleDocTemplate(pdf_buffer, pagesize=A4)
            elements = []
            styles = getSampleStyleSheet()
            
            title_style = ParagraphStyle(
                'TitleStyle',
                parent=styles['Heading1'],
                fontSize=18,
                textColor=colors.HexColor("#1A365D"),
                spaceAfter=12
            )
            
            elements.append(Paragraph("PERSONEL GELİŞİM VE PERFORMANS RAPORU", title_style))
            elements.append(Paragraph(f"<b>Rapor Tarihi:</b> {datetime.date.today().strftime('%d.%m.%Y')}", styles['Normal']))
            elements.append(Spacer(1, 15))
            
            elements.append(Paragraph("<b>1. Son Spor Testi Kayıtları</b>", styles['Heading2']))
            if not sports_df.empty:
                s_data = [sports_df.columns.tolist()] + sports_df.head(10).values.tolist()
                t_sport = Table(s_data)
                t_sport.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2B6CB0")),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0,0), (-1,0), 6),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.grey)
                ]))
                elements.append(t_sport)
            else:
                elements.append(Paragraph("Spor verisi bulunamadı.", styles['Normal']))
                
            elements.append(Spacer(1, 15))
            elements.append(Paragraph("<b>2. Son Yazılı Sınav Kayıtları</b>", styles['Heading2']))
            if not exams_df.empty:
                e_data = [exams_df.columns.tolist()] + exams_df.head(10).values.tolist()
                t_exam = Table(e_data)
                t_exam.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2D3748")),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.grey)
                ]))
                elements.append(t_exam)
            else:
                elements.append(Paragraph("Sınav verisi bulunamadı.", styles['Normal']))
                
            doc.build(elements)
            pdf_buffer.seek(0)
            return pdf_buffer.getvalue()

        pdf_bytes = generate_pdf()
        st.download_button(
            label="📥 PDF Sunum Raporunu İndir (.pdf)",
            data=pdf_bytes,
            file_name=f"personel_sunum_raporu_{datetime.date.today()}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    st.divider()
    st.subheader("📋 Veri Önizleme")
    st.markdown("##### 🏋️ Spor Testleri Tablosu")
    st.dataframe(sports_df, use_container_width=True)
    st.markdown("##### 📚 Yazılı Sınavlar Tablosu")
    st.dataframe(exams_df, use_container_width=True)

    conn.close()

# ---------------------------------------------------------
# 5. YÖNETİCİ HESAP AYARLARI (SADECE ADMİN)
# ---------------------------------------------------------
elif choice == "⚙️ Yönetici Hesap Ayarları":
    st.title("⚙️ Sistem Yöneticisi Paneli")
    st.write("Bu ekrandan yeni yöneticiler ekleyebilir veya rollerini düzenleyebilirsiniz.")
    
    conn = get_connection()
    
    col_u1, col_u2 = st.columns([1, 2])
    
    with col_u1:
        st.subheader("➕ Yeni Yönetici / Kullanıcı Ekle")
        with st.form("add_user_form"):
            u_name = st.text_input("Ad Soyad")
            u_username = st.text_input("Kullanıcı Adı")
            u_password = st.text_input("Şifre", type="password")
            u_role = st.selectbox("Yetki Rolü", [
                ("operator", "Veri Giriş Yöneticisi"),
                ("reporter", "Sunum / Rapor Yöneticisi"),
                ("admin", "Sistem Yöneticisi (Admin)")
            ], format_func=lambda x: x[1])
            
            user_save = st.form_submit_button("Kullanıcıyı Kaydet", use_container_width=True)
            if user_save:
                if u_username and u_password and u_name:
                    try:
                        c = conn.cursor()
                        c.execute("INSERT INTO users (username, password, role, name) VALUES (?, ?, ?, ?)",
                                  (u_username, u_password, u_role[0], u_name))
                        conn.commit()
                        st.success(f"{u_name} adlı kullanıcı başarıyla eklendi!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Bu kullanıcı adı zaten mevcut!")
                else:
                    st.error("Lütfen tüm alanları doldurun.")

    with col_u2:
        st.subheader("👥 Mevcut Sistem Kullanıcıları")
        users_df = pd.read_sql_query("SELECT id, name as 'Ad Soyad', username as 'Kullanıcı Adı', role as 'Rol' FROM users", conn)
        st.dataframe(users_df, use_container_width=True)

    conn.close()
