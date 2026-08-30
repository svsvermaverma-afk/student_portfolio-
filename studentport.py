import streamlit as st
import sqlite3
import pandas as pd
import os
import re
from datetime import datetime

# --- Page Config ---
st.set_page_config(page_title="Class 12-B CBSE Portfolio Portal", page_icon="🎓", layout="wide")

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

# --- Database Connection ---
def get_db_connection():
    return sqlite3.connect("class12b_portfolio.db", check_same_thread=False)

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Students Master Table
    c.execute('''
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
            role TEXT DEFAULT 'Student'
        )
    ''')
    
    # Portfolio Table
    c.execute('''
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
    ''')
    
    # Safe Auto-Migration
    c.execute("PRAGMA table_info(students)")
    student_cols = [row[1] for row in c.fetchall()]
    if "academic_goals" not in student_cols:
        c.execute("ALTER TABLE students ADD COLUMN academic_goals TEXT DEFAULT ''")
    if "strengths_weaknesses" not in student_cols:
        c.execute("ALTER TABLE students ADD COLUMN strengths_weaknesses TEXT DEFAULT ''")

    # Clean existing decimal traces in db
    try:
        c.execute("UPDATE students SET password = REPLACE(password, '.0', '') WHERE password LIKE '%.0'")
        c.execute("UPDATE students SET sr_no = REPLACE(sr_no, '.0', '') WHERE sr_no LIKE '%.0'")
        c.execute("UPDATE students SET roll_no = REPLACE(roll_no, '.0', '') WHERE roll_no LIKE '%.0'")
    except Exception:
        pass

    # Ensure Admin Exists
    c.execute("SELECT * FROM students WHERE username = 'admin'")
    if not c.fetchone():
        c.execute("""
            INSERT OR REPLACE INTO students (roll_no, username, password, student_name, role, class_name)
            VALUES ('ADMIN01', 'admin', 'admin123', 'Class Teacher (12-B)', 'Teacher', '12-B')
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
        
        c.execute("DELETE FROM students WHERE role='Student'")
        
        success_count = 0
        for _, row in df_excel.iterrows():
            s_name = clean_val(row.get("STUDENT'S NAME", ""))
            sr_no = clean_val(row.get("S.R. NO.", ""))
            r_no = clean_val(row.get("ROLL NO.", ""))
            
            if not s_name or s_name.lower() in ["nan", "nat", "null"] or r_no == "0":
                continue
            
            login_username = " ".join(s_name.split())
            login_password = sr_no if sr_no else "123456"
            
            dob_val = clean_val(row.get("D.O.B.", ""))
            if "00:00:00" in dob_val:
                dob_val = dob_val.replace("00:00:00", "").strip()
            
            c.execute("""
                INSERT OR REPLACE INTO students (
                    roll_no, username, password, class_name, sr_no, roll_no_10th, 
                    pen_no, aadhar_no, dob, dob_dd, dob_mm, dob_yyyy, 
                    occupation, ecode, dept, student_name, student_name_hindi, 
                    father_name, father_name_hindi, mother_name, mother_name_hindi, 
                    gender, caste, category, religion, address, mob_no, email_id, role
                ) VALUES (?, ?, ?, '12-B', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Student')
            """, (
                r_no, login_username, login_password,
                sr_no,
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
                clean_val(row.get("EMAIL ID", ""))
            ))
            success_count += 1
            
        conn.commit()
        conn.close()
        return success_count, "Success"
    except Exception as e:
        return 0, f"Excel Reading Error: {str(e)}"

init_db()

# Auto self-healing check
def ensure_database_populated():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM students WHERE role='Student'")
    count = c.fetchone()[0]
    conn.close()
    if count == 0:
        sync_excel_data()

ensure_database_populated()

# --- Authentication Logic ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_data = None

def login_user(entered_user, entered_pass):
    user_clean = " ".join(entered_user.strip().split())
    pass_clean = entered_pass.strip()
    pass_variants = [pass_clean, pass_clean + ".0", pass_clean.replace(".0", "")]
    
    conn = get_db_connection()
    c = conn.cursor()
    for p in set(pass_variants):
        c.execute("""
            SELECT * FROM students 
            WHERE (LOWER(TRIM(username)) = LOWER(?) OR LOWER(TRIM(student_name)) = LOWER(?)) 
            AND (TRIM(password) = ? OR TRIM(sr_no) = ?)
        """, (user_clean, user_clean, p, p))
        user = c.fetchone()
        if user:
            conn.close()
            return user
    conn.close()
    return None

def logout_user():
    st.session_state.logged_in = False
    st.session_state.user_data = None
    st.rerun()

# --- Login UI ---
if not st.session_state.logged_in:
    st.title("🎓 Class 12-B Continuous & Comprehensive Portfolio Portal")
    st.caption("Internal Assessment & Student Portfolio Management")
    
    col1, col2 = st.columns([1.2, 1])
    with col1:
        st.subheader("Login to Portfolio")
        user_input = st.text_input("Login ID (Student Name / Admin Username)")
        pass_input = st.text_input("Password (S.R. No. for Students)", type="password")
        
        if st.button("Login", type="primary", use_container_width=True):
            ensure_database_populated()
            user = login_user(user_input, pass_input)
            if user:
                st.session_state.logged_in = True
                st.session_state.user_data = user
                st.success(f"Welcome {user[15]}!")
                st.rerun()
            else:
                st.error("Invalid Name or Password (S.R. No.)!")
                
    with col2:
        st.info("""
        **📌 Instructions for Students:**
        - **Login ID:** Enter your full name as registered in school.
        - **Password:** Enter your **S.R. Number**.
        """)

# --- Authenticated App ---
else:
    user_row = st.session_state.user_data
    role = user_row[30] if len(user_row) > 30 else user_row[-1]
    student_roll = user_row[0]
    student_username = user_row[1]
    student_sr = user_row[4]
    student_name = user_row[15]
    
    with st.sidebar:
        st.write(f"### 👋 **{student_name}**")
        st.badge(f"Role: {role}")
        if role == "Student":
            st.write(f"**Roll No:** {student_roll}")
            st.write(f"**S.R. No:** {student_sr}")
        st.write("**Class & Section:** 12-B")
        st.divider()
        if st.button("Logout", use_container_width=True):
            logout_user()

    conn = get_db_connection()

    # ==========================================
    # 1. TEACHER DASHBOARD
    # ==========================================
    if role == "Teacher":
        st.title("👨‍🏫 Teacher Evaluation Panel - Class 12-B")
        
        tab1, tab2, tab3 = st.tabs([
            "📑 Portfolio Assessment & Grading", 
            "👥 Class Master Records", 
            "🔄 Excel File Status & Sync"
        ])
        
        with tab1:
            st.subheader("Submitted Student Portfolios")
            try:
                query = """
                    SELECT p.id, s.roll_no, s.student_name, s.sr_no, p.portfolio_section, 
                           p.category, p.title, p.description, p.learning_reflection, 
                           p.project_link, p.total_marks, p.grade, p.feedback, p.submitted_on
                    FROM portfolio p
                    LEFT JOIN students s ON p.student_username = s.username
                    ORDER BY p.id DESC
                """
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
                
                st.markdown("##### 📝 CBSE Scoring Rubric (0-5 per Criteria)")
                c_r1, c_r2, c_r3, c_r4 = st.columns(4)
                with c_r1:
                    r_reg = st.slider("Regularity (0-5)", 0, 5, 4)
                with c_r2:
                    r_auth = st.slider("Authenticity (0-5)", 0, 5, 4)
                with c_r3:
                    r_refl = st.slider("Reflection (0-5)", 0, 5, 4)
                with c_r4:
                    r_creat = st.slider("Creativity (0-5)", 0, 5, 4)
                
                total_calculated = r_reg + r_auth + r_refl + r_creat
                final_grade_str = f"{total_calculated}/20"
                new_feedback = st.text_input("Teacher's Feedback / Remarks", value=sel_row['feedback'])
                
                if st.button("Save Assessment", type="primary"):
                    c = conn.cursor()
                    c.execute("""
                        UPDATE portfolio 
                        SET rubric_regularity=?, rubric_authenticity=?, rubric_reflection=?, 
                            rubric_creativity=?, total_marks=?, grade=?, feedback=?
                        WHERE id=?
                    """, (r_reg, r_auth, r_refl, r_creat, total_calculated, final_grade_str, new_feedback, selected_pid))
                    conn.commit()
                    st.success("Marks & Rubric Saved Successfully!")
                    st.rerun()

        with tab2:
            st.subheader("Class 12-B Master Records")
            try:
                students_df = pd.read_sql_query("""
                    SELECT roll_no, sr_no, student_name, student_name_hindi, father_name, 
                           dob, aadhar_no, pen_no, mob_no, email_id, address 
                    FROM students WHERE role='Student' ORDER BY CAST(roll_no AS INTEGER) ASC
                """, conn)
            except Exception:
                students_df = pd.DataFrame()

            st.write(f"Total Active Students in DB: **{len(students_df)}**")
            st.dataframe(students_df, use_container_width=True)
            if not students_df.empty:
                st.download_button("📥 Export Clean Data (CSV)", students_df.to_csv(index=False).encode('utf-8'), "Class12B_Master.csv", "text/csv")

        with tab3:
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
        st.caption(f"S.R. No: {student_sr} | Roll No: {student_roll} | Class: 12-B")
        
        tab_s1, tab_s2, tab_s3, tab_s4, tab_s5 = st.tabs([
            "🎴 2-Page Portfolio Card",
            "📂 My Submissions Record", 
            "➕ Submit New Artifact / Work", 
            "🎯 Profile & Goal Setting",
            "👤 Official Details"
        ])
        
        # --- TAB 1: 2-PAGE GREETING / PORTFOLIO CARD ---
        with tab_s1:
            st.subheader("🎴 Official 2-Page Student Portfolio Card")
            st.caption("Standard Assessment Portfolio - Session 2026-27")
            
            # Fetch goals and submissions
            c = conn.cursor()
            c.execute("SELECT academic_goals, strengths_weaknesses FROM students WHERE username=?", (student_username,))
            res_goals = c.fetchone()
            p_goals = res_goals[0] if res_goals and res_goals[0] else "Not specified yet."
            p_sw = res_goals[1] if res_goals and res_goals[1] else "Not specified yet."
            
            try:
                card_items = pd.read_sql_query(
                    "SELECT * FROM portfolio WHERE student_username=? ORDER BY id DESC",
                    conn, params=(student_username,)
                )
            except Exception:
                card_items = pd.DataFrame()
            
            items_html = ""
            if card_items.empty:
                items_html = "<p style='color:#64748B; font-style:italic;'>No portfolio artifacts submitted yet.</p>"
            else:
                for _, itm in card_items.iterrows():
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

            hindi_name_str = f"({user_row[16]})" if user_row[16] else ""
            today_date_str = datetime.now().strftime('%d-%m-%Y')

            # Render Page 1
            st.markdown("### 📄 Page 1: Introductory & Student Profile")
            p1_html = f"""<div style="border: 2px solid #1E3A8A; border-radius: 10px; padding: 20px; background: #FFFFFF; font-family: sans-serif; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">
<div style="text-align: center; border-bottom: 2px solid #E2E8F0; padding-bottom: 10px; margin-bottom: 15px;">
<h2 style="margin: 0; color: #1E3A8A; font-size: 20px; text-transform: uppercase;">SENIOR SECONDARY STUDENT PORTFOLIO</h2>
<h4 style="margin: 4px 0 0 0; color: #475569; font-weight: normal; font-size: 14px;">Academic Session: 2026 - 2027 | Class: 12-B</h4>
<div style="display: inline-block; background: #1E3A8A; color: white; padding: 3px 12px; border-radius: 12px; font-size: 11px; margin-top: 6px; font-weight: bold;">OFFICIAL STUDENT DOSSIER</div>
</div>
<div style="display: flex; gap: 15px; margin-bottom: 15px;">
<table style="width: 70%; border-collapse: collapse; font-size: 13px;">
<tr style="background: #F1F5F9;"><td style="padding: 6px; font-weight: bold; width: 35%;">Student Name:</td><td style="padding: 6px; color: #1E3A8A; font-weight: bold;">{user_row[15]} {hindi_name_str}</td></tr>
<tr><td style="padding: 6px; font-weight: bold;">Roll No:</td><td style="padding: 6px;">{user_row[0]}</td></tr>
<tr style="background: #F1F5F9;"><td style="padding: 6px; font-weight: bold;">S.R. No:</td><td style="padding: 6px;">{user_row[4]}</td></tr>
<tr><td style="padding: 6px; font-weight: bold;">Father's Name:</td><td style="padding: 6px;">{user_row[17]}</td></tr>
<tr style="background: #F1F5F9;"><td style="padding: 6px; font-weight: bold;">Mother's Name:</td><td style="padding: 6px;">{user_row[19]}</td></tr>
<tr><td style="padding: 6px; font-weight: bold;">Date of Birth:</td><td style="padding: 6px;">{user_row[8]}</td></tr>
<tr style="background: #F1F5F9;"><td style="padding: 6px; font-weight: bold;">PEN / Aadhar:</td><td style="padding: 6px;">{user_row[6]} / {user_row[7]}</td></tr>
<tr><td style="padding: 6px; font-weight: bold;">Contact / Email:</td><td style="padding: 6px;">{user_row[26]} | {user_row[27]}</td></tr>
</table>
<div style="width: 30%; border: 2px dashed #94A3B8; border-radius: 8px; display: flex; flex-direction: column; align-items: center; justify-content: center; background: #F8FAFC; padding: 10px; text-align: center;">
<div style="font-size: 38px;">🎓</div>
<div style="font-weight: bold; font-size: 13px; color: #1E3A8A; margin-top: 5px;">{user_row[15]}</div>
<div style="font-size: 12px; color: #64748B;">Class 12-B</div>
<div style="font-size: 11px; color: #059669; margin-top: 6px; border: 1px solid #059669; padding: 2px 6px; border-radius: 10px;">Verified Student</div>
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
</div>"""
            st.html(p1_html)

            # Render Page 2
            st.markdown("### 📄 Page 2: Continuous Assessment & Evaluation Record")
            p2_html = f"""<div style="border: 2px solid #1E3A8A; border-radius: 10px; padding: 20px; background: #FFFFFF; font-family: sans-serif; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">
<div style="text-align: center; border-bottom: 2px solid #E2E8F0; padding-bottom: 10px; margin-bottom: 15px;">
<h3 style="margin: 0; color: #1E3A8A; font-size: 18px; text-transform: uppercase;">LEARNING ARTIFACTS & EVALUATION RECORD</h3>
<div style="display: inline-block; background: #059669; color: white; padding: 3px 12px; border-radius: 12px; font-size: 11px; margin-top: 6px; font-weight: bold;">CONTINUOUS & COMPREHENSIVE EVALUATION</div>
</div>
<div style="margin-bottom: 15px;">
<div style="color: #1E3A8A; font-weight: bold; font-size: 14px; margin-bottom: 8px;">📚 Key Academic & Practical Artifacts:</div>
{items_html}
</div>
<div style="border: 1px solid #CBD5E1; border-radius: 6px; padding: 12px; background: #F8FAFC; margin-top: 15px;">
<div style="margin: 0 0 8px 0; color: #1E3A8A; font-weight: bold; font-size: 13px;">📝 CBSE Portfolio Rubric Criteria (Max Marks: 20)</div>
<div style="display: flex; gap: 8px; font-size: 12px; text-align: center;">
<div style="flex: 1; background: white; padding: 6px; border: 1px solid #CBD5E1; border-radius: 4px;"><strong>1. Regularity</strong><br>(5 M)</div>
<div style="flex: 1; background: white; padding: 6px; border: 1px solid #CBD5E1; border-radius: 4px;"><strong>2. Authenticity</strong><br>(5 M)</div>
<div style="flex: 1; background: white; padding: 6px; border: 1px solid #CBD5E1; border-radius: 4px;"><strong>3. Reflection</strong><br>(5 M)</div>
<div style="flex: 1; background: white; padding: 6px; border: 1px solid #CBD5E1; border-radius: 4px;"><strong>4. Creativity</strong><br>(5 M)</div>
</div>
<div style="display: flex; justify-content: space-between; align-items: flex-end; margin-top: 25px; padding-top: 10px; border-top: 1px dashed #94A3B8; font-size: 12px;">
<div>
<div><strong>Student Signature:</strong> _____________________</div>
<div style="color: #64748B; font-size: 11px; margin-top: 4px;">Date: {today_date_str}</div>
</div>
<div style="text-align: right;">
<div><strong>Teacher Signature:</strong> _____________________</div>
<div style="color: #64748B; font-size: 11px; margin-top: 4px;">Class Teacher (12-B)</div>
</div>
</div>
</div>
</div>"""
            st.html(p2_html)

            # Print Button
            st.divider()
            col_p1, col_p2 = st.columns([1, 3])
            with col_p1:
                st.components.v1.html("""
                    <button onclick="window.parent.print()" style="background-color: #1E3A8A; color: white; border: none; padding: 10px 20px; font-size: 14px; border-radius: 6px; cursor: pointer; font-weight: bold; width: 100%;">🖨️ Print / Save as PDF</button>
                """, height=50)
            with col_p2:
                st.caption("Tip: Aap browser me **Save as PDF** select karke is 2-page portfolio card ko download kar sakte hain.")

        # --- TAB 2: Submissions Record ---
        with tab_s2:
            st.subheader("My Portfolio Records")
            try:
                my_port = pd.read_sql_query(
                    "SELECT * FROM portfolio WHERE student_username=? ORDER BY id DESC",
                    conn, params=(student_username,)
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

        # --- TAB 3: Submit New Artifact ---
        with tab_s3:
            st.subheader("Add Work to Portfolio")
            with st.form("cbse_submission_form"):
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
                        c = conn.cursor()
                        c.execute("""
                            INSERT INTO portfolio (
                                student_username, portfolio_section, category, title, 
                                description, learning_reflection, project_link, submitted_on
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (student_username, section.split('.')[1].strip(), sub_category, title, description, reflection, link, now_str))
                        conn.commit()
                        st.success("Artifact successfully submitted!")
                        st.rerun()
                    else:
                        st.error("Title is required!")

        # --- TAB 4: Profile & Goal Setting ---
        with tab_s4:
            st.subheader("🎯 Academic Goals & Self Profile")
            curr_goals = ""
            curr_sw = ""
            try:
                c = conn.cursor()
                c.execute("SELECT academic_goals, strengths_weaknesses FROM students WHERE username=?", (student_username,))
                res = c.fetchone()
                if res:
                    curr_goals = res[0] if res[0] else ""
                    curr_sw = res[1] if res[1] else ""
            except Exception:
                pass
            
            with st.form("goals_form"):
                goals = st.text_area("My Goals for Session 2026-27:", value=curr_goals)
                sw = st.text_area("My Strengths & Areas to Improve:", value=curr_sw)
                
                if st.form_submit_button("Save Goals"):
                    c = conn.cursor()
                    c.execute("UPDATE students SET academic_goals=?, strengths_weaknesses=? WHERE username=?", (goals, sw, student_username))
                    conn.commit()
                    st.success("Goals updated!")
                    st.rerun()

        # --- TAB 5: Official Details ---
        with tab_s5:
            st.subheader("Official Details (School Record)")
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"**Roll No:** {user_row[0]}")
                st.write(f"**S.R. No:** {user_row[4]}")
                st.write(f"**Name (English):** {user_row[15]}")
                st.write(f"**Name (Hindi):** {user_row[16]}")
                st.write(f"**Father's Name:** {user_row[17]}")
                st.write(f"**Mother's Name:** {user_row[19]}")
                st.write(f"**D.O.B:** {user_row[8]}")
            with c2:
                st.write(f"**Aadhar No:** {user_row[7]}")
                st.write(f"**PEN No:** {user_row[6]}")
                st.write(f"**Mobile:** {user_row[26]}")
                st.write(f"**Email:** {user_row[27]}")
                st.write(f"**Address:** {user_row[25]}")

    conn.close()
