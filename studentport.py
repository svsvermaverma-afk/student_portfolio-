import streamlit as st
import sqlite3
import pandas as pd
import os
import re
from datetime import datetime

# --- Page Config ---
st.set_page_config(page_title="Class 12-B CBSE Portfolio Portal", page_icon="🎓", layout="wide")

# --- Cleaner Function ---
def clean_val(val):
    if pd.isna(val) or val is None:
        return ""
    val_str = str(val).strip()
    if val_str.lower() in ["nan", "none", "nat", "<na>", "null"]:
        return ""
    if re.match(r'^-?\d+\.0+$', val_str):
        val_str = val_str.split('.')[0]
    return val_str

# --- Database Setup ---
def get_db_connection():
    return sqlite3.connect("class12b_portfolio.db", check_same_thread=False)

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Students Table
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
    
    # Portfolio Submissions Table with CBSE Rubrics
    c.execute('''
        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_username TEXT,
            portfolio_section TEXT NOT NULL,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            learning_reflection TEXT,
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
    
    # Ensure Admin Account
    c.execute("SELECT * FROM students WHERE username = 'admin'")
    if not c.fetchone():
        c.execute("""
            INSERT OR REPLACE INTO students (roll_no, username, password, student_name, role, class_name)
            VALUES ('ADMIN01', 'admin', 'admin123', 'Class Teacher (12-B)', 'Teacher', '12-B')
        """)
        
    conn.commit()
    conn.close()

# --- Sync studentport.xlsx ---
def sync_excel_data():
    excel_files = ["studentport.xlsx", "studentport.xls"]
    target_file = None
    for f in excel_files:
        if os.path.exists(f):
            target_file = f
            break
            
    if not target_file:
        return 0, "studentport.xlsx file nahi mili."

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
            
            if not s_name or s_name.lower() in ["nan", "nat"] or r_no == "0":
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
                r_no, login_username, login_password, '12-B',
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
        return 0, str(e)

init_db()

# --- Login Authentication ---
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
    st.caption("CBSE & State Board Internal Assessment Management System")
    
    col1, col2 = st.columns([1.2, 1])
    with col1:
        st.subheader("Login to Portfolio")
        user_input = st.text_input("Login ID (Student Name / Admin Username)")
        pass_input = st.text_input("Password (S.R. No. for Students)", type="password")
        
        if st.button("Login", type="primary", use_container_width=True):
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
        **Login Credentials Guide:**
        - **Teacher (Admin):**
          - ID: `admin` | Password: `admin123`
        - **Students:**
          - **Login ID:** Full Name (e.g. `AJIT KUMAR`)
          - **Password:** S.R. NO. (e.g. `37212`)
        """)

# --- Authenticated Interface ---
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
    # 1. TEACHER DASHBOARD (CBSE RUBRICS EVALUATION)
    # ==========================================
    if role == "Teacher":
        st.title("👨‍🏫 Teacher Evaluation & Assessment Panel - Class 12-B")
        
        tab1, tab2, tab3 = st.tabs([
            "📑 Portfolio Assessment & Rubric Grading", 
            "👥 Class Master Records", 
            "🔄 Re-Sync Excel Data"
        ])
        
        with tab1:
            st.subheader("All Submitted Portfolio Artifacts")
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
                st.info("No artifacts submitted yet.")
            else:
                st.dataframe(
                    df_port[["roll_no", "student_name", "portfolio_section", "category", "title", "total_marks", "grade", "submitted_on"]],
                    use_container_width=True
                )
                
                st.divider()
                st.subheader("🎯 CBSE Rubric-Based Evaluation")
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
                    st.markdown(f"**Student Self-Reflection:**")
                    st.info(sel_row['learning_reflection'] if sel_row['learning_reflection'] else "No self-reflection entered.")
                    if sel_row['project_link']:
                        st.markdown(f"🔗 **Attachment / Work Link:** [{sel_row['project_link']}]({sel_row['project_link']})")
                
                st.markdown("##### 📝 Scoring Rubric (Out of 5 Marks per Criteria)")
                c_r1, c_r2, c_r3, c_r4 = st.columns(4)
                with c_r1:
                    r_reg = st.slider("Regularity & Timeliness (0-5)", 0, 5, 4)
                with c_r2:
                    r_auth = st.slider("Authenticity & Quality (0-5)", 0, 5, 4)
                with c_r3:
                    r_refl = st.slider("Reflection & Learning (0-5)", 0, 5, 4)
                with c_r4:
                    r_creat = st.slider("Creativity / Effort (0-5)", 0, 5, 4)
                
                total_calculated = r_reg + r_auth + r_refl + r_creat  # Out of 20
                final_grade_str = f"{total_calculated}/20"
                
                new_feedback = st.text_input("Teacher's Feedback / Remarks", value=sel_row['feedback'])
                
                if st.button("Save CBSE Assessment & Marks", type="primary"):
                    c = conn.cursor()
                    c.execute("""
                        UPDATE portfolio 
                        SET rubric_regularity=?, rubric_authenticity=?, rubric_reflection=?, 
                            rubric_creativity=?, total_marks=?, grade=?, feedback=?
                        WHERE id=?
                    """, (r_reg, r_auth, r_refl, r_creat, total_calculated, final_grade_str, new_feedback, selected_pid))
                    conn.commit()
                    st.success("Assessment with Rubrics successfully saved!")
                    st.rerun()

        with tab2:
            st.subheader("Class 12-B Master Student Records")
            students_df = pd.read_sql_query("""
                SELECT roll_no, sr_no, student_name, student_name_hindi, father_name, 
                       dob, aadhar_no, pen_no, mob_no, email_id, address 
                FROM students WHERE role='Student' ORDER BY CAST(roll_no AS INTEGER) ASC
            """, conn)
            st.dataframe(students_df, use_container_width=True)
            if not students_df.empty:
                st.download_button("📥 Export Clean Data (CSV)", students_df.to_csv(index=False).encode('utf-8'), "Class12B_Master.csv", "text/csv")

        with tab3:
            st.subheader("Sync with studentport.xlsx")
            if st.button("🔄 Sync Data Now", type="primary"):
                count, msg = sync_excel_data()
                st.success(f"{count} students updated successfully!")
                st.rerun()

    # ==========================================
    # 2. STUDENT DASHBOARD (5-SECTION CBSE PORTFOLIO)
    # ==========================================
    else:
        st.title(f"🎓 Student Portfolio - {student_name}")
        st.caption(f"S.R. No: {student_sr} | Roll No: {student_roll} | Class: 12-B")
        
        tab_s1, tab_s2, tab_s3, tab_s4 = st.tabs([
            "📂 My Complete Portfolio Record", 
            "➕ Submit New Artifact / Work", 
            "🎯 Student Profile & Goal Setting",
            "👤 Official Details"
        ])
        
        # --- TAB 1: Complete Portfolio ---
        with tab_s1:
            st.subheader("Submitted Portfolio Artifacts")
            my_port = pd.read_sql_query(
                "SELECT * FROM portfolio WHERE student_username=? ORDER BY id DESC",
                conn, params=(student_username,)
            )
            
            if my_port.empty:
                st.info("Aapka portfolio khali hai. Naya kaam submit karne ke liye 'Submit New Artifact' tab par jayein.")
            else:
                for _, row in my_port.iterrows():
                    with st.expander(f"📌 [{row['portfolio_section']}] {row['title']} - Score: {row['grade']}"):
                        col_e1, col_e2 = st.columns(2)
                        with col_e1:
                            st.write(f"**Category:** {row['category']}")
                            st.write(f"**Submitted Date:** {row['submitted_on']}")
                            st.write(f"**Work Description:** {row['description']}")
                            if row['project_link']:
                                st.write(f"🔗 **Link:** [{row['project_link']}]({row['project_link']})")
                        with col_e2:
                            st.write(f"**My Self-Reflection:** {row['learning_reflection']}")
                            st.divider()
                            st.write(f"👨‍🏫 **Teacher's Feedback:** {row['feedback']}")
                            if row['total_marks'] > 0:
                                st.write(f"**Rubric Marks Breakdown:** Regularity: {row['rubric_regularity']}/5 | Authenticity: {row['rubric_authenticity']}/5 | Reflection: {row['rubric_reflection']}/5 | Creativity: {row['rubric_creativity']}/5")

        # --- TAB 2: Submit New Work under 5 Pillars ---
        with tab_s2:
            st.subheader("Add Artifact to Portfolio")
            with st.form("cbse_portfolio_submission_form"):
                
                section = st.selectbox("1. Select Portfolio Section / Pillar*", [
                    "2. Academic Artifacts (Best CW/HW, Unit Tests, Error Analysis)",
                    "3. Projects & Practical Work (Lab Experiments, Working Models, Surveys)",
                    "4. Creative & Co-Curricular (Art Integration, Creative Writing, Certificates)",
                    "5. Self & Peer Assessment (Reflections & Group Feedback)"
                ])
                
                # Category mapping based on standard sections
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
                description = st.text_area("4. Summary / Description of the Activity")
                reflection = st.text_area("5. Student Reflection (Maine isse kya seekha? / What I learned & challenges faced)")
                link = st.text_input("6. Google Drive / Photo / GitHub Link of the Work")
                
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
                        st.success("Artifact portfolio me successfully add ho gaya!")
                        st.rerun()
                    else:
                        st.error("Title dena zaroori hai.")

        # --- TAB 3: Student Profile & Goals ---
        with tab_s3:
            st.subheader("🎯 Student Profile, Interests & Academic Goals")
            st.caption("Introductory Section - Set your aspirations and strengths for the session.")
            
            c = conn.cursor()
            c.execute("SELECT academic_goals, strengths_weaknesses FROM students WHERE username=?", (student_username,))
            res = c.fetchone()
            curr_goals = res[0] if res and res[0] else ""
            curr_sw = res[1] if res and res[1] else ""
            
            with st.form("goals_form"):
                goals = st.text_area("My Academic & Career Goals for Class 12:", value=curr_goals, placeholder="e.g., Score 90%+ in Board Exams, Master Physics Numericals, Prepare for Competitive Exams...")
                sw = st.text_area("My Strengths & Areas to Improve:", value=curr_sw, placeholder="e.g., Strength: Problem Solving & Diagrams | Improvement: Time Management during Unit Tests")
                
                if st.form_submit_button("Save Goals & Profile"):
                    c.execute("UPDATE students SET academic_goals=?, strengths_weaknesses=? WHERE username=?", (goals, sw, student_username))
                    conn.commit()
                    st.success("Profile goals updated successfully!")
                    st.rerun()

        # --- TAB 4: Official Profile Details ---
        with tab_s4:
            st.subheader("1. Introductory Section - Official Student Profile")
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
