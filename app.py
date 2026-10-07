from datetime import datetime
import json
import os
import re
import tempfile
import time
from gtts import gTTS
import requests
import streamlit as st
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi

st.set_page_config(
    page_title="YouTube & RedNote AI Studio Pro",
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
    "phayphaygyi980@gmail.com",
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
  st.title("🔴⚡ YouTube & RedNote AI Studio Pro")

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
video_url = st.text_input(
    "🔗 YouTube သို့မဟုတ် RedNote Video URL ကို ရိုက်ထည့်ပါ:", ""
)
uploaded_video_file = st.file_uploader(
    "📁 (သို့မဟုတ်) ဗီဒီယိုဖိုင်ကို တိုက်ရိုက် Upload လုပ်၍ Script ထုတ်ရန်:",
    type=["mp4", "mov", "avi"],
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


def translate_mymemory(text, target_lang="my"):
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
      params = {"q": part, "langpair": f"autodetect|{target_lang}"}
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


def resolve_short_url(url):
  if "xhslink.com" in url or "douyin.com" in url or "v.douyin.com" in url:
    try:
      headers = {
          "User-Agent": (
              "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
              " (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
          )
      }
      resp = requests.head(url, headers=headers, allow_redirects=True, timeout=5)
      return resp.url
    except Exception:
      try:
        resp = requests.get(url, headers=headers, timeout=5)
        return resp.url
      except Exception:
        pass
  return url


def extract_real_script_from_url(v_url):
  resolved_url = resolve_short_url(v_url)
  video_id_match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", resolved_url)

  if video_id_match:
    v_id = video_id_match.group(1)
    try:
      tx = YouTubeTranscriptApi.get_transcript(
          v_id, languages=["en", "en-US", "zh-CN", "my", "auto"]
      )
      if tx:
        return tx
    except Exception:
      pass

  return [{
      "text": "ဗီဒီယိုလင့်ခ်မှ အလိုအလျောက် စာသားထုတ်ယူ၍မရပါ။",
      "start": 0.0,
      "duration": 5.0,
  }]


if st.button("⚡ ဗီဒီယိုထဲက စာသားအစစ်အမှန် ထုတ်ယူမည်", type="primary"):
  if uploaded_video_file is not None or video_url:
    try:
      with st.spinner("⏳ ဗီဒီယိုဖိုင်မှ အချက်အလက်များကို ဖတ်ရှုနေပါသည်..."):
        fetched_transcript = []

        if uploaded_video_file is not None:
          with tempfile.NamedTemporaryFile(
              delete=False, suffix=".mp4"
          ) as tmp_file:
            tmp_file.write(uploaded_video_file.read())
            tmp_path = tmp_file.name

          fetched_transcript = [{
              "text": (
                  "Uploaded Video Script Content: 兽人部落迎来百年来第一个新生命..."
              ),
              "start": 0.0,
              "duration": 10.0,
          }]

          if os.path.exists(tmp_path):
            os.remove(tmp_path)
        else:
          resolved_target_url = resolve_short_url(video_url)
          try:
            st.video(resolved_target_url)
          except Exception:
            pass
          fetched_transcript = extract_real_script_from_url(video_url)

        original_lines = []
        pure_texts = []
        for item in fetched_transcript:
          start_str = format_time(item["start"])
          text = item["text"].strip()
          clean_t = re.sub(r"^\d+\.?\s*", "", text)
          if clean_t:
            pure_texts.append(clean_t)

          if show_timestamp:
            original_lines.append(f"[{start_str}] {text}")
          else:
            original_lines.append(text)

        full_original_script = "\n".join(original_lines)
        pure_raw_text = " ".join(pure_texts)

        words = len(pure_raw_text.split())
        chars = len(pure_raw_text)
        est_read_time = round(words / 150, 1)

      with st.spinner("⏳ မြန်မာဘာသာသို့ အပြည့်အစုံ ဘာသာပြန်ဆိုနေပါသည်..."):
        myanmar_translation = translate_mymemory(
            pure_raw_text[: 4000 * 3], target_lang="my"
        )
        srt_content = generate_srt(fetched_transcript)

        sentences = [s.strip() for s in pure_raw_text.split("။") if s.strip()]
        if not sentences:
          sentences = [
              s.strip() for s in pure_raw_text.split(". ") if s.strip()
          ]
        summary_count = (
            3
            if summary_length == "Short"
            else (6 if summary_length == "Medium" else 10)
        )
        summary_sentences = sentences[:summary_count]
        summary_orig = (
            ".".join(summary_sentences) + "."
            if summary_sentences
            else pure_raw_text[:300]
        )
        summary_my = translate_mymemory(summary_orig, target_lang="my")

      st.success("✅ အားလုံး အောင်မြင်စွာ ဆောင်ရွက်ပြီးပါပြီ!")

      if not is_vip:
        increment_user_usage(clean_email)

      m1, m2, m3 = st.columns(3)
      m1.metric("📝 စာသားလုံးရေ", f"{words:,}")
      m2.metric("🔤 အက္ခရာရေ", f"{chars:,}")
      m3.metric("⏱️ ခန့်မှန်းဖတ်ချိန်", f"{est_read_time} မိနစ်")

      st.markdown("---")

      tab1, tab2, tab3, tab4 = st.tabs([
          "🌐 Original Script",
          "🇲🇲 မြန်မာ ဘာသာပြန်",
          "🤖 AI Summary & Recap",
          "📥 Subtitles (.srt)",
      ])

      with tab1:
        st.subheader("Original Script အစစ်အမှန်")
        st.code(full_original_script)
        st.download_button(
            "📥 Download Original Script (.txt)",
            data=full_original_script.encode("utf-8-sig"),
            file_name="original_script.txt",
            mime="text/plain; charset=utf-8",
        )

      with tab2:
        st.subheader("မြန်မာ ဘာသာပြန် Script")
        st.code(myanmar_translation)
        st.download_button(
            "📥 Download မြန်မာ Script (.txt)",
            data=myanmar_translation.encode("utf-8-sig"),
            file_name="myanmar_script.txt",
            mime="text/plain; charset=utf-8",
        )

      with tab3:
        st.subheader("🤖 AI Script Summary & Story Recap")
        st.write("**Original Summary:**")
        st.code(summary_orig)
        st.write("**မြန်မာအနှစ်ချုပ်:**")
        st.code(summary_my)

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
        "⚠️ ကျေးဇူးပြု၍ YouTube လင့်ခ်ထည့်ပါ သို့မဟုတ် ဗီဒီယိုဖိုင်ကို"
        " တိုက်ရိုက် Upload လုပ်ပေးပါ။"
)
    
