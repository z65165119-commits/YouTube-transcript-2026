from datetime import datetime
import json
import os
import re
import time
import requests
import streamlit as st
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi

st.set_page_config(
    page_title="YouTube & RedNote Script Studio",
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
  st.title("🔴⚡ YouTube & RedNote Script Studio")

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
st.sidebar.header("⚙️ Script Options")
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
    "📝 (သို့မဟုတ်) ဗီဒီယိုထဲက စာသားများကို တိုက်ရိုက်ကူးထည့်ရန် (Optional):",
    "",
    placeholder=(
        "လင့်ခ်မှ စာသားဖတ်မရပါက ဤနေရာတွင် တရုတ် (သို့မဟုတ်) အင်္ဂလိပ်"
        " စာသားများကို တိုက်ရိုက်ကူးထည့်နိုင်ပါသည်..."
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
      params = {"q": part, "langpair": "autodetect|my"}
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


def fetch_script_universal(v_url):
  resolved_url = resolve_short_url(v_url)

  video_id_match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", resolved_url)
  if video_id_match:
    try:
      v_id = video_id_match.group(1)
      tx = YouTubeTranscriptApi.get_transcript(
          v_id, languages=["en", "en-US", "zh-CN", "my", "auto"]
      )
      if tx:
        return tx
    except Exception:
      pass

  ydl_opts = {
      "skip_download": True,
      "writesubtitles": True,
      "writeautomaticsub": True,
      "subtitleslangs": ["en", "zh", "zh-CN", "my", "en-US"],
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
      info = ydl.extract_info(resolved_url, download=False)
      title = info.get("title", "Video Post")
      description = info.get("description", "")
      duration = info.get("duration", 10.0)

      combined_meta = f"{title}. {description}".strip()
      if combined_meta:
        return [{
            "text": combined_meta,
            "start": 0.0,
            "duration": duration if duration else 10.0,
        }]
  except Exception:
    pass

  return [{
      "text": (
          "ဗီဒီယိုလင့်ခ်မှ အလိုအလျောက် စာသားထုတ်ယူ၍မရပါ။ ကျေးဇူးပြု၍"
          " အထက်ပါ စာသားထည့်ရန် နေရာတွင် တိုက်ရိုက်ကူးထည့်ပါ။"
      ),
      "start": 0.0,
      "duration": 5.0,
  }]


if st.button("⚡ Script ထုတ်ယူမည်", type="primary"):
  if manual_text_input.strip() or video_url:
    try:
      resolved_target_url = (
          resolve_short_url(video_url) if video_url else ""
      )

      if resolved_target_url:
        st.video(resolved_target_url)

      with st.spinner("⏳ စာသားများနှင့် အချက်အလက်များကို ထုတ်ယူနေပါသည်..."):
        if manual_text_input.strip():
          pure_raw_text = manual_text_input.strip()
          fetched_transcript = [{
              "text": pure_raw_text,
              "start": 0.0,
              "duration": 10.0,
          }]
        else:
          fetched_transcript = fetch_script_universal(video_url)

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

      with st.spinner(
          "⏳ မြန်မာဘာသာသို့ အပိုင်းလိုက် ဘာသာပြန်ဆိုနေပါသည်..."
      ):
        myanmar_translation = translate_mymemory(pure_raw_text[: 4000 * 3])
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
        summary_my = translate_mymemory(summary_orig)

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
        st.subheader("Original Script")
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
        st.write("**မြန်မာအနှစ်ချုပ် / ပြန်လည်ဆန်းသစ်ချက်:**")
        st.code(summary_my)

      with tab4:
        st.subheader("📄 SRT Subtitle File")
        st.code(srt_content[:2000] + "\n[Truncated Preview]")
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
        "⚠️ ကျေးဇူးပြု၍ ဗီဒီယို Link ထည့်ပါ (သို့မဟုတ်) အောက်ပါ စာသားထည့်ရန်"
        " နေရာတွင် စာသားများ ရိုက်ထည့်/ကူးထည့်ပေးပါ။"
      )
      
