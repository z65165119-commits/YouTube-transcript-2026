from datetime import datetime
import json
import os
import re
import streamlit as st
from yt_dlp import YoutubeDL

st.set_page_config(
    page_title="YouTube Transcript Extractor", page_icon="📝", layout="wide"
)

# ---------------------------------------------------------
# 🗄️ JSON DATABASE FUNCTIONS
# ---------------------------------------------------------
DB_FILE = "usage_db.json"


def load_db():
  if os.path.exists(DB_FILE):
    try:
      with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    except Exception:
      return {}
  return {}


def save_db(db):
  with open(DB_FILE, "w", encoding="utf-8") as f:
    json.dump(db, f, ensure_ascii=False, indent=4)


def get_user_usage(email):
  db = load_db()
  clean_email = email.strip().lower()
  if clean_email not in db:
    db[clean_email] = {"count": 0, "first_used": str(datetime.now())}
    save_db(db)
  return db[clean_email]["count"]


def increment_user_usage(email):
  db = load_db()
  clean_email = email.strip().lower()
  if clean_email not in db:
    db[clean_email] = {"count": 1, "first_used": str(datetime.now())}
  else:
    db[clean_email]["count"] += 1
  save_db(db)


# ---------------------------------------------------------
# 🔑 LOGIN SESSION MANAGEMENT
# ---------------------------------------------------------
ALLOWED_EMAILS = [
    "soemoe@gmail.com",
    "customer1@gmail.com",
    "zlynn7368@gmail.com",
]

FREE_LIMIT = 5

if "logged_in" not in st.session_state:
  st.session_state["logged_in"] = False
  st.session_state["user_email"] = ""

# ---------------------------------------------------------
# 🔝 HEADER BAR
# ---------------------------------------------------------
col_title, col_auth = st.columns([3, 1])

with col_title:
  st.title("📝 ယူကျု့ Transcript သီးသန့် ထုတ်ယူရန်")

with col_auth:
  if st.session_state["logged_in"]:
    st.write(f"👋 **{st.session_state['user_email']}**")
    if st.button("အကောင့်ထွက်မည်", key="signout_btn"):
      st.session_state["logged_in"] = False
      st.session_state["user_email"] = ""
      st.rerun()

if not st.session_state["logged_in"]:
  st.markdown("---")
  st.warning("⚠️ အသုံးပြုရန် သင့်၏ အီးမေးလ်ဖြင့် အရင် ဝင်ရောက်ပါ။")

  with st.form("login_form"):
    input_email = st.text_input("📧 အီးမေးလ် လိပ်စာ:")
    submit_login = st.form_submit_button("အကောင့်ဝင်မည်", type="primary")

    if submit_login:
      if input_email and "@" in input_email:
        st.session_state["logged_in"] = True
        st.session_state["user_email"] = input_email.strip().lower()
        st.success("✅ အောင်မြင်စွာ ဝင်ရောက်ပြီးပါပြီ!")
        st.rerun()
      else:
        st.error("❌ မှန်ကန်သော အီးမေးလ်လိပ်စာ ထည့်ပါ။")

  st.stop()

clean_email = st.session_state["user_email"]
allowed_emails_lower = [e.strip().lower() for e in ALLOWED_EMAILS]
is_vip = clean_email in allowed_emails_lower
current_usage = get_user_usage(clean_email)

# ---------------------------------------------------------
# ⚙️ SIDEBAR
# ---------------------------------------------------------
st.sidebar.header("👤 အသုံးပြုသူ အချက်အလက်")
st.sidebar.write(f"**အီးမေးလ်:**\n{clean_email}")

if is_vip:
  st.sidebar.success("👑 **VIP အကန့်အသတ်မဲ့ အသုံးပြုခွင့်**")
else:
  remaining = max(0, FREE_LIMIT - current_usage)
  st.sidebar.info(f"🎁 အခမဲ့ ကျန်ရှိသည့်အကြိမ်: {remaining} / {FREE_LIMIT}")
  st.sidebar.markdown(
      "💬 **VIP ဝယ်ယူရန် ဆက်သွယ်ရန်:**\nTelegram: [@lynn_m2026](https://t.me/lynn_m2026)"
  )

st.sidebar.markdown("---")

if not is_vip and current_usage >= FREE_LIMIT:
  st.error("❌ သင့်၏ အခမဲ့ ၅ ကြိမ် အသုံးပြုခွင့် ကုန်ဆုံးသွားပါပြီ။")
  st.warning(
      "ဆက်လက်အသုံးပြုလိုပါက Telegram **@lynn_m2026** သို့ ဆက်သွယ်၍ VIP"
      " ရယူပါ။"
  )
  st.stop()

# ---------------------------------------------------------
# 🎬 YOUTUBE TRANSCRIPT EXTRACTION VIA YT-DLP
# ---------------------------------------------------------
video_url = st.text_input("🔗 YouTube ဗီဒီယိုလင့်ခ်ကို ရိုက်ထည့်ပါ:", "")


def get_youtube_transcript_ytdlp(url):
  ydl_opts = {
      "skip_download": True,
      "writesubtitles": True,
      "writeautomaticsub": True,
      "subtitleslangs": ["en", "my"],
      "quiet": True,
  }

  # Subtitles ကို တိုက်ရိုက်ဖတ်ရန် yt-dlp info ထုတ်ယူခြင်း
  with YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info(url, download=False)
    subtitles = info.get("subtitles", {})
    auto_captions = info.get("automatic_captions", {})

    # အင်္ဂလိပ် (သို့) မြန်မာ စာတန်းထိုး ရရှိနိုင်မှုကို စစ်ဆေးခြင်း
    sub_data = None
    lang_found = None
    for lang in ["en", "my", "en-US"]:
      if lang in subtitles:
        sub_data = subtitles[lang]
        lang_found = lang
        break
      elif lang in auto_captions:
        sub_data = auto_captions[lang]
        lang_found = lang
        break

    if not sub_data:
      raise Exception(
          "ဤဗီဒီယိုတွင် တရားဝင် သို့မဟုတ် အလိုအလျောက် စာတန်းထိုး လုံးဝ မရှိပါ။"
      )

    # vtt သို့မဟုတ် json3 ဖော်မတ်လင့်ခ်ကို ရှာပြီး စာသားဆွဲထုတ်ရန်
    target_format = None
    for fmt in sub_data:
      if fmt.get("ext") in ["vtt", "json3", "srv1"]:
        target_format = fmt
        break

    if not target_format:
      target_format = sub_data[0]

    sub_url = target_format.get("url")
    import requests

    res = requests.get(sub_url, timeout=10)
    if res.status_code != 200:
      raise Exception("စာတန်းထိုးဖိုင်ကို ဒေါင်းလုပ်ဆွဲ၍ မရပါ။")

    content = res.text
    # VTT ဖော်မတ်မှ စာသားသန့်စင်ခြင်း
    lines = content.split("\n")
    clean_texts = []
    for line in lines:
      # အချိန်အမှတ်အသားများနှင့် VTT tags များကို ဖယ်ရှားခြင်း
      if "-->" in line or line.startswith("WEBVTT") or line.strip().isdigit():
        continue
      if line.strip():
        # HTML tags တွေပါရင် ဖယ်ထုတ်ရန်
        clean_line = re.sub(r"<[^>]+>", "", line).strip()
        if clean_line and clean_line not in clean_texts:
          clean_texts.append(clean_line)

    return " ".join(clean_texts)


if st.button("🚀 YouTube Transcript ကို ဆွဲထုတ်မည်", type="primary"):
  if video_url:
    try:
      st.video(video_url)
      with st.spinner(
          "⏳ yt-dlp ကို အသုံးပြု၍ Transcript ဆွဲထုတ်နေပါသည်..."
      ):
        transcript_text = get_youtube_transcript_ytdlp(video_url)

      if not is_vip:
        increment_user_usage(clean_email)

      st.success("✅ အောင်မြင်စွာ ဆွဲထုတ်ပြီးပါပြီ!")

      words = len(transcript_text.split())
      chars = len(transcript_text)
      m1, m2 = st.columns(2)
      m1.metric("📝 စာသားလုံးရေ", f"{words:,}")
      m2.metric("🔤 အက္ခရာရေ", f"{chars:,}")

      st.markdown("---")
      st.subheader("ရရှိလာသော Transcript စာသားများ")
      st.code(transcript_text, height=350)

      st.download_button(
          "📥 Download Transcript (.txt)",
          data=transcript_text.encode("utf-8-sig"),
          file_name="youtube_transcript.txt",
          mime="text/plain; charset=utf-8",
      )

    except Exception as e:
      st.error(
          "❌ Transcript ဆွဲထုတ်၍ မရပါ။ (အမှားအယွင်း: "
          f"{str(e)})\n\n💡 မှတ်ချက်။ ။ အချို့သော Movie Recaps"
          " ဗီဒီယိုများတွင် မူရင်းစာတန်းထိုး လုံးဝပါရှိခြင်း မရှိတတ်ပါ။"
      )
  else:
    st.warning("⚠️ ကျေးဇူးပြု၍ YouTube လင့်ခ် ထည့်သွင်းပေးပါ။")
    
