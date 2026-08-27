from datetime import datetime
import json
import os
import re
import google.generativeai as genai
import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi

st.set_page_config(
    page_title="DeepLearn AI - YouTube Myanmar Text Script",
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
  st.title("🎬 DeepLearn AI - YouTube Myanmar Text Script")

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

if not is_vip and current_usage >= FREE_LIMIT:
  st.error("❌ သင့်၏ အခမဲ့ ၅ ကြိမ် အသုံးပြုခွင့် ကုန်ဆုံးသွားပါပြီ။")
  st.warning("ဆက်လက်အသုံးပြုလိုပါက Telegram **@lynn_m2026** ထံသို့ ဆက်သွယ်ပါ။")
  st.stop()

# ---------------------------------------------------------
# 🎬 MAIN APP LOGIC
# ---------------------------------------------------------
video_url = st.text_input("🔗 YouTube Video URL ကို ရိုက်ထည့်ပါ:", "")


def extract_video_id(url):
  match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", url)
  return match.group(1) if match else None


def fetch_transcript_items(video_id):
  try:
    # Fetch list of transcripts, supporting auto-generated/manual english or any available language
    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
    transcript = None

    try:
      transcript = transcript_list.find_transcript(["en", "en-US", "my"])
    except Exception:
      for tr in transcript_list:
        transcript = tr
        break

    if transcript:
      return transcript.fetch()
  except Exception:
    try:
      # Fallback to direct get_transcript if list_transcripts fails
      return YouTubeTranscriptApi.get_transcript(video_id, languages=["en", "my"])
    except Exception as e:
      st.error(f"Transcript ထုတ်ယူရာတွင် အမှားရှိပါသည်: {str(e)}")
      return None
  return None


if st.button("⚡ မြန်မာစာ Script ထုတ်မည်", type="primary"):
  active_key = user_api_key.strip() if user_api_key else secret_api_key
  if not active_key:
    st.warning(
        "⚠️ ကျေးဇူးပြု၍ Sidebar တွင် Google Gemini API Key ထည့်ပေးပါ (သို့မဟုတ်"
        " Secrets တွင် သတ်မှတ်ပေးပါ)။"
    )
  elif video_url:
    video_id = extract_video_id(video_url)
    if not video_id:
      st.error("❌ YouTube Link မမှန်ပါ။ ပြန်စစ်ပေးပါ။")
    else:
      try:
        st.video(video_url)
        full_myanmar_script = ""

        with st.spinner(
            "⏳ YouTube Transcript ဆွဲထုတ်နေပြီး Gemini AI ဖြင့်"
            " မြန်မာလိုဘာသာပြန်နေပါပြီ..."
        ):
          transcript_items = fetch_transcript_items(video_id)

          if transcript_items:
            genai.configure(api_key=active_key)
            model = genai.GenerativeModel("gemini-1.5-flash")

            chunk_size = 60
            for i in range(0, len(transcript_items), chunk_size):
              chunk = transcript_items[i : i + chunk_size]
              chunk_text = ""
              for item in chunk:
                start_time = int(item.get("start", 0))
                minutes = start_time // 60
                seconds = start_time % 60
                time_str = f"[{minutes:02d}:{seconds:02d}]"
                chunk_text += f"{time_str} {item.get('text', '').strip()}\n"

              prompt = (
                  "You are an expert translator. Below is a segment of a"
                  " YouTube video transcript with timestamps. Translate the"
                  " spoken text line-by-line into natural, fluent, spoken-style"
                  " Myanmar (Burmese) language so the user can easily read and"
                  " record their own voiceover. Keep the timestamps like [00:15]"
                  " so the user knows when each part is spoken.\n\nSegment:\n"
                  f"{chunk_text}"
              )

              response = model.generate_content(prompt)
              if response and response.text:
                full_myanmar_script += response.text.strip() + "\n"

            if full_myanmar_script:
              st.success("👑 မြန်မာစာ Script အောင်မြင်စွာ ထွက်ရှိလာပါပြီ!")

              if not is_vip:
                increment_user_usage(clean_email)

              st.markdown("---")
              st.subheader("📝 မြန်မာစာ Script (Voiceover ဖတ်ရန်)")
              st.code(full_myanmar_script, height=500)
              st.download_button(
                  "📥 Download မြန်မာ Script (.txt)",
                  data=full_myanmar_script.encode("utf-8-sig"),
                  file_name="youtube_myanmar_script.txt",
                  mime="text/plain; charset=utf-8",
              )
            else:
              st.error("❌ ဘာသာပြန်ဆိုမှု အထွက် မရှိပါ။")
          else:
            st.error(
                "❌ ဤဗီဒီယိုတွင် Transcript (စာတန်းထိုး) ရယူ၍မရပါ သို့မဟုတ်"
                " ပိတ်ထားခြင်း ဖြစ်နိုင်ပါသည်။"
            )

      except Exception as e:
        st.error(f"❌ အမှားအယွင်း ဖြစ်ပေါ်သွားပါသည်: {str(e)}")
  else:
    st.warning("⚠️ ကျေးဇူးပြု၍ YouTube Video Link ကို ရိုက်ထည့်ပေးပါ။")
                                                 
