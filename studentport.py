import streamlit as st
import pandas as pd
import os
import re
import base64
from datetime import datetime
from sqlalchemy import create_engine, text

# --- Page Config ---
st.set_page_config(page_title="Class 12-B UP Board Portfolio Portal", page_icon="🎓", layout="wide")

# --- Cleaner Helper Function ---
def clean_val(val):
    if pd.isna(val) or val is None:
        return ""
    val_str = str(val).strip()
    if val_str.lower() in ["nan", "none", "nat", "<na>", "null"]:
        return ""
    if re.match(r'^-?\d+\.0+$', val_str):
        val_str = val_str.split('.')[0]
    return val_str

def safe_b64_decode(data_str):
    if not data_str or len(data_str) < 50:
        return None
    try:
        return base64.b64decode(data_str)
    except Exception:
        return None

# --- Zero-Data-Loss Cloud Database Connection ---
@st.cache_resource
def get_engine():
    # Priority 1: Supabase / PostgreSQL Cloud Database (Zero Data Loss)
    if "DB_URL" in st.secrets:
        db_uri = st.secrets["DB_URL"]
        # Handle SQLAlchemy dialect compatibility
        if db_uri.startswith("postgres://"):
            db_uri = db_uri.replace("postgres://", "postgresql://", 1)
        return create_engine(db_uri, pool_pre_ping=True)
    # Priority 2: Fallback Local SQLite
    return create_engine("sqlite:///class12b_portfolio.db")

engine = get_engine()

def init_db():
    with engine.begin() as conn:
        # Students Master Table
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS students (
                roll_no TEXT,
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL,
                class_name TEXT DEFAULT '12-B',
                sr_no TEXT,
                roll_no_10th TEXT,
                pen_no TEXT,
                aadhar_no TEXT,
                dob TEXT,
                dob_dd TEXT,
                dob_mm TEXT,
                dob_yyyy TEXT,
                occupation TEXT,
                ecode TEXT,
                dept TEXT,
                student_name TEXT NOT NULL,
                student_name_hindi TEXT,
                father_name TEXT,
                father_name_hindi TEXT,
                mother_name TEXT,
                mother_name_hindi TEXT,
                gender TEXT,
                caste TEXT,
                category TEXT,
                religion TEXT,
                address TEXT,
                mob_no TEXT,
                email_id TEXT,
                academic_goals TEXT DEFAULT '',
                strengths_weaknesses TEXT DEFAULT '',
                photo_b64 TEXT DEFAULT '',
                role TEXT DEFAULT 'Student'
            )
        '''))
        
        # Portfolio Table
        # SERIAL / AUTOINCREMENT handling for PostgreSQL vs SQLite
        if "postgresql" in str(engine.url):
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS portfolio (
                    id SERIAL PRIMARY KEY,
                    student_username TEXT,
                    portfolio_section TEXT DEFAULT 'General',
                    category TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    learning_reflection TEXT DEFAULT '',
                    project_link TEXT,
                    rubric_regularity INTEGER DEFAULT 0,
                    rubric_authenticity INTEGER DEFAULT 0,
                    rubric_reflection INTEGER DEFAULT 0,
                    rubric_creativity INTEGER DEFAULT 0,
                    total_marks INTEGER DEFAULT 0,
                    grade TEXT DEFAULT 'Pending Evaluation',
                    feedback TEXT DEFAULT 'No feedback yet',
                    submitted_on TEXT
                )
            '''))
        else:
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS portfolio (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_username TEXT,
                    portfolio_section TEXT DEFAULT 'General',
                    category TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    learning_reflection TEXT DEFAULT '',
                    project_link TEXT,
                    rubric_regularity INTEGER DEFAULT 0,
                    rubric_authenticity INTEGER DEFAULT 0,
                    rubric_reflection INTEGER DEFAULT 0,
                    rubric_creativity INTEGER DEFAULT 0,
                    total_marks INTEGER DEFAULT 0,
                    grade TEXT DEFAULT 'Pending Evaluation',
                    feedback TEXT DEFAULT 'No feedback yet',
                    submitted_on TEXT
                )
            '''))

        # Ensure Admin Account Exists
        res = conn.execute(text("SELECT username FROM students WHERE username = 'admin'")).fetchone()
        if not res:
            conn.execute(text("""
                INSERT INTO students (roll_no, username, password, student_name, role, class_name)
                VALUES ('ADMIN01', 'admin', 'admin123', 'Class Teacher (12-B)', 'Teacher', '12-B')
            """))

# --- Deep File Locator for Excel ---
def find_excel_file():
    for root, dirs, files in os.walk("."):
        for f in files:
            if f.lower() in ["studentport.xlsx", "studentport.xls"]:
                return os.path.join(root, f)
    return None

# --- Excel Sync Logic ---
def sync_excel_data():
    target_file = find_excel_file()
    if not target_file:
        return 0, "Error: 'studentport.xlsx' file repository me nahi mili."

    try:
        df_excel = pd.read_excel(target_file, dtype=str)
        with engine.begin() as conn:
            # Preserve existing photos & goals
            res_p = conn.execute(text("SELECT username, photo_b64, academic_goals, strengths_weaknesses FROM students WHERE role='Student'")).fetchall()
            existing_meta = {row[0]: (row[1], row[2], row[3]) for row in res_p}
            
            # Refresh student list
            conn.execute(text("DELETE FROM students WHERE role='Student'"))
            
            success_count = 0
            for _, row in df_excel.iterrows():
                s_name = clean_val(row.get("STUDENT'S NAME", ""))
                sr_no = clean_val(row.get("S.R. NO.", ""))
                r_no = clean_val(row.get("ROLL NO.", ""))
                
                if not s_name or s_name.lower() in ["nan", "nat", "null"] or r_no == "0":
                    continue
                
                login_username = " ".join(s_name.split())
                login_password = sr_no if sr_no else "123456"
                
                saved_photo, saved_goals, saved_sw = existing_meta.get(login_username, ("", "", ""))
                
                dob_val = clean_val(row.get("D.O.B.", ""))
                if "00:00:00" in dob_val:
                    dob_val = dob_val.replace("00:00:00", "").strip()
                
                conn.execute(text("""
                    INSERT INTO students (
                        roll_no, username, password, class_name, sr_no, roll_no_10th, 
                        pen_no, aadhar_no, dob, dob_dd, dob_mm, dob_yyyy, 
                        occupation, ecode, dept, student_name, student_name_hindi, 
                        father_name, father_name_hindi, mother_name, mother_name_hindi, 
                        gender, caste, category, religion, address, mob_no, email_id, 
                        academic_goals, strengths_weaknesses, photo_b64, role
                    ) VALUES (
                        :r_no, :u_name, :p_word, '12-B', :sr_no, :r_10, 
                        :pen, :aadhar, :dob, :dd, :mm, :yyyy, 
                        :occ, :ecode, :dept, :s_name, :s_name_h, 
                        :f_name, :f_name_h, :m_name, :m_name_h, 
                        :gen, :caste, :cat, :rel, :addr, :mob, :email, 
                        :goals, :sw, :photo, 'Student'
                    )
                """), {
                    "r_no": r_no, "u_name": login_username, "p_word": login_password,
                    "sr_no": sr_no,
                    "r_10": clean_val(row.get("roll numer 10th", "")),
                    "pen": clean_val(row.get("PEN NUMBER", "")),
                    "aadhar": clean_val(row.get("AADHAR NO.", "")),
                    "dob": dob_val,
                    "dd": clean_val(row.get("DD", "")),
                    "mm": clean_val(row.get("MM", "")),
                    "yyyy": clean_val(row.get("YYYY", "")),
                    "occ": clean_val(row.get("OCCUPATION Other-OTH / Hindalco -HE / Hindalco Supply- HS", "")),
                    "ecode": clean_val(row.get("E.CODE", "")),
                    "dept": clean_val(row.get("DEPT.", "")),
                    "s_name": login_username,
                    "s_name_h": clean_val(row.get("STUDENT NAME IN HINDI", "")),
                    "f_name": clean_val(row.get("FATHER'S NAME", "")),
                    "f_name_h": clean_val(row.get("FATHER'S NAME IN HINDI", "")),
                    "m_name": clean_val(row.get("MOTHER'S NAME", "")),
                    "m_name_h": clean_val(row.get("MOTHER'S NAME IN HINDI", "")),
                    "gen": clean_val(row.get("GENDER", "")),
                    "caste": clean_val(row.get("CASTE", "")),
                    "cat": clean_val(row.get("CAT.", "")),
                    "rel": clean_val(row.get("RELIGION", "")),
                    "addr": clean_val(row.get("ADDRESS", "")),
                    "mob": clean_val(row.get("MOB. NO.", "")),
                    "email": clean_val(row.get("EMAIL ID", "")),
                    "goals": saved_goals,
                    "sw": saved_sw,
                    "photo": saved_photo
                })
                success_count += 1
                
        return success_count, "Success"
    except Exception as e:
        return 0, f"Excel Reading Error: {str(e)}"

init_db()

# Auto self-healing check on startup
def ensure_database_populated():
    with engine.connect() as conn:
        res = conn.execute(text("SELECT COUNT(*) FROM students WHERE role='Student'")).fetchone()
        count = res[0] if res else 0
        if count == 0:
            sync_excel_data()

ensure_database_populated()

# --- Helper: Generate Full 2-Page HTML Document ---
def generate_portfolio_html(student_dict, portfolio_items_df):
    s_photo = student_dict.get("photo_b64", "")
    if safe_b64_decode(s_photo):
        photo_html = f'<img src="data:image/jpeg;base64,{s_photo}" style="width: 90px; height: 110px; object-fit: cover; border-radius: 6px; border: 2px solid #1E3A8A;"/>'
    else:
        photo_html = '<div style="font-size: 38px;">🎓</div><div style="font-size: 10px; color: #94A3B8; margin-top: 4px;">Photo Pending</div>'

    items_html = ""
    if portfolio_items_df.empty:
        items_html = "<p style='color:#64748B; font-style:italic;'>No portfolio artifacts submitted yet.</p>"
    else:
        for _, itm in portfolio_items_df.iterrows():
            refl_block = f"<div style='font-size: 12px; color: #0284C7; margin-top: 4px;'><strong>Reflection:</strong> {itm['learning_reflection']}</div>" if itm['learning_reflection'] else ""
            fb_block = f"<div style='font-size: 12px; color: #D97706; margin-top: 4px;'><strong>Teacher Feedback:</strong> {itm['feedback']}</div>" if itm['feedback'] != "No feedback yet" else ""
            items_html += f"""
            <div style="border-left: 4px solid #1E3A8A; padding: 10px 14px; margin-bottom: 12px; background: #F8FAFC; border-radius: 4px; border-top: 1px solid #E2E8F0; border-right: 1px solid #E2E8F0; border-bottom: 1px solid #E2E8F0;">
                <div style="font-weight: bold; color: #1E3A8A; font-size: 14px;">📌 [{itm['portfolio_section']}] {itm['title']} <span style="float: right; color: #059669;">Score: {itm['grade']}</span></div>
                <div style="font-size: 12px; color: #475569; margin-top: 4px;"><strong>Category:</strong> {itm['category']} | <strong>Date:</strong> {itm['submitted_on']}</div>
                <div style="font-size: 13px; color: #1E293B; margin-top: 4px;">{itm['description']}</div>
                {refl_block}
                {fb_block}
            </div>
            """

    hindi_name = f"({student_dict.get('student_name_hindi')})" if student_dict.get('student_name_hindi') else ""
    today_str = datetime.now().strftime('%d-%m-%Y')
    p_goals = student_dict.get("academic_goals") if student_dict.get("academic_goals") else "Not specified yet."
    p_sw = student_dict.get("strengths_weaknesses") if student_dict.get("strengths_weaknesses") else "Not specified yet."

    full_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Portfolio - {student_dict.get('student_name')}</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f1f5f9; padding: 20px; }}
        .page-container {{ max-width: 850px; margin: 0 auto; }}
        .card-page {{ border: 2px solid #1E3A8A; border-radius: 10px; padding: 25px; background: #FFFFFF; box-shadow: 0 4px 10px rgba(0,0,0,0.05); margin-bottom: 30px; page-break-after: always; }}
        @media print {{
            body {{ background: none; padding: 0; }}
            .card-page {{ box-shadow: none; margin-bottom: 0; page-break-after: always; }}
        }}
    </style>
</head>
<body>
<div class="page-container">
    <!-- PAGE 1 -->
    <div class="card-page">
        <div style="text-align: center; border-bottom: 2px solid #E2E8F0; padding-bottom: 10px; margin-bottom: 15px;">
            <h2 style="margin: 0; color: #1E3A8A; font-size: 20px; text-transform: uppercase;">UP BOARD STUDENT PORTFOLIO</h2>
            <h4 style="margin: 4px 0 0 0; color: #475569; font-weight: normal; font-size: 14px;">माध्यमिक शिक्षा परिषद्, उत्तर प्रदेश | सत्र: 2026 - 2027 | Class: 12-B</h4>
            <div style="display: inline-block; background: #1E3A8A; color: white; padding: 3px 12px; border-radius: 12px; font-size: 11px; margin-top: 6px; font-weight: bold;">OFFICIAL STUDENT DOSSIER</div>
        </div>
        <div style="display: flex; gap: 15px; margin-bottom: 15px;">
            <table style="width: 70%; border-collapse: collapse; font-size: 13px;">
                <tr style="background: #F1F5F9;"><td style="padding: 6px; font-weight: bold; width: 35%;">Student Name:</td><td style="padding: 6px; color: #1E3A8A; font-weight: bold;">{student_dict.get('student_name', '')} {hindi_name}</td></tr>
                <tr><td style="padding: 6px; font-weight: bold;">Roll No:</td><td style="padding: 6px;">{student_dict.get('roll_no', '')}</td></tr>
                <tr style="background: #F1F5F9;"><td style="padding: 6px; font-weight: bold;">S.R. No:</td><td style="padding: 6px;">{student_dict.get('sr_no', '')}</td></tr>
                <tr><td style="padding: 6px; font-weight: bold;">Father's Name:</td><td style="padding: 6px;">{student_dict.get('father_name', '')}</td></tr>
                <tr style="background: #F1F5F9;"><td style="padding: 6px; font-weight: bold;">Mother's Name:</td><td style="padding: 6px;">{student_dict.get('mother_name', '')}</td></tr>
                <tr><td style="padding: 6px; font-weight: bold;">Date of Birth:</td><td style="padding: 6px;">{student_dict.get('dob', '')}</td></tr>
                <tr style="background: #F1F5F9;"><td style="padding: 6px; font-weight: bold;">PEN / Aadhar:</td><td style="padding: 6px;">{student_dict.get('pen_no', '')} / {student_dict.get('aadhar_no', '')}</td></tr>
                <tr><td style="padding: 6px; font-weight: bold;">Contact / Email:</td><td style="padding: 6px;">{student_dict.get('mob_no', '')} | {student_dict.get('email_id', '')}</td></tr>
            </table>
            <div style="width: 30%; border: 2px dashed #94A3B8; border-radius: 8px; display: flex; flex-direction: column; align-items: center; justify-content: center; background: #F8FAFC; padding: 8px; text-align: center;">
                {photo_html}
                <div style="font-weight: bold; font-size: 13px; color: #1E3A8A; margin-top: 5px;">{student_dict.get('student_name', '')}</div>
                <div style="font-size: 12px; color: #64748B;">Class 12-B (UP Board)</div>
                <div style="font-size: 11px; color: #059669; margin-top: 4px; border: 1px solid #059669; padding: 2px 6px; border-radius: 10px;">Verified Student</div>
            </div>
        </div>
        <div style="margin-top: 10px;">
            <div style="color: #1E3A8A; font-weight: bold; font-size: 14px; margin-bottom: 6px;">🎯 Academic Vision & Target Goals:</div>
            <div style="background: #F8FAFC; border-left: 4px solid #3B82F6; padding: 8px 12px; border-radius: 4px; font-size: 13px; color: #334155;">{p_goals}</div>
        </div>
        <div style="margin-top: 10px;">
            <div style="color: #1E3A8A; font-weight: bold; font-size: 14px; margin-bottom: 6px;">💡 Strengths & Growth Areas:</div>
            <div style="background: #F8FAFC; border-left: 4px solid #10B981; padding: 8px 12px; border-radius: 4px; font-size: 13px; color: #334155;">{p_sw}</div>
        </div>
    </div>

    <!-- PAGE 2 -->
    <div class="card-page">
        <div style="text-align: center; border-bottom: 2px solid #E2E8F0; padding-bottom: 10px; margin-bottom: 15px;">
            <h3 style="margin: 0; color: #1E3A8A; font-size: 18px; text-transform: uppercase;">LEARNING ARTIFACTS & EVALUATION RECORD</h3>
            <div style="display: inline-block; background: #059669; color: white; padding: 3px 12px; border-radius: 12px; font-size: 11px; margin-top: 6px; font-weight: bold;">UP BOARD CONTINUOUS EVALUATION</div>
        </div>
        <div style="margin-bottom: 15px;">
            <div style="color: #1E3A8A; font-weight: bold; font-size: 14px; margin-bottom: 8px;">📚 Key Academic & Practical Artifacts:</div>
            {items_html}
        </div>
        <div style="border: 1px solid #CBD5E1; border-radius: 6px; padding: 12px; background: #F8FAFC; margin-top: 15px;">
            <div style="margin: 0 0 8px 0; color: #1E3A8A; font-weight: bold; font-size: 13px;">📝 UP Board Portfolio Rubric Criteria (Max Marks: 20)</div>
            <div style="display: flex; gap: 8px; font-size: 12px; text-align: center;">
                <div style="flex: 1; background: white; padding: 6px; border: 1px solid #CBD5E1; border-radius: 4px;"><strong>1. Regularity</strong><br>(5 M)</div>
                <div style="flex: 1; background: white; padding: 6px; border: 1px solid #CBD5E1; border-radius: 4px;"><strong>2. Authenticity</strong><br>(5 M)</div>
                <div style="flex: 1; background: white; padding: 6px; border: 1px solid #CBD5E1; border-radius: 4px;"><strong>3. Reflection</strong><br>(5 M)</div>
                <div style="flex: 1; background: white; padding: 6px; border: 1px solid #CBD5E1; border-radius: 4px;"><strong>4. Creativity</strong><br>(5 M)</div>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: flex-end; margin-top: 25px; padding-top: 10px; border-top: 1px dashed #94A3B8; font-size: 12px;">
                <div>
                    <div><strong>Student Signature:</strong> _____________________</div>
                    <div style="color: #64748B; font-size: 11px; margin-top: 4px;">Date: {today_str}</div>
                </div>
                <div style="text-align: right;">
                    <div><strong>Teacher Signature:</strong> _____________________</div>
                    <div style="color: #64748B; font-size: 11px; margin-top: 4px;">Class Teacher (12-B)</div>
                </div>
            </div>
        </div>
    </div>
</div>
</body>
</html>
"""
    return full_html

# --- Session State Management ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

def login_user(entered_user, entered_pass):
    user_clean = " ".join(entered_user.strip().split())
    pass_clean = entered_pass.strip()
    pass_variants = [pass_clean, pass_clean + ".0", pass_clean.replace(".0", "")]
    
    with engine.connect() as conn:
        for p in set(pass_variants):
            query = text("""
                SELECT username FROM students 
                WHERE (LOWER(TRIM(username)) = LOWER(:u) OR LOWER(TRIM(student_name)) = LOWER(:u)) 
                AND (TRIM(password) = :p OR TRIM(sr_no) = :p)
            """)
            res = conn.execute(query, {"u": user_clean, "p": p}).fetchone()
            if res:
                return res[0]
    return None

def logout_user():
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.rerun()

# --- Login UI ---
if not st.session_state.logged_in or not st.session_state.username:
    st.title("🎓 Class 12-B UP Board Continuous Portfolio Portal")
    st.caption("माध्यमिक शिक्षा परिषद्, उत्तर प्रदेश - आंतरिक मूल्यांकन एवं पोर्टफोलियो प्रबंधन")
    
    col1, col2 = st.columns([1.2, 1])
    with col1:
        st.subheader("Login to Portfolio")
        user_input = st.text_input("Login ID (Student Name / Admin Username)")
        pass_input = st.text_input("Password (S.R. No. for Students)", type="password")
        
        if st.button("Login", type="primary", use_container_width=True):
            ensure_database_populated()
            valid_user = login_user(user_input, pass_input)
            if valid_user:
                st.session_state.logged_in = True
                st.session_state.username = valid_user
                st.rerun()
            else:
                st.error("Invalid Name or Password (S.R. No.)!")
                
    with col2:
        st.info("""
        **📌 Instructions for Students:**
        - **Login ID:** Apna School Record wala Name enter karein.
        - **Password:** Apna **S.R. Number** enter karein.
        """)

# --- Authenticated Interface ---
else:
    with engine.connect() as conn:
        user_df = pd.read_sql_query(text("SELECT * FROM students WHERE username=:u"), conn, params={"u": st.session_state.username})
    
    if user_df.empty:
        logout_user()

    user_dict = user_df.iloc[0].to_dict()
    role = user_dict.get("role", "Student")
    student_roll = user_dict.get("roll_no", "")
    student_username = user_dict.get("username", "")
    student_sr = user_dict.get("sr_no", "")
    student_name = user_dict.get("student_name", "")
    student_photo = user_dict.get("photo_b64", "")
    
    with st.sidebar:
        decoded_sidebar_photo = safe_b64_decode(student_photo)
        if decoded_sidebar_photo:
            st.image(decoded_sidebar_photo, width=100)
        st.write(f"### 👋 **{student_name}**")
        st.badge(f"Role: {role}")
        if role == "Student":
            st.write(f"**Roll No:** {student_roll}")
            st.write(f"**S.R. No:** {student_sr}")
        st.write("**Board:** UP BOARD")
        st.write("**Class & Section:** 12-B")
        st.divider()
        if st.button("Logout", use_container_width=True):
            logout_user()

    # ==========================================
    # 1. TEACHER / ADMIN DASHBOARD
    # ==========================================
    if role == "Teacher":
        st.title("👨‍🏫 Teacher Evaluation Panel - Class 12-B (UP Board)")
        
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📑 Assessment & Grading", 
            "🎴 View & Download Student Portfolios",
            "👥 Class Master Records & Photo Upload", 
            "🗑️ Manage & Delete Records",
            "🔄 Excel File Status & Sync"
        ])
        
        # TAB 1: Evaluation
        with tab1:
            st.subheader("Submitted Student Portfolios")
            try:
                with engine.connect() as conn:
                    query = text("""
                        SELECT p.id, s.roll_no, s.student_name, s.sr_no, p.portfolio_section, 
                               p.category, p.title, p.description, p.learning_reflection, 
                               p.project_link, p.total_marks, p.grade, p.feedback, p.submitted_on
                        FROM portfolio p
                        LEFT JOIN students s ON p.student_username = s.username
                        ORDER BY p.id DESC
                    """)
                    df_port = pd.read_sql_query(query, conn)
            except Exception:
                df_port = pd.DataFrame()
            
            if df_port.empty:
                st.info("Abhi tak kisi student ne submission nahi kiya hai.")
            else:
                st.dataframe(
                    df_port[["roll_no", "student_name", "portfolio_section", "category", "title", "total_marks", "grade", "submitted_on"]],
                    use_container_width=True
                )
                
                st.divider()
                st.subheader("🎯 Evaluate Artifact")
                selected_pid = st.selectbox("Select Submission to Grade", df_port["id"].tolist())
                sel_row = df_port[df_port["id"] == selected_pid].iloc[0]
                
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    st.markdown(f"**Student:** {sel_row['student_name']} (Roll: {sel_row['roll_no']})")
                    st.markdown(f"**Section:** `{sel_row['portfolio_section']}`")
                    st.markdown(f"**Category:** {sel_row['category']}")
                    st.markdown(f"**Title:** **{sel_row['title']}**")
                    st.markdown(f"**Description:** {sel_row['description']}")
                with col_d2:
                    st.markdown(f"**Student Reflection:**")
                    st.info(sel_row['learning_reflection'] if sel_row['learning_reflection'] else "No self-reflection entered.")
                    if sel_row['project_link']:
                        st.markdown(f"🔗 **Attachment Link:** [{sel_row['project_link']}]({sel_row['project_link']})")
                
                st.markdown("##### 📝 UP Board Internal Assessment Rubric (0-5 per Criteria)")
                c_r1, c_r2, c_r3, c_r4 = st.columns(4)
                with c_r1:
                    r_reg = st.slider("Regularity & Timeliness (0-5)", 0, 5, 4)
                with c_r2:
                    r_auth = st.slider("Quality & Authenticity (0-5)", 0, 5, 4)
                with c_r3:
                    r_refl = st.slider("Reflection & Learning (0-5)", 0, 5, 4)
                with c_r4:
                    r_creat = st.slider("Creativity & Presentation (0-5)", 0, 5, 4)
                
                total_calculated = r_reg + r_auth + r_refl + r_creat
                final_grade_str = f"{total_calculated}/20"
                new_feedback = st.text_input("Teacher's Feedback / Remarks", value=sel_row['feedback'])
                
                if st.button("Save Assessment", type="primary"):
                    with engine.begin() as conn:
                        conn.execute(text("""
                            UPDATE portfolio 
                            SET rubric_regularity=:r1, rubric_authenticity=:r2, rubric_reflection=:r3, 
                                rubric_creativity=:r4, total_marks=:tot, grade=:grd, feedback=:fb
                            WHERE id=:pid
                        """), {
                            "r1": r_reg, "r2": r_auth, "r3": r_refl, "r4": r_creat,
                            "tot": total_calculated, "grd": final_grade_str, "fb": new_feedback, "pid": selected_pid
                        })
                    st.success("Marks & Rubric Saved Successfully!")
                    st.rerun()

        # TAB 2: Admin View & Download Student Portfolios
        with tab2:
            st.subheader("🎴 View & Download Individual Student Portfolio Cards")
            with engine.connect() as conn:
                all_stus = pd.read_sql_query(text("SELECT username, student_name, roll_no FROM students WHERE role='Student' ORDER BY CAST(roll_no AS INTEGER) ASC"), conn)
            
            if all_stus.empty:
                st.warning("Koi students available nahi hain.")
            else:
                target_stu_user = st.selectbox(
                    "Choose Student to View Card", 
                    all_stus["username"].tolist(),
                    format_func=lambda x: f"Roll {all_stus[all_stus['username']==x]['roll_no'].values[0]} - {all_stus[all_stus['username']==x]['student_name'].values[0]}"
                )
                
                with engine.connect() as conn:
                    target_stu_data = pd.read_sql_query(text("SELECT * FROM students WHERE username=:u"), conn, params={"u": target_stu_user}).iloc[0].to_dict()
                    target_stu_items = pd.read_sql_query(text("SELECT * FROM portfolio WHERE student_username=:u ORDER BY id DESC"), conn, params={"u": target_stu_user})
                
                generated_html = generate_portfolio_html(target_stu_data, target_stu_items)
                
                col_btn1, col_btn2 = st.columns([1, 2])
                with col_btn1:
                    st.download_button(
                        label=f"📥 Download {target_stu_data.get('student_name')}'s Portfolio Card (.html)",
                        data=generated_html,
                        file_name=f"Portfolio_{target_stu_data.get('roll_no')}_{target_stu_data.get('student_name')}.html",
                        mime="text/html",
                        type="primary"
                    )
                with col_btn2:
                    st.caption("Aap is file ko download karke offline kisi bhi browser mein open karke print/PDF bana sakte hain.")

                st.divider()
                st.components.v1.html(generated_html, height=1100, scrolling=True)

        # TAB 3: Master Records & Photo Upload
        with tab3:
            st.subheader("Class 12-B Master Records & Photo Management")
            with st.expander("📸 Upload / Update Student Photo (Teacher Panel)"):
                with engine.connect() as conn:
                    students_list = pd.read_sql_query(text("SELECT username, student_name, roll_no FROM students WHERE role='Student' ORDER BY CAST(roll_no AS INTEGER) ASC"), conn)
                
                if not students_list.empty:
                    chosen_student = st.selectbox(
                        "Select Student to Upload Photo", 
                        students_list["username"].tolist(),
                        format_func=lambda x: f"{students_list[students_list['username']==x]['roll_no'].values[0]} - {students_list[students_list['username']==x]['student_name'].values[0]}"
                    )
                    t_uploaded_img = st.file_uploader("Choose Student Passport Photo (JPG/PNG)", type=["jpg", "jpeg", "png"], key="teacher_photo_upload")
                    if t_uploaded_img is not None:
                        t_b64 = base64.b64encode(t_uploaded_img.read()).decode("utf-8")
                        if st.button("Save Photo for Selected Student", type="primary"):
                            with engine.begin() as conn:
                                conn.execute(text("UPDATE students SET photo_b64=:p WHERE username=:u"), {"p": t_b64, "u": chosen_student})
                            st.success(f"Photo uploaded for {chosen_student}!")
                            st.rerun()

            try:
                with engine.connect() as conn:
                    students_df = pd.read_sql_query(text("""
                        SELECT roll_no, sr_no, student_name, student_name_hindi, father_name, 
                               dob, aadhar_no, pen_no, mob_no, email_id, 
                               CASE WHEN photo_b64 != '' THEN 'Uploaded ✅' ELSE 'Pending ❌' END AS photo_status
                        FROM students WHERE role='Student' ORDER BY CAST(roll_no AS INTEGER) ASC
                    """), conn)
            except Exception:
                students_df = pd.DataFrame()

            st.write(f"Total Active Students in DB: **{len(students_df)}**")
            st.dataframe(students_df, use_container_width=True)
            if not students_df.empty:
                st.download_button("📥 Export Clean Data (CSV)", students_df.to_csv(index=False).encode('utf-8'), "Class12B_Master.csv", "text/csv")

        # TAB 4: Delete Data Management (Admin)
        with tab4:
            st.subheader("🗑️ Delete & Manage Records (Admin Controls)")
            st.warning("⚠️ Dhyan dein: Yahan se data delete karne par permanently remove ho jayega.")
            
            c_del1, c_del2 = st.columns(2)
            with c_del1:
                st.markdown("#### 1. Delete Specific Submission Entry")
                with engine.connect() as conn:
                    del_items = pd.read_sql_query(text("SELECT id, student_username, title, portfolio_section FROM portfolio ORDER BY id DESC"), conn)
                
                if not del_items.empty:
                    sel_sub_del = st.selectbox(
                        "Select Submission to Delete", 
                        del_items["id"].tolist(),
                        format_func=lambda x: f"ID {x}: {del_items[del_items['id']==x]['student_username'].values[0]} - {del_items[del_items['id']==x]['title'].values[0]}"
                    )
                    if st.button("Delete Selected Submission", type="secondary"):
                        with engine.begin() as conn:
                            conn.execute(text("DELETE FROM portfolio WHERE id=:pid"), {"pid": sel_sub_del})
                        st.success("Submission successfully delete ho gaya!")
                        st.rerun()
                else:
                    st.info("No submissions to delete.")

            with c_del2:
                st.markdown("#### 2. Delete Student Record")
                with engine.connect() as conn:
                    all_stu_del = pd.read_sql_query(text("SELECT username, student_name, roll_no FROM students WHERE role='Student' ORDER BY CAST(roll_no AS INTEGER) ASC"), conn)
                
                if not all_stu_del.empty:
                    sel_user_del = st.selectbox(
                        "Select Student to Remove", 
                        all_stu_del["username"].tolist(),
                        format_func=lambda x: f"Roll {all_stu_del[all_stu_del['username']==x]['roll_no'].values[0]} - {all_stu_del[all_stu_del['username']==x]['student_name'].values[0]}",
                        key="del_stu_box"
                    )
                    if st.button("Delete Student & All Submissions", type="secondary"):
                        with engine.begin() as conn:
                            conn.execute(text("DELETE FROM students WHERE username=:u"), {"u": sel_user_del})
                            conn.execute(text("DELETE FROM portfolio WHERE student_username=:u"), {"u": sel_user_del})
                        st.success(f"{sel_user_del} aur unke sabhi submissions permanently delete ho gaye!")
                        st.rerun()
                else:
                    st.info("No students to delete.")

        # TAB 5: Excel Status & Sync
        with tab5:
            st.subheader("Excel File Status & Force Sync")
            excel_path = find_excel_file()
            if excel_path:
                st.success(f"✅ Excel file detected successfully at: `{excel_path}`")
            else:
                st.error("❌ 'studentport.xlsx' file detect nahi ho rahi hai.")
                
            if st.button("🔄 Force Re-Sync Data from Excel", type="primary"):
                count, msg = sync_excel_data()
                if count > 0:
                    st.success(f"🎉 {count} students ka data database me successfully refresh ho gaya!")
                    st.rerun()
                else:
                    st.error(msg)

    # ==========================================
    # 2. STUDENT DASHBOARD
    # ==========================================
    else:
        st.title(f"🎓 Student Portfolio - {student_name}")
        st.caption(f"UP BOARD | S.R. No: {student_sr} | Roll No: {student_roll} | Class: 12-B")
        
        tab_s1, tab_s2, tab_s3, tab_s4, tab_s5, tab_s6 = st.tabs([
            "🎴 2-Page Portfolio Card",
            "🖼️ Upload / Change Photo",
            "📂 My Submissions Record", 
            "➕ Submit New Artifact / Work", 
            "🎯 Profile & Goal Setting",
            "👤 Official Details"
        ])
        
        # --- TAB 1: 2-PAGE PORTFOLIO CARD ---
        with tab_s1:
            st.subheader("🎴 UP Board Official Student Portfolio Card (2-Page)")
            st.caption("माध्यमिक शिक्षा परिषद्, उत्तर प्रदेश - सत्र: 2026-27")
            
            try:
                with engine.connect() as conn:
                    card_items = pd.read_sql_query(
                        text("SELECT * FROM portfolio WHERE student_username=:u ORDER BY id DESC"),
                        conn, params={"u": student_username}
                    )
            except Exception:
                card_items = pd.DataFrame()
            
            student_full_html = generate_portfolio_html(user_dict, card_items)
            
            col_d1, col_d2 = st.columns([1, 2])
            with col_d1:
                st.download_button(
                    label="📥 Download My Portfolio Card (.html)",
                    data=student_full_html,
                    file_name=f"Portfolio_{student_roll}_{student_name}.html",
                    mime="text/html",
                    type="primary"
                )
            with col_d2:
                st.caption("Aap is file ko direct download karke kisi bhi phone ya computer me offline dekh aur print kar sakte hain.")

            st.divider()
            st.components.v1.html(student_full_html, height=1100, scrolling=True)

        # --- TAB 2: UPLOAD PHOTO ---
        with tab_s2:
            st.subheader("🖼️ Upload Passport Size Photo")
            st.caption("Aapki photo portfolio card ke Page 1 par display hogi.")
            
            c_ph1, c_ph2 = st.columns([1, 2])
            with c_ph1:
                decoded_img = safe_b64_decode(student_photo)
                if decoded_img:
                    st.image(decoded_img, caption="Current Photo", width=140)
                else:
                    st.info("No photo uploaded yet.")
                    
            with c_ph2:
                uploaded_img = st.file_uploader("Choose Photo (JPG, JPEG, PNG)", type=["jpg", "jpeg", "png"])
                if uploaded_img is not None:
                    img_bytes = uploaded_img.read()
                    encoded_str = base64.b64encode(img_bytes).decode("utf-8")
                    if st.button("Save & Upload Photo", type="primary"):
                        with engine.begin() as conn:
                            conn.execute(text("UPDATE students SET photo_b64=:p WHERE username=:u"), {"p": encoded_str, "u": student_username})
                        st.success("Photo successfully upload ho gayi!")
                        st.rerun()

        # --- TAB 3: SUBMISSIONS RECORD ---
        with tab_s3:
            st.subheader("My Portfolio Records")
            try:
                with engine.connect() as conn:
                    my_port = pd.read_sql_query(
                        text("SELECT * FROM portfolio WHERE student_username=:u ORDER BY id DESC"),
                        conn, params={"u": student_username}
                    )
            except Exception:
                my_port = pd.DataFrame()
            
            if my_port.empty:
                st.info("Aapka portfolio abhi khali hai. Naya kaam submit karne ke liye 'Submit New Artifact' tab par jayein.")
            else:
                for _, row in my_port.iterrows():
                    with st.expander(f"📌 [{row['portfolio_section']}] {row['title']} - Score: {row['grade']}"):
                        c_sub1, c_sub2 = st.columns(2)
                        with c_sub1:
                            st.write(f"**Category:** {row['category']}")
                            st.write(f"**Submitted On:** {row['submitted_on']}")
                            st.write(f"**Description:** {row['description']}")
                            if row['project_link']:
                                st.write(f"🔗 **Link:** [{row['project_link']}]({row['project_link']})")
                        with c_sub2:
                            st.write(f"**My Self-Reflection:** {row['learning_reflection']}")
                            st.divider()
                            st.write(f"👨‍🏫 **Teacher Feedback:** {row['feedback']}")
                            if row.get('total_marks', 0) > 0:
                                st.write(f"**Rubric Breakdown:** Regularity: {row['rubric_regularity']}/5 | Authenticity: {row['rubric_authenticity']}/5 | Reflection: {row['rubric_reflection']}/5 | Creativity: {row['rubric_creativity']}/5")

        # --- TAB 4: SUBMIT ARTIFACT ---
        with tab_s4:
            st.subheader("Add Work to Portfolio")
            with st.form("upboard_submission_form"):
                section = st.selectbox("1. Select Portfolio Pillar*", [
                    "2. Academic Artifacts (Best CW/HW, Unit Tests, Error Analysis)",
                    "3. Projects & Practical Work (Lab Experiments, Working Models, Surveys)",
                    "4. Creative & Co-Curricular (Art Integration, Creative Writing, Certificates)",
                    "5. Self & Peer Assessment (Reflections & Group Feedback)"
                ])
                
                if "Academic" in section:
                    cat_options = ["Best Classwork / Notes Sample", "Unit Test Paper with Correction", "Error Analysis & Learning Sheet", "Assignment / Worksheet"]
                elif "Projects" in section:
                    cat_options = ["Physics / Science Lab Practical Record", "Working Model / STEM Design", "Computer Science / Coding Project", "Survey / Case Study Report"]
                elif "Creative" in section:
                    cat_options = ["Art Integration (Poster / Mind Map / Chart)", "Self-Written Essay / Poem / Article", "Competition Certificate / Award", "Exhibition Display"]
                else:
                    cat_options = ["Term Self-Assessment Reflection", "Peer Review / Group Activity Feedback"]
                    
                sub_category = st.selectbox("2. Artifact Category*", cat_options)
                title = st.text_input("3. Title of Work / Topic*")
                description = st.text_area("4. Summary of the Activity")
                reflection = st.text_area("5. Student Reflection (Maine isse kya seekha? / What I learned & challenges faced)")
                link = st.text_input("6. Google Drive / Photo / GitHub Link")
                
                if st.form_submit_button("Submit to Portfolio", type="primary"):
                    if title:
                        now_str = datetime.now().strftime("%d-%b-%Y %I:%M %p")
                        with engine.begin() as conn:
                            conn.execute(text("""
                                INSERT INTO portfolio (
                                    student_username, portfolio_section, category, title, 
                                    description, learning_reflection, project_link, submitted_on
                                ) VALUES (:u, :sec, :cat, :tit, :desc, :refl, :lnk, :sub_on)
                            """), {
                                "u": student_username, "sec": section.split('.')[1].strip(),
                                "cat": sub_category, "tit": title, "desc": description,
                                "refl": reflection, "lnk": link, "sub_on": now_str
                            })
                        st.success("Artifact successfully submitted!")
                        st.rerun()
                    else:
                        st.error("Title is required!")

        # --- TAB 5: PROFILE GOALS ---
        with tab_s5:
            st.subheader("🎯 Academic Goals & Self Profile")
            curr_goals = user_dict.get("academic_goals", "")
            curr_sw = user_dict.get("strengths_weaknesses", "")
            
            with st.form("goals_form"):
                goals = st.text_area("My Goals for Session 2026-27:", value=curr_goals if curr_goals else "")
                sw = st.text_area("My Strengths & Areas to Improve:", value=curr_sw if curr_sw else "")
                
                if st.form_submit_button("Save Goals"):
                    with engine.begin() as conn:
                        conn.execute(text("UPDATE students SET academic_goals=:g, strengths_weaknesses=:sw WHERE username=:u"), {
                            "g": goals, "sw": sw, "u": student_username
                        })
                    st.success("Goals updated!")
                    st.rerun()

        # --- TAB 6: OFFICIAL DETAILS ---
        with tab_s6:
            st.subheader("Official Details (School Record)")
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"**Roll No:** {user_dict.get('roll_no', '')}")
                st.write(f"**S.R. No:** {user_dict.get('sr_no', '')}")
                st.write(f"**Name (English):** {user_dict.get('student_name', '')}")
                st.write(f"**Name (Hindi):** {user_dict.get('student_name_hindi', '')}")
                st.write(f"**Father's Name:** {user_dict.get('father_name', '')}")
                st.write(f"**Mother's Name:** {user_dict.get('mother_name', '')}")
                st.write(f"**D.O.B:** {user_dict.get('dob', '')}")
            with c2:
                st.write(f"**Aadhar No:** {user_dict.get('aadhar_no', '')}")
                st.write(f"**PEN No:** {user_dict.get('pen_no', '')}")
                st.write(f"**Mobile:** {user_dict.get('mob_no', '')}")
                st.write(f"**Email:** {user_dict.get('email_id', '')}")
                st.write(f"**Address:** {user_dict.get('address', '')}")
