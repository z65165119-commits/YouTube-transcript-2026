from datetime import datetime
import io
import json
import os
import re
import time
from gtts import gTTS
import requests
import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi

st.set_page_config(
    page_title="YouTube to Myanmar Voice (Line-by-Line)",
    page_icon="🔊",
    layout="wide",
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
  st.title("🔊 ယူကျု့ မူရင်းအတိုင်း မြန်မာအသံထွက် (Line-by-Line)")

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
# 🎬 MAIN LOGIC
# ---------------------------------------------------------
video_url = st.text_input("🔗 YouTube ဗီဒီယိုလင့်ခ်ကို ရိုက်ထည့်ပါ:", "")


def extract_video_id(url):
  match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", url)
  return match.group(1) if match else None


def format_time(seconds):
  minutes = int(seconds // 60)
  secs = int(seconds % 60)
  return f"{minutes:02d}:{secs:02d}"


def translate_text(text):
  if not text.strip():
    return ""
  try:
    url = "https://translate.googleapis.com/translate_a/single"
    params = {"client": "gtx", "sl": "auto", "tl": "my", "dt": "t", "q": text}
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, params=params, headers=headers, timeout=5)
    if res.status_code == 200:
      data = res.json()
      if data and data[0]:
        return "".join(
            [item[0] for item in data[0] if item and item[0]]
        ).strip()
  except Exception:
    pass
  return text


if st.button("🚀 မူရင်းအတိုင်း Transcript နှင့် မြန်မာအသံများ ထုတ်မည်", type="primary"):
  if video_url:
    video_id = extract_video_id(video_url)
    if not video_id:
      st.error("❌ YouTube Link မမှန်ပါ။")
    else:
      try:
        st.video(video_url)

        with st.spinner("⏳ မူရင်း Transcript များကို ဆွဲထုတ်နေပါသည်..."):
          # Error မတက်စေရန် YouTubeTranscriptApi ကို အမှန်ကန်ဆုံး ပုံစံဖြင့် ခေါ်သုံးခြင်း
          try:
            transcript_list = YouTubeTranscriptApi.get_transcript(
                video_id, languages=["en", "my", "auto"]
            )
          except Exception:
            # ဗားရှင်းအသစ်များအတွက် အခြားနည်းလမ်းဖြင့် ဆွဲထုတ်ခြင်း
            transcript_obj = YouTubeTranscriptApi()
            fetched = transcript_obj.fetch(
                video_id, languages=["en", "my", "auto"]
            )
            transcript_list = [{"text": d.text, "start": d.start, "duration": d.duration} for d in fetched]

        with st.spinner("⏳ စာကြောင်းတစ်ကြောင်းချင်းစီကို မြန်မာလို ပြောင်းလဲနေပါသည်..."):
          processed_lines = []
          full_myanmar_text = []

          for idx, item in enumerate(transcript_list):
            start_time = format_time(item["start"])
            en_text = item["text"].strip()
            my_text = translate_text(en_text)

            if my_text:
              full_myanmar_text.append(my_text)
              processed_lines.append(
                  {"time": start_time, "my_text": my_text, "index": idx + 1}
              )
            time.sleep(0.02)

        st.success("✅ အောင်မြင်စွာ ဖန်တီးပြီးပါပြီ!")

        if not is_vip:
          increment_user_usage(clean_email)

        combined_script = "\n".join(
            [f"[{l['time']}] {l['my_text']}" for l in processed_lines]
        )
        complete_raw_text = " ".join(full_myanmar_text)

        tab1, tab2 = st.tabs(
            ["🇲🇲 အချိန်အမှတ်အသားပါ Script", "🔊 အသံဖိုင်များ (Line-by-Line & Full)"]
        )

        with tab1:
          st.subheader("အချိန်အမှတ်အသားပါ မြန်မာ Script")
          st.code(combined_script, height=400)
          st.download_button(
              "📥 Download မြန်မာ Script (.txt)",
              data=combined_script.encode("utf-8-sig"),
              file_name="timed_myanmar_script.txt",
              mime="text/plain; charset=utf-8",
          )

        with tab2:
          st.subheader("🔊 မူရင်းဗီဒီယိုပုံစံ မြန်မာအသံထွက်များ")

          st.markdown("##### 📌 ဗီဒီယို တစ်ခုလုံးစာ မြန်မာအသံ (Full Audio)")
          try:
            tts_full = gTTS(text=complete_raw_text[:3000], lang="my")
            audio_full_fp = io.BytesIO()
            tts_full.write_to_fp(audio_full_fp)
            audio_full_fp.seek(0)
            st.audio(audio_full_fp, format="audio/mp3")
            st.download_button(
                "📥 Download Full MP3 အသံဖိုင်",
                data=audio_full_fp,
                file_name="full_myanmar_voice.mp3",
                mime="audio/mp3",
            )
          except Exception as e:
            st.warning(f"Full Audio ထုတ်ယူ၍ မရပါ: {str(e)}")

          st.markdown("---")
          st.markdown("##### ⏱️ စာကြောင်းလိုက် အသံထွက် နားဆင်ရန်")

          for line in processed_lines[:15]:
            cols = st.columns([1, 4])
            cols[0].write(f"⏱️ **{line['time']}**")
            cols[1].write(line["my_text"])
          st.info(
              "💡 စာကြောင်းရေများပါက အပေါ်ရှိ Full Audio ကို တိုက်ရိုက်"
              " အသုံးပြုနိုင်ပါသည်။"
          )

      except Exception as e:
        st.error(
            "❌ ဤဗီဒီယိုမှ Transcript ဆွဲထုတ်၍ မရပါ (သို့) စာတန်းထိုး"
            f" ပိတ်ထားပါသည်။ အမှားအယွင်း: {str(e)}"
        )
  else:
    st.warning("⚠️ ကျေးဇူးပြု၍ YouTube လင့်ခ် ထည့်သွင်းပေးပါ။")
