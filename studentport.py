import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- Page Config ---
st.set_page_config(page_title="Class 12-B Portfolio & Student Portal", page_icon="🎓", layout="wide")

# --- Database Connection & Init ---
def get_db_connection():
    return sqlite3.connect("class12b_portfolio.db", check_same_thread=False)

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Students / Users Table with All Excel Fields
    c.execute('''
        CREATE TABLE IF NOT EXISTS students (
            roll_no TEXT PRIMARY KEY,
            username TEXT UNIQUE,
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
            student_roll_no TEXT,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            project_link TEXT,
            grade TEXT DEFAULT 'Pending',
            feedback TEXT DEFAULT 'No feedback yet',
            submitted_on TEXT,
            FOREIGN KEY (student_roll_no) REFERENCES students(roll_no)
        )
    ''')
    
    # Admin / Teacher Account
    c.execute("SELECT * FROM students WHERE username = 'admin'")
    if not c.fetchone():
        c.execute("""
            INSERT INTO students (roll_no, username, password, student_name, role, class_name)
            VALUES ('ADMIN01', 'admin', 'admin123', 'Class Teacher (12-B)', 'Teacher', '12-B')
        """)
        
    conn.commit()
    conn.close()

init_db()

# --- Session State ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_data = None

def login_user(username_or_roll, password):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        SELECT * FROM students 
        WHERE (username=? OR roll_no=?) AND password=?
    """, (username_or_roll, username_or_roll, password))
    user = c.fetchone()
    conn.close()
    return user

def logout_user():
    st.session_state.logged_in = False
    st.session_state.user_data = None
    st.rerun()

# --- Login Page ---
if not st.session_state.logged_in:
    st.title("🎓 Class 12-B Portfolio & Student Portal")
    st.caption("Central Database & Portfolio Management System")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("Login")
        user_input = st.text_input("Roll No / Username")
        pass_input = st.text_input("Password", type="password")
        
        if st.button("Login", type="primary", use_container_width=True):
            user = login_user(user_input, pass_input)
            if user:
                st.session_state.logged_in = True
                st.session_state.user_data = user
                st.success(f"Welcome {user[15]}!")
                st.rerun()
            else:
                st.error("Invalid Roll No / Username ya Password!")
                
    with col2:
        st.info("""
        **Default Admin (Teacher) Login:**
        - **Username:** `admin`
        - **Password:** `admin123`
        
        *(Students can login using their Roll No as Username and default password set during registration).*
        """)

# --- Main App (Logged In) ---
else:
    user_row = st.session_state.user_data
    role = user_row[28]  # Role column
    student_roll = user_row[0]
    student_name = user_row[15]
    
    # Sidebar
    with st.sidebar:
        st.write(f"### 👋 Welcome, **{student_name}**")
        st.write(f"**Role:** `{role}`")
        if role == "Student":
            st.write(f"**Roll No:** {student_roll}")
            st.write(f"**Mobile:** {user_row[26]}")
        st.write("**Class:** 12-B")
        st.divider()
        if st.button("Logout", use_container_width=True):
            logout_user()

    conn = get_db_connection()

    # ==========================================
    # 1. TEACHER / ADMIN DASHBOARD
    # ==========================================
    if role == "Teacher":
        st.title("👨‍🏫 Teacher Dashboard - Class 12-B")
        
        tabs = st.tabs([
            "📋 Portfolios Review", 
            "👥 All Students Data", 
            "➕ Add Single Student", 
            "📂 Bulk Upload (Excel)"
        ])
        
        # --- TAB 1: Review Portfolios ---
        with tabs[0]:
            st.subheader("Student Portfolio Submissions")
            query = """
                SELECT p.id, s.roll_no, s.student_name, p.title, p.category, 
                       p.description, p.project_link, p.grade, p.feedback, p.submitted_on
                FROM portfolio p
                JOIN students s ON p.student_roll_no = s.roll_no
                ORDER BY p.id DESC
            """
            df_port = pd.read_sql_query(query, conn)
            
            if df_port.empty:
                st.info("No submissions yet.")
            else:
                st.dataframe(df_port[["roll_no", "student_name", "title", "category", "grade", "submitted_on"]], use_container_width=True)
                st.divider()
                st.write("#### Evaluate Submission")
                selected_pid = st.selectbox("Select Submission ID to Grade", df_port["id"].tolist())
                sel_row = df_port[df_port["id"] == selected_pid].iloc[0]
                
                st.write(f"**Student:** {sel_row['student_name']} (Roll: {sel_row['roll_no']})")
                st.write(f"**Project Title:** {sel_row['title']} | **Category:** {sel_row['category']}")
                st.write(f"**Description:** {sel_row['description']}")
                if sel_row['project_link']:
                    st.write(f"**Link:** [{sel_row['project_link']}]({sel_row['project_link']})")
                    
                col_g1, col_g2 = st.columns(2)
                with col_g1:
                    new_grade = st.selectbox("Grade", ["A+", "A", "B+", "B", "C", "Needs Revision"])
                with col_g2:
                    new_feedback = st.text_input("Feedback / Remarks", value=sel_row['feedback'])
                    
                if st.button("Update Grade & Feedback", type="primary"):
                    c = conn.cursor()
                    c.execute("UPDATE portfolio SET grade=?, feedback=? WHERE id=?", (new_grade, new_feedback, selected_pid))
                    conn.commit()
                    st.success("Evaluation Saved!")
                    st.rerun()

        # --- TAB 2: All Students Database ---
        with tabs[1]:
            st.subheader("Class 12-B Master Student Records")
            students_df = pd.read_sql_query("SELECT * FROM students WHERE role='Student' ORDER BY roll_no", conn)
            st.dataframe(students_df, use_container_width=True)
            
            # Download CSV Button
            if not students_df.empty:
                csv_data = students_df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Export Complete Data (CSV)", csv_data, "Class12B_Students_Master.csv", "text/csv")

        # --- TAB 3: Add Single Student (Matching Your Excel Columns) ---
        with tabs[2]:
            st.subheader("Add Student Information (All Fields)")
            with st.form("single_student_form"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    r_no = st.text_input("ROLL NO.*")
                    sr_no = st.text_input("S.R. NO.")
                    roll_10th = st.text_input("roll number 10th")
                    pen_no = st.text_input("PEN NUMBER")
                    aadhar = st.text_input("AADHAR NO.")
                with c2:
                    dob = st.date_input("D.O.B.")
                    occupation = st.selectbox("OCCUPATION", ["Other-OTH", "Hindalco -HE", "Hindalco Supply- HS"])
                    ecode = st.text_input("E.CODE")
                    dept = st.text_input("DEPT.")
                    gender = st.selectbox("GENDER", ["MALE", "FEMALE", "OTHER"])
                with c3:
                    caste = st.text_input("CASTE")
                    cat = st.selectbox("CAT. (Category)", ["GEN", "OBC", "SC", "ST", "EWS"])
                    religion = st.text_input("RELIGION", value="HINDU")
                    mob = st.text_input("MOB. NO.")
                    email = st.text_input("EMAIL ID")

                st.markdown("---")
                c4, c5 = st.columns(2)
                with c4:
                    s_name = st.text_input("STUDENT'S NAME*")
                    f_name = st.text_input("FATHER'S NAME")
                    m_name = st.text_input("MOTHER'S NAME")
                with c5:
                    s_name_h = st.text_input("STUDENT NAME IN HINDI")
                    f_name_h = st.text_input("FATHER'S NAME IN HINDI")
                    m_name_h = st.text_input("MOTHER'S NAME IN HINDI")

                address = st.text_area("ADDRESS")
                
                st.markdown("---")
                col_acc1, col_acc2 = st.columns(2)
                with col_acc1:
                    u_name = st.text_input("Login Username (Default will be Roll No if left blank)")
                with col_acc2:
                    p_word = st.text_input("Student Login Password*", value="123456", type="password")

                save_student = st.form_submit_button("Save Student to Database", type="primary")

                if save_student:
                    if not r_no or not s_name:
                        st.error("ROLL NO aur STUDENT'S NAME zaroori fields hain!")
                    else:
                        username_final = u_name if u_name else r_no
                        dob_str = dob.strftime("%d/%m/%Y")
                        dd = dob.strftime("%d")
                        mm = dob.strftime("%m")
                        yyyy = dob.strftime("%Y")
                        
                        try:
                            c = conn.cursor()
                            c.execute("""
                                INSERT INTO students (
                                    roll_no, username, password, class_name, sr_no, roll_no_10th, 
                                    pen_no, aadhar_no, dob, dob_dd, dob_mm, dob_yyyy, 
                                    occupation, ecode, dept, student_name, student_name_hindi, 
                                    father_name, father_name_hindi, mother_name, mother_name_hindi, 
                                    gender, caste, category, religion, address, mob_no, email_id, role
                                ) VALUES (?, ?, ?, '12-B', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Student')
                            """, (
                                r_no, username_final, p_word, sr_no, roll_10th, 
                                pen_no, aadhar, dob_str, dd, mm, yyyy, 
                                occupation, ecode, dept, s_name, s_name_h, 
                                f_name, f_name_h, m_name, m_name_h, 
                                gender, caste, cat, religion, address, mob, email
                            ))
                            conn.commit()
                            st.success(f"Student {s_name} ({r_no}) database me add ho gaya!")
                        except sqlite3.IntegrityError:
                            st.error("Ye Roll Number ya Username pehle se database me exist karta hai!")

        # --- TAB 4: Bulk Excel Upload ---
        with tabs[3]:
            st.subheader("Bulk Import from Excel Sheet")
            st.write("Aap apni poori Excel file direct upload kar sakte hain.")
            
            uploaded_file = st.file_uploader("Upload Excel File (.xlsx)", type=["xlsx", "xls"])
            if uploaded_file is not None:
                try:
                    df_excel = pd.read_excel(uploaded_file)
                    st.write("Preview of Uploaded Data:")
                    st.dataframe(df_excel.head(5), use_container_width=True)
                    
                    if st.button("Import All Rows to Database"):
                        c = conn.cursor()
                        success_count = 0
                        for _, row in df_excel.iterrows():
                            # Clean field access
                            r_no = str(row.get("ROLL NO.", "")).strip()
                            s_name = str(row.get("STUDENT'S NAME", "")).strip()
                            if not r_no or r_no == "nan":
                                continue
                            
                            dob_val = str(row.get("D.O.B.", ""))
                            dd = str(row.get("DD", ""))
                            mm = str(row.get("MM", ""))
                            yyyy = str(row.get("YYYY", ""))
                            
                            try:
                                c.execute("""
                                    INSERT OR REPLACE INTO students (
                                        roll_no, username, password, class_name, sr_no, roll_no_10th, 
                                        pen_no, aadhar_no, dob, dob_dd, dob_mm, dob_yyyy, 
                                        occupation, ecode, dept, student_name, student_name_hindi, 
                                        father_name, father_name_hindi, mother_name, mother_name_hindi, 
                                        gender, caste, category, religion, address, mob_no, email_id, role
                                    ) VALUES (?, ?, ?, '12-B', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Student')
                                """, (
                                    r_no, r_no, "123456",
                                    str(row.get("S.R. NO.", "")),
                                    str(row.get("roll numer 10th", "")),
                                    str(row.get("PEN NUMBER", "")),
                                    str(row.get("AADHAR NO.", "")),
                                    dob_val, dd, mm, yyyy,
                                    str(row.get("OCCUPATION Other-OTH / Hindalco -HE / Hindalco Supply- HS", "")),
                                    str(row.get("E.CODE", "")),
                                    str(row.get("DEPT.", "")),
                                    s_name,
                                    str(row.get("STUDENT NAME IN HINDI", "")),
                                    str(row.get("FATHER'S NAME", "")),
                                    str(row.get("FATHER'S NAME IN HINDI", "")),
                                    str(row.get("MOTHER'S NAME", "")),
                                    str(row.get("MOTHER'S NAME IN HINDI", "")),
                                    str(row.get("GENDER", "")),
                                    str(row.get("CASTE", "")),
                                    str(row.get("CAT.", "")),
                                    str(row.get("RELIGION", "")),
                                    str(row.get("ADDRESS", "")),
                                    str(row.get("MOB. NO.", "")),
                                    str(row.get("EMAIL ID", "")),
                                )
                                )
                                success_count += 1
                            except Exception as err:
                                pass
                        
                        conn.commit()
                        st.success(f"{success_count} Students successfully import ho gaye! (Default Password: `123456`)")
                except Exception as e:
                    st.error(f"Error reading file: {e}")

    # ==========================================
    # 2. STUDENT DASHBOARD
    # ==========================================
    else:
        st.title(f"🎒 My Portfolio - {student_name}")
        st.caption(f"Roll No: {student_roll} | Class: 12-B")
        
        tab_s1, tab_s2, tab_s3 = st.tabs(["📁 My Projects & Grades", "➕ Submit New Portfolio", "👤 My Profile Details"])
        
        with tab_s1:
            st.subheader("Submitted Items")
            my_port = pd.read_sql_query(
                "SELECT title, category, description, project_link, grade, feedback, submitted_on FROM portfolio WHERE student_roll_no=? ORDER BY id DESC",
                conn, params=(student_roll,)
            )
            if my_port.empty:
                st.info("Abhi tak koi portfolio submission nahi kiya gaya.")
            else:
                for _, row in my_port.iterrows():
                    with st.expander(f"📌 {row['title']} ({row['category']}) - Grade: {row['grade']}"):
                        st.write(f"**Submitted on:** {row['submitted_on']}")
                        st.write(f"**Description:** {row['description']}")
                        if row['project_link']:
                            st.write(f"**Project Link:** [{row['project_link']}]({row['project_link']})")
                        st.divider()
                        st.write(f"**Teacher Feedback:** {row['feedback']}")

        with tab_s2:
            st.subheader("Submit New Work / Project")
            with st.form("student_sub_form"):
                p_title = st.text_input("Project / Assignment Title*")
                p_cat = st.selectbox("Category", [
                    "Physics Practical / Model",
                    "Computer Science / Python Project",
                    "Chemistry Record",
                    "Maths Activity",
                    "Art & Exhibition Project"
                ])
                p_desc = st.text_area("Description / Summary")
                p_url = st.text_input("Project / Drive / Github Link")
                
                if st.form_submit_button("Submit Entry"):
                    if p_title:
                        now_str = datetime.now().strftime("%d-%b-%Y %I:%M %p")
                        c = conn.cursor()
                        c.execute("""
                            INSERT INTO portfolio (student_roll_no, title, category, description, project_link, submitted_on)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (student_roll, p_title, p_cat, p_desc, p_url, now_str))
                        conn.commit()
                        st.success("Portfolio successfully submit ho gaya!")
                        st.rerun()
                    else:
                        st.error("Title zaroori hai.")

        with tab_s3:
            st.subheader("Official Details Recorded in School")
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"**Roll No:** {user_row[0]}")
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
