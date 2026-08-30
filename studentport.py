import streamlit as st
import sqlite3
import pandas as pd
import os
import re
import base64
from datetime import datetime

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

# --- Database Connection & Setup ---
def get_db_connection():
    return sqlite3.connect("class12b_portfolio.db", check_same_thread=False)

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Students Master Table with unique S.R. No as Primary ID
    c.execute('''
        CREATE TABLE IF NOT EXISTS students (
            sr_no TEXT PRIMARY KEY,
            roll_no TEXT,
            username TEXT,
            password TEXT NOT NULL,
            class_name TEXT DEFAULT '12-B',
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
    ''')
    
    # Portfolio Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_sr_no TEXT,
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
    ''')
    
    # Auto-clean legacy decimals
    try:
        c.execute("UPDATE students SET password = REPLACE(password, '.0', '') WHERE password LIKE '%.0'")
        c.execute("UPDATE students SET sr_no = REPLACE(sr_no, '.0', '') WHERE sr_no LIKE '%.0'")
        c.execute("UPDATE students SET roll_no = REPLACE(roll_no, '.0', '') WHERE roll_no LIKE '%.0'")
    except Exception:
        pass

    # Ensure Admin Exists
    c.execute("SELECT * FROM students WHERE username = 'admin' OR sr_no = 'ADMIN01'")
    if not c.fetchone():
        c.execute("""
            INSERT OR REPLACE INTO students (sr_no, roll_no, username, password, student_name, role, class_name)
            VALUES ('ADMIN01', 'ADMIN', 'admin', 'admin123', 'Class Teacher (12-B)', 'Teacher', '12-B')
        """)
        
    conn.commit()
    conn.close()

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
        conn = get_db_connection()
        c = conn.cursor()
        
        # Preserve existing photos & goals mapped by S.R. No
        c.execute("SELECT sr_no, photo_b64, academic_goals, strengths_weaknesses FROM students WHERE role='Student'")
        existing_meta = {row[0]: (row[1], row[2], row[3]) for row in c.fetchall()}
        
        c.execute("DELETE FROM students WHERE role='Student'")
        
        success_count = 0
        for _, row in df_excel.iterrows():
            s_name = clean_val(row.get("STUDENT'S NAME", ""))
            sr_no = clean_val(row.get("S.R. NO.", ""))
            r_no = clean_val(row.get("ROLL NO.", ""))
            
            if not s_name or not sr_no or s_name.lower() in ["nan", "nat", "null"] or r_no == "0":
                continue
            
            login_username = " ".join(s_name.split())
            login_password = sr_no
            saved_photo, saved_goals, saved_sw = existing_meta.get(sr_no, ("", "", ""))
            
            dob_val = clean_val(row.get("D.O.B.", ""))
            if "00:00:00" in dob_val:
                dob_val = dob_val.replace("00:00:00", "").strip()
            
            c.execute("""
                INSERT OR REPLACE INTO students (
                    sr_no, roll_no, username, password, class_name, roll_no_10th, 
                    pen_no, aadhar_no, dob, dob_dd, dob_mm, dob_yyyy, 
                    occupation, ecode, dept, student_name, student_name_hindi, 
                    father_name, father_name_hindi, mother_name, mother_name_hindi, 
                    gender, caste, category, religion, address, mob_no, email_id, 
                    academic_goals, strengths_weaknesses, photo_b64, role
                ) VALUES (?, ?, ?, ?, '12-B', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Student')
            """, (
                sr_no, r_no, login_username, login_password,
                clean_val(row.get("roll numer 10th", "")),
                clean_val(row.get("PEN NUMBER", "")),
                clean_val(row.get("AADHAR NO.", "")),
                dob_val,
                clean_val(row.get("DD", "")),
                clean_val(row.get("MM", "")),
                clean_val(row.get("YYYY", "")),
                clean_val(row.get("OCCUPATION Other-OTH / Hindalco -HE / Hindalco Supply- HS", "")),
                clean_val(row.get("E.CODE", "")),
                clean_val(row.get("DEPT.", "")),
                login_username,
                clean_val(row.get("STUDENT NAME IN HINDI", "")),
                clean_val(row.get("FATHER'S NAME", "")),
                clean_val(row.get("FATHER'S NAME IN HINDI", "")),
                clean_val(row.get("MOTHER'S NAME", "")),
                clean_val(row.get("MOTHER'S NAME IN HINDI", "")),
                clean_val(row.get("GENDER", "")),
                clean_val(row.get("CASTE", "")),
                clean_val(row.get("CAT.", "")),
                clean_val(row.get("RELIGION", "")),
                clean_val(row.get("ADDRESS", "")),
                clean_val(row.get("MOB. NO.", "")),
                clean_val(row.get("EMAIL ID", "")),
                saved_goals, saved_sw, saved_photo
            ))
            success_count += 1
            
        conn.commit()
        conn.close()
        return success_count, "Success"
    except Exception as e:
        return 0, f"Excel Reading Error: {str(e)}"

init_db()

# Auto self-healing check on startup
def ensure_database_populated():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM students WHERE role='Student'")
    count = c.fetchone()[0]
    conn.close()
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
if "current_user_sr" not in st.session_state:
    st.session_state.current_user_sr = ""

def login_user(entered_user, entered_pass):
    user_clean = " ".join(entered_user.strip().split())
    pass_clean = entered_pass.strip()
    pass_variants = [pass_clean, pass_clean + ".0", pass_clean.replace(".0", "")]
    
    conn = get_db_connection()
    c = conn.cursor()
    for p in set(pass_variants):
        c.execute("""
            SELECT sr_no FROM students 
            WHERE (LOWER(TRIM(username)) = LOWER(?) OR LOWER(TRIM(student_name)) = LOWER(?) OR TRIM(sr_no) = ?) 
            AND (TRIM(password) = ? OR TRIM(sr_no) = ?)
        """, (user_clean, user_clean, user_clean, p, p))
        res = c.fetchone()
        if res:
            conn.close()
            return res[0]
    conn.close()
    return None

def logout_user():
    st.session_state.logged_in = False
    st.session_state.current_user_sr = ""
    st.rerun()

# --- Login UI ---
if not st.session_state.logged_in or not st.session_state.current_user_sr:
    st.title("🎓 Class 12-B UP Board Continuous Portfolio Portal")
    st.caption("माध्यमिक शिक्षा परिषद्, उत्तर प्रदेश - आंतरिक मूल्यांकन एवं पोर्टफोलियो प्रबंधन")
    
    col1, col2 = st.columns([1.2, 1])
    with col1:
        st.subheader("Login to Portfolio")
        user_input = st.text_input("Login ID (Student Name / S.R. No / Admin Username)")
        pass_input = st.text_input("Password (S.R. No. for Students)", type="password")
        
        if st.button("Login", type="primary", use_container_width=True):
            ensure_database_populated()
            valid_sr = login_user(user_input, pass_input)
            if valid_sr:
                st.session_state.logged_in = True
                st.session_state.current_user_sr = valid_sr
                st.rerun()
            else:
                st.error("Invalid Name or Password (S.R. No.)!")
                
    with col2:
        st.info("""
        **📌 Instructions for Students:**
        - **Login ID:** Apna School Record wala Name ya S.R. No enter karein.
        - **Password:** Apna **S.R. Number** enter karein.
        """)

# --- Authenticated App ---
else:
    conn = get_db_connection()
    user_df = pd.read_sql_query("SELECT * FROM students WHERE sr_no=?", conn, params=(st.session_state.current_user_sr,))
    
    if user_df.empty:
        conn.close()
        logout_user()

    user_dict = user_df.iloc[0].to_dict()
    role = user_dict.get("role", "Student")
    student_roll = user_dict.get("roll_no", "")
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
            conn.close()
            logout_user()

    # ==========================================
    # 1. TEACHER / ADMIN DASHBOARD
    # ==========================================
    if role == "Teacher":
        st.title("👨‍🏫 Teacher Evaluation Panel - Class 12-B (UP Board)")
