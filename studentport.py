import streamlit as st
import sqlite3
import pandas as pd
import os
import re
from datetime import datetime

# --- Page Config ---
st.set_page_config(page_title="Class 12-B Portfolio Portal", page_icon="🎓", layout="wide")

# --- Robust Cleaner Function ---
def clean_val(val):
    if pd.isna(val) or val is None:
        return ""
    val_str = str(val).strip()
    
    # Check for empty/nan patterns
    if val_str.lower() in ["nan", "none", "nat", "<na>", "null"]:
        return ""
        
    # Remove float decimal like '1.0' -> '1', '38954.0' -> '38954'
    if re.match(r'^-?\d+\.0+$', val_str):
        val_str = val_str.split('.')[0]
        
    # Date cleaner (Agar date me timestamp 00:00:00 ho to remove karein)
    if "00:00:00" in val_str:
        val_str = val_str.replace("00:00:00", "").strip()
        try:
            parsed_dt = pd.to_datetime(val_str)
            val_str = parsed_dt.strftime("%d-%m-%Y")
        except Exception:
            pass
            
    return val_str

# --- Database Connection ---
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
            role TEXT DEFAULT 'Student'
        )
    ''')
    
    # Portfolio Submissions Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_username TEXT,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            project_link TEXT,
            grade TEXT DEFAULT 'Pending',
            feedback TEXT DEFAULT 'No feedback yet',
            submitted_on TEXT
        )
    ''')
    
    # Admin Account
    c.execute("SELECT * FROM students WHERE username = 'admin'")
    if not c.fetchone():
        c.execute("""
            INSERT OR REPLACE INTO students (roll_no, username, password, student_name, role, class_name)
            VALUES ('ADMIN01', 'admin', 'admin123', 'Class Teacher (12-B)', 'Teacher', '12-B')
        """)
        
    conn.commit()
    conn.close()

# --- Excel Sync & Auto-Clean Function ---
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
        
        # Puraana student data clear karein (Teacher admin record retain rahega)
        c.execute("DELETE FROM students WHERE role='Student'")
        
        success_count = 0
        for _, row in df_excel.iterrows():
            s_name = clean_val(row.get("STUDENT'S NAME", ""))
            sr_no = clean_val(row.get("S.R. NO.", ""))
            r_no = clean_val(row.get("ROLL NO.", ""))
            
            # Agar Name ya Roll No blank/0 ho to skip karein
            if not s_name or s_name.lower() in ["nan", "nat"] or r_no == "0":
                continue
            
            # Username = Student Name, Password = S.R. No.
            login_username = s_name.strip()
            login_password = sr_no if sr_no else "123456"
            
            dob_val = clean_val(row.get("D.O.B.", ""))
            
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
                s_name,
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

# --- Authentication Logic ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_data = None

def login_user(username, password):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        SELECT * FROM students 
        WHERE (LOWER(TRIM(username)) = LOWER(TRIM(?)) OR LOWER(TRIM(student_name)) = LOWER(TRIM(?))) 
        AND TRIM(password) = TRIM(?)
    """, (username, username, password))
    user = c.fetchone()
    conn.close()
    return user

def logout_user():
    st.session_state.logged_in = False
    st.session_state.user_data = None
    st.rerun()

# --- Login UI ---
if not st.session_state.logged_in:
    st.title("🎓 Class 12-B Portfolio & Student Portal")
    st.caption("Central Database & Portfolio Management System")
    
    col1, col2 = st.columns([1.2, 1])
    with col1:
        st.subheader("Login")
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
                st.error("Invalid Name ya Password (S.R. No.)!")
                
    with col2:
        st.info("""
        **Login Guide:**
        - **Teacher (Admin):**
          - ID: `admin` | Password: `admin123`
        - **Students:**
          - **Login ID:** Apna Name (e.g. `ABHIMANYU YADAV`)
          - **Password:** Apna S.R. NO. (e.g. `38954`)
        """)

# --- Authenticated Dashboards ---
else:
    user_row = st.session_state.user_data
    role = user_row[28]
    student_roll = user_row[0]
    student_username = user_row[1]
    student_sr = user_row[4]
    student_name = user_row[15]
    
    with st.sidebar:
        st.write(f"### 👋 Welcome, **{student_name}**")
        st.write(f"**Role:** `{role}`")
        if role == "Student":
            st.write(f"**Roll No:** {student_roll}")
            st.write(f"**S.R. No:** {student_sr}")
        st.write("**Class:** 12-B")
        st.divider()
        if st.button("Logout", use_container_width=True):
            logout_user()

    conn = get_db_connection()

    # ==========================================
    # TEACHER DASHBOARD
    # ==========================================
    if role == "Teacher":
        st.title("👨‍🏫 Teacher Dashboard - Class 12-B")
        
        tab1, tab2, tab3 = st.tabs([
            "📋 Portfolios Review", 
            "👥 All Students Data", 
            "🔄 Re-Sync Excel Data"
        ])
        
        with tab1:
            st.subheader("Student Portfolio Submissions")
            try:
                query = """
                    SELECT p.id, s.roll_no, s.student_name, s.sr_no, p.title, p.category, 
                           p.description, p.project_link, p.grade, p.feedback, p.submitted_on
                    FROM portfolio p
                    LEFT JOIN students s ON p.student_username = s.username
                    ORDER BY p.id DESC
                """
                df_port = pd.read_sql_query(query, conn)
            except Exception:
                df_port = pd.DataFrame()
            
            if df_port.empty:
                st.info("Abhi tak koi portfolio submission nahi hua hai.")
            else:
                st.dataframe(df_port[["roll_no", "student_name", "sr_no", "title", "category", "grade", "submitted_on"]], use_container_width=True)
                st.divider()
                st.write("#### Evaluate Submission")
                selected_pid = st.selectbox("Select Submission ID", df_port["id"].tolist())
                sel_row = df_port[df_port["id"] == selected_pid].iloc[0]
                
                st.write(f"**Student:** {sel_row['student_name']} (Roll: {sel_row['roll_no']} | S.R.: {sel_row['sr_no']})")
                st.write(f"**Title:** {sel_row['title']} | **Category:** {sel_row['category']}")
                st.write(f"**Description:** {sel_row['description']}")
                if sel_row['project_link']:
                    st.write(f"**Link:** [{sel_row['project_link']}]({sel_row['project_link']})")
                    
                col_g1, col_g2 = st.columns(2)
                with col_g1:
                    new_grade = st.selectbox("Grade", ["A+", "A", "B+", "B", "C", "Needs Revision"])
                with col_g2:
                    new_feedback = st.text_input("Teacher Feedback", value=sel_row['feedback'])
                    
                if st.button("Update Grade & Feedback", type="primary"):
                    c = conn.cursor()
                    c.execute("UPDATE portfolio SET grade=?, feedback=? WHERE id=?", (new_grade, new_feedback, selected_pid))
                    conn.commit()
                    st.success("Evaluation Saved!")
                    st.rerun()

        with tab2:
            st.subheader("Class 12-B Master Student Records (Clean Data)")
            try:
                students_df = pd.read_sql_query("""
                    SELECT roll_no, sr_no, student_name, student_name_hindi, father_name, 
                           dob, aadhar_no, pen_no, mob_no, email_id, address 
                    FROM students WHERE role='Student' 
                    ORDER BY CAST(roll_no AS INTEGER) ASC
                """, conn)
            except Exception:
                students_df = pd.DataFrame()

            st.write(f"Total Active Students: **{len(students_df)}**")
            st.dataframe(students_df, use_container_width=True)
            
            if not students_df.empty:
                csv_data = students_df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Export Clean Data (CSV)", csv_data, "Class12B_Students_Clean.csv", "text/csv")

        with tab3:
            st.subheader("Sync with studentport.xlsx")
            st.write("Click below to clean all decimals and refresh data:")
            if st.button("🔄 Sync & Clean Data Now", type="primary"):
                count, msg = sync_excel_data()
                if count > 0:
                    st.success(f"{count} students ka data bina decimal ke successfully clean & load ho gaya!")
                    st.rerun()
                else:
                    st.error(f"Sync error: {msg}")

    # ==========================================
    # STUDENT DASHBOARD
    # ==========================================
    else:
        st.title(f"🎒 My Portfolio - {student_name}")
        st.caption(f"S.R. No: {student_sr} | Roll No: {student_roll} | Class: 12-B")
        
        tab_s1, tab_s2, tab_s3 = st.tabs(["📁 My Submissions & Grades", "➕ Submit New Work", "👤 My Profile Details"])
        
        with tab_s1:
            st.subheader("Submitted Items")
            try:
                my_port = pd.read_sql_query(
                    "SELECT title, category, description, project_link, grade, feedback, submitted_on FROM portfolio WHERE student_username=? ORDER BY id DESC",
                    conn, params=(student_username,)
                )
            except Exception:
                my_port = pd.DataFrame()

            if my_port.empty:
                st.info("Abhi tak koi portfolio submission nahi kiya gaya.")
            else:
                for _, row in my_port.iterrows():
                    with st.expander(f"📌 {row['title']} ({row['category']}) - Grade: {row['grade']}"):
                        st.write(f"**Submitted on:** {row['submitted_on']}")
                        st.write(f"**Description:** {row['description']}")
                        if row['project_link']:
                            st.write(f"**Link:** [{row['project_link']}]({row['project_link']})")
                        st.divider()
                        st.write(f"**Teacher Feedback:** {row['feedback']}")

        with tab_s2:
            st.subheader("Submit New Work / Project")
            with st.form("student_sub_form"):
                p_title = st.text_input("Project / Assignment Title*")
                p_cat = st.selectbox("Category", [
                    "Physics Practical / Working Model",
                    "Computer Science / Python Project",
                    "Chemistry Record / Project",
                    "Maths Activity",
                    "Art & Science Exhibition",
                    "Other Activity"
                ])
                p_desc = st.text_area("Description / Summary")
                p_url = st.text_input("Project / Drive / Github Link")
                
                if st.form_submit_button("Submit Entry"):
                    if p_title:
                        now_str = datetime.now().strftime("%d-%b-%Y %I:%M %p")
                        c = conn.cursor()
                        c.execute("""
                            INSERT INTO portfolio (student_username, title, category, description, project_link, submitted_on)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (student_username, p_title, p_cat, p_desc, p_url, now_str))
                        conn.commit()
                        st.success("Portfolio successfully submit ho gaya!")
                        st.rerun()
                    else:
                        st.error("Title zaroori hai.")

        with tab_s3:
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
