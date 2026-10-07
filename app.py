from datetime import datetime
import io
import json
import os
import re
import tempfile
import time
from gtts import gTTS
from moviepy.editor import AudioFileClip, VideoFileClip
import requests
import streamlit as st
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi

st.set_page_config(
    page_title="YouTube & RedNote AI Studio Suite",
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


def get_user_data(email):
  db = load_db()
  clean_email = email.strip().lower()
  if clean_email not in db:
    db[clean_email] = {
        "count": 0,
        "first_used": str(datetime.now()),
        "is_vip": False,
        "vip_plan": None,
    }
    save_db(db)
  return db[clean_email]


def increment_user_usage(email):
  db = load_db()
  clean_email = email.strip().lower()
  if clean_email not in db:
    db[clean_email] = {
        "count": 1,
        "first_used": str(datetime.now()),
        "is_vip": False,
        "vip_plan": None,
    }
  else:
    db[clean_email]["count"] += 1
  save_db(db)


# ---------------------------------------------------------
# 🔑 LOGIN SESSION MANAGEMENT & VIP PLANS
# ---------------------------------------------------------
VIP_USERS = {
    "soemoe@gmail.com": "1 Year",
    "phayphaygyi980@gmail.com": "3 Months",
    "zlynn7368@gmail.com": "1 Year",
}

FREE_LIMIT = 5

if "logged_in" not in st.session_state:
  st.session_state["logged_in"] = False
  st.session_state["user_email"] = ""

# ---------------------------------------------------------
# 🔝 HEADER BAR WITH SIGN IN / USER INFO
# ---------------------------------------------------------
col_title, col_auth = st.columns([3, 1])

with col_title:
  st.title("🔴⚡ YouTube & RedNote AI Studio")

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
is_vip = clean_email in [e.lower() for e in VIP_USERS.keys()]
user_vip_plan = VIP_USERS.get(clean_email, "Free")
user_data = get_user_data(clean_email)
current_usage = user_data["count"]

# ---------------------------------------------------------
# ⚙️ SIDEBAR - USER ACCOUNT & VIP PACKAGES
# ---------------------------------------------------------
st.sidebar.header("👤 Account Info")
st.sidebar.write(f"**Logged in as:**\n{clean_email}")

if is_vip:
  st.sidebar.success(f"👑 **VIP Member ({user_vip_plan})**")
else:
  remaining = max(0, FREE_LIMIT - current_usage)
  st.sidebar.info(f"🎁 အခမဲ့ သုံးစွဲခွင့် ကျန်ရှိသည့်အကြိမ်: {remaining} / {FREE_LIMIT}")

st.sidebar.markdown("---")
st.sidebar.header("💎 VIP နှုန်းထားများ & အစီအစဉ်များ")
st.sidebar.markdown("""
- **၁ လစာ (1 Month):** 5,000 MMK / 5$
- **၂ လစာ (2 Months):** 9,000 MMK / 9$
- **၃ လစာ (3 Months):** 12,000 MMK / 12$
- **၁ နှစ်စာ (1 Year):** 35,000 MMK / 35$
""")
st.sidebar.markdown(
    "💬 **VIP ဝယ်ယူရန် ဆက်သွယ်ရန်:**\nTelegram: [@lynn_m2026](https://t.me/lynn_m2026)"
)

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Options & AI Voice Settings")
show_timestamp = st.sidebar.checkbox("Timestamps ထည့်ရန်", value=False)
summary_length = st.sidebar.select_slider(
    "AI Summary အတိုအရှည်",
    options=["Short", "Medium", "Detailed"],
    value="Medium",
)

voice_gender = st.sidebar.selectbox(
    "🎙️ AI အသံအမျိုးအစား (Voice Type)",
    [
        "Normal / Female (အမျိုးသမီးသံ)",
        "Deep Man (အမျိုးသားအသံကြီး)",
        "Young Boy (ကောင်လေးအသံ)",
        "Energetic Narrator (ဇာတ်ကြောင်းပြောသူ အသံ)",
    ],
    index=0,
)

if not is_vip and current_usage >= FREE_LIMIT:
  st.error("❌ သင့်၏ အခမဲ့ ၅ ကြိမ် အသုံးပြုခွင့် ကုန်ဆုံးသွားပါပြီ။")
  st.warning(
      "ဆက်လက်အသုံးပြုလိုပါက Telegram **@lynn_m2026** ထံသို့ ဆက်သွယ်၍ **VIP"
      " Packages (၁လ၊ ၂လ၊ ၃လ၊ ၁နှစ်)** ကို ဝယ်ယူအားပေးနိုင်ပါသည်။"
  )
  st.stop()

# ---------------------------------------------------------
# 🎬 MAIN APP LOGIC
# ---------------------------------------------------------
video_url = st.text_input(
    "🔗 YouTube သို့မဟုတ် RedNote (Xiaohongshu) Video URL ကို ရိုက်ထည့်ပါ:", ""
)
manual_text_input = st.text_area(
    "📝 (သို့မဟုတ်) RedNote ဗီဒီယိုထဲက တရုတ်စာသားများကို တိုက်ရိုက်ကူးထည့်ရန်:",
    "",
    placeholder=(
        "ဗီဒီယိုလင့်ခ်မှ စာသားဖတ်မရပါက ဤနေရာတွင် တရုတ်စာသားများကို"
        " ကူးထည့်ပေးနိုင်ပါသည်..."
    ),
)


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


def translate_mymemory(text):
  if not text.strip():
    return ""

  max_len = 450
  sentences = [
      text[i : i + max_len] for i in range(0, len(text), max_len)
  ]
  translated_chunks = []

  for part in sentences:
    try:
      url = "https://api.mymemory.translated.net/get"
      params = {"q": part, "langpair": "zh|my"}
      response = requests.get(url, params=params, timeout=10)
      if response.status_code == 200:
        data = response.json()
        translated_text = data.get("responseData", {}).get(
            "translatedText", ""
        )
        if translated_text and "MYMEMORY WARNING" not in translated_text:
          translated_chunks.append(translated_text)
        else:
          translated_chunks.append(part)
      else:
        translated_chunks.append(part)
    except Exception:
      translated_chunks.append(part)
    time.sleep(0.3)

  return " ".join(translated_chunks)


def download_and_process_video(v_url, audio_path, output_path):
  """yt-dlp ဖြင့် ဗီဒီယိုဖိုင်ကို Download ဆွဲပြီး moviepy ဖြင့် မြန်မာအသံ (Voiceover) ကို ပေါင်းထည့်ခြင်း"""
  ydl_opts = {
      "format": "best[ext=mp4]/best",
      "outtmpl": output_path,
      "quiet": True,
      "geo_bypass": True,
      "http_headers": {
          "User-Agent": (
              "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
              " (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
          )
      },
  }

  try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
      ydl.download([v_url])

    # MoviePy ဖြင့် ဗီဒီယိုနှင့် အသံအသစ် ပေါင်းစပ်ခြင်း
    video_clip = VideoFileClip(output_path)
    audio_clip = AudioFileClip(audio_path)

    # အသံအရှည်ကို ဗီဒီယိုအရှည်နှင့် ညှိရန် (သို့မဟုတ် ဗီဒီယိုအသံကို ဖယ်ရှား၍ မြန်မာအသံအစားထိုးရန်)
    final_clip = video_clip.set_audio(audio_clip)
    final_output = output_path.replace(".mp4", "_myanmar.mp4")
    final_clip.write_videofile(
        final_output,
        codec="libx264",
        audio_codec="aac",
        logger=None,
    )

    video_clip.close()
    audio_clip.close()
    return final_output
  except Exception as e:
    return None


if st.button("⚡ မြန်မာအသံပါ ဗီဒီယိုအသစ် ထုတ်လုပ်မည်", type="primary"):
  if manual_text_input.strip() or video_url:
    try:
      with st.spinner("⏳ စာသားများကို ဘာသာပြန်ဆို၍ အသံဖိုင် ဖန်တီးနေပါသည်..."):
        if manual_text_input.strip():
          pure_raw_text = manual_text_input.strip()
          fetched_transcript = [{
              "text": pure_raw_text,
              "start": 0.0,
              "duration": 10.0,
          }]
        else:
          # Metadata / Title ယူရန်
          with yt_dlp.YoutubeDL({"quiet": True, "skip_download": True}) as ydl:
            info = ydl.extract_info(video_url, download=False)
            title = info.get("title", "RedNote Video")
            description = info.get("description", "")
            pure_raw_text = f"{title}. {description}".strip()
          fetched_transcript = [{
              "text": pure_raw_text,
              "start": 0.0,
              "duration": 10.0,
          }]

        myanmar_translation = translate_mymemory(pure_raw_text[: 4000 * 3])
        srt_content = generate_srt(fetched_transcript)

        # gTTS ဖြင့် မြန်မာအသံဖိုင် ဖန်တီးခြင်း
        tld_setting = "com"
        if "Man" in voice_gender or "Boy" in voice_gender:
          tld_setting = "com.sg"

        tts = gTTS(
            text=myanmar_translation[:1500], lang="my", tld=tld_setting
        )
        audio_fp = io.BytesIO()
        tts.write_to_fp(audio_fp)
        audio_fp.seek(0)

        # Temporary Audio File သိမ်းဆည်းရန်
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_audio:
          tmp_audio.write(audio_fp.read())
          tmp_audio_path = tmp_audio.name

      # ဗီဒီယိုပါရှိလျှင် MoviePy ဖြင့် ပေါင်းစပ်ထုတ်လုပ်ခြင်း
      final_video_path = None
      if video_url:
        with st.spinner(
            "⏳ Original ဗီဒီယိုကို ဒေါင်းလုဒ်ဆွဲ၍ မြန်မာအသံနှင့် ချိတ်ဆက်နေပါသည်"
            " (ခဏစောင့်ပါ)..."
        ):
          with tempfile.NamedTemporaryFile(
              delete=False, suffix=".mp4"
          ) as tmp_vid:
            tmp_vid_path = tmp_vid.name
          final_video_path = download_and_process_video(
              video_url, tmp_audio_path, tmp_vid_path
          )

      st.success("✅ အားလုံး အောင်မြင်စွာ ဆောင်ရွက်ပြီးပါပြီ!")

      if not is_vip:
        increment_user_usage(clean_email)

      tab1, tab2, tab3, tab4 = st.tabs([
          "🎬 မြန်မာအသံပါ ဗီဒီယို (Final Video)",
          "🔊 မြန်မာအသံ (Voiceover MP3)",
          "🌐 မြန်မာ ဘာသာပြန် Script",
          "📥 Subtitles (.srt)",
      ])

      with tab1:
        st.subheader("🎥 မြန်မာအသံထွက်ဖြင့် ပြန်လည်ထုတ်လုပ်ထားသော ဗီဒီယို")
        if final_video_path and os.path.exists(final_video_path):
          st.video(final_video_path)
          with open(final_video_path, "rb") as f:
            st.download_button(
                "📥 Download မြန်မာအသံပါ ဗီဒီယိုဖိုင် (.mp4)",
                data=f,
                file_name="myanmar_voiceover_video.mp4",
                mime="video/mp4",
            )
        else:
          st.warning(
              "⚠️ ဗီဒီယိုလင့်ခ်မှ ဗီဒီယိုဖိုင် నేరుವಾಗಿ ဒေါင်းလုဒ်ဆွဲ၍မရပါ"
              " (သို့မဟုတ် လင့်ခ်ကန့်သတ်ချက်ရှိပါသည်။) သို့သော် အောက်ပါ Tab"
              " များတွင် အသံဖိုင်နှင့် စာသားများကို ရယူနိုင်ပါသည်။"
          )
          if video_url:
            st.video(video_url)

      with tab2:
        st.subheader("🔊 Myanmar Voiceover MP3")
        st.audio(tmp_audio_path, format="audio/mp3")
        with open(tmp_audio_path, "rb") as af:
          st.download_button(
              "📥 Download Voiceover MP3 (.mp3)",
              data=af,
              file_name="myanmar_voiceover.mp3",
              mime="audio/mp3",
          )

      with tab3:
        st.subheader("🇲🇲 မြန်မာ ဘာသာပြန် Script")
        st.code(myanmar_translation)
        st.download_button(
            "📥 Download မြန်မာ Script (.txt)",
            data=myanmar_translation.encode("utf-8-sig"),
            file_name="myanmar_script.txt",
            mime="text/plain; charset=utf-8",
        )

      with tab4:
        st.subheader("📄 SRT Subtitle File")
        st.code(srt_content)
        st.download_button(
            "📥 Download Subtitle (.srt)",
            data=srt_content.encode("utf-8-sig"),
            file_name="subtitle.srt",
            mime="text/plain; charset=utf-8",
        )

    except Exception as e:
      st.error(f"❌ အမှားအယွင်း ဖြစ်ပေါ်သွားပါသည်: {str(e)}")
  else:
    st.warning(
        "⚠️ ကျေးဇူးပြု၍ ဗီဒီယို Link ထည့်ပါ (သို့မဟုတ်) တရုတ်စာသားများကို"
        " ကူးထည့်ပေးပါ။"
    )
    
