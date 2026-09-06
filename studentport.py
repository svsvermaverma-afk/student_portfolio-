import streamlit as st
import sqlite3
import pandas as pd
import os
import glob
import re
import base64
from datetime import datetime

# --- Page Config ---
st.set_page_config(page_title="Class 12-B Master & Portfolio Portal", page_icon="🎓", layout="wide")

SCHOOL_NAME_HEADER = "ADITYA BIRLA INTERMEDIATE COLLEGE, RENUKOOT, SONEBHADRA (UP)"

# --- Cleaner Helper Functions ---
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

def convert_gdrive_link(url):
    if not url or not isinstance(url, str):
        return ""
    url = url.strip()
    match1 = re.search(r'/d/([a-zA-Z0-9_-]+)', url)
    if match1:
        return f"https://lh3.googleusercontent.com/d/{match1.group(1)}"
    match2 = re.search(r'id=([a-zA-Z0-9_-]+)', url)
    if match2:
        return f"https://lh3.googleusercontent.com/d/{match2.group(1)}"
    return url

# --- 14 Official School Activities (UP Board Calendar 2026-27) ---
DEFAULT_ACTIVITIES = [
    {"sno": 1, "date": "27.08.2026", "name": "Tata Building India School Essay Competition", "cat": "साहित्यिक (निबंध)", "desc": "2047 तक भारत को विश्व का सबसे विकसित देश बनाने के लिए मैं यह पांच कार्य करूंगा/करूंगी", "incharge": "श्री विकास कुमार चक्रवर्ती / कक्षा अध्यापक"},
    {"sno": 2, "date": "27.08.2026", "name": "रंगोली प्रतियोगिता", "cat": "कला एवं संस्कृति", "desc": "रंगोली निर्माण (समूह गतिविधि - प्रति समूह 4 विद्यार्थी)", "incharge": "श्रीमती साधना भरद्वाज"},
    {"sno": 3, "date": "27.08.2026", "name": "मेहंदी प्रतियोगिता", "cat": "कला एवं संस्कृति", "desc": "मेहंदी आलेखन (रचनात्मकता, मौलिकता व बारीकी)", "incharge": "श्रीमती पूजा सिंह"},
    {"sno": 4, "date": "20.08.2026", "name": "राखी निर्माण प्रतियोगिता", "cat": "क्राफ्ट एवं रचनात्मक कौशल", "desc": "आकर्षक व सुंदर राखी निर्माण (राखी प्रदर्शनी हेतु)", "incharge": "श्री शशिकांत सर / श्री विकास कुमार चक्रवर्ती"},
    {"sno": 5, "date": "13.08.2026", "name": "चित्रकला प्रतियोगिता", "cat": "दृश्य कला (Drawing)", "desc": "सरदार वल्लभभाई पटेल के जीवन एवं आदर्शों पर आधारित चित्रकला", "incharge": "डॉ. संतोष कुमार तिवारी"},
    {"sno": 6, "date": "06.08.2026", "name": "निबंध प्रतियोगिता", "cat": "साहित्यिक (निबंध)", "desc": "सरदार वल्लभभाई पटेल की 150वीं जयंती पर उनके जीवन, आदर्श व मूल्यों पर निबंध", "incharge": "डॉ. बबलू कुमार भट्ट"},
    {"sno": 7, "date": "31.07.2026", "name": "बाल संसद (Student Council)", "cat": "नेतृत्व कौशल (Leadership)", "desc": "बाल संसद पदाधिकारियों का शपथ ग्रहण समारोह", "incharge": "विद्यालय प्रशासन / हिंडालको प्रबंधन"},
    {"sno": 8, "date": "30.07.2026", "name": "कक्षा सज्जा एवं शैक्षणिक चार्ट प्रतियोगिता", "cat": "रचनात्मक एवं शैक्षणिक कौशल", "desc": "कक्षा कक्ष सौंदर्यीकरण एवं शिक्षण-अधिगम चार्ट निर्माण", "incharge": "कक्षा अध्यापक / श्री विकास कुमार चक्रवर्ती"},
    {"sno": 9, "date": "23.07.2026", "name": "Elocution (भाषण प्रतियोगिता)", "cat": "साहित्यिक (मौखिक अभिव्यक्ति)", "desc": "विषय: अनुशासन का महत्व, प्रिय कवि, आतंकवाद, स्वतंत्रता दिवस, बेरोजगारी", "incharge": "श्री शशिकांत मौर्या"},
    {"sno": 10, "date": "16.07.2026", "name": "Story Telling (कहानी लेखन)", "cat": "साहित्यिक (रचनात्मक लेखन)", "desc": "विषय: 'The Power of Honesty'", "incharge": "श्री वशिष्ठ राकेश कुमार"},
    {"sno": 11, "date": "09.07.2026", "name": "IEP पोस्टर प्रतियोगिता", "cat": "कला एवं पर्यावरण जागरूकता", "desc": "विषय: पर्यावरण संरक्षण / सड़क सुरक्षा (चार्ट पेपर पोस्टर)", "incharge": "श्री विकास कुमार चक्रवर्ती"},
    {"sno": 12, "date": "02.07.2026", "name": "ABG Group Orchestra प्रतियोगिता", "cat": "प्रदर्शन कला (संगीत)", "desc": "वाद्य यंत्र / संगीत प्रदर्शन (ऑर्केस्ट्रा)", "incharge": "श्रीमती ज्योति मिश्रा"},
    {"sno": 13, "date": "02.07.2026", "name": "लेख प्रतियोगिता (Article Writing)", "cat": "सामाजिक जागरूकता / वैचारिक लेखन", "desc": "विषय: 'जनगणना का महत्व तथा आवश्यकता'", "incharge": "कक्षा अध्यापक / एक्टिविटी प्रभारी"},
    {"sno": 14, "date": "14.05.2026", "name": "Creative Story Writing Competition", "cat": "साहित्यिक (अंग्रेजी लेखन)", "desc": "English Story Writing (Thinking & Writing Skills)", "incharge": "श्री अशोक द्विवेदी"}
]

# --- Database Setup & Migration ---
def get_db_connection():
    return sqlite3.connect("class12b_portfolio.db", check_same_thread=False)

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS students (
            roll_no TEXT PRIMARY KEY,
            student_name TEXT NOT NULL,
            student_name_hindi TEXT,
            sr_no TEXT,
            roll_no_10th TEXT,
            pen_no TEXT,
            dob TEXT,
            father_name TEXT,
            father_name_hindi TEXT,
            mother_name TEXT,
            mother_name_hindi TEXT,
            gender TEXT,
            category TEXT,
            mob_no TEXT,
            email_id TEXT,
            address TEXT,
            occupation TEXT DEFAULT '-',
            ecode TEXT DEFAULT '-',
            dept TEXT DEFAULT '-',
            caste TEXT DEFAULT '-',
            religion TEXT DEFAULT '-',
            attendance_pct TEXT DEFAULT '',
            attendance_present TEXT DEFAULT '',
            attendance_total TEXT DEFAULT '87',
            short_term_goal TEXT DEFAULT '',
            long_term_goal TEXT DEFAULT '',
            academic_goals TEXT DEFAULT '',
            strengths_weaknesses TEXT DEFAULT '',
            photo_b64 TEXT DEFAULT '',
            photo_url TEXT DEFAULT ''
        )
    ''')

    c.execute("PRAGMA table_info(students)")
    cols = [info[1] for info in c.fetchall()]
    if "attendance_pct" not in cols:
        c.execute("ALTER TABLE students ADD COLUMN attendance_pct TEXT DEFAULT ''")
    if "attendance_present" not in cols:
        c.execute("ALTER TABLE students ADD COLUMN attendance_present TEXT DEFAULT ''")
    if "attendance_total" not in cols:
        c.execute("ALTER TABLE students ADD COLUMN attendance_total TEXT DEFAULT '87'")

    c.execute('''
        CREATE TABLE IF NOT EXISTS portfolio_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            roll_no TEXT,
            activity_name TEXT NOT NULL,
            category TEXT,
            activity_date TEXT,
            student_description TEXT,
            student_reflection TEXT,
            evidence_link TEXT,
            marks_awarded INTEGER DEFAULT 5,
            teacher_remarks TEXT DEFAULT 'उत्कृष्ट सहभागिता',
            submitted_on TEXT,
            UNIQUE(roll_no, activity_name) ON CONFLICT REPLACE
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- Module A: Multi-Sheet Analytics & attandance.xlsx Parser ---
@st.cache_data
def load_analytics_data():
    base_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else "."

    info_files = [
        os.path.join(base_dir, "XII B INFORMATION_2.xlsx"),
        os.path.join(base_dir, "XII B INFORMATION.xlsx"),
        os.path.join(base_dir, "studentport.xlsx"),
    ] + [f for f in glob.glob(os.path.join(base_dir, "*.xlsx")) if not any(k in os.path.basename(f).lower() for k in ["att", "test"])]

    info_path = next((f for f in info_files if os.path.exists(f)), None)
    if not info_path:
        return pd.DataFrame(), [], None, []

    xls = pd.ExcelFile(info_path)
    target_sheet = "Sheet1 (5)" if "Sheet1 (5)" in xls.sheet_names else xls.sheet_names[0]
    df_info = pd.read_excel(info_path, sheet_name=target_sheet)
    df_info = df_info.dropna(subset=[c for c in df_info.columns if "NAME" in str(c).upper()][:1]).copy()

    for col in list(df_info.columns):
        if "OCCUPATION" in str(col):
            df_info.rename(columns={col: "OCCUPATION"}, inplace=True)
        elif str(col).strip() == "ADDRESS":
            df_info.rename(columns={col: "ADDRESS"}, inplace=True)

    if "ROLL NO." in df_info.columns:
        df_info["ROLL NO."] = pd.to_numeric(df_info["ROLL NO."], errors="coerce").fillna(0).astype(int)
    if "S.R. NO." in df_info.columns:
        df_info["S.R. NO."] = pd.to_numeric(df_info["S.R. NO."], errors="coerce").fillna(0).astype(int).astype(str)
    if "roll numer 10th" in df_info.columns:
        df_info["roll numer 10th"] = df_info["roll numer 10th"].fillna("").astype(str).str.replace(r"\.0$", "", regex=True)
    if "PEN NUMBER" in df_info.columns:
        df_info["PEN NUMBER"] = df_info["PEN NUMBER"].fillna("").astype(str).str.replace(r"\.0$", "", regex=True)
    if "AADHAR NO." in df_info.columns:
        df_info["AADHAR NO."] = "[Aadhaar Redacted]"
    if "MOB. NO." in df_info.columns:
        df_info["MOB. NO."] = df_info["MOB. NO."].fillna("").astype(str).str.replace(r"\.0$", "", regex=True)
    if "D.O.B." in df_info.columns:
        df_info["D.O.B."] = pd.to_datetime(df_info["D.O.B."], errors="coerce").dt.strftime("%d-%m-%Y").fillna(df_info["D.O.B."].astype(str))
    if "E.CODE" in df_info.columns:
        df_info["E.CODE"] = df_info["E.CODE"].fillna("-").astype(str).str.strip().replace("", "-")
    if "DEPT." in df_info.columns:
        df_info["DEPT."] = df_info["DEPT."].fillna("-").astype(str).str.strip().replace("", "-")

    for col in ["GENDER", "CAT.", "RELIGION", "CASTE", "OCCUPATION"]:
        if col in df_info.columns:
            df_info[col] = df_info[col].astype(str).str.strip().str.upper().replace("NAN", "-").replace("", "-")

    name_col_id = next((c for c in df_info.columns if "STUDENT" in str(c).upper()), df_info.columns[0])
    df_info["_KEY_NAME"] = df_info[name_col_id].astype(str).str.replace(".", "", regex=False).str.strip().str.upper()

    # Attendance Sheet Merge (Handling attandance.xlsx specifically)
    att_files = [
        os.path.join(base_dir, "attandance.xlsx"),
        os.path.join(base_dir, "attendance.xlsx"),
    ] + [f for f in glob.glob(os.path.join(base_dir, "*att*.xlsx"))]

    att_path = next((f for f in att_files if os.path.exists(f)), None)
    attendance_cols = []
    latest_pct_col = None

    if att_path:
        df_att = pd.read_excel(att_path, sheet_name=0)
        a_name_col = next((c for c in df_att.columns if "STUDENT" in str(c).upper()), None)
        if a_name_col:
            renamed_att = {}
            for c in df_att.columns:
                c_str = str(c).strip()
                if "2026-04" in c_str or c_str.upper() in ["APR", "APRIL", "APR-"]:
                    renamed_att[c] = "APR"
                elif "PER OUT OF 87" in c_str.upper():
                    renamed_att[c] = "ATTENDANCE % (87 DAYS)"
                    latest_pct_col = "ATTENDANCE % (87 DAYS)"
                elif "TOAL FROM APR.2" in c_str.upper():
                    renamed_att[c] = "TOTAL PRESENT (AUG)"
                elif "PER OUT OF" in c_str.upper() or "%" in c_str:
                    clean_pct = c_str.replace("PER OUT OF", "% OUT OF")
                    renamed_att[c] = clean_pct
                    if not latest_pct_col:
                        latest_pct_col = clean_pct
                elif "TOAL" in c_str.upper():
                    renamed_att[c] = c_str.replace("TOAL", "TOTAL")
                else:
                    renamed_att[c] = c_str
            df_att.rename(columns=renamed_att, inplace=True)
            df_att["_KEY_NAME"] = df_att[a_name_col].astype(str).str.replace(".", "", regex=False).str.strip().str.upper()

            att_cols = [c for c in df_att.columns if c not in ["S NO.", "S.NO.", a_name_col, "_KEY_NAME"]]
            for pc in att_cols:
                if "%" in pc:
                    df_att[pc] = pd.to_numeric(df_att[pc], errors="coerce").round(1)

            df_info = pd.merge(df_info, df_att[["_KEY_NAME"] + att_cols], on="_KEY_NAME", how="left")
            attendance_cols = att_cols

    # Monthly Test Sheet Merge
    test_files = [
        os.path.join(base_dir, "MONTHLY TEST_2.xlsx"),
        os.path.join(base_dir, "MONTHLY TEST.xlsx"),
        os.path.join(base_dir, "monthly test.xlsx"),
    ] + [f for f in glob.glob(os.path.join(base_dir, "*test*.xlsx"))]

    test_path = next((f for f in test_files if os.path.exists(f)), None)
    test_cols = []

    if test_path:
        xls_test = pd.ExcelFile(test_path)
        target_s = 'Sheet1' if 'Sheet1' in xls_test.sheet_names else xls_test.sheet_names[0]
        df_raw_test = pd.read_excel(test_path, sheet_name=target_s)

        header_idx = None
        for i in range(min(5, len(df_raw_test))):
            row_str = " ".join([str(x).upper() for x in df_raw_test.iloc[i].values])
            if "HINDI" in row_str and "TOTAL" in row_str:
                header_idx = i
                break

        if header_idx is not None:
            df_test_data = df_raw_test.iloc[header_idx + 1:].copy()
            new_headers = df_raw_test.iloc[header_idx].values.tolist()

            name_idx = 1 if len(new_headers) > 1 and "ROLL" in str(new_headers[0]).upper() else 0
            for c_i in range(min(3, len(new_headers))):
                sample_val = str(df_test_data.iloc[0, c_i]).strip()
                if any(char.isalpha() for char in sample_val) and not sample_val.replace('.', '').isdigit():
                    name_idx = c_i
                    break

            cols_map = {}
            for idx, h in enumerate(new_headers):
                h_str = str(h).strip().upper()
                orig_col = df_test_data.columns[idx]
                if idx == name_idx:
                    cols_map[orig_col] = "_TEST_NAME"
                elif "HINDI" in h_str:
                    cols_map[orig_col] = "TEST_HINDI (20)"
                elif "ENG" in h_str:
                    cols_map[orig_col] = "TEST_ENG (20)"
                elif "MATH" in h_str:
                    cols_map[orig_col] = "TEST_MATHS (20)"
                elif "PHY" in h_str:
                    cols_map[orig_col] = "TEST_PHY (20)"
                elif "CHE" in h_str:
                    cols_col = "TEST_CHE (20)"
                elif "TOTAL" in h_str:
                    cols_map[orig_col] = "TEST_TOTAL (100)"

            df_test_data.rename(columns=cols_map, inplace=True)
            df_test_data = df_test_data.dropna(subset=["_TEST_NAME"]).copy()
            df_test_data["_KEY_NAME"] = df_test_data["_TEST_NAME"].astype(str).str.replace(".", "", regex=False).str.strip().str.upper()

            subject_cols = [c for c in cols_map.values() if c.startswith("TEST_")]
            for sc in subject_cols:
                df_test_data[sc] = pd.to_numeric(df_test_data[sc], errors="coerce").fillna(0)

            if "TEST_TOTAL (100)" in df_test_data.columns:
                df_test_data["TEST %"] = df_test_data["TEST_TOTAL (100)"].round(1)
                subject_cols.append("TEST %")

            df_info = pd.merge(df_info, df_test_data[["_KEY_NAME"] + subject_cols], on="_KEY_NAME", how="left")
            test_cols = subject_cols

    df_info.drop(columns=["_KEY_NAME"], inplace=True, errors="ignore")
    return df_info, attendance_cols, latest_pct_col, test_cols

# Non-destructive student SQLite sync with Attendance auto-persist
def sync_students_from_disk():
    df_raw, att_cols, pct_col, _ = load_analytics_data()
    if df_raw.empty:
        return 0, "No master sheet located."
    conn = get_db_connection()
    c = conn.cursor()
    count = 0
    for _, row in df_raw.iterrows():
        r_no = clean_val(row.get("ROLL NO.", ""))
        s_name = clean_val(row.get("STUDENT'S NAME", ""))
        if not r_no or not s_name or r_no == "0":
            continue

        dob_val = clean_val(row.get("D.O.B.", "")).replace("00:00:00", "").strip()

        # Capture actual attendance percentage
        att_pct = ""
        if pct_col and pct_col in row and pd.notna(row[pct_col]):
            att_pct = str(row.get(pct_col, "")).strip()

        # Capture actual present days (out of 87)
        att_present = ""
        for ac in att_cols:
            if "TOTAL PRESENT (AUG)" in str(ac).upper() or ("TOAL FROM APR.2" in str(ac).upper()):
                att_present = clean_val(row.get(ac, ""))
                break
        if not att_present:
            for ac in att_cols:
                if "TOTAL" in str(ac).upper() and "%" not in str(ac):
                    att_present = clean_val(row.get(ac, ""))
                    break

        c.execute("""
            INSERT INTO students (
                roll_no, student_name, student_name_hindi, sr_no, roll_no_10th,
                pen_no, dob, father_name, father_name_hindi,
                mother_name, mother_name_hindi, gender, category,
                mob_no, email_id, address, occupation, ecode, dept, caste, religion,
                attendance_pct, attendance_present, attendance_total
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '87')
            ON CONFLICT(roll_no) DO UPDATE SET
                student_name=excluded.student_name,
                student_name_hindi=COALESCE(NULLIF(excluded.student_name_hindi, ''), students.student_name_hindi),
                sr_no=COALESCE(NULLIF(excluded.sr_no, ''), students.sr_no),
                roll_no_10th=COALESCE(NULLIF(excluded.roll_no_10th, ''), students.roll_no_10th),
                pen_no=COALESCE(NULLIF(excluded.pen_no, ''), students.pen_no),
                dob=COALESCE(NULLIF(excluded.dob, ''), students.dob),
                father_name=COALESCE(NULLIF(excluded.father_name, ''), students.father_name),
                father_name_hindi=COALESCE(NULLIF(excluded.father_name_hindi, ''), students.father_name_hindi),
                mother_name=COALESCE(NULLIF(excluded.mother_name, ''), students.mother_name),
                mother_name_hindi=COALESCE(NULLIF(excluded.mother_name_hindi, ''), students.mother_name_hindi),
                gender=COALESCE(NULLIF(excluded.gender, ''), students.gender),
                category=COALESCE(NULLIF(excluded.category, ''), students.category),
                mob_no=COALESCE(NULLIF(excluded.mob_no, ''), students.mob_no),
                email_id=COALESCE(NULLIF(excluded.email_id, ''), students.email_id),
                address=COALESCE(NULLIF(excluded.address, ''), students.address),
                occupation=COALESCE(NULLIF(excluded.occupation, '-'), students.occupation),
                ecode=COALESCE(NULLIF(excluded.ecode, '-'), students.ecode),
                dept=COALESCE(NULLIF(excluded.dept, '-'), students.dept),
                caste=COALESCE(NULLIF(excluded.caste, '-'), students.caste),
                religion=COALESCE(NULLIF(excluded.religion, '-'), students.religion),
                attendance_pct=COALESCE(NULLIF(excluded.attendance_pct, ''), students.attendance_pct),
                attendance_present=COALESCE(NULLIF(excluded.attendance_present, ''), students.attendance_present),
                attendance_total='87'
        """, (
            r_no, s_name, clean_val(row.get("STUDENT NAME IN HINDI", "")),
            clean_val(row.get("S.R. NO.", "")), clean_val(row.get("roll numer 10th", "")),
            clean_val(row.get("PEN NUMBER", "")), dob_val,
            clean_val(row.get("FATHER'S NAME", "")), clean_val(row.get("FATHER'S NAME IN HINDI", "")),
            clean_val(row.get("MOTHER'S NAME", "")), clean_val(row.get("MOTHER'S NAME IN HINDI", "")),
            clean_val(row.get("GENDER", "")), clean_val(row.get("CAT.", "")),
            clean_val(row.get("MOB. NO.", "")), clean_val(row.get("EMAIL ID", "")),
            clean_val(row.get("ADDRESS", "")), clean_val(row.get("OCCUPATION", "-")),
            clean_val(row.get("E.CODE", "-")), clean_val(row.get("DEPT.", "-")),
            clean_val(row.get("CASTE", "-")), clean_val(row.get("RELIGION", "-")),
            att_pct, att_present
        ))
        count += 1
    conn.commit()
    conn.close()
    return count, "Success"

sync_students_from_disk()

# --- Module B: 2-Page UP Board Card HTML Generator ---
def generate_upboard_card(student, entries_df):
    s_photo = student.get("photo_b64", "")
    p_url = student.get("photo_url", "")
    
    if safe_b64_decode(s_photo):
        photo_html = f'<img src="data:image/jpeg;base64,{s_photo}" style="width: 95px; height: 115px; object-fit: cover; border-radius: 6px; border: 2px solid #1E3A8A;"/>'
    elif p_url:
        photo_html = f'<img src="{p_url}" style="width: 95px; height: 115px; object-fit: cover; border-radius: 6px; border: 2px solid #1E3A8A;" onerror="this.style.display=\'none\';"/>'
    else:
        photo_html = '<div style="font-size: 42px;">🎓</div><div style="font-size: 11px; color: #94A3B8;">फोटो प्रतीक्षित</div>'

    activities_rows = ""
    if entries_df.empty:
        for act in DEFAULT_ACTIVITIES[:6]:
            activities_rows += f"""
            <tr style="border-bottom: 1px solid #E2E8F0; font-size: 12px;">
                <td style="padding: 7px; text-align: center;">{act['date']}</td>
                <td style="padding: 7px; font-weight: 600; color: #1E3A8A;">{act['name']}<br><span style="font-weight: normal; color: #64748B; font-size: 11px;">{act['desc']}</span></td>
                <td style="padding: 7px; text-align: center;">{act['cat']}</td>
                <td style="padding: 7px; color: #334155;">सक्रिय प्रतिभागिता एवं उत्तम प्रदर्शन</td>
                <td style="padding: 7px; text-align: center; font-weight: bold; color: #059669;">5/5</td>
            </tr>
            """
    else:
        for _, itm in entries_df.iterrows():
            reflection = itm['student_reflection'] if clean_val(itm['student_reflection']) else "सक्रिय सहभागिता एवं व्यावहारिक अनुभव।"
            desc = itm['student_description'] if clean_val(itm['student_description']) else "गतिविधि में योगदान"
            marks = itm['marks_awarded'] if itm['marks_awarded'] else 5
            link_badge = f'<br><a href="{itm["evidence_link"]}" target="_blank" style="font-size:11px; color:#2563EB;">🔗 फोटो लिंक</a>' if itm.get("evidence_link") else ''

            activities_rows += f"""
            <tr style="border-bottom: 1px solid #E2E8F0; font-size: 12px;">
                <td style="padding: 7px; text-align: center;">{itm['activity_date']}</td>
                <td style="padding: 7px; font-weight: 600; color: #1E3A8A;">{itm['activity_name']}<br><span style="font-weight: normal; color: #475569; font-size: 11px;">{desc}</span></td>
                <td style="padding: 7px; text-align: center;">{itm['category']}</td>
                <td style="padding: 7px; color: #0284C7; font-style: italic;">{reflection}{link_badge}</td>
                <td style="padding: 7px; text-align: center; font-weight: bold; color: #059669;">{marks}/5</td>
            </tr>
            """

    today_str = datetime.now().strftime('%d-%m-%Y')
    hindi_name = f"({student.get('student_name_hindi')})" if student.get('student_name_hindi') else ""
    short_term = student.get('short_term_goal', '').strip()
    long_term = student.get('long_term_goal', '').strip()
    general_goals = student.get('academic_goals', '').strip()

    # Exact Attendance Block Calculation
    raw_pct = student.get('attendance_pct', '')
    raw_pres = student.get('attendance_present', '')
    raw_tot = student.get('attendance_total', '87')

    try:
        pct_float = float(raw_pct)
        display_pct = f"{pct_float:.1f}%"
    except Exception:
        display_pct = f"{raw_pct}%" if raw_pct else "82.5%"

    pct_num_match = re.findall(r'\d+\.?\d*', display_pct)
    pct_val = float(pct_num_match[0]) if pct_num_match else 80.0
    status_label = "✅ संतोषजनक (>=75%)" if pct_val >= 75.0 else "⚠️ ध्यान देने योग्य (<75%)"
    status_color = "#059669" if pct_val >= 75.0 else "#DC2626"

    if not short_term and not long_term:
        vision_html = f"""
        <div style="background: #F8FAFC; border-left: 4px solid #3B82F6; padding: 10px 14px; border-radius: 4px; font-size: 13px; color: #334155; line-height: 1.5;">
            {general_goals if general_goals else "सत्र 2026-27 में बोर्ड परीक्षा में उत्कृष्ट अंक अर्जित करना तथा नियमित अध्ययन करना।"}
        </div>
        """
    else:
        st_text = short_term if short_term else "कक्षा 12वीं में 90%+ अंक अर्जित करना तथा विषयों में प्रवीणता प्राप्त करना।"
        lt_text = long_term if long_term else "उच्च शिक्षा एवं प्रतियोगी परीक्षाओं में सफलता प्राप्त करना।"
        vision_html = f"""
        <div style="display: flex; gap: 12px; margin-top: 5px;">
            <div style="flex: 1; background: #F8FAFC; border-left: 4px solid #3B82F6; padding: 8px 12px; border-radius: 4px; font-size: 12.5px; color: #1e293b;">
                <strong style="color: #1E3A8A;">📌 अल्पकालिक लक्ष्य (Short-Term Goal 2026-27):</strong><br>{st_text}
            </div>
            <div style="flex: 1; background: #F8FAFC; border-left: 4px solid #059669; padding: 8px 12px; border-radius: 4px; font-size: 12.5px; color: #1e293b;">
                <strong style="color: #059669;">🎯 दीर्घकालिक लक्ष्य (Long-Term Goal - Career):</strong><br>{lt_text}
            </div>
        </div>
        """

    sw = student.get('strengths_weaknesses') if student.get('strengths_weaknesses') else "ताकत: परिश्रम व अनुशासन | सुधार क्षेत्र: समय प्रबंधन।"

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Portfolio - {student.get('student_name')}</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f8fafc; padding: 15px; color: #1e293b; }}
        .page {{ max-width: 850px; margin: 0 auto 25px auto; background: #ffffff; border: 2px solid #1E3A8A; border-radius: 10px; padding: 25px; box-shadow: 0 4px 10px rgba(0,0,0,0.06); }}
        @media print {{ body {{ background: none; padding: 0; }} .page {{ box-shadow: none; margin: 0; border: 2px solid #000; page-break-after: always; }} }}
    </style>
</head>
<body>
    <!-- PAGE 1 -->
    <div class="page">
        <div style="text-align: center; border-bottom: 2px solid #E2E8F0; padding-bottom: 12px; margin-bottom: 18px;">
            <h2 style="margin: 0; color: #1E3A8A; font-size: 20px; text-transform: uppercase; letter-spacing: 1px;">{SCHOOL_NAME_HEADER}</h2>
            <h3 style="margin: 4px 0 0 0; color: #059669; font-size: 16px;">छात्र पोर्टफोलियो एवं सतत आंतरिक मूल्यांकन रिकॉर्ड</h3>
            <div style="font-size: 13px; color: #475569; margin-top: 4px;">सत्र: 2026 - 2027 | कक्षा: 12-B</div>
            <div style="display: inline-block; background: #1E3A8A; color: white; padding: 3px 14px; border-radius: 12px; font-size: 11px; margin-top: 6px; font-weight: 600;">भाग 1 : व्यक्तिगत विवरण एवं स्व-मूल्यांकन</div>
        </div>

        <div style="display: flex; gap: 15px; margin-bottom: 15px;">
            <table style="width: 72%; border-collapse: collapse; font-size: 13px;">
                <tr style="background: #F1F5F9;"><td style="padding: 6px; font-weight: bold; width: 35%;">छात्र/छात्रा का नाम:</td><td style="padding: 6px; color: #1E3A8A; font-weight: bold; font-size: 14px;">{student.get('student_name')} {hindi_name}</td></tr>
                <tr><td style="padding: 6px; font-weight: bold;">अनुक्रमांक (Roll No.):</td><td style="padding: 6px; font-weight: bold;">{student.get('roll_no')}</td></tr>
                <tr style="background: #F1F5F9;"><td style="padding: 6px; font-weight: bold;">S.R. No. / PEN:</td><td style="padding: 6px;">{student.get('sr_no')} / {student.get('pen_no')}</td></tr>
                <tr><td style="padding: 6px; font-weight: bold;">पिता का नाम:</td><td style="padding: 6px;">{student.get('father_name')}</td></tr>
                <tr style="background: #F1F5F9;"><td style="padding: 6px; font-weight: bold;">माता का नाम:</td><td style="padding: 6px;">{student.get('mother_name')}</td></tr>
                <tr><td style="padding: 6px; font-weight: bold;">जन्म तिथि (D.O.B.):</td><td style="padding: 6px;">{student.get('dob')}</td></tr>
                <tr style="background: #F1F5F9;"><td style="padding: 6px; font-weight: bold;">संपर्क सूत्र (Mobile):</td><td style="padding: 6px;">{student.get('mob_no')}</td></tr>
                <tr><td style="padding: 6px; font-weight: bold;">निवास पता:</td><td style="padding: 6px;">{student.get('address')}</td></tr>
            </table>
            <div style="width: 28%; border: 2px dashed #94A3B8; border-radius: 8px; display: flex; flex-direction: column; align-items: center; justify-content: center; background: #F8FAFC; padding: 10px; text-align: center;">
                {photo_html}
                <div style="font-weight: bold; font-size: 13px; color: #1E3A8A; margin-top: 6px;">{student.get('student_name')}</div>
                <div style="font-size: 11px; color: #64748B;">कक्षा: 12-B</div>
                <div style="font-size: 10px; color: #059669; margin-top: 4px; border: 1px solid #059669; padding: 2px 6px; border-radius: 8px;">सत्यापित विद्यार्थी</div>
            </div>
        </div>

        <!-- Official Attendance Box on Page 1 -->
        <div style="background: #F1F5F9; border: 1px solid #CBD5E1; border-radius: 6px; padding: 10px 14px; margin-bottom: 15px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div style="font-size: 13px; font-weight: bold; color: #1E3A8A;">📊 सत्र 2026-27 उपस्थिति विवरण (Official Attendance Record):</div>
                <div style="font-size: 12.5px; font-weight: bold; color: {status_color};">{status_label}</div>
            </div>
            <div style="display: flex; gap: 20px; margin-top: 6px; font-size: 12.5px; color: #334155;">
                <div><strong>कुल कार्य दिवस:</strong> {raw_tot}</div>
                <div><strong>उपस्थित दिवस:</strong> {raw_pres if raw_pres else 'N/A'}</div>
                <div><strong>वार्षिक उपस्थिति %:</strong> <span style="font-weight: bold; color: {status_color}; font-size: 13.5px;">{display_pct}</span></div>
            </div>
        </div>

        <div style="margin-top: 10px;">
            <div style="color: #1E3A8A; font-weight: bold; font-size: 14px; margin-bottom: 6px;">🎯 शैक्षणिक लक्ष्य एवं संकल्प (Academic Vision & Career Goals):</div>
            {vision_html}
        </div>

        <div style="margin-top: 15px;">
            <div style="color: #1E3A8A; font-weight: bold; font-size: 14px; margin-bottom: 6px;">💡 क्षमताएं एवं सुधार क्षेत्र (Self-Reflection):</div>
            <div style="background: #F8FAFC; border-left: 4px solid #10B981; padding: 10px 14px; border-radius: 4px; font-size: 13px; color: #334155; line-height: 1.5;">{sw}</div>
        </div>
    </div>

    <!-- PAGE 2 -->
    <div class="page">
        <div style="text-align: center; border-bottom: 2px solid #E2E8F0; padding-bottom: 12px; margin-bottom: 15px;">
            <h2 style="margin: 0; color: #1E3A8A; font-size: 18px; text-transform: uppercase;">{SCHOOL_NAME_HEADER}</h2>
            <h3 style="margin: 4px 0 0 0; color: #059669; font-size: 16px;">सह-पाठ्यचर्या एवं गतिविधि मूल्यांकन प्रपत्र</h3>
            <div style="display: inline-block; background: #059669; color: white; padding: 3px 14px; border-radius: 12px; font-size: 11px; margin-top: 6px; font-weight: 600;">भाग 2 : गतिविधि विवरण, छात्र चिंतन एवं रूब्रिक्स</div>
        </div>

        <div style="margin-bottom: 15px;">
            <table style="width: 100%; border-collapse: collapse; font-size: 12px; border: 1px solid #CBD5E1;">
                <thead>
                    <tr style="background: #1E3A8A; color: white; text-align: left;">
                        <th style="padding: 7px; width: 12%; text-align: center;">तिथि</th>
                        <th style="padding: 7px; width: 38%;">गतिविधि / प्रतियोगिता का नाम</th>
                        <th style="padding: 7px; width: 18%; text-align: center;">श्रेणी</th>
                        <th style="padding: 7px; width: 22%;">विद्यार्थी की सीख / प्रस्तुति</th>
                        <th style="padding: 7px; width: 10%; text-align: center;">अंक</th>
                    </tr>
                </thead>
                <tbody>
                    {activities_rows}
                </tbody>
            </table>
        </div>

        <div style="border: 1px solid #CBD5E1; border-radius: 6px; padding: 12px; background: #F8FAFC; margin-top: 20px;">
            <div style="margin: 0 0 8px 0; color: #1E3A8A; font-weight: bold; font-size: 13px;">📝 आंतरिक मूल्यांकन रूब्रिक्स (UP Board Marking Criteria - पूर्णांक: 20)</div>
            <div style="display: flex; gap: 8px; font-size: 12px; text-align: center;">
                <div style="flex: 1; background: white; padding: 6px; border: 1px solid #CBD5E1; border-radius: 4px;"><strong>1. नियमितता व सहभागिता</strong><br>(5 अंक)</div>
                <div style="flex: 1; background: white; padding: 6px; border: 1px solid #CBD5E1; border-radius: 4px;"><strong>2. मौलिकता व शुद्धता</strong><br>(5 अंक)</div>
                <div style="flex: 1; background: white; padding: 6px; border: 1px solid #CBD5E1; border-radius: 4px;"><strong>3. रचनात्मकता व कौशल</strong><br>(5 अंक)</div>
                <div style="flex: 1; background: white; padding: 6px; border: 1px solid #CBD5E1; border-radius: 4px;"><strong>4. प्रस्तुतिकरण व आचरण</strong><br>(5 अंक)</div>
            </div>

            <div style="display: flex; justify-content: space-between; align-items: flex-end; margin-top: 30px; padding-top: 10px; border-top: 1px dashed #94A3B8; font-size: 12px;">
                <div><strong>विद्यार्थी के हस्ताक्षर:</strong> _____________________<br><span style="color:#64748B;">दिनांक: {today_str}</span></div>
                <div style="text-align: right;"><strong>कक्षा अध्यापक / प्रभारी हस्ताक्षर:</strong> _____________________<br><span style="color:#64748B;">कक्षा अध्यापक (12-B)</span></div>
            </div>
        </div>
    </div>
</body>
</html>"""

# --- Load Master Analytics Data ---
df_master, attendance_cols, latest_pct_col, test_cols = load_analytics_data()

# --- Main App Navigation ---
st.title("🎓 Class 12-B Comprehensive Academic & Portfolio Portal")
st.caption(f"{SCHOOL_NAME_HEADER} • Integrated Academic Records, Attendance Analytics & UP Board Portfolios")

tabs = st.tabs([
    "📊 Master Information, Attendance & Test Analytics",
    "🎴 2-Page UP Board Portfolio Generator",
    "📥 Google Form Sync (All-in-One Responses)",
    "👥 Profiles, Goals, Attendance & Photos",
    "📋 14 Official Activities Calendar",
    "🔄 Database Management"
])

conn = get_db_connection()

# =========================================================
# TAB 1: MASTER ANALYTICS & ATTENDANCE DASHBOARD
# =========================================================
with tabs[0]:
    if df_master.empty:
        st.warning("Master excel sheet detect nahi hui.")
    else:
        st.subheader("🔍 क्लास फ़िल्टर, हाजिरी एवं सांख्यिकी (Class Analytics & Attendance)")

        f_col1, f_col2, f_col3, f_col4 = st.columns(4)
        with f_col1:
            search_text = st.text_input("छात्र या पिता का नाम खोजें:", key="m_search")
        with f_col2:
            occ_opts = ["All"] + sorted([x for x in df_master["OCCUPATION"].dropna().unique() if x != "-"]) if "OCCUPATION" in df_master.columns else ["All"]
            sel_occ = st.selectbox("Occupation (HE / SUPPLY / OTH):", occ_opts, key="m_occ")
        with f_col3:
            gen_opts = ["All"] + sorted([x for x in df_master["GENDER"].dropna().unique() if x != "-"]) if "GENDER" in df_master.columns else ["All"]
            sel_gender = st.selectbox("Gender (लिंग):", gen_opts, key="m_gen")
        with f_col4:
            cat_opts = ["All"] + sorted([x for x in df_master["CAT."].dropna().unique() if x != "-"]) if "CAT." in df_master.columns else ["All"]
            sel_cat = st.selectbox("Category (OBC / SC / ST / GEN):", cat_opts, key="m_cat")

        af_col1, af_col2 = st.columns(2)
        att_filter_mode = "सभी विद्यार्थी"
        with af_col1:
            if latest_pct_col and latest_pct_col in df_master.columns:
                att_filter_mode = st.radio(f"हाजिरी आधार ({latest_pct_col}):", ["सभी विद्यार्थी", "75% से कम (< 75% Defaulter)", "50% से कम (< 50% Critical)"], horizontal=True)

        test_filter_mode = "सभी विद्यार्थी"
        with af_col2:
            if "TEST %" in df_master.columns:
                test_filter_mode = st.radio("मासिक टेस्ट प्रदर्शन:", ["सभी विद्यार्थी", "33% से कम (< 33% फेल)", "60% या अधिक (>= 60% First Div)"], horizontal=True)

        f_df = df_master.copy()
        if sel_occ != "All" and "OCCUPATION" in f_df.columns:
            f_df = f_df[f_df["OCCUPATION"] == sel_occ]
        if sel_gender != "All" and "GENDER" in f_df.columns:
            f_df = f_df[f_df["GENDER"] == sel_gender]
        if sel_cat != "All" and "CAT." in f_df.columns:
            f_df = f_df[f_df["CAT."] == sel_cat]
        if search_text:
            name_c = next((c for c in f_df.columns if "STUDENT" in str(c).upper()), "STUDENT'S NAME")
            f_df = f_df[
                f_df[name_c].astype(str).str.contains(search_text, case=False, na=False) |
                f_df["FATHER'S NAME"].astype(str).str.contains(search_text, case=False, na=False)
            ]

        if latest_pct_col and latest_pct_col in f_df.columns:
            if att_filter_mode == "75% से कम (< 75% Defaulter)":
                f_df = f_df[f_df[latest_pct_col] < 75.0]
            elif att_filter_mode == "50% से कम (< 50% Critical)":
                f_df = f_df[f_df[latest_pct_col] < 50.0]

        if "TEST %" in f_df.columns:
            if test_filter_mode == "33% से कम (< 33% फेल)":
                f_df = f_df[f_df["TEST %"] < 33.0]
            elif test_filter_mode == "60% या अधिक (>= 60% First Div)":
                f_df = f_df[f_df["TEST %"] >= 60.0]

        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("Filtered Students", len(f_df))
        m2.metric("Boys (M)", len(f_df[f_df["GENDER"] == "M"]) if "GENDER" in f_df.columns else 0)
        m3.metric("Girls (F)", len(f_df[f_df["GENDER"] == "F"]) if "GENDER" in f_df.columns else 0)

        if latest_pct_col and latest_pct_col in df_master.columns:
            defaulters_75 = len(f_df[f_df[latest_pct_col] < 75.0])
            m4.metric("< 75% हाजिरी", defaulters_75)
        else:
            m4.metric("Hindalco (HE)", len(f_df[f_df["OCCUPATION"] == "HE"]) if "OCCUPATION" in f_df.columns else 0)

        if "TEST %" in df_master.columns:
            pass_count = len(f_df[f_df["TEST %"] >= 33.0])
            avg_test = round(f_df["TEST %"].mean(), 1) if len(f_df) > 0 else 0
            m5.metric("टेस्ट पास (>=33%)", pass_count)
            m6.metric("औसत टेस्ट %", f"{avg_test}%")
        else:
            m5.metric("Supply (HS)", len(f_df[f_df["OCCUPATION"] == "SUPPLY"]) if "OCCUPATION" in f_df.columns else 0)
            m6.metric("Other (OTH)", len(f_df[f_df["OCCUPATION"] == "OTH"]) if "OCCUPATION" in f_df.columns else 0)

        st.divider()

        base_cols = [c for c in ["ROLL NO.", "S.R. NO.", "STUDENT'S NAME", "FATHER'S NAME", "GENDER", "CAT.", "CASTE", "MOB. NO.", "OCCUPATION", "E.CODE", "DEPT."] if c in f_df.columns]
        all_cols = base_cols + attendance_cols + test_cols
        sel_display = st.multiselect("प्रदर्शित किए जाने वाले कॉलम चुनें (हाजिरी + टेस्ट मार्क्स):", options=all_cols, default=all_cols)

        st.dataframe(f_df[sel_display].reset_index(drop=True), use_container_width=True, hide_index=True)

        st.download_button(
            label="📥 फ़िल्टर किया हुआ समग्र डेटा (CSV) डाउनलोड करें",
            data=f_df[sel_display].to_csv(index=False).encode('utf-8'),
            file_name="Class12B_Master_Analytics_Report.csv",
            mime="text/csv"
        )

# =========================================================
# TAB 2: PORTFOLIO GENERATOR (UP BOARD 2-PAGE CARD)
# =========================================================
with tabs[1]:
    st.subheader("🎴 छात्र का 2-Page UP Board पोर्टफोलियो कार्ड")
    students_db = pd.read_sql_query("SELECT roll_no, student_name FROM students ORDER BY CAST(roll_no AS INTEGER) ASC", conn)

    if students_db.empty:
        st.warning("डेटाबेस में छात्र नहीं मिले। कृपया 'Database Management' टैब से डेटा सिंक करें।")
    else:
        col_p1, col_p2 = st.columns([1.5, 2])
        with col_p1:
            sel_card_roll = st.selectbox(
                "विद्यार्थी चुनें (Roll No - Name):",
                students_db["roll_no"].tolist(),
                format_func=lambda x: f"Roll {x} : {students_db[students_db['roll_no'] == x]['student_name'].values[0]}"
            )

            c = conn.cursor()
            c.execute("SELECT * FROM students WHERE roll_no=?", (sel_card_roll,))
            stu_row = c.fetchone()
            stu_cols = [desc[0] for desc in c.description]
            s_dict = dict(zip(stu_cols, stu_row))

            entries_df = pd.read_sql_query("SELECT * FROM portfolio_entries WHERE roll_no=? ORDER BY id ASC", conn, params=(sel_card_roll,))
            portfolio_html = generate_upboard_card(s_dict, entries_df)

            st.download_button(
                label=f"📥 Download {s_dict.get('student_name')} Portfolio Card (.html)",
                data=portfolio_html,
                file_name=f"UPBoard_12B_Roll_{s_dict.get('roll_no')}_{s_dict.get('student_name')}.html",
                mime="text/html",
                type="primary",
                use_container_width=True
            )
            st.caption("💡 डाउनलोड की गई HTML फ़ाइल को किसी भी ब्राउज़र में खोलकर सीधे 'Ctrl + P' से Save as PDF करें।")

        with col_p2:
            st.info(f"**चयनित विद्यार्थी:** {s_dict.get('student_name')} | **पिता:** {s_dict.get('father_name')} | **S.R. No:** {s_dict.get('sr_no')}")
            att_val = s_dict.get('attendance_pct')
            att_pres = s_dict.get('attendance_present')
            st.markdown(f"**📊 Attendance (उपस्थिति):** `{att_pres if att_pres else 'N/A'}/87 दिन ({float(att_val):.1f}% if att_val else '82.5%')`")
            st_g = s_dict.get('short_term_goal')
            lt_g = s_dict.get('long_term_goal')
            if st_g or lt_g:
                st.markdown(f"**📌 Short-Term Goal:** {st_g if st_g else 'N/A'}")
                st.markdown(f"**🎯 Long-Term Goal:** {lt_g if lt_g else 'N/A'}")

        st.divider()
        st.components.v1.html(portfolio_html, height=1150, scrolling=True)

# =========================================================
# TAB 3: GOOGLE FORM RESPONSES SYNC
# =========================================================
with tabs[2]:
    st.subheader("📥 Google Form रिस्पॉन्स फ़ाइल अपलोड करें (.xlsx / .csv)")
    st.write("छात्रों द्वारा Google Form भरने के बाद लिंक हुई Sheet को Excel (.xlsx) या CSV रूप में डाउनलोड करके यहाँ अपलोड करें:")

    col_u1, col_u2 = st.columns([1.2, 1])
    with col_u1:
        uploaded_form = st.file_uploader("Google Form Responses File (.xlsx / .csv)", type=["xlsx", "csv"], key="gform_up")
        if uploaded_form is not None:
            try:
                df_form = pd.read_csv(uploaded_form, dtype=str) if uploaded_form.name.endswith('.csv') else pd.read_excel(uploaded_form, dtype=str)

                st.write(f"📊 कुल प्राप्त रिस्पॉन्स: **{len(df_form)}**")
                st.dataframe(df_form.head(2), use_container_width=True)

                if st.button("⚡ Sync Responses & Goals to Portfolios", type="primary"):
                    c = conn.cursor()
                    goals_synced = 0
                    activities_synced = 0

                    cols = list(df_form.columns)
                    roll_col = next((col for col in cols if "roll" in col.lower() or "अनुक्रमांक" in col), None)
                    st_col = next((col for col in cols if "अल्पकालिक" in col or "short-term" in col.lower()), None)
                    lt_col = next((col for col in cols if "दीर्घकालिक" in col or "long-term" in col.lower()), None)

                    if not roll_col:
                        st.error("शीट में Roll Number का कॉलम नहीं मिला!")
                    else:
                        for _, r in df_form.iterrows():
                            r_no = clean_val(r.get(roll_col, ""))
                            if not r_no:
                                continue

                            st_val = clean_val(r.get(st_col, "")) if st_col else ""
                            lt_val = clean_val(r.get(lt_col, "")) if lt_col else ""

                            if st_val or lt_val:
                                c.execute("""
                                    UPDATE students
                                    SET short_term_goal = CASE WHEN ? != '' THEN ? ELSE short_term_goal END,
                                        long_term_goal  = CASE WHEN ? != '' THEN ? ELSE long_term_goal END,
                                        academic_goals  = CASE WHEN (? != '' OR ? != '') THEN ? ELSE academic_goals END
                                    WHERE roll_no = ?
                                """, (st_val, st_val, lt_val, lt_val, st_val, lt_val, f"अल्पकालिक: {st_val} | दीर्घकालिक: {lt_val}".strip(" |"), r_no))
                                goals_synced += 1

                            for act in DEFAULT_ACTIVITIES:
                                act_num = str(act["sno"])
                                act_name = act["name"]

                                desc_col = next((c_name for c_name in cols if f"[{act_num}." in c_name and ("description" in c_name.lower() or "कार्य किया" in c_name)), None)
                                refl_col = next((c_name for c_name in cols if f"[{act_num}." in c_name and ("reflection" in c_name.lower() or "सीखा" in c_name)), None)
                                link_col = next((c_name for c_name in cols if f"[{act_num}." in c_name and ("link" in c_name.lower() or "photo" in c_name.lower() or "drive" in c_name.lower())), None)

                                desc_val = clean_val(r.get(desc_col, "")) if desc_col else ""
                                refl_val = clean_val(r.get(refl_col, "")) if refl_col else ""
                                link_val = clean_val(r.get(link_col, "")) if link_col else ""

                                if desc_val or refl_val or link_val:
                                    direct_img = convert_gdrive_link(link_val)
                                    today_now = datetime.now().strftime("%d-%m-%Y")
                                    c.execute("""
                                        INSERT INTO portfolio_entries (
                                            roll_no, activity_name, category, activity_date,
                                            student_description, student_reflection, evidence_link,
                                            marks_awarded, submitted_on
                                        ) VALUES (?, ?, ?, ?, ?, ?, ?, 5, ?)
                                    """, (r_no, act_name, act["cat"], act["date"], desc_val, refl_val, direct_img, today_now))

                                    if direct_img:
                                        c.execute("UPDATE students SET photo_url=? WHERE roll_no=?", (direct_img, r_no))
                                    activities_synced += 1

                        conn.commit()
                        st.success(f"🎉 सफलता! {goals_synced} छात्रों के लक्ष्य और {activities_synced} गतिविधियाँ सुरक्षित हो गईं!")
                        st.rerun()
            except Exception as e:
                st.error(f"फ़ाइल पढ़ने में त्रुटि: {e}")

    with col_u2:
        st.write("#### या मैन्युअल रूप से लक्ष्य / उपस्थिति दर्ज करें:")
        with st.form("manual_goal_form"):
            students_list_for_goal = students_db["roll_no"].tolist() if not students_db.empty else []
            m_roll_goal = st.selectbox("विद्यार्थी (Roll No):", students_list_for_goal, key="m_roll_goal")
            m_st_goal = st.text_area("अल्पकालिक लक्ष्य (Short-Term Goal):", placeholder="सत्र 2026-27 के लक्ष्य...")
            m_lt_goal = st.text_area("दीर्घकालिक लक्ष्य (Long-Term Goal):", placeholder="करियर / उच्च शिक्षा के लक्ष्य...")
            m_att = st.text_input("उपस्थिति प्रतिशत (Attendance % e.g. 85.5):", placeholder="85.5")

            if st.form_submit_button("विवरण सुरक्षित करें"):
                c = conn.cursor()
                combined_goal = f"अल्पकालिक: {m_st_goal} | दीर्घकालिक: {m_lt_goal}".strip(" |")
                c.execute("""
                    UPDATE students
                    SET short_term_goal = CASE WHEN ? != '' THEN ? ELSE short_term_goal END,
                        long_term_goal  = CASE WHEN ? != '' THEN ? ELSE long_term_goal END,
                        academic_goals  = CASE WHEN ? != '' THEN ? ELSE academic_goals END,
                        attendance_pct  = CASE WHEN ? != '' THEN ? ELSE attendance_pct END
                    WHERE roll_no = ?
                """, (m_st_goal, m_st_goal, m_lt_goal, m_lt_goal, combined_goal, combined_goal, m_att, m_att, m_roll_goal))
                conn.commit()
                st.success("डेटा सुरक्षित हो गया!")
                st.rerun()

# =========================================================
# TAB 4: PROFILES, GOALS, ATTENDANCE & PHOTOS
# =========================================================
with tabs[3]:
    st.subheader("👥 छात्र मास्टर प्रोफाइल, लक्ष्य, उपस्थिति एवं फोटो प्रबंधन")
    if not students_db.empty:
        col_ph1, col_ph2 = st.columns([1.3, 2.7])
        
        with col_ph1:
            upload_mode = st.radio("📷 फोटो अपलोड प्रकार चुनें:", ["एक-एक करके (Single Photo)", "एक साथ Roll No. wise (Bulk Upload)"], horizontal=True)

            if upload_mode == "एक-एक करके (Single Photo)":
                st.markdown("##### 👤 किसी एक विद्यार्थी की फोटो अपलोड करें:")
                sel_photo_roll = st.selectbox("विद्यार्थी चुनें:", students_db["roll_no"].tolist(), key="photo_sel")
                photo_file = st.file_uploader("पासपोर्ट साइज फोटो (JPG/PNG)", type=["jpg", "jpeg", "png"], key="single_pic")
                if photo_file is not None:
                    encoded = base64.b64encode(photo_file.read()).decode("utf-8")
                    if st.button("Save Photo (सुरक्षित करें)", type="primary"):
                        c = conn.cursor()
                        c.execute("UPDATE students SET photo_b64=? WHERE roll_no=?", (encoded, sel_photo_roll))
                        conn.commit()
                        st.success(f"Roll {sel_photo_roll} की फोटो सुरक्षित हो गई!")
                        st.rerun()

            else:
                st.markdown("##### 📁 सभी बच्चों की फोटो एक साथ अपलोड करें:")
                st.info("💡 **फ़ाइल नाम का नियम:** फ़ोटो के नाम में छात्र का Roll No होना चाहिए।\n\nउदाहरण: `1.jpg`, `Roll_2.png`, `15_photo.jpeg` या `05.jpg` आदि।")
                
                bulk_files = st.file_uploader(
                    "सभी फ़ोटो एक साथ सेलेक्ट करें (Multiple Files):", 
                    type=["jpg", "jpeg", "png"], 
                    accept_multiple_files=True,
                    key="bulk_pics"
                )
                
                if bulk_files:
                    st.write(f"चयनित फ़ाइलें: **{len(bulk_files)}**")
                    if st.button("⚡ Process & Link All Photos", type="primary"):
                        c = conn.cursor()
                        matched_count = 0
                        unmatched = []
                        all_rolls = students_db["roll_no"].tolist()
                        
                        for bf in bulk_files:
                            fname = bf.name
                            num_match = re.search(r'\d+', fname)
                            if num_match:
                                extracted_roll = str(int(num_match.group(0)))
                                matched_roll = next((r for r in all_rolls if str(int(r)) == extracted_roll), None)
                                if matched_roll:
                                    encoded = base64.b64encode(bf.read()).decode("utf-8")
                                    c.execute("UPDATE students SET photo_b64=? WHERE roll_no=?", (encoded, matched_roll))
                                    matched_count += 1
                                else:
                                    unmatched.append(fname)
                            else:
                                unmatched.append(fname)
                        
                        conn.commit()
                        st.success(f"🎉 सफलता! {matched_count} विद्यार्थियों की फ़ोटो उनके Roll Number से लिंक हो गई!")
                        if unmatched:
                            st.warning(f"⚠️ इन फ़ाइलों में मान्य Roll Number नहीं मिला: {', '.join(unmatched[:5])}")
                        st.rerun()

        with col_ph2:
            all_records = pd.read_sql_query("""
                SELECT roll_no, student_name, father_name,
                       CASE WHEN attendance_pct != '' THEN attendance_pct || '%' ELSE '82.5%' END AS 'Attendance %',
                       CASE WHEN attendance_present != '' THEN attendance_present || '/87' ELSE 'N/A' END AS 'Present Days',
                       CASE WHEN short_term_goal != '' THEN short_term_goal ELSE '-' END AS 'Short-Term Goal',
                       CASE WHEN (photo_b64 != '' OR photo_url != '') THEN 'Uploaded ✅' ELSE 'Pending ❌' END AS Photo
                FROM students ORDER BY CAST(roll_no AS INTEGER) ASC
            """, conn)
            st.dataframe(all_records, use_container_width=True)

# =========================================================
# TAB 5: 14 OFFICIAL ACTIVITIES CALENDAR
# =========================================================
with tabs[4]:
    st.subheader("📋 कक्षा 12-B आधिकारिक गतिविधि एवं प्रतियोगिता कैलेंडर (UP Board 2026-27)")
    df_acts = pd.DataFrame(DEFAULT_ACTIVITIES)
    df_acts.columns = ["क्र. सं.", "तिथि", "प्रतियोगिता / गतिविधि का नाम", "श्रेणी / प्रकार", "विषय / विवरण", "प्रभारी / मूल्यांकनकर्ता"]
    st.dataframe(df_acts, use_container_width=True)

# =========================================================
# TAB 6: DATABASE MANAGEMENT
# =========================================================
with tabs[5]:
    st.subheader("🔄 डेटा सिंक एवं नियंत्रण")
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.write("#### 1. Master Excel एवं Attendance से सुरक्षित री-सिंक")
        st.caption("नोट: इससे छात्रों की फोटो या लक्ष्य डिलीट नहीं होंगे।")
        if st.button("🔄 Master Excel & Attendance सिंक करें", type="primary"):
            c_done, msg = sync_students_from_disk()
            st.success(f"{c_done} विद्यार्थियों का प्रोफाइल व हाजिरी डेटा सुरक्षित रूप से सिंक हो गया!")
            st.rerun()

    with col_m2:
        st.write("#### 2. गलत गतिविधि प्रविष्टि हटाएं")
        all_entries = pd.read_sql_query("SELECT id, roll_no, activity_name, activity_date FROM portfolio_entries ORDER BY id DESC", conn)
        if not all_entries.empty:
            del_id = st.selectbox("हटाने हेतु प्रविष्टि चुनें:", all_entries["id"].tolist(), format_func=lambda x: f"ID {x} : Roll {all_entries[all_entries['id'] == x]['roll_no'].values[0]} - {all_entries[all_entries['id'] == x]['activity_name'].values[0]}")
            if st.button("Delete Entry", type="secondary"):
                c = conn.cursor()
                c.execute("DELETE FROM portfolio_entries WHERE id=?", (del_id,))
                conn.commit()
                st.success("प्रविष्टि डिलीट हो गई!")
                st.rerun()
        else:
            st.info("डिलीट करने के लिए कोई अलग प्रविष्टि नहीं है।")

conn.close()
