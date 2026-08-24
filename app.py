from datetime import datetime
import io
import json
import os
import re
import time
from deep_translator import GoogleTranslator
from gtts import gTTS
import streamlit as st
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi

st.set_page_config(
    page_title="YouTube AI Studio & Script Suite",
    page_icon="🔴",
    layout="wide",
)

# ---------------------------------------------------------
# 🗄️ JSON DATABASE FUNCTIONS FOR PERSISTENT USAGE TRACKING
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
# 🔝 HEADER BAR WITH SIGN IN / USER INFO
# ---------------------------------------------------------
col_title, col_auth = st.columns([3, 1])

with col_title:
  st.title("🔴⚡ YouTube AI Studio")

with col_auth:
  if st.session_state["logged_in"]:
    st.write(f"👋 **{st.session_state['user_email']}**")
    if st.button("Sign Out", key="signout_btn"):
      st.session_state["logged_in"] = False
      st.session_state["user_email"] = ""
      st.rerun()

# ---------------------------------------------------------
# 🚨 MANDATORY LOGIN CHECK
# ---------------------------------------------------------
if not st.session_state["logged_in"]:
  st.markdown("---")
  st.warning("⚠️ App အသုံးပြုရန် သင့်၏ Gmail (သို့) Email ဖြင့် အရင် ဝင်ရောက်ပါ။")

  with st.form("login_form"):
    input_email = st.text_input("📧 Your Gmail Address:")
    submit_login = st.form_submit_button("Sign In / ဝင်မည်", type="primary")

    if submit_login:
      if input_email and "@" in input_email:
        st.session_state["logged_in"] = True
        st.session_state["user_email"] = input_email.strip().lower()
        st.success("✅ အောင်မြင်စွာ ဝင်ရောက်ပြီးပါပြီ!")
        st.rerun()
      else:
        st.error("❌ ကျေးဇူးပြု၍ မှန်ကန်သော Email လိပ်စာ ထည့်ပါ။")

  st.stop()

clean_email = st.session_state["user_email"]
allowed_emails_lower = [e.strip().lower() for e in ALLOWED_EMAILS]
is_vip = clean_email in allowed_emails_lower
current_usage = get_user_usage(clean_email)

# ---------------------------------------------------------
# ⚙️ SIDEBAR - USER ACCOUNT & OPTIONS
# ---------------------------------------------------------
st.sidebar.header("👤 Account Info")
st.sidebar.write(f"**Logged in as:**\n{clean_email}")

if is_vip:
  st.sidebar.success("👑 **VIP Unlimited Access**")
else:
  remaining = max(0, FREE_LIMIT - current_usage)
  st.sidebar.info(f"🎁 အခမဲ့ သုံးစွဲခွင့် ကျန်ရှိသည့်အကြိမ်: {remaining} / {FREE_LIMIT}")
  st.sidebar.markdown(
      "💬 **VIP ဝယ်ယူရန် ဆက်သွယ်ရန်:**\nTelegram: [@lynn_m2026](https://t.me/lynn_m2026)"
  )

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Options")
show_timestamp = st.sidebar.checkbox("Timestamps ထည့်ရန်", value=False)
summary_length = st.sidebar.select_slider(
    "AI Summary အတိုအရှည်",
    options=["Short", "Medium", "Detailed"],
    value="Medium",
)

# 🛑 Non-VIP တွေအတွက် ၅ ကြိမ်ပြည့်ရင် ရပ်တန့်မည့် စနစ်
if not is_vip and current_usage >= FREE_LIMIT:
  st.error("❌ သင့်၏ အခမဲ့ ၅ ကြိမ် အသုံးပြုခွင့် ကုန်ဆုံးသွားပါပြီ။")
  st.warning(
      "ဆက်လက်အသုံးပြုလိုပါက Telegram **@lynn_m2026** ထံသို့ ဆက်သွယ်၍ **VIP"
      " Access** ရယူပါရန်။"
  )
  st.stop()

# ---------------------------------------------------------
# 🎬 MAIN APP LOGIC
# ---------------------------------------------------------
video_url = st.text_input("🔗 YouTube Video URL ကို ရိုက်ထည့်ပါ:", "")


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


def chunked_translate(text, chunk_size=800):
  if not text.strip():
    return ""

  translator = GoogleTranslator(source="auto", target="my")
  if len(text) <= chunk_size:
    try:
      return translator.translate(text)
    except Exception:
      return text

  chunks = [
      text[i : i + chunk_size] for i in range(0, len(text), chunk_size)
  ]
  translated_chunks = []

  for chunk in chunks:
    success = False
    for attempt in range(3):
      try:
        res = translator.translate(chunk)
        if res:
          translated_chunks.append(res)
          success = True
          break
      except Exception:
        pass
      time.sleep(0.4)

    if not success:
      translated_chunks.append(chunk)
    time.sleep(0.3)

  return " ".join(translated_chunks)


def fetch_transcript_robust(v_url, v_id):
  try:
    tx = YouTubeTranscriptApi.get_transcript(
        v_id, languages=["en", "en-US", "my", "auto"]
    )
    if tx:
      return tx
  except Exception:
    pass

  ydl_opts = {
      "skip_download": True,
      "writesubtitles": True,
      "writeautomaticsub": True,
      "subtitleslangs": ["en", "my", "en-US"],
      "quiet": True,
  }

  try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
      info = ydl.extract_info(v_url, download=False)
      subtitles = info.get("subtitles") or info.get("automatic_captions")

      if subtitles:
        lang = None
        for l in ["en", "en-US", "my"]:
          if l in subtitles:
            lang = l
            break
        if not lang:
          lang = list(subtitles.keys())[0]

        sub_data = subtitles[lang]
        import requests

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
                parsed_transcript.append(
                    {"text": text, "start": start, "duration": dur}
                )
          if parsed_transcript:
            return parsed_transcript
  except Exception:
    pass

  raise Exception(
      "ဒီဗီဒီယိုတွင် YouTube Transcript (သို့) Subtitles လုံးဝ မရှိပါ (သို့မဟုတ်"
      " YouTube မှ တားမြစ်ထားပါသည်)။"
  )


if st.button("⚡ Script & AI Processing စတင်မည်", type="primary"):
  if video_url:
    video_id = extract_video_id(video_url)
    if not video_id:
      st.error("❌ YouTube Link မမှန်ပါ။ ပြန်စစ်ပေးပါ။")
    else:
      try:
        st.video(video_url)

        with st.spinner("⏳ Transcript နှင့် AI Data များကို ထုတ်ယူနေပါသည်..."):
          fetched_transcript = fetch_transcript_robust(video_url, video_id)

          english_lines = []
          raw_text_combined = ""
          for item in fetched_transcript:
            start_str = format_time(item["start"])
            text = item["text"].strip()
            raw_text_combined += text + " "
            if show_timestamp:
              english_lines.append(f"[{start_str}] {text}")
            else:
              english_lines.append(text)

          full_english_script = "\n".join(english_lines)

          words = len(raw_text_combined.split())
          chars = len(raw_text_combined)
          est_read_time = round(words / 150, 1)

        with st.spinner("⏳ မြန်မာဘာသာသို့ ဘာသာပြန်ဆိုနေပါသည်..."):
          myanmar_translation = chunked_translate(raw_text_combined)

          srt_content = generate_srt(fetched_transcript)

          sentences = raw_text_combined.split(". ")
          summary_sentences = (
              sentences[:3]
              if summary_length == "Short"
              else (sentences[:6] if summary_length == "Medium" else sentences[:10])
          )
          summary_en = ". ".join(summary_sentences) + "."
          summary_my = chunked_translate(summary_en)

        st.success("✅ အားလုံး အောင်မြင်စွာ ထုတ်ယူဘာသာပြန်ပြီးပါပြီ!")

        # Free User ဖြစ်မှသာ Database ထဲတွင် အကြိမ်ရေ တိုးပေးမည်
        if not is_vip:
          increment_user_usage(clean_email)

        m1, m2, m3 = st.columns(3)
        m1.metric("📝 စာသားလုံးရေ (Words)", f"{words:,}")
        m2.metric("🔤 အက္ခရာရေ (Chars)", f"{chars:,}")
        m3.metric("⏱️ ခန့်မှန်းဖတ်ချိန်", f"{est_read_time} မိနစ်")

        st.markdown("---")

        tab1, tab2, tab3, tab4 = st.tabs([
            "🇬🇧 English Script",
            "🇲🇲 မြန်မာ ဘာသာပြန်",
            "🤖 AI Summary & Recap",
            "📥 Subtitles & TTS Audio",
        ])

        with tab1:
          st.subheader("English Script")
          st.info(
              "💡 ညာဘက်အပေါ်ထောင့်ရှိ **Copy icon** ကိုနှိပ်၍ တစ်ချက်တည်း"
              " ကူးယူနိုင်ပါသည်။"
          )
          st.code(full_english_script)
          st.download_button(
              "📥 Download English Script (.txt)",
              data=full_english_script.encode("utf-8-sig"),
              file_name="english_script.txt",
              mime="text/plain; charset=utf-8",
          )

        with tab2:
          st.subheader("မြန်မာ ဘာသာပြန် Script")
          st.info(
              "💡 ညာဘက်အပေါ်ထောင့်ရှိ **Copy icon** ကိုနှိပ်၍ တစ်ချက်တည်း"
              " ကူးယူနိုင်ပါသည်။"
          )
          st.code(myanmar_translation)
          st.download_button(
              "📥 Download မြန်မာ Script (.txt)",
              data=myanmar_translation.encode("utf-8-sig"),
              file_name="myanmar_script.txt",
              mime="text/plain; charset=utf-8",
          )

        with tab3:
          st.subheader("🤖 AI Script Summary & Story Recap")
          st.write("**English Summary:**")
          st.code(summary_en)
          st.write("**မြန်မာအနှစ်ချုပ် / ပြန်လည်ဆန်းသစ်ချက်:**")
          st.code(summary_my)

        with tab4:
          st.subheader("🎬 SRT Subtitle & Myanmar Voiceover (TTS)")
          col_sub, col_audio = st.columns(2)

          with col_sub:
            st.write("📄 **SRT Subtitle File:**")
            st.code(srt_content[:2000] + "\n[Truncated Preview]")
            st.download_button(
                "📥 Download Subtitle (.srt)",
                data=srt_content.encode("utf-8-sig"),
                file_name="subtitle.srt",
                mime="text/plain; charset=utf-8",
            )

          with col_audio:
            st.write("🔊 **Myanmar Text-to-Speech (TTS Voiceover):**")
            try:
              tts_text = summary_my[:300]
              tts = gTTS(text=tts_text, lang="my")
              audio_fp = io.BytesIO()
              tts.write_to_fp(audio_fp)
              audio_fp.seek(0)
              st.audio(audio_fp, format="audio/mp3")
            except Exception as e:
              st.warning(f"Audio TTS Generation မရရှိပါ: {str(e)}")

      except Exception as e:
        st.error(f"❌ အမှားအယွင်း ဖြစ်ပေါ်သွားပါသည်: {str(e)}")
  else:
    st.warning("⚠️ ကျေးဇူးပြု၍ YouTube Link ရိုက်ထည့်ပေးပါ။")
    
