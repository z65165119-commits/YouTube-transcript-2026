from datetime import datetime
from deep_translator import GoogleTranslator
import json
import os
import re
import requests
import streamlit as st
from yt_dlp import YoutubeDL

st.set_page_config(
    page_title="YouTube to Myanmar Script", page_icon="🇲🇲", layout="wide"
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
  st.title("🇲🇲 ယူကျု့ ဗီဒီယိုမှ မြန်မာ Script သက်သက် ထုတ်ယူရန်")

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
# 🛠️ HELPER FUNCTIONS
# ---------------------------------------------------------
def get_youtube_transcript_ytdlp(url):
  ydl_opts = {
      "skip_download": True,
      "writesubtitles": True,
      "writeautomaticsub": True,
      "subtitleslangs": ["en", "my"],
      "quiet": True,
  }

  with YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info(url, download=False)
    subtitles = info.get("subtitles", {})
    auto_captions = info.get("automatic_captions", {})

    sub_data = None
    for lang in ["en", "my", "en-US", "en-GB"]:
      if lang in subtitles:
        sub_data = subtitles[lang]
        break
      elif lang in auto_captions:
        sub_data = auto_captions[lang]
        break

    if not sub_data:
      raise Exception(
          "ဤဗီဒီယိုတွင် တရားဝင် သို့မဟုတ် အလိုအလျောက် စာတန်းထိုး လုံးဝ မရှိပါ။"
      )

    vtt_url = None
    for fmt in sub_data:
      if fmt.get("ext") == "vtt":
        vtt_url = fmt.get("url")
        break

    if not vtt_url:
      vtt_url = sub_data[0].get("url")

    res = requests.get(vtt_url, timeout=10)
    if res.status_code != 200:
      raise Exception("စာတန်းထိုးဖိုင်ကို ဒေါင်းလုပ်ဆွဲ၍ မရပါ။")

    content = res.text
    lines = content.split("\n")
    clean_texts = []

    for line in lines:
      if (
          "-->" in line
          or line.startswith("WEBVTT")
          or line.strip().isdigit()
          or line.startswith("NOTE")
          or "Kind:" in line
          or "Language:" in line
        ):
        continue
      if line.strip():
        clean_line = re.sub(r"<[^>]+>", "", line).strip()
        if clean_line and (
            not clean_texts or clean_texts[-1] != clean_line
        ):
          clean_texts.append(clean_line)

    return " ".join(clean_texts)


def translate_to_myanmar_fast(text):
  if not text.strip():
    return ""

  # စာသားတွေကို စကားလုံးရေ အတိုအထوالလေးတွေ (အများဆုံး စာလုံးရေ ၄၀၀ ခန့်စီ) ပိုင်းထုတ်မည်
  words = text.split()
  chunks = []
  current_chunk = []
  current_length = 0

  for word in words:
    current_length += len(word) + 1
    current_chunk.append(word)
    if current_length > 400:
      chunks.append(" ".join(current_chunk))
      current_chunk = []
      current_length = 0

  if current_chunk:
    chunks.append(" ".join(current_chunk))

  translator = GoogleTranslator(source="en", target="my")
  translated_chunks = []

  for chunk in chunks:
    try:
      translated = translator.translate(chunk)
      if translated:
        translated_chunks.append(translated)
      else:
        translated_chunks.append(chunk)
    except Exception:
      translated_chunks.append(chunk)

  return " ".join(translated_chunks)


# ---------------------------------------------------------
# 🎬 MAIN UI & LOGIC
# ---------------------------------------------------------
video_url = st.text_input("🔗 YouTube ဗီဒီယိုလင့်ခ်ကို ရိုက်ထည့်ပါ:", "")

if st.button("🚀 မြန်မာ Script သက်သက် ထုတ်ယူမည်", type="primary"):
  if video_url:
    try:
      st.video(video_url)
      with st.spinner("⏳ Transcript ဆွဲထုတ်ပြီး မြန်မာလို ဘာသာပြန်နေပါပြီ..."):
        english_transcript = get_youtube_transcript_ytdlp(video_url)
        myanmar_script = translate_to_myanmar_fast(english_transcript)

      if not is_vip:
        increment_user_usage(clean_email)

      st.success("✅ မြန်မာ Script အောင်မြင်စွာ ထွက်ရှိလာပါပြီ!")

      words = len(myanmar_script.split())
      chars = len(myanmar_script)
      m1, m2 = st.columns(2)
      m1.metric("📝 မြန်မာစာလုံးရေ", f"{words:,}")
      m2.metric("🔤 အက္ခရာရေ", f"{chars:,}")

      st.markdown("---")
      st.subheader("🇲🇲 ရရှိလာသော မြန်မာ Script")
      st.code(myanmar_script, height=350)

      st.download_button(
          "📥 Download မြန်မာ Script (.txt)",
          data=myanmar_script.encode("utf-8-sig"),
          file_name="myanmar_script.txt",
          mime="text/plain; charset=utf-8",
      )

    except Exception as e:
      st.error(
          "❌ Transcript ဆွဲထုတ်၍ မရပါ။ (အမှားအယွင်း: "
          f"{str(e)})\n\n💡 မှတ်ချက်။ ။ အချို့သော ဗီဒီယိုများတွင် စာတန်းထိုး"
          " လုံးဝပါရှိခြင်း မရှိတတ်ပါ။"
      )
  else:
    st.warning("⚠️ ကျေးဇူးပြု၍ YouTube လင့်ခ် ထည့်သွင်းပေးပါ။")
      
