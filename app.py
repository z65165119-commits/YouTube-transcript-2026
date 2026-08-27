from datetime import datetime
import json
import os
import re
import google.generativeai as genai
import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi

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
  st.title("🔴⚡ YouTube AI Studio (Movie Recap Pro)")

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
    help=(
        "Streamlit Secrets တွင် ထည့်ထားခြင်း မရှိပါက ဤနေရာတွင် တိုက်ရိုက်"
        " ထည့်နိုင်ပါသည်။"
    ),
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
      "ဆက်လက်အသုံးပြုလိုပါက Telegram **@lynn_m2026** ထံသို့ ဆက်သွယ်၍ **VIP"
      " Access** ရယူပါရန်။"
  )
  st.stop()

# ---------------------------------------------------------
# 🎬 MAIN APP LOGIC
# ---------------------------------------------------------
video_url = st.text_input("🔗 YouTube Movie Recap Video URL ကို ရိုက်ထည့်ပါ:", "")
manual_movie_title = st.text_input(
    "🎬 ရုပ်ရှင်နာမည် (သို့) အဓိက အကြောင်းအရာ (Transcript မရပါက ဤနေရာတွင်"
    " ဖြည့်ပါ):",
    "",
)


def extract_video_id(url):
  match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", url)
  return match.group(1) if match else None


def fetch_transcript_text(v_id):
  try:
    transcript_list = YouTubeTranscriptApi.list_transcripts(v_id)
    for transcript in transcript_list:
      fetched = transcript.fetch()
      if fetched:
        return " ".join([entry["text"].strip() for entry in fetched])
  except Exception as e:
    print(f"Transcript Error: {e}")
  return None


if st.button("⚡ Movie Recap Script ထုတ်မည်", type="primary"):
  if not user_api_key:
    st.warning(
        "⚠️ ကျေးဇူးပြု၍ Google Gemini API Key ကို Streamlit Secrets (သို့) Sidebar"
        " တွင် ထည့်ပေးပါ။"
    )
  elif video_url or manual_movie_title:
    try:
      if video_url:
        st.video(video_url)
        video_id = extract_video_id(video_url)
      else:
        video_id = None

      full_myanmar_script = ""
      source_text = ""

      with st.spinner(
          "⏳ Gemini AI ဖြင့် မြန်မာ Movie Recap Script ကို ဖန်တီးနေပါပြီ..."
      ):
        genai.configure(api_key=user_api_key.strip())
        model = genai.GenerativeModel("gemini-3.6-flash")

        # ၁။ Transcript ဆွဲထုတ်ရန် ကြိုးစားမည်
        transcript_text = None
        if video_id:
          transcript_text = fetch_transcript_text(video_id)

        if transcript_text:
          source_text = transcript_text
          prompt = (
              "You are a professional YouTube Movie Recap scriptwriter. Read"
              " the following English YouTube video transcript and"
              " rewrite/translate it into an extremely engaging, natural,"
              " suspenseful, and fluent Myanmar (Burmese) script suitable"
              " for a voiceover movie recap video. Make it sound professional"
              " and cinematic:\n\n"
              f"{source_text[:15000]}"
          )
        elif manual_movie_title:
          source_text = manual_movie_title
          prompt = (
              f"Provide a comprehensive, highly engaging, suspenseful, and"
              f" cinematic movie recap script in natural Myanmar (Burmese)"
              f" language based on this movie title or topic:"
              f" {manual_movie_title}."
          )
        else:
          st.error(
              "❌ ဤဗီဒီယိုတွင် Transcript မရှိပါ။ ကျေးဇူးပြု၍ အထက်ပါ box"
              " တွင် ရုပ်ရှင်နာမည်ကို ထည့်ပေးပါ။"
          )
          st.stop()

        response = model.generate_content(prompt)
        full_myanmar_script = (
            response.text.strip()
            if response and response.text
            else "AI generation failed."
        )

        words = len(source_text.split())
        est_read_time = round(words / 150, 1) if words > 0 else 5.0

        # ၂။ AI Summary ထုတ်မည်
        sum_model = genai.GenerativeModel("gemini-3.6-flash")
        sum_prompt = (
            "Provide a short captivating summary and logline of this movie in"
            f" both English and Myanmar ({summary_length} version):"
            f"\n\n{source_text[:4000]}"
        )
        sum_res = sum_model.generate_content(sum_prompt)
        summary_text = (
            sum_res.text if sum_res and sum_res.text else "Summary not available."
        )

      st.success("👑 Movie Recap Script အောင်မြင်စွာ ထွက်ရှိလာပါပြီ!")

      if not is_vip:
        increment_user_usage(clean_email)

      m1, m2 = st.columns(2)
      m1.metric("📝 ခန့်မှန်း စာလုံးရေ (Words)", f"{words:,}")
      m2.metric("⏱️ ပြောဆိုဖတ်ရှုချိန်", f"{est_read_time} မိနစ်ခန့်")

      st.markdown("---")

      tab1, tab2 = st.tabs([
          "🇲🇲 မြန်မာ Movie Recap Script",
          "🤖 AI Story Summary",
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

    except Exception as e:
      st.error(f"❌ အမှားအယွင်း ဖြစ်ပေါ်သွားပါသည်: {str(e)}")
  else:
    st.warning(
        "⚠️ ကျေးဇူးပြု၍ YouTube Link (သို့) ရုပ်ရှင်နာမည် တစ်ခုခုကို ထည့်ပေးပါ။"
    )
        
