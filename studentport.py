import streamlit as st
import sqlite3
import pandas as pd
import os
import re
import base64
from datetime import datetime

# --- Page Config ---
st.set_page_config(page_title="UP Board Class 12-B Portfolio Console", page_icon="🎓", layout="wide")


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


# Pre-defined 14 Official School Activities (UP Board Calendar 2026-27)
DEFAULT_ACTIVITIES = [
    {"sno": 1, "date": "27.08.2026", "name": "Tata Building India School Essay Competition", "cat": "साहित्यिक (निबंध)",
     "desc": "2047 तक भारत को विश्व का सबसे विकसित देश बनाने के लिए मैं यह पांच कार्य करूंगा/करूंगी",
     "incharge": "श्री विकास कुमार चक्रवर्ती / कक्षा अध्यापक"},
    {"sno": 2, "date": "27.08.2026", "name": "रंगोली प्रतियोगिता", "cat": "कला एवं संस्कृति",
     "desc": "रंगोली निर्माण (समूह गतिविधि - प्रति समूह 4 विद्यार्थी)", "incharge": "श्रीमती साधना भरद्वाज"},
    {"sno": 3, "date": "27.08.2026", "name": "मेहंदी प्रतियोगिता", "cat": "कला एवं संस्कृति",
     "desc": "मेहंदी आलेखन (रचनात्मकता, मौलिकता व बारीकी)", "incharge": "श्रीमती पूजा सिंह"},
    {"sno": 4, "date": "20.08.2026", "name": "राखी निर्माण प्रतियोगिता", "cat": "क्राफ्ट एवं रचनात्मक कौशल",
     "desc": "आकर्षक व सुंदर राखी निर्माण (राखी प्रदर्शनी हेतु)",
     "incharge": "श्री शशिकांत सर / श्री विकास कुमार चक्रवर्ती"},
    {"sno": 5, "date": "13.08.2026", "name": "चित्रकला प्रतियोगिता", "cat": "दृश्य कला (Drawing)",
     "desc": "सरदार वल्लभभाई पटेल के जीवन एवं आदर्शों पर आधारित चित्रकला", "incharge": "डॉ. संतोष कुमार तिवारी"},
    {"sno": 6, "date": "06.08.2026", "name": "निबंध प्रतियोगिता", "cat": "साहित्यिक (निबंध)",
     "desc": "सरदार वल्लभभाई पटेल की 150वीं जयंती पर उनके जीवन, आदर्श व मूल्यों पर निबंध",
     "incharge": "डॉ. बबलू कुमार भट्ट"},
    {"sno": 7, "date": "31.07.2026", "name": "बाल संसद (Student Council)", "cat": "नेतृत्व कौशल (Leadership)",
     "desc": "बाल संसद पदाधिकारियों का शपथ ग्रहण समारोह", "incharge": "विद्यालय प्रशासन / हिंडालको प्रबंधन"},
    {"sno": 8, "date": "30.07.2026", "name": "कक्षा सज्जा एवं शैक्षणिक चार्ट प्रतियोगिता",
     "cat": "रचनात्मक एवं शैक्षणिक कौशल", "desc": "कक्षा कक्ष सौंदर्यीकरण एवं शिक्षण-अधिगम चार्ट निर्माण",
     "incharge": "कक्षा अध्यापक / श्री विकास कुमार चक्रवर्ती"},
    {"sno": 9, "date": "23.07.2026", "name": "Elocution (भाषण प्रतियोगिता)", "cat": "साहित्यिक (मौखिक अभिव्यक्ति)",
     "desc": "विषय: अनुशासन का महत्व, प्रिय कवि, आतंकवाद, स्वतंत्रता दिवस, बेरोजगारी",
     "incharge": "श्री शशिकांत मौर्या"},
    {"sno": 10, "date": "16.07.2026", "name": "Story Telling (कहानी लेखन)", "cat": "साहित्यिक (रचनात्मक लेखन)",
     "desc": "विषय: 'The Power of Honesty'", "incharge": "श्री वशिष्ठ राकेश कुमार"},
    {"sno": 11, "date": "09.07.2026", "name": "IEP पोस्टर प्रतियोगिता", "cat": "कला एवं पर्यावरण जागरूकता",
     "desc": "विषय: पर्यावरण संरक्षण / सड़क सुरक्षा (चार्ट पेपर पोस्टर)", "incharge": "श्री विकास कुमार चक्रवर्ती"},
    {"sno": 12, "date": "02.07.2026", "name": "ABG Group Orchestra प्रतियोगिता", "cat": "प्रदर्शन कला (संगीत)",
     "desc": "वाद्य यंत्र / संगीत प्रदर्शन (ऑर्केस्ट्रा)", "incharge": "श्रीमती ज्योति मिश्रा"},
    {"sno": 13, "date": "02.07.2026", "name": "लेख प्रतियोगिता (Article Writing)",
     "cat": "सामाजिक जागरूकता / वैचारिक लेखन", "desc": "विषय: 'जनगणना का महत्व तथा आवश्यकता'",
     "incharge": "कक्षा अध्यापक / एक्टिविटी प्रभारी"},
    {"sno": 14, "date": "14.05.2026", "name": "Creative Story Writing Competition", "cat": "साहित्यिक (अंग्रेजी लेखन)",
     "desc": "English Story Writing (Thinking & Writing Skills)", "incharge": "श्री अशोक द्विवेदी"}
]


def init_db():
    conn = get_db_connection()
    c = conn.cursor()

    # Students Table
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
            short_term_goal TEXT DEFAULT '',
            long_term_goal TEXT DEFAULT '',
            academic_goals TEXT DEFAULT '',
            strengths_weaknesses TEXT DEFAULT '',
            photo_b64 TEXT DEFAULT ''
        )
    ''')

    # Migration check for existing databases
    c.execute("PRAGMA table_info(students)")
    cols = [info[1] for info in c.fetchall()]
    if "short_term_goal" not in cols:
        c.execute("ALTER TABLE students ADD COLUMN short_term_goal TEXT DEFAULT ''")
    if "long_term_goal" not in cols:
        c.execute("ALTER TABLE students ADD COLUMN long_term_goal TEXT DEFAULT ''")

    # Submissions / Form Responses Table
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


# Deep File Locator for Excel
def find_excel_file():
    for root, dirs, files in os.walk("."):
        for f in files:
            if f.lower() in ["studentport.xlsx", "studentport.xls"]:
                return os.path.join(root, f)
    return None


# Non-destructive Sync Students Profile from Excel
def sync_students_excel():
    target_file = find_excel_file()
    if not target_file:
        return 0, "studentport.xlsx file नहीं मिली।"
    try:
        df_excel = pd.read_excel(target_file, dtype=str)
        conn = get_db_connection()
        c = conn.cursor()

        count = 0
        for _, row in df_excel.iterrows():
            r_no = clean_val(row.get("ROLL NO.", ""))
            s_name = clean_val(row.get("STUDENT'S NAME", ""))
            if not r_no or not s_name or r_no == "0" or s_name.lower() in ["nan", "nat"]:
                continue

            dob_val = clean_val(row.get("D.O.B.", "")).replace("00:00:00", "").strip()

            # Insert if not exists, or update basic demographic info WITHOUT overwriting photos or goals
            c.execute("""
                INSERT INTO students (
                    roll_no, student_name, student_name_hindi, sr_no, roll_no_10th, 
                    pen_no, dob, father_name, father_name_hindi, 
                    mother_name, mother_name_hindi, gender, category, 
                    mob_no, email_id, address
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    address=COALESCE(NULLIF(excluded.address, ''), students.address)
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
        return count, "Success"
    except Exception as e:
        return 0, str(e)


init_db()

# Safe initial sync: populate if empty
conn = get_db_connection()
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM students")
if c.fetchone()[0] == 0:
    sync_students_excel()
conn.close()


# --- Helper: Generate Official 2-Page UP Board Card ---
def generate_upboard_card(student, entries_df):
    s_photo = student.get("photo_b64", "")
    if safe_b64_decode(s_photo):
        photo_html = f'<img src="data:image/jpeg;base64,{s_photo}" style="width: 95px; height: 115px; object-fit: cover; border-radius: 6px; border: 2px solid #1E3A8A;"/>'
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

            activities_rows += f"""
            <tr style="border-bottom: 1px solid #E2E8F0; font-size: 12px;">
                <td style="padding: 7px; text-align: center;">{itm['activity_date']}</td>
                <td style="padding: 7px; font-weight: 600; color: #1E3A8A;">{itm['activity_name']}<br><span style="font-weight: normal; color: #475569; font-size: 11px;">{desc}</span></td>
                <td style="padding: 7px; text-align: center;">{itm['category']}</td>
                <td style="padding: 7px; color: #0284C7; font-style: italic;">{reflection}</td>
                <td style="padding: 7px; text-align: center; font-weight: bold; color: #059669;">{marks}/5</td>
            </tr>
            """

    today_str = datetime.now().strftime('%d-%m-%Y')
    hindi_name = f"({student.get('student_name_hindi')})" if student.get('student_name_hindi') else ""

    short_term = student.get('short_term_goal', '').strip()
    long_term = student.get('long_term_goal', '').strip()
    general_goals = student.get('academic_goals', '').strip()

    if not short_term and not long_term:
        vision_html = f"""
        <div style="background: #F8FAFC; border-left: 4px solid #3B82F6; padding: 10px 14px; border-radius: 4px; font-size: 13px; color: #334155; line-height: 1.5;">
            {general_goals if general_goals else "सत्र 2026-27 में बोर्ड परीक्षा में उत्कृष्ट अंक अर्जित करना तथा नियमित अध्ययन करना।"}
        </div>
        """
    else:
        st_text = short_term if short_term else "कक्षा 12वीं में 90%+ अंक अर्जित करना तथा विषयों में प्रवीणता प्राप्त करना।"
        lt_text = long_term if long_term else "उच्च शिक्षा एवं प्रतियोगी परीक्षाओं (Engineering/CUET/NDA आदि) में सफलता प्राप्त करना।"
        vision_html = f"""
        <div style="display: flex; gap: 12px; margin-top: 5px;">
            <div style="flex: 1; background: #F8FAFC; border-left: 4px solid #3B82F6; padding: 8px 12px; border-radius: 4px; font-size: 12.5px; color: #1e293b;">
                <strong style="color: #1E3A8A;">📌 अल्पकालिक लक्ष्य (Short-Term Goal 2026-27):</strong><br>
                {st_text}
            </div>
            <div style="flex: 1; background: #F8FAFC; border-left: 4px solid #059669; padding: 8px 12px; border-radius: 4px; font-size: 12.5px; color: #1e293b;">
                <strong style="color: #059669;">🎯 दीर्घकालिक लक्ष्य (Long-Term Goal - Career):</strong><br>
                {lt_text}
            </div>
        </div>
        """

    sw = student.get('strengths_weaknesses') if student.get('strengths_weaknesses') else "ताकत: परिश्रम व अनुशासन | सुधार क्षेत्र: समय प्रबंधन।"

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Portfolio - {student.get('student_name')}</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f8fafc; padding: 15px; color: #1e293b; }}
        .page {{ max-width: 850px; margin: 0 auto 25px auto; background: #ffffff; border: 2px solid #1E3A8A; border-radius: 10px; padding: 25px; box-shadow: 0 4px 10px rgba(0,0,0,0.06); }}
        @media print {{
            body {{ background: none; padding: 0; }}
            .page {{ box-shadow: none; margin: 0; border: 2px solid #000; page-break-after: always; }}
        }}
    </style>
</head>
<body>
    <!-- ================= PAGE 1 ================= -->
    <div class="page">
        <div style="text-align: center; border-bottom: 2px solid #E2E8F0; padding-bottom: 12px; margin-bottom: 18px;">
            <h2 style="margin: 0; color: #1E3A8A; font-size: 22px; text-transform: uppercase; letter-spacing: 1px;">माध्यमिक शिक्षा परिषद्, उत्तर प्रदेश (UP BOARD)</h2>
            <h3 style="margin: 4px 0 0 0; color: #059669; font-size: 17px;">छात्र पोर्टफोलियो एवं सतत आंतरिक मूल्यांकन रिकॉर्ड</h3>
            <div style="font-size: 13px; color: #475569; margin-top: 4px;">सत्र: 2026 - 2027 | कक्षा: 12-B</div>
            <div style="display: inline-block; background: #1E3A8A; color: white; padding: 3px 14px; border-radius: 12px; font-size: 11px; margin-top: 6px; font-weight: 600;">भाग 1 : व्यक्तिगत विवरण एवं स्व-मूल्यांकन</div>
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
                <div style="font-size: 11px; color: #64748B;">कक्षा: 12-B</div>
                <div style="font-size: 10px; color: #059669; margin-top: 4px; border: 1px solid #059669; padding: 2px 6px; border-radius: 8px;">सत्यापित विद्यार्थी</div>
            </div>
        </div>

        <div style="margin-top: 15px;">
            <div style="color: #1E3A8A; font-weight: bold; font-size: 14px; margin-bottom: 6px;">🎯 शैक्षणिक लक्ष्य एवं संकल्प (Academic Vision & Career Goals):</div>
            {vision_html}
        </div>

        <div style="margin-top: 15px;">
            <div style="color: #1E3A8A; font-weight: bold; font-size: 14px; margin-bottom: 6px;">💡 क्षमताएं एवं सुधार क्षेत्र (Self-Reflection):</div>
            <div style="background: #F8FAFC; border-left: 4px solid #10B981; padding: 10px 14px; border-radius: 4px; font-size: 13px; color: #334155; line-height: 1.5;">{sw}</div>
        </div>
    </div>

    <!-- ================= PAGE 2 ================= -->
    <div class="page">
        <div style="text-align: center; border-bottom: 2px solid #E2E8F0; padding-bottom: 12px; margin-bottom: 15px;">
            <h3 style="margin: 0; color: #1E3A8A; font-size: 19px; text-transform: uppercase;">सह-पाठ्यचर्या एवं गतिविधि मूल्यांकन प्रपत्र</h3>
            <div style="display: inline-block; background: #059669; color: white; padding: 3px 14px; border-radius: 12px; font-size: 11px; margin-top: 6px; font-weight: 600;">भाग 2 : गतिविधि विवरण, छात्र चिंतन एवं रूब्रिक्स</div>
        </div>

        <div style="margin-bottom: 15px;">
            <div style="color: #1E3A8A; font-weight: bold; font-size: 13px; margin-bottom: 8px;">📋 सत्र 2026-27 में संपादित प्रमुख गतिविधियां एवं प्रतियोगिताएं:</div>
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
                <div>
                    <div><strong>विद्यार्थी के हस्ताक्षर:</strong> _____________________</div>
                    <div style="color: #64748B; font-size: 11px; margin-top: 4px;">दिनांक: {today_str}</div>
                </div>
                <div style="text-align: right;">
                    <div><strong>कक्षा अध्यापक / प्रभारी हस्ताक्षर:</strong> _____________________</div>
                    <div style="color: #64748B; font-size: 11px; margin-top: 4px;">कक्षा अध्यापक (12-B)</div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>"""
    return html_content


# ==========================================
# TEACHER CENTRAL CONSOLE
# ==========================================
st.title("🎓 UP Board Class 12-B Master Portfolio Portal")
st.caption("कक्षा अध्यापक प्रबंधन कंसोल - 1-क्लिक पोर्टफोलियो जनरेटर एवं गूगल फॉर्म सिंक")

tabs = st.tabs([
    "🎴 Generate & Download Portfolio",
    "📥 Google Form Sync / Entry",
    "👥 Student Profiles & Photos",
    "📋 14 Official Activities Reference",
    "🔄 Refresh & Manage Data"
])

conn = get_db_connection()

# --- TAB 1: 2-PAGE PORTFOLIO DOWNLOAD ---
with tabs[0]:
    st.subheader("🎴 छात्र का 2-Page UP Board पोर्टफोलियो कार्ड देखें व डाउनलोड करें")
    students_df = pd.read_sql_query(
        "SELECT roll_no, student_name, student_name_hindi FROM students ORDER BY CAST(roll_no AS INTEGER) ASC", conn)

    if students_df.empty:
        st.warning("कोई छात्र रिकॉर्ड नहीं मिला। कृपया 'Refresh & Manage Data' टैब से studentport.xlsx सिंक करें।")
    else:
        col_s1, col_s2 = st.columns([1.5, 2])
        with col_s1:
            selected_roll = st.selectbox(
                "विद्यार्थी चुनें (Roll No - Name):",
                students_df["roll_no"].tolist(),
                format_func=lambda x: f"Roll {x} : {students_df[students_df['roll_no'] == x]['student_name'].values[0]}"
            )

            # Fetch details
            c = conn.cursor()
            c.execute("SELECT * FROM students WHERE roll_no=?", (selected_roll,))
            stu_row = c.fetchone()
            stu_cols = [desc[0] for desc in c.description]
            student_dict = dict(zip(stu_cols, stu_row))

            entries_df = pd.read_sql_query("SELECT * FROM portfolio_entries WHERE roll_no=? ORDER BY id ASC", conn,
                                           params=(selected_roll,))
            portfolio_html = generate_upboard_card(student_dict, entries_df)

            st.download_button(
                label=f"📥 Download {student_dict.get('student_name')} Portfolio Card (.html)",
                data=portfolio_html,
                file_name=f"UPBoard_12B_Roll_{student_dict.get('roll_no')}_{student_dict.get('student_name')}.html",
                mime="text/html",
                type="primary",
                use_container_width=True
            )
            st.caption("💡 डाउनलोड की गई HTML फ़ाइल को किसी भी ब्राउज़र में खोलकर सीधे 'Ctrl + P' से Save as PDF करें।")

        with col_s2:
            st.info(
                f"**चयनित विद्यार्थी:** {student_dict.get('student_name')} | **पिता:** {student_dict.get('father_name')} | **S.R. No:** {student_dict.get('sr_no')}")
            
            st_g = student_dict.get('short_term_goal')
            lt_g = student_dict.get('long_term_goal')
            if st_g or lt_g:
                st.markdown(f"**📌 Short-Term Goal:** {st_g if st_g else 'N/A'}")
                st.markdown(f"**🎯 Long-Term Goal:** {lt_g if lt_g else 'N/A'}")

        st.divider()
        st.components.v1.html(portfolio_html, height=1150, scrolling=True)


# --- TAB 2: GOOGLE FORM DATA SYNC / MANUAL INPUT ---
with tabs[1]:
    st.subheader("📥 Google Form डेटा सिंक (Response Sheet)")
    st.write(
        "छात्रों द्वारा Google Form भरने के बाद लिंक हुई Google Sheet को **File -> Download -> Microsoft Excel (.xlsx) या CSV (.csv)** के रूप में डाउनलोड करके यहाँ अपलोड करें:")

    col_up1, col_up2 = st.columns([1.2, 1])
    with col_up1:
        uploaded_form = st.file_uploader("Google Form Responses File (.xlsx / .csv)", type=["xlsx", "csv"])
        if uploaded_form is not None:
            try:
                if uploaded_form.name.endswith('.csv'):
                    df_form = pd.read_csv(uploaded_form, dtype=str)
                else:
                    df_form = pd.read_excel(uploaded_form, dtype=str)

                st.write(f"📊 कुल प्रविष्टियाँ (Responses found): **{len(df_form)}**")
                st.dataframe(df_form.head(2), use_container_width=True)

                if st.button("⚡ Sync Responses & Goals to Portfolios", type="primary"):
                    c = conn.cursor()
                    goals_synced = 0
                    activities_synced = 0

                    cols = list(df_form.columns)

                    # Identify Roll Number Column
                    roll_col = next((col for col in cols if "roll" in col.lower() or "अनुक्रमांक" in col), None)

                    # Identify Short-Term & Long-Term Goal Columns
                    st_col = next((col for col in cols if "अल्पकालिक" in col or "short-term" in col.lower()), None)
                    lt_col = next((col for col in cols if "दीर्घकालिक" in col or "long-term" in col.lower()), None)

                    if not roll_col:
                        st.error("शीट में Roll Number का कॉलम नहीं मिला! कृपया सुनिश्चित करें कि फॉर्म में 'Roll Number' मौजूद है।")
                    else:
                        for _, r in df_form.iterrows():
                            r_no = clean_val(r.get(roll_col, ""))
                            if not r_no:
                                continue

                            # 1. Update Goals only when not empty
                            st_val = clean_val(r.get(st_col, "")) if st_col else ""
                            lt_val = clean_val(r.get(lt_col, "")) if lt_col else ""

                            if st_val or lt_val:
                                c.execute("""
                                    UPDATE students 
                                    SET short_term_goal = CASE WHEN ? != '' THEN ? ELSE short_term_goal END,
                                        long_term_goal = CASE WHEN ? != '' THEN ? ELSE long_term_goal END,
                                        academic_goals = CASE WHEN (? != '' OR ? != '') THEN ? ELSE academic_goals END
                                    WHERE roll_no = ?
                                """, (
                                    st_val, st_val,
                                    lt_val, lt_val,
                                    st_val, lt_val,
                                    f"अल्पकालिक: {st_val} | दीर्घकालिक: {lt_val}".strip(" |"),
                                    r_no
                                ))
                                goals_synced += 1

                            # 2. Update Activities (1 to 14)
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
                                    today_now = datetime.now().strftime("%d-%m-%Y")
                                    c.execute("""
                                        INSERT INTO portfolio_entries (
                                            roll_no, activity_name, category, activity_date,
                                            student_description, student_reflection, evidence_link, 
                                            marks_awarded, submitted_on
                                        ) VALUES (?, ?, ?, ?, ?, ?, ?, 5, ?)
                                    """, (
                                        r_no, act_name, act["cat"], act["date"],
                                        desc_val, refl_val, link_val, today_now
                                    ))
                                    activities_synced += 1

                        conn.commit()
                        st.success(f"🎉 सफलता! {goals_synced} छात्रों के लक्ष्य (Goals) और {activities_synced} गतिविधियाँ सुरक्षित हो गईं!")
                        st.rerun()

            except Exception as e:
                st.error(f"फ़ाइल पढ़ने में त्रुटि: {e}")

    with col_up2:
        st.write("#### या मैन्युअल रूप से लक्ष्य / गतिविधि दर्ज करें:")
        with st.form("manual_goal_form"):
            st.markdown("**1. छात्र का शैक्षणिक विज़न दर्ज करें:**")
            m_roll_goal = st.selectbox("विद्यार्थी (Roll No):",
                                       students_df["roll_no"].tolist() if not students_df.empty else [], key="m_roll_goal")
            m_st_goal = st.text_area("अल्पकालिक लक्ष्य (Short-Term Goal):", placeholder="सत्र 2026-27 के लक्ष्य...")
            m_lt_goal = st.text_area("दीर्घकालिक लक्ष्य (Long-Term Goal):", placeholder="करियर / उच्च शिक्षा के लक्ष्य...")

            if st.form_submit_button("लक्ष्य सुरक्षित करें"):
                c = conn.cursor()
                combined_goal = f"अल्पकालिक: {m_st_goal} | दीर्घकालिक: {m_lt_goal}".strip(" |")
                c.execute("""
                    UPDATE students 
                    SET short_term_goal = CASE WHEN ? != '' THEN ? ELSE short_term_goal END,
                        long_term_goal = CASE WHEN ? != '' THEN ? ELSE long_term_goal END,
                        academic_goals = CASE WHEN ? != '' THEN ? ELSE academic_goals END
                    WHERE roll_no = ?
                """, (m_st_goal, m_st_goal, m_lt_goal, m_lt_goal, combined_goal, combined_goal, m_roll_goal))
                conn.commit()
                st.success("शैक्षणिक लक्ष्य सुरक्षित हो गए!")
                st.rerun()

# --- TAB 3: PROFILES & PHOTO UPLOAD ---
with tabs[2]:
    st.subheader("👥 छात्र मास्टर प्रोफाइल, लक्ष्य एवं फोटो प्रबंधन")
    if not students_df.empty:
        col_ph1, col_ph2 = st.columns([1.2, 2.8])
        with col_ph1:
            sel_photo_roll = st.selectbox("फोटो अपलोड हेतु छात्र चुनें:", students_df["roll_no"].tolist(), key="photo_sel")
            photo_file = st.file_uploader("पासपोर्ट साइज फोटो (JPG/PNG)", type=["jpg", "jpeg", "png"])
            if photo_file is not None:
                encoded = base64.b64encode(photo_file.read()).decode("utf-8")
                if st.button("Save Photo to Student Profile", type="primary"):
                    c = conn.cursor()
                    c.execute("UPDATE students SET photo_b64=? WHERE roll_no=?", (encoded, sel_photo_roll))
                    conn.commit()
                    st.success(f"Roll {sel_photo_roll} की फोटो स्थायी रूप से सुरक्षित हो गई!")
                    st.rerun()

        with col_ph2:
            all_records = pd.read_sql_query("""
                SELECT roll_no, student_name, father_name, 
                       CASE WHEN short_term_goal != '' THEN short_term_goal ELSE '-' END AS 'Short-Term Goal',
                       CASE WHEN long_term_goal != '' THEN long_term_goal ELSE '-' END AS 'Long-Term Goal',
                       CASE WHEN photo_b64 != '' THEN 'Uploaded ✅' ELSE 'Pending ❌' END AS Photo
                FROM students ORDER BY CAST(roll_no AS INTEGER) ASC
            """, conn)
            st.dataframe(all_records, use_container_width=True)

# --- TAB 4: 14 OFFICIAL ACTIVITIES CALENDAR ---
with tabs[3]:
    st.subheader("📋 कक्षा 12-B आधिकारिक गतिविधि एवं प्रतियोगिता कैलेंडर (UP Board 2026-27)")
    df_acts = pd.DataFrame(DEFAULT_ACTIVITIES)
    df_acts.columns = ["क्र. सं.", "तिथि", "प्रतियोगिता / गतिविधि का नाम", "श्रेणी / प्रकार", "विषय / विवरण",
                       "प्रभारी / मूल्यांकनकर्ता"]
    st.dataframe(df_acts, use_container_width=True)

# --- TAB 5: REFRESH & DELETE MANAGEMENT ---
with tabs[4]:
    st.subheader("🔄 डेटा सिंक एवं नियंत्रण")
    col_mg1, col_mg2 = st.columns(2)
    with col_mg1:
        st.write("#### 1. studentport.xlsx से सुरक्षित सिंक")
        st.caption("नोट: इससे छात्रों की फोटो या लक्ष्य डिलीट नहीं होंगे।")
        if st.button("🔄 studentport.xlsx सिंक करें", type="primary"):
            c_done, msg = sync_students_excel()
            st.success(f"{c_done} विद्यार्थियों का प्रोफाइल डेटा सुरक्षित रूप से सिंक हो गया!")
            st.rerun()

    with col_mg2:
        st.write("#### 2. गलत गतिविधि प्रविष्टि हटाएं")
        all_entries = pd.read_sql_query(
            "SELECT id, roll_no, activity_name, activity_date FROM portfolio_entries ORDER BY id DESC", conn)
        if not all_entries.empty:
            del_id = st.selectbox("हटाने हेतु प्रविष्टि चुनें:", all_entries["id"].tolist(), format_func=lambda
                x: f"ID {x} : Roll {all_entries[all_entries['id'] == x]['roll_no'].values[0]} - {all_entries[all_entries['id'] == x]['activity_name'].values[0]}")
            if st.button("Delete Entry", type="secondary"):
                c = conn.cursor()
                c.execute("DELETE FROM portfolio_entries WHERE id=?", (del_id,))
                conn.commit()
                st.success("प्रविष्टि डिलीट हो गई!")
                st.rerun()
        else:
            st.info("डिलीट करने के लिए कोई अलग प्रविष्टि नहीं है।")

conn.close()
