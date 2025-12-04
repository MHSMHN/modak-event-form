# app.py
import streamlit as st
import pandas as pd
from datetime import datetime
import os
import re
import uuid
import threading

# -----------------------
# تنظیمات و ثابت‌ها
# -----------------------
st.set_page_config(page_title="موداک - ثبت ایده", layout="wide", page_icon="rocket")

EXCEL_FILE = "ideas.xlsx"
FILES_DIR = "files"
ADMIN_PASSWORD = "ic.iaun.modak2025"  # ←← رمز ادمین را اینجا تغییر بده
excel_lock = threading.Lock()

# -----------------------
# استایل مینیمال سفید/آبی (RTL)
# -----------------------
st.markdown("""
<style>
    @font-face { font-family: 'Vazir'; src: url('https://cdn.fontcdn.ir/Font/Persian/Vazir/Vazir.woff') format('woff'); }
    html, body, [class*="css"] { font-family: 'Vazir', sans-serif !important; direction: rtl; text-align: right; background: #ffffff; color: #0f172a; }
    h1,h2,h3 { color: #0f4bd8; text-align: center; margin: 0.25rem 0; }
    .stButton>button, .stDownloadButton>button { background-color: #0f4bd8 !important; color: #fff !important; border-radius: 8px !important; padding: 8px 18px !important; }
    .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stSelectbox>div>div>div { border-radius: 8px; border: 1px solid #e6eefc; padding: 8px; text-align: right; }
    .stDataFrame { border: 1px solid #e6eefc; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# -----------------------
# توابع کمکی
# -----------------------
def normalize_phone(phone: str) -> str:
    return re.sub(r"[^\d]", "", phone or "")

def is_valid_phone(phone: str) -> bool:
    p = normalize_phone(phone)
    return len(p) == 11 and p.startswith("09")

def is_valid_email(email: str) -> bool:
    if not email:
        return False
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email.strip()) is not None

def safe_filename(original_name: str, phone_clean: str) -> str:
    name = re.sub(r"[^\w\-.\u0600-\u06FF]", "_", original_name, flags=re.UNICODE)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    uid = uuid.uuid4().hex[:8]
    return f"{phone_clean}_{ts}_{uid}_{name}"[:120]

def read_ideas_df() -> pd.DataFrame:
    if os.path.exists(EXCEL_FILE):
        try:
            return pd.read_excel(EXCEL_FILE, engine="openpyxl")
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()

def reset_form_state():
    # پاک‌سازی فیلدهای فرم و بازگشت به حالت پیش‌فرض
    keys_to_remove = [k for k in st.session_state.keys() if k.startswith("person_") or k.startswith("member_") or k in ("title", "desc", "files")]
    for k in keys_to_remove:
        try:
            del st.session_state[k]
        except Exception:
            pass
    st.session_state.participant_kind = "انفرادی"
    st.session_state.extra_member_count = 0
    st.session_state.last_submission = None
    st.experimental_rerun()

# -----------------------
# session_state اولیه
# -----------------------
if "participant_kind" not in st.session_state:
    st.session_state.participant_kind = "انفرادی"
if "extra_member_count" not in st.session_state:
    st.session_state.extra_member_count = 0
if "last_submission" not in st.session_state:
    st.session_state.last_submission = None

# -----------------------
# هدر
# -----------------------
st.markdown("<h1>فرم ثبت ایده و نوآوری</h1>", unsafe_allow_html=True)
st.markdown("<h3>مرکز رشد دانشگاه آزاد اسلامی نجف آباد با مشارکت صندوق سرمایه‌گذاری خطرپذیر گروه فولاد مبارکه برگزار می‌کند:</h3>", unsafe_allow_html=True)
st.markdown("<h4 style='color:#6b7280; text-align:center;'>رویداد موداک ۱۴۰۴</h4>", unsafe_allow_html=True)
st.divider()

# -----------------------
# انتخاب نوع شرکت‌کننده (بیرون از فرم)
# -----------------------
st.subheader("نوع شرکت‌کننده")
kind = st.radio(
    "لطفاً نوع شرکت‌کننده را انتخاب کنید",
    ["انفرادی", "تیمی"],
    index=0 if st.session_state.participant_kind == "انفرادی" else 1,
    horizontal=True
)
st.session_state.participant_kind = kind

# تنظیم تعداد اعضا برای حالت انفرادی/تیمی
if kind == "انفرادی":
    st.session_state.extra_member_count = 0
else:
    st.markdown("**تعداد اعضای اضافه (بدون احتساب سرگروه) — حداکثر 4 نفر**")
    extra = st.number_input(
        "تعداد اعضای اضافه",
        min_value=0, max_value=4,
        value=st.session_state.get("extra_member_count", 0),
        step=1,
        key="extra_member_count_input"
    )
    st.session_state.extra_member_count = int(extra)

st.divider()

# -----------------------
# فرم اصلی (clear_on_submit=True)
# -----------------------
with st.form("idea_form", clear_on_submit=True):
    st.subheader("اطلاعات شخص" if st.session_state.participant_kind == "انفرادی" else "اطلاعات سرگروه")

    c1, c2 = st.columns(2)
    person_name = c1.text_input("نام*", key="person_name")
    person_family = c2.text_input("نام خانوادگی*", key="person_family")

    c3, c4 = st.columns(2)
    phone = c3.text_input("شماره موبایل*", placeholder="09123456789", key="phone")
    email = c4.text_input("ایمیل*", placeholder="example@domain.com", key="email")

    city = st.selectbox("شهر*", ["اصفهان","تهران","مشهد","شیراز","تبریز","کرج","اهواز","قم","سایر"], key="city")

    st.divider()

    # اعضای تیم فقط در حالت تیمی
    extra_members = []
    if st.session_state.participant_kind == "تیمی" and st.session_state.extra_member_count > 0:
        st.subheader("اطلاعات اعضای تیم (بدون سرگروه)")
        for i in range(st.session_state.extra_member_count):
            k1, k2 = st.columns(2)
            name_key = f"member_name_{i}"
            family_key = f"member_family_{i}"
            m_name = k1.text_input(f"نام عضو {i+1}", key=name_key)
            m_family = k2.text_input(f"نام خانوادگی عضو {i+1}", key=family_key)
            extra_members.append((m_name.strip(), m_family.strip()))

    st.divider()
    st.subheader("اطلاعات ایده")
    title = st.text_input("عنوان ایده*", key="title")
    desc = st.text_area("توضیح کامل ایده*", height=220, key="desc",
                        placeholder="مسئله چیست؟ راه‌حل چیست؟ نوآوری کجاست؟ بازار هدف کیست؟ مزیت رقابتی چیست؟")
    files = st.file_uploader("آپلود فایل‌های ضمیمه (اختیاری)", accept_multiple_files=True, key="files")

    submit = st.form_submit_button("ارسال ایده 🚀", use_container_width=True)

# -----------------------
# پردازش ارسال
# -----------------------
if submit:
    errors = []
    if not (person_name and person_name.strip() and person_family and person_family.strip()):
        errors.append("نام و نام‌خانوادگی را وارد کنید.")
    if not (phone and phone.strip()):
        errors.append("شماره موبایل را وارد کنید.")
    if not (email and email.strip()):
        errors.append("ایمیل را وارد کنید.")
    if not (title and title.strip() and desc and desc.strip()):
        errors.append("عنوان و توضیح ایده را وارد کنید.")

    phone_clean = normalize_phone(phone)
    if not is_valid_phone(phone_clean):
        errors.append("شماره موبایل باید ۱۱ رقمی و با ۰۹ شروع شود.")
    if not is_valid_email(email):
        errors.append("ایمیل معتبر وارد کنید.")

    members_full = []
    if st.session_state.participant_kind == "تیمی":
        for i in range(st.session_state.extra_member_count):
            m_name = st.session_state.get(f"member_name_{i}", "").strip()
            m_family = st.session_state.get(f"member_family_{i}", "").strip()
            if not (m_name and m_family):
                errors.append(f"نام و نام‌خانوادگی عضو {i+1} را کامل وارد کنید.")
            else:
                members_full.append(f"{m_name} {m_family}")

    if errors:
        for e in dict.fromkeys(errors):
            st.error(e)
    else:
        members_str = " | ".join(members_full) if members_full else "-"
        total_count = 1 + len(members_full) if st.session_state.participant_kind == "تیمی" else 1
        data = {
            "زمان ثبت": datetime.now().strftime("%Y/%m/%d - %H:%M"),
            "نام متقاضی": f"{person_name.strip()} {person_family.strip()}",
            "موبایل": phone_clean,
            "ایمیل": email.strip(),
            "شهر": city,
            "نوع": st.session_state.participant_kind,
            "اعضای تیم (بدون سرگروه)": members_str,
            "تعداد اعضا (بدون سرگروه)": len(members_full) if st.session_state.participant_kind == "تیمی" else 0,
            "تعداد کل اعضا (شامل سرگروه)": total_count,
            "عنوان ایده": title.strip(),
            "توضیح ایده": desc.strip(),
            "تعداد فایل": len(files) if files else 0
        }

        try:
            with excel_lock:
                df_old = read_ideas_df()
                new_id = 1
                if not df_old.empty and "شماره ایده" in df_old.columns:
                    try:
                        new_id = int(df_old["شماره ایده"].max()) + 1
                    except Exception:
                        new_id = len(df_old) + 1
                elif not df_old.empty:
                    new_id = len(df_old) + 1
                data["شماره ایده"] = new_id
                df_final = pd.concat([df_old, pd.DataFrame([data])], ignore_index=True) if not df_old.empty else pd.DataFrame([data])
                df_final.to_excel(EXCEL_FILE, index=False, engine="openpyxl")
        except Exception as exc:
            st.error(f"خطا در ذخیره‌سازی اکسل: {exc}")
            st.info("در صورت نیاز، کتابخانه openpyxl را نصب کنید: pip install openpyxl")
            st.stop()

        if files:
            os.makedirs(FILES_DIR, exist_ok=True)
            for f in files:
                try:
                    fname = safe_filename(f.name, phone_clean)
                    with open(os.path.join(FILES_DIR, fname), "wb") as out:
                        out.write(f.getbuffer())
                except Exception as ex:
                    st.warning(f"خطا در ذخیره فایل {f.name}: {ex}")

        st.success("ایده با موفقیت ثبت شد.")
        st.balloons()
        st.session_state.last_submission = data

# -----------------------
# دکمه ثبت ایده جدید (نمایش فقط بعد از ارسال موفق)
# -----------------------
if st.session_state.get("last_submission"):
    st.markdown("---")
    st.info("ایده شما ثبت شد. برای ثبت ایده جدید از دکمه زیر استفاده کنید.")
    if st.button("ثبت ایده جدید"):
        reset_form_state()

# -----------------------
# پنل ادمین
# -----------------------
st.divider()
with st.expander("پنل ادمین: برای باز کردن کلیک کنید."):
    admin_password_input = st.text_input("رمز عبور ادمین", type="password")
    if admin_password_input == ADMIN_PASSWORD:
        st.success("به پنل ادمین خوش آمدید.")

        # خواندن داده‌ها
        df = read_ideas_df()
        total = len(df) if not df.empty else 0
        individual = len(df[df.get("نوع", "") == "انفرادی"]) if not df.empty else 0
        team = len(df[df.get("نوع", "") == "تیمی"]) if not df.empty else 0

        # نمایش متریک‌ها
        col1, col2, col3 = st.columns(3)
        col1.metric("تعداد کل ایده‌ها", total)
        col2.metric("ایده‌های انفرادی", individual)
        col3.metric("ایده‌های تیمی", team)

        st.markdown("#### مشاهده داده‌ها")
        if total > 0:
            st.dataframe(df.fillna("-"), use_container_width=True)

            # دانلود اکسل خروجی
            try:
                with open(EXCEL_FILE, "rb") as fh:
                    excel_bytes = fh.read()
                st.download_button(
                    label="دانلود فایل اکسل (خروجی کامل)",
                    data=excel_bytes,
                    file_name=f"ideas_export_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except FileNotFoundError:
                st.warning("فایل اکسل خروجی هنوز ایجاد نشده است.")
            except Exception as ex:
                st.error(f"خطا در آماده‌سازی دانلود اکسل: {ex}")
        else:
            st.info("هنوز هیچ ایده‌ای ثبت نشده است.")

        st.markdown("#### فایل‌های آپلود شده")
        if os.path.exists(FILES_DIR):
            files_list = sorted(os.listdir(FILES_DIR))
            if files_list:
                for file in files_list:
                    file_path = os.path.join(FILES_DIR, file)
                    try:
                        size_kb = os.path.getsize(file_path) // 1024
                    except Exception:
                        size_kb = "?"
                    try:
                        with open(file_path, "rb") as fobj:
                            st.download_button(
                                label=f"دانلود {file} ({size_kb} KB)",
                                data=fobj.read(),
                                file_name=file
                            )
                    except Exception:
                        st.warning(f"خطا در خواندن فایل {file}")
            else:
                st.info("هیچ فایلی آپلود نشده است.")
        else:
            st.info("هیچ فایلی آپلود نشده است.")
    elif admin_password_input:
        st.error("رمز اشتباه است. لطفاً دوباره تلاش کنید.")