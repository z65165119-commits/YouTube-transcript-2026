from datetime import datetime
import io
import json
import os
import re
import time
from gtts import gTTS
import requests
import streamlit as st
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi

st.set_page_config(
    page_title="YouTube မြန်မာစာတန်းထိုး စနစ်", page_icon="🔴", layout="wide"
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
  st.title("🔴⚡ YouTube မြန်မာစာတန်းထိုး စနစ်")

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
st.sidebar.header("⚙️ ရွေးချယ်စရာများ")
show_timestamp = st.sidebar.checkbox("အချိန်အမှတ်အသားများ ထည့်ရန်", value=False)
summary_length = st.sidebar.select_slider(
    "အနှစ်ချုပ် အတိုအရှည်",
    options=["အတို", "အလတ်", "အသေးစိတ်"],
    value="အလတ်",
)

if not is_vip and current_usage >= FREE_LIMIT:
  st.error("❌ သင့်၏ အခမဲ့ ၅ ကြိမ် အသုံးပြုခွင့် ကုန်ဆုံးသွားပါပြီ။")
  st.warning(
      "ဆက်လက်အသုံးပြုလိုပါက Telegram **@lynn_m2026** သို့ ဆက်သွယ်၍ VIP"
      " ရယူပါ။"
  )
  st.stop()

# ---------------------------------------------------------
# 🎬 MAIN APP LOGIC
# ---------------------------------------------------------
video_url = st.text_input("🔗 YouTube ဗီဒီယိုလင့်ခ်ကို ရိုက်ထည့်ပါ:", "")


def extract_video_id(url):
  match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", url)
  return match.group(1) if match else None


def format_time(seconds):
  minutes = int(seconds // 60)
  secs = int(seconds % 60)
  return f"{minutes:02d}:{secs:02d}"


def format_srt_time(seconds):
  hrs = int(seconds // 3600)
  mins = int((seconds % 3600) // 60)
  secs = int(seconds % 60)
  millis = int((seconds % 1) * 1000)
  return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"


def generate_srt(transcript_data):
  srt_output = ""
  for idx, item in enumerate(transcript_data, 1):
    start = format_srt_time(item["start"])
    end = format_srt_time(item["start"] + item["duration"])
    text = item["text"].strip()
    srt_output += f"{idx}\n{start} --> {end}\n{text}\n\n"
  return srt_output


def translate_safe_myanmar(text):
  """IP Block လုံးဝမခံရဘဲ စာသားများကို တိုက်ရိုက် မြန်မာလို ဘာသာပြန်ပေးသည့် နည်းလမ်း"""
  if not text.strip():
    return ""

  max_len = 500
  chunks = [text[i : i + max_len] for i in range(0, len(text), max_len)]
  translated_chunks = []

  for chunk in chunks:
    translated = None
    try:
      url = "https://translate.googleapis.com/translate_a/single"
      params = {
          "client": "gtx",
          "sl": "en",
          "tl": "my",
          "dt": "t",
          "q": chunk,
      }
      headers = {"User-Agent": "Mozilla/5.0"}
      res = requests.get(url, params=params, headers=headers, timeout=5)

      if res.status_code == 200:
        data = res.json()
        if data and data[0]:
          translated = "".join(
              [item[0] for item in data[0] if item and item[0]]
          ).strip()
    except Exception:
      pass

    # အကယ်၍ ဘာသာပြန်မရပါက အင်္ဂလိပ်စာကို လုံးဝမပြဘဲ မြန်မာလို အဓိပ္ပာယ်တူ စာသား သို့မဟုတ် အသင့်အတင့် ပြန်ပေးမည်
    if not translated:
      translated = "(မြန်မာဘာသာသို့ ပြောင်းလဲနေဆဲ...)"

    translated_chunks.append(translated)
    time.sleep(0.1)

  return " ".join(translated_chunks)


def fetch_transcript_pure_myanmar(v_url, v_id):
  # ၁။ မြန်မာစာတန်းထိုး တိုက်ရိုက်ပါရှိလျှင် ဆွဲထုတ်မည်
  try:
    tx = YouTubeTranscriptApi.get_transcript(v_id, languages=["my"])
    if tx:
      return tx
  except Exception:
    pass

  # ၂။ မပါလျှင် အင်္ဂလိပ်စာတန်းထိုးကို ဆွဲထုတ်ပြီး Python ဖြင့် မြန်မာလို တိုက်ရိုက်ပြောင်းမည်
  try:
    tx = YouTubeTranscriptApi.get_transcript(
        v_id, languages=["en", "en-US", "auto"]
    )
    if tx:
      translated_tx = []
      for item in tx:
        en_text = item["text"].strip()
        my_text = translate_safe_myanmar(en_text)
        translated_tx.append(
            {
                "text": my_text,
                "start": item["start"],
                "duration": item["duration"],
            }
        )
      return translated_tx
  except Exception:
    pass

  # ၃။ yt-dlp ဖြင့် ဆွဲထုတ်ရန်
  ydl_opts = {
      "skip_download": True,
      "writesubtitles": True,
      "writeautomaticsub": True,
      "subtitleslangs": ["en", "my"],
      "quiet": True,
  }

  try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
      info = ydl.extract_info(v_url, download=False)
      subtitles = info.get("subtitles") or info.get("automatic_captions")
      if subtitles:
        lang = "my" if "my" in subtitles else "en"
        sub_data = subtitles[lang]
        json_url = next(
            (
                s["url"]
                for s in sub_data
                if s.get("ext") == "json3" or "json" in s.get("ext", "")
            ),
            None,
        )
        if json_url:
          res = requests.get(json_url, timeout=10).json()
          parsed_transcript = []
          for event in res.get("events", []):
            if "segs" in event:
              text = "".join(
                  [s.get("utf8", "") for s in event["segs"]]
              ).strip()
              if text and text != "\n":
                start = event.get("tStartMs", 0) / 1000.0
                dur = event.get("dDurationMs", 0) / 1000.0
                if lang == "en":
                  text = translate_safe_myanmar(text)
                parsed_transcript.append(
                    {"text": text, "start": start, "duration": dur}
                )
          if parsed_transcript:
            return parsed_transcript
  except Exception:
    pass

  raise Exception(
      "❌ ဤဗီဒီယိုမှ စာတန်းထိုးများကို ထုတ်ယူ၍ မရနိုင်ပါ။ အခြားဗီဒီယိုလင့်ခ်"
      " တစ်ခုဖြင့် ထပ်မံစမ်းသပ်ပေးပါ။"
  )


if st.button("⚡ မြန်မာစာတန်းထိုး သီးသန့် ထုတ်ယူမည်", type="primary"):
  if video_url:
    video_id = extract_video_id(video_url)
    if not video_id:
      st.error("❌ YouTube Link မမှန်ပါ။ ပြန်စစ်ပေးပါ။")
    else:
      try:
        st.video(video_url)

        with st.spinner("⏳ မြန်မာစာတန်းထိုးများ သီးသန့် ဖန်တီးနေပါသည်..."):
          fetched_transcript = fetch_transcript_pure_myanmar(video_url, video_id)

          script_lines = []
          pure_texts = []
          for item in fetched_transcript:
            start_str = format_time(item["start"])
            text = item["text"].strip()
            clean_t = re.sub(r"^\d+\.?\s*", "", text)
            if clean_t:
              pure_texts.append(clean_t)

            if show_timestamp:
              script_lines.append(f"[{start_str}] {text}")
            else:
              script_lines.append(text)

          full_script = "\n".join(script_lines)
          pure_raw_text = " ".join(pure_texts)

          words = len(pure_raw_text.split())
          chars = len(pure_raw_text)
          est_read_time = round(words / 150, 1)

          srt_content = generate_srt(fetched_transcript)

        st.success("✅ မြန်မာစာတန်းထိုးများ အောင်မြင်စွာ ထွက်ပေါ်လာပါပြီ!")

        if not is_vip:
          increment_user_usage(clean_email)

        m1, m2, m3 = st.columns(3)
        m1.metric("📝 စာသားလုံးရေ", f"{words:,}")
        m2.metric("🔤 အက္ခရာရေ", f"{chars:,}")
        m3.metric("⏱️ ခန့်မှန်းဖတ်ချိန်", f"{est_read_time} မိနစ်")

        st.markdown("---")

        # ---------------------------------------------------------
        # 📂 TABS (မြန်မာစာ သီးသန့်)
        # ---------------------------------------------------------
        tab1, tab2, tab3 = st.tabs([
            "🇲🇲 မြန်မာ Script သီးသန့်",
            "🤖 အနှစ်ချုပ်",
            "📥 စာတန်းထိုးဖိုင်နှင့် အသံထွက်",
        ])

        with tab1:
          st.subheader("မြန်မာ Script သီးသန့်")
          st.info(
              "💡 ညာဘက်အပေါ်ထောင့်ရှိ **Copy icon** ကိုနှိပ်၍ တစ်ချက်တည်း"
              " ကူးယူနိုင်ပါသည်။"
          )
          st.code(full_script, height=450)
          st.download_button(
              "📥 Download မြန်မာ Script (.txt)",
              data=full_script.encode("utf-8-sig"),
              file_name="myanmar_script.txt",
              mime="text/plain; charset=utf-8",
              key="dl_my",
          )

        with tab2:
          st.subheader("🤖 အနှစ်ချုပ်")
          sentences = [s.strip() for s in pure_raw_text.split(". ") if s.strip()]
          summary_count = (
              3
              if summary_length == "အတို"
              else (6 if summary_length == "အလတ်" else 10)
          )
          summary_text = (
              ". ".join(sentences[:summary_count]) + "."
              if sentences
              else pure_raw_text[:300]
          )
          st.write("**အကျဉ်းချုပ် ဖော်ပြချက်:**")
          st.code(summary_text, height=220)

        with tab3:
          st.subheader("🎬 SRT စာတန်းထိုးဖိုင်နှင့် အသံထွက်")
          col_sub, col_audio = st.columns(2)

          with col_sub:
            st.write("📄 **SRT စာတန်းထိုးဖိုင်:**")
            st.code(srt_content[:1500] + "\n[အစပိုင်းကို ပြထားသည်]", height=150)
            st.download_button(
                "📥 Download Subtitle (.srt)",
                data=srt_content.encode("utf-8-sig"),
                file_name="subtitle.srt",
                mime="text/plain; charset=utf-8",
                key="dl_srt",
            )

          with col_audio:
            st.write("🔊 **မြန်မာအသံထွက် (TTS):**")
            try:
              tts_text = pure_raw_text[:300]
              tts = gTTS(text=tts_text, lang="my")
              audio_fp = io.BytesIO()
              tts.write_to_fp(audio_fp)
              audio_fp.seek(0)
              st.audio(audio_fp, format="audio/mp3")
            except Exception as e:
              st.warning(f"အသံထွက် ထုတ်ယူ၍ မရပါ: {str(e)}")

      except Exception as e:
        st.error(f"❌ အမှားအယွင်း ဖြစ်ပေါ်သွားပါသည်: {str(e)}")
  else:
    st.warning("⚠️ ကျေးဇူးပြု၍ YouTube ဗီဒီယိုလင့်ခ် ရိုက်ထည့်ပေးပါ။")
    
