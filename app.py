from datetime import datetime
import io
import json
import os
import re
import time
from gtts import gTTS
import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi

try:
  import google.generativeai as genai
except ImportError:
  pass

# yt-dlp check for advanced audio downloading
try:
  import yt_dlp
except ImportError:
  pass

st.set_page_config(
    page_title="YouTube AI Studio & Script Suite",
    page_icon="🔴",
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
  st.title("🔴⚡ YouTube AI Studio (Movie Recap Edition)")

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
# ⚙️ SIDEBAR - API KEY & OPTIONS
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
st.sidebar.header("🔑 Google Gemini API Key")
user_api_key = st.sidebar.text_input(
    "API Key ထည့်ရန်",
    value="AIzaSyChFnyloI7Jf38fAed4tfDzf954ojjep5I",
    type="password",
    help="သင့်ရဲ့ Gemini API Key ကို ဤနေရာတွင် ထည့်ပါ။",
)

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Options")
summary_length = st.sidebar.select_slider(
    "AI Summary အတိုအရှည်",
    options=["Short", "Medium", "Detailed"],
    value="Medium",
)

if not is_vip and current_usage >= FREE_LIMIT:
  st.error("❌ သင့်၏ အခမဲ့ ၅ ကြိမ် အသုံးပြုခွင့် ကုန်ဆုံးသွားပါပြီ။")
  st.warning(
      "ဆက်လက်အသုံးပြုလိုပါက Telegram **@lynn_m2026** ထံသို့ ဆက်သွယ်၍ေ **VIP"
      " Access** ရယူပါရန်။"
  )
  st.stop()

# ---------------------------------------------------------
# 🎬 MAIN APP LOGIC
# ---------------------------------------------------------
video_url = st.text_input("🔗 YouTube Movie Recap Video URL ကို ရိုက်ထည့်ပါ:", "")


def extract_video_id(url):
  match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", url)
  return match.group(1) if match else None


def download_audio_and_upload_to_gemini(url, api_key):
  """Movie Recap တွေမှာ Subtitle မရှိရင် အသံဖိုင်ကိုထုတ်ပြီး Gemini ဆီ တိုက်ရိုက်ပို့စစ်ပေးသည်"""
  audio_filename = "recap_audio.mp3"
  if os.path.exists(audio_filename):
    os.remove(audio_filename)

  ydl_opts = {
      "format": "bestaudio/best",
      "postprocessors": [{
          "key": "FFmpegExtractAudio",
          "preferredcodec": "mp3",
          "preferredquality": "128",
      }],
      "outtmpl": "recap_audio",
      "quiet": True,
  }

  try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
      ydl.download([url])

    if not os.path.exists(audio_filename):
      # Try finding any mp3 created
      files = [f for f in os.listdir(".") if f.endswith(".mp3")]
      if files:
        audio_filename = files[0]
      else:
        raise Exception("Audio file could not be downloaded.")

    genai.configure(api_key=api_key.strip())
    st.info("🔄 ဗီဒီယိုအသံဖိုင်ကို Gemini AI သို့ တိုက်ရိုက်တင်သွင်းနေပါပြီ...")

    audio_file = genai.upload_file(audio_filename)
    model = genai.GenerativeModel("gemini-1.5-flash")

    prompt = (
        "Listen to this YouTube movie recap audio carefully. Provide a"
        " comprehensive, well-structured Myanmar (Burmese) translation and"
        " detailed story recap script suitable for making a Myanmar movie recap"
        " video script."
    )

    response = model.generate_content([audio_file, prompt])

    # Cleanup
    if os.path.exists(audio_filename):
      os.remove(audio_filename)

    return (
        response.text.strip()
        if response and response.text
        else "Failed to process audio."
    )
  except Exception as e:
    if os.path.exists(audio_filename):
      os.remove(audio_filename)
    raise Exception(f"Audio processing error: {str(e)}")


def fetch_transcript_bulletproof(v_id):
  try:
    tx_list = YouTubeTranscriptApi.list_transcripts(v_id)
    for t in tx_list:
      fetched = t.fetch()
      if fetched:
        return " ".join([entry["text"].strip() for entry in fetched])
  except Exception:
    pass
  return None


if st.button("⚡ Movie Recap Script ထုတ်မည်", type="primary"):
  if not user_api_key:
    st.warning(
        "⚠️ ကျေးဇူးပြု၍ ဘယ်ဘက် Sidebar တွင် Google Gemini API Key ထည့်ပေးပါ။"
    )
  elif video_url:
    video_id = extract_video_id(video_url)
    if not video_id:
      st.error("❌ YouTube Link မမှန်ပါ။ ပြန်စစ်ပေးပါ။")
    else:
      try:
        st.video(video_url)
        full_myanmar_script = ""
        raw_text_combined = ""

        with st.spinner(
            "⏳ Movie Recap ဗီဒီယို၏ အချက်အလက်များကို ဆွဲထုတ်နေပါပြီ..."
        ):
          # First try standard transcript
          transcript_text = fetch_transcript_bulletproof(video_id)

          if transcript_text:
            raw_text_combined = transcript_text
            genai.configure(api_key=user_api_key.strip())
            model = genai.GenerativeModel("gemini-1.5-flash")
            prompt = (
                "Translate and adapt the following YouTube movie recap English"
                " text into an engaging, natural, and fluent Myanmar (Burmese)"
                " script for a movie recap video:\n\n"
                f"{raw_text_combined[:8000]}"
            )
            response = model.generate_content(prompt)
            full_myanmar_script = (
                response.text.strip()
                if response and response.text
                else raw_text_combined
            )
          else:
            # Fallback to direct audio processing via yt-dlp & Gemini File API for hidden/recap videos
            full_myanmar_script = download_audio_and_upload_to_gemini(
                video_url, user_api_key
            )
            raw_text_combined = full_myanmar_script

          words = len(raw_text_combined.split())
          est_read_time = round(words / 150, 1)

          # AI Summary
          genai.configure(api_key=user_api_key.strip())
          sum_model = genai.GenerativeModel("gemini-1.5-flash")
          sum_prompt = (
              "Provide a short summary/logline of this movie recap in both"
              f" English and Myanmar ({summary_length} version):"
              f"\n\n{raw_text_combined[:4000]}"
          )
          sum_res = sum_model.generate_content(sum_prompt)
          summary_text = (
              sum_res.text if sum_res and sum_res.text else "Summary not available."
          )

        st.success("✅ Movie Recap Script အောင်မြင်စွာ ထွက်ရှိလာပါပြီ!")

        if not is_vip:
          increment_user_usage(clean_email)

        m1, m2 = st.columns(2)
        m1.metric("📝 ခန့်မှန်း စာလုံးရေ (Words)", f"{words:,}")
        m2.metric("⏱️ ပြောဆိုဖတ်ရှုချိန်", f"{est_read_time} မိနစ်ခန့်")

        st.markdown("---")

        tab1, tab2, tab3 = st.tabs([
            "🇲🇲 မြန်မာ Movie Recap Script",
            "🤖 AI Story Summary",
            "📥 Audio Voiceover (TTS)",
        ])

        with tab1:
          st.subheader("မြန်မာ Movie Recap Script")
          st.code(full_myanmar_script, height=450)
          st.download_button(
              "📥 Download မြန်မာ Script (.txt)",
              data=full_myanmar_script.encode("utf-8-sig"),
              file_name="movie_recap_myanmar_script.txt",
              mime="text/plain; charset=utf-8",
          )

        with tab2:
          st.subheader("🤖 AI Story Summary & Logline")
          st.write(summary_text)

        with tab3:
          st.subheader("🔊 Myanmar Text-to-Speech (Audio Preview)")
          try:
            tts_text = full_myanmar_script[:400]
            tts = gTTS(text=tts_text, lang="my")
            audio_fp = io.BytesIO()
            tts.write_to_fp(audio_fp)
            audio_fp.seek(0)
            st.audio(audio_fp, format="audio/mp3")
          except Exception as e:
            st.warning(f"Audio TTS မရရှိပါ: {str(e)}")

      except Exception as e:
        st.error(
            "❌ အမှားအယွင်း ဖြစ်ပေါ်သွားပါသည် (Movie Recap Audio/Transcript"
            f" Error): {str(e)}"
        )
  else:
    st.warning("⚠️ ကျေးဇူးပြု၍ YouTube Movie Recap Link ကို ရိုက်ထည့်ပေးပါ။")
    
