from datetime import datetime
import io
import os
import re
import tempfile
import google.generativeai as genai
from gtts import gTTS
from moviepy.editor import AudioFileClip, VideoFileClip
import streamlit as st
from yt_dlp import YoutubeDL
from youtube_transcript_api import YouTubeTranscriptApi

st.set_page_config(
    page_title="DeepLearn AI - Movie Recap Studio Pro",
    page_icon="🎬",
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
        import json

        return json.load(f)
    except Exception:
      return {}
  return {}


def save_db(db):
  with open(DB_FILE, "w", encoding="utf-8") as f:
    import json

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
  st.title("🎬 DeepLearn AI - Movie Recap Studio Pro")

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

secret_api_key = ""
try:
  if "GEMINI_API_KEY" in st.secrets:
    secret_api_key = st.secrets["GEMINI_API_KEY"]
except Exception:
  pass

user_api_key = st.sidebar.text_input(
    "API Key ထည့်ရန်",
    value=secret_api_key,
    type="password",
    help="Streamlit Secrets မှ သို့မဟုတ် ဤနေရာတွင် တိုက်ရိုက်ထည့်ပါ။",
)

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Video Options")
voice_speed = st.sidebar.selectbox(
    "အသံထွက် အမြန်နှုန်း", ["Normal", "Fast (1.25x)"], index=0
)

if not is_vip and current_usage >= FREE_LIMIT:
  st.error("❌ သင့်၏ အခမဲ့ ၅ ကြိမ် အသုံးပြုခွင့် ကုန်ဆုံးသွားပါပြီ။")
  st.warning("ဆက်လက်အသုံးပြုလိုပါက Telegram **@lynn_m2026** ထံသို့ ဆက်သွယ်ပါ။")
  st.stop()

# ---------------------------------------------------------
# 🎬 MAIN APP LOGIC
# ---------------------------------------------------------
video_url = st.text_input("🔗 YouTube Movie Recap Video URL ကို ရိုက်ထည့်ပါ:", "")


def extract_video_id(url):
  match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", url)
  return match.group(1) if match else None


def download_youtube_video(url, output_path):
  ydl_opts = {
      "format": "best[ext=mp4]/best",
      "outtmpl": output_path,
      "quiet": True,
  }
  with YoutubeDL(ydl_opts) as ydl:
    ydl.download([url])


if st.button("⚡ Ready-to-Post Recap Video ထုတ်မည်", type="primary"):
  if not user_api_key:
    st.warning("⚠️ ကျေးဇူးပြု၍ Google Gemini API Key ထည့်ပေးပါ။")
  elif video_url:
    video_id = extract_video_id(video_url)
    if not video_id:
      st.error("❌ YouTube Link မမှန်ပါ။ ပြန်စစ်ပေးပါ။")
    else:
      try:
        with tempfile.TemporaryDirectory() as tmpdir:
          video_filename = os.path.join(tmpdir, "source_video.mp4")
          output_video_filename = os.path.join(tmpdir, "final_recap_video.mp4")
          audio_filename = os.path.join(tmpdir, "myanmar_voice.mp3")

          with st.spinner(
              "⏳ ၁/၄ - YouTube ဗီဒီယိုနှင့် အချက်အလက်များကို"
              " ဆွဲထုတ်နေပါပြီ..."
          ):
            try:
              download_youtube_video(video_url, video_filename)
            except Exception:
              st.error(
                  "❌ YouTube ဗီဒီယိုကို တိုက်ရိုက်ဒေါင်းလုဒ်ဆွဲ၍ မရပါ။"
                  " (Server ကန့်သတ်ချက်)"
              )
              st.stop()

            # Transcript ဖမ်းယူခြင်း
            transcript_text = ""
            try:
              tx_list = YouTubeTranscriptApi.list_transcripts(video_id)
              for t in tx_list:
                fetched = t.fetch()
                if fetched:
                  transcript_text = " ".join(
                      [entry["text"].strip() for entry in fetched]
                  )
                  break
            except Exception:
              pass

          with st.spinner(
              "⏳ ၂/၄ - Gemini AI ဖြင့် မြန်မာ Movie Recap Script"
              " ရေးသားနေပါပြီ..."
          ):
            genai.configure(api_key=user_api_key.strip())
            model = genai.GenerativeModel("gemini-2.5-flash")

            if not transcript_text:
              transcript_text = (
                  "Cinematic movie recap story based on link: " + video_url
              )

            prompt = (
                "Translate and rewrite the following into an engaging, natural,"
                " and smooth Myanmar (Burmese) voiceover script for a TikTok"
                " movie recap video. Keep it punchy and exciting:\n\n"
                f"{transcript_text[:12000]}"
            )
            response = model.generate_content(prompt)
            myanmar_script = (
                response.text.strip()
                if response and response.text
                else "ဇာတ်လမ်းအကျဉ်း"
            )

          with st.spinner(
              "⏳ ၃/၄ - မြန်မာအသံဖိုင် (Voiceover) ဖန်တီးနေပါပြီ..."
          ):
            # gTTS ဖြင့် မြန်မာအသံထုတ်ယူခြင်း (အက္ခရာ ၄၀၀၀ ကန့်သတ်ချက်ကို ထိန်းချုပ်ရန်)
            tts_text = myanmar_script[
                :3000
            ]  # First part for audio generation
            tts = gTTS(text=tts_text, lang="my", slow=False)
            tts.save(audio_filename)

          with st.spinner(
              "⏳ ၄/၄ - မူရင်းဗီဒီယိုနှင့် မြန်မာအသံကို ပေါင်းစပ်နေပါပြီ"
              " (Video Rendering)..."
          ):
            # MoviePy ဖြင့် ဗီဒီယိုနှင့် အသံပေါင်းစပ်ခြင်း
            video_clip = VideoFileClip(video_filename)
            audio_clip = AudioFileClip(audio_filename)

            # အသံအရှည်နဲ့ ဗီဒီယိုအရှည် ကိုက်ညီအောင် လုပ်ဆောင်ခြင်း
            if audio_clip.duration < video_clip.duration:
              video_clip = video_clip.subclip(0, audio_clip.duration)
            else:
              # ဗီဒီယိုထက် အသံကပိုရှည်ရင် ဗီဒီယိုကို Loop လုပ်ရန် (သို့မဟုတ် အသံအတိုင်းထားရန်)
              pass

            final_clip = video_clip.set_audio(audio_clip)
            final_clip.write_videofile(
                output_video_filename,
                codec="libx264",
                audio_codec="aac",
                fps=24,
                preset="ultrafast",
                logger=None,
            )

            # ဖိုင်ကို Read လုပ်ရန်
            with open(output_video_filename, "rb") as f:
              video_bytes = f.read()

          st.success("🎉 အောင်မြင်ပါပြီ! Ready-to-post Recap Video ထွက်လာပါပြီ။")

          if not is_vip:
            increment_user_usage(clean_email)

          # ဗီဒီယို Preview ပြသရန်နှင့် Download ခလုတ်
          st.video(output_video_filename)

          st.download_button(
              label="📥 Download Ready-to-Post Video (.mp4)",
              data=video_bytes,
              file_name="myanmar_movie_recap.mp4",
              mime="video/mp4",
          )

          with st.expander("📝 ထွက်လာသော မြန်မာ Script ကို ကြည့်ရန်"):
            st.write(myanmar_script)

      except Exception as e:
        st.error(
            f"❌ ဗီဒီယိုထုတ်လုပ်ရာတွင် အမှားအယွင်း ဖြစ်ပေါ်သွားပါသည်: {str(e)}"
        )
  else:
    st.warning("⚠️ ကျေးဇူးပြု၍ YouTube Movie Recap Link ကို ရိုက်ထည့်ပေးပါ။")
            
