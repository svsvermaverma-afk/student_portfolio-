import streamlit as st
import sqlite3
import pandas as pd
import os
import re
from datetime import datetime

# --- Page Config ---
st.set_page_config(page_title="UP Board Class 12-B Auto-Sync Portfolio", page_icon="🎓", layout="wide")

def clean_val(val):
    if pd.isna(val) or val is None:
        return ""
    val_str = str(val).strip()
    if val_str.lower() in ["nan", "none", "nat", "<na>", "null"]:
        return ""
    if re.match(r'^-?\d+\.0+$', val_str):
        val_str = val_str.split('.')[0]
    return val_str

# Google Drive लिंक को डायरेक्ट इमेज URL में बदलने का फ़ंक्शन
def convert_gdrive_link(url):
    if not url or not isinstance(url, str):
        return ""
    url = url.strip()
    # drive.google.com/file/d/FILE_ID/view...
    match1 = re.search(r'/d/([a-zA-Z0-9_-]+)', url)
    if match1:
        file_id = match1.group(1)
        return f"https://lh3.googleusercontent.com/d/{file_id}"
    # id=FILE_ID
    match2 = re.search(r'id=([a-zA-Z0-9_-]+)', url)
    if match2:
        file_id = match2.group(1)
        return f"https://lh3.googleusercontent.com/d/{file_id}"
    return url

# --- Database Setup ---
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
            academic_goals TEXT DEFAULT '',
            strengths_weaknesses TEXT DEFAULT '',
            photo_url TEXT DEFAULT ''
        )
    ''')
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
            submitted_on TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS app_config (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- Sync Local Profile Excel ---
def find_excel_file():
    for root, dirs, files in os.walk("."):
        for f in files:
            if f.lower() in ["studentport.xlsx", "studentport.xls"]:
                return os.path.join(root, f)
    return None

def sync_profiles_from_excel():
    f = find_excel_file()
    if not f:
        return 0
    df = pd.read_excel(f, dtype=str)
    conn = get_db_connection()
    c = conn.cursor()
    count = 0
    for _, row in df.iterrows():
        r_no = clean_val(row.get("ROLL NO.", ""))
        s_name = clean_val(row.get("STUDENT'S NAME", ""))
        if not r_no or not s_name or r_no == "0":
            continue
        dob_val = clean_val(row.get("D.O.B.", "")).replace("00:00:00", "").strip()
        c.execute("""
            INSERT OR IGNORE INTO students (
                roll_no, student_name, student_name_hindi, sr_no, roll_no_10th, 
                pen_no, dob, father_name, father_name_hindi, 
                mother_name, mother_name_hindi, gender, category, 
                mob_no, email_id, address
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            r_no, s_name, clean_val(row.get("STUDENT NAME IN HINDI", "")),
            clean_val(row.get("S.R. NO.", "")),
            clean_val(row.get("roll numer 10th", "")),
            clean_val(row.get("PEN NUMBER", "")),
            dob_val,
            clean_val(row.get("FATHER'S NAME", "")),
            clean_val(row.get("FATHER'S NAME IN HINDI", "")),
            clean_val(row.get("MOTHER'S NAME", "")),
            clean_val(row.get("MOTHER'S NAME IN HINDI", "")),
            clean_val(row.get("GENDER", "")),
            clean_val(row.get("CAT.", "")),
            clean_val(row.get("MOB. NO.", "")),
            clean_val(row.get("EMAIL ID", "")),
            clean_val(row.get("ADDRESS", ""))
        ))
        count += 1
    conn.commit()
    conn.close()
    return count

sync_profiles_from_excel()

# --- Live Google Sheet Auto-Sync Function ---
def sync_google_sheet_data(sheet_csv_url):
    if not sheet_csv_url:
        return 0, "URL नहीं मिला"
    try:
        df_sheet = pd.read_csv(sheet_csv_url, dtype=str)
        conn = get_db_connection()
        c = conn.cursor()
        
        # Reset entries and refresh live
        c.execute("DELETE FROM portfolio_entries")
        
        imported = 0
        for _, r in df_sheet.iterrows():
            # Flexible column detection
            r_no = ""
            s_act = ""
            desc = ""
            refl = ""
            photo = ""
            
            for col in df_sheet.columns:
                c_low = col.lower()
                if "roll" in c_low or "अनुक्रमांक" in c_low:
                    r_no = clean_val(r[col])
                elif "activity" in c_low or "गतिविधि" in c_low or "प्रतियोगिता" in c_low:
                    s_act = clean_val(r[col])
                elif "desc" in c_low or "विवरण" in c_low or "कार्य" in c_low:
                    desc = clean_val(r[col])
                elif "refl" in c_low or "सीख" in c_low or "चिंतन" in c_low:
                    refl = clean_val(r[col])
                elif "photo" in c_low or "फोटो" in c_low or "चित्र" in c_low or "upload" in c_low or "drive" in c_low:
                    photo = clean_val(r[col])

            if r_no and s_act:
                direct_img = convert_gdrive_link(photo)
                today_str = datetime.now().strftime("%d.%m.%Y")
                
                c.execute("""
                    INSERT INTO portfolio_entries (
                        roll_no, activity_name, category, activity_date,
                        student_description, student_reflection, evidence_link, submitted_on
                    ) VALUES (?, ?, 'सह-पाठ्यचर्या', ?, ?, ?, ?, ?)
                """, (r_no, s_act, today_str, desc, refl, direct_img, today_str))
                
                # Agar photo mili to student profile me bhi save kar do
                if direct_img:
                    c.execute("UPDATE students SET photo_url=? WHERE roll_no=?", (direct_img, r_no))
                    
                imported += 1
                
        conn.commit()
        conn.close()
        return imported, "Success"
    except Exception as e:
        return 0, str(e)

# --- Fetch Saved Google Sheet URL ---
conn = get_db_connection()
c = conn.cursor()
c.execute("SELECT value FROM app_config WHERE key='sheet_csv_url'")
saved_cfg = c.fetchone()
saved_url = saved_cfg[0] if saved_cfg else ""
conn.close()

# Auto-sync in background if URL is available
if saved_url:
    sync_google_sheet_data(saved_url)

# --- 2-Page UP Board Card HTML Generator ---
def render_portfolio_card(student, entries_df):
    p_url = student.get("photo_url", "")
    if p_url:
        photo_html = f'<img src="{p_url}" style="width: 95px; height: 115px; object-fit: cover; border-radius: 6px; border: 2px solid #1E3A8A;" onerror="this.style.display=\'none\';"/>'
    else:
        photo_html = '<div style="font-size: 42px;">🎓</div><div style="font-size: 11px; color: #94A3B8;">फोटो प्रतीक्षित</div>'

    rows_html = ""
    if entries_df.empty:
        rows_html = """<tr><td colspan="5" style="text-align:center; padding:12px; color:#64748B;">गूगल फॉर्म से कोई प्रविष्टि प्राप्त नहीं हुई है।</td></tr>"""
    else:
        for _, itm in entries_df.iterrows():
            img_thumb = f'<br><a href="{itm["evidence_link"]}" target="_blank" style="font-size:11px; color:#2563EB;">🔗 फोटो देखें</a>' if itm["evidence_link"] else ''
            rows_html += f"""
            <tr style="border-bottom: 1px solid #E2E8F0; font-size: 12px;">
                <td style="padding: 7px; text-align: center;">{itm['activity_date']}</td>
                <td style="padding: 7px; font-weight: 600; color: #1E3A8A;">{itm['activity_name']}<br><span style="font-weight: normal; color: #475569; font-size: 11px;">{itm['student_description']}</span></td>
                <td style="padding: 7px; text-align: center;">{itm['category']}</td>
                <td style="padding: 7px; color: #0284C7; font-style: italic;">{itm['student_reflection']}{img_thumb}</td>
                <td style="padding: 7px; text-align: center; font-weight: bold; color: #059669;">{itm['marks_awarded']}/5</td>
            </tr>
            """

    today_str = datetime.now().strftime('%d-%m-%Y')
    hindi_name = f"({student.get('student_name_hindi')})" if student.get('student_name_hindi') else ""

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
    <div class="page">
        <div style="text-align: center; border-bottom: 2px solid #E2E8F0; padding-bottom: 12px; margin-bottom: 18px;">
            <h2 style="margin: 0; color: #1E3A8A; font-size: 22px; text-transform: uppercase;">माध्यमिक शिक्षा परिषद्, उत्तर प्रदेश (UP BOARD)</h2>
            <h3 style="margin: 4px 0 0 0; color: #059669; font-size: 17px;">छात्र पोर्टफोलियो एवं सतत आंतरिक मूल्यांकन रिकॉर्ड</h3>
            <div style="font-size: 13px; color: #475569; margin-top: 4px;">सत्र: 2026 - 2027 | कक्षा: 12-B</div>
            <div style="display: inline-block; background: #1E3A8A; color: white; padding: 3px 14px; border-radius: 12px; font-size: 11px; margin-top: 6px; font-weight: 600;">भाग 1 : व्यक्तिगत विवरण एवं छात्र परिचय</div>
        </div>

        <div style="display: flex; gap: 15px; margin-bottom: 20px;">
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
                <div style="font-size: 11px; color: #64748B;">कक्षा: 12-B (UP Board)</div>
                <div style="font-size: 10px; color: #059669; margin-top: 4px; border: 1px solid #059669; padding: 2px 6px; border-radius: 8px;">सत्यापित विद्यार्थी</div>
            </div>
        </div>
        <div style="margin-top: 15px;">
            <div style="color: #1E3A8A; font-weight: bold; font-size: 14px; margin-bottom: 6px;">🎯 शैक्षणिक लक्ष्य एवं संकल्प (Academic Vision):</div>
            <div style="background: #F8FAFC; border-left: 4px solid #3B82F6; padding: 10px 14px; border-radius: 4px; font-size: 13px; color: #334155;">सत्र 2026-27 में बोर्ड परीक्षा में उत्कृष्ट प्रदर्शन करना तथा समयबद्ध अध्ययन करना।</div>
        </div>
    </div>

    <div class="page">
        <div style="text-align: center; border-bottom: 2px solid #E2E8F0; padding-bottom: 12px; margin-bottom: 15px;">
            <h3 style="margin: 0; color: #1E3A8A; font-size: 19px; text-transform: uppercase;">सह-पाठ्यचर्या एवं गतिविधि मूल्यांकन प्रपत्र</h3>
            <div style="display: inline-block; background: #059669; color: white; padding: 3px 14px; border-radius: 12px; font-size: 11px; margin-top: 6px; font-weight: 600;">भाग 2 : गूगल फॉर्म आधारित गतिविधि विवरण व रूब्रिक्स</div>
        </div>

        <div style="margin-bottom: 15px;">
            <table style="width: 100%; border-collapse: collapse; font-size: 12px; border: 1px solid #CBD5E1;">
                <thead>
                    <tr style="background: #1E3A8A; color: white; text-align: left;">
                        <th style="padding: 7px; width: 12%; text-align: center;">तिथि</th>
                        <th style="padding: 7px; width: 38%;">गतिविधि / प्रतियोगिता</th>
                        <th style="padding: 7px; width: 15%; text-align: center;">श्रेणी</th>
                        <th style="padding: 7px; width: 25%;">विद्यार्थी की प्रस्तुति व सीख</th>
                        <th style="padding: 7px; width: 10%; text-align: center;">अंक</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
        </div>

        <div style="border: 1px solid #CBD5E1; border-radius: 6px; padding: 12px; background: #F8FAFC; margin-top: 25px;">
            <div style="margin: 0 0 8px 0; color: #1E3A8A; font-weight: bold; font-size: 13px;">📝 आंतरिक मूल्यांकन रूब्रिक्स (पूर्णांक: 20)</div>
            <div style="display: flex; gap: 8px; font-size: 12px; text-align: center;">
                <div style="flex: 1; background: white; padding: 6px; border: 1px solid #CBD5E1; border-radius: 4px;"><strong>1. नियमितता</strong><br>(5 अंक)</div>
                <div style="flex: 1; background: white; padding: 6px; border: 1px solid #CBD5E1; border-radius: 4px;"><strong>2. मौलिकता</strong><br>(5 अंक)</div>
                <div style="flex: 1; background: white; padding: 6px; border: 1px solid #CBD5E1; border-radius: 4px;"><strong>3. रचनात्मकता</strong><br>(5 अंक)</div>
                <div style="flex: 1; background: white; padding: 6px; border: 1px solid #CBD5E1; border-radius: 4px;"><strong>4. प्रस्तुतिकरण</strong><br>(5 अंक)</div>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: flex-end; margin-top: 30px; padding-top: 10px; border-top: 1px dashed #94A3B8; font-size: 12px;">
                <div><strong>विद्यार्थी के हस्ताक्षर:</strong> _____________________<br><span style="color:#64748B;">दिनांक: {today_str}</span></div>
                <div style="text-align: right;"><strong>कक्षा अध्यापक हस्ताक्षर:</strong> _____________________<br><span style="color:#64748B;">कक्षा अध्यापक (12-B)</span></div>
            </div>
        </div>
    </div>
</body>
</html>"""

# =========================================================
# MAIN APP (SINGLE CONSOLE - NO LOGIN)
# =========================================================
st.title("🎓 UP Board Class 12-B Live Portfolio Console")
st.caption("Auto-Sync Mode: Google Sheet & Google Form Integration")

conn = get_db_connection()
tab_main, tab_sync, tab_students = st.tabs([
    "🎴 Generate & Download Portfolio", 
    "🔗 Google Sheet Auto-Sync Setup", 
    "👥 Student Master Records"
])

# --- TAB 1: CARD VIEW & DOWNLOAD ---
with tab_main:
    st.subheader("छात्र का 2-Page UP Board पोर्टफोलियो")
    students_df = pd.read_sql_query("SELECT roll_no, student_name FROM students ORDER BY CAST(roll_no AS INTEGER) ASC", conn)
    
    if students_df.empty:
        st.warning("कोई छात्र रिकॉर्ड नहीं मिला।")
    else:
        col_c1, col_c2 = st.columns([1.5, 2])
        with col_c1:
            sel_roll = st.selectbox(
                "विद्यार्थी चुनें (Roll No - Name):",
                students_df["roll_no"].tolist(),
                format_func=lambda x: f"Roll {x} : {students_df[students_df['roll_no']==x]['student_name'].values[0]}"
            )
            
            c = conn.cursor()
            c.execute("SELECT * FROM students WHERE roll_no=?", (sel_roll,))
            stu_row = c.fetchone()
            stu_cols = [d[0] for d in c.description]
            s_dict = dict(zip(stu_cols, stu_row))
            
            entries = pd.read_sql_query("SELECT * FROM portfolio_entries WHERE roll_no=? ORDER BY id DESC", conn, params=(sel_roll,))
            card_html = render_portfolio_card(s_dict, entries)
            
            st.download_button(
                label=f"📥 Download {s_dict.get('student_name')} Card (.html)",
                data=card_html,
                file_name=f"Portfolio_Roll_{s_dict.get('roll_no')}_{s_dict.get('student_name')}.html",
                mime="text/html",
                type="primary",
                use_container_width=True
            )
        with col_c2:
            st.info(f"**नाम:** {s_dict.get('student_name')} | **S.R. No:** {s_dict.get('sr_no')} | **कुल गतिविधियां:** {len(entries)}")

        st.divider()
        st.components.v1.html(card_html, height=1150, scrolling=True)

# --- TAB 2: AUTO-SYNC CONFIGURATION ---
with tab_sync:
    st.subheader("🔗 Google Form / Sheet Auto-Sync Setup")
    st.write("Google Sheet से **'Publish to web' (CSV Link)** यहाँ डालें, डेटा अपने-आप सिंक होता रहेगा:")
    
    new_url = st.text_input("Google Sheet CSV URL:", value=saved_url, placeholder="https://docs.google.com/spreadsheets/d/e/.../pub?gid=0&single=true&output=csv")
    
    col_s1, col_s2 = st.columns([1, 2])
    with col_s1:
        if st.button("Save & Sync Now (तुरंत सिंक करें)", type="primary"):
            if new_url:
                c = conn.cursor()
                c.execute("INSERT OR REPLACE INTO app_config (key, value) VALUES ('sheet_csv_url', ?)", (new_url,))
                conn.commit()
                cnt, msg = sync_google_sheet_data(new_url)
                if cnt > 0:
                    st.success(f"🎉 {cnt} रिस्पॉन्स सफलतापूर्वक सिंक हो गए!")
                    st.rerun()
                else:
                    st.error(f"सिंक असफल: {msg}")
            else:
                st.warning("कृपया मान्य URL दर्ज करें।")
                
    with col_s2:
        if st.button("🔄 Force Re-Sync (ताजा डेटा लाएं)"):
            if saved_url:
                cnt, msg = sync_google_sheet_data(saved_url)
                st.success(f"{cnt} प्रविष्टियां अपडेट हो गईं!")
                st.rerun()

# --- TAB 3: ALL RECORDS ---
with tab_students:
    st.subheader("Class 12-B Master Database")
    all_recs = pd.read_sql_query("SELECT roll_no, sr_no, student_name, father_name, mob_no, photo_url FROM students ORDER BY CAST(roll_no AS INTEGER) ASC", conn)
    st.dataframe(all_recs, use_container_width=True)
    if not all_recs.empty:
        st.download_button("📥 Export Master CSV", all_recs.to_csv(index=False).encode('utf-8'), "Students_Master.csv", "text/csv")

conn.close()
