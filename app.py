from datetime import datetime
import io
import json
import os
from gtts import gTTS
import requests
import streamlit as st

st.set_page_config(
    page_title="Script to Myanmar Voice & Text", page_icon="🇲🇲", layout="wide"
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
  st.title("🇲🇲 ယူကျု့နှင့် အခြား Script များကို မြန်မာအသံသို့ ပြောင်းရန်")

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
# 📝 MAIN INPUT & TRANSLATE + TTS LOGIC
# ---------------------------------------------------------
st.markdown(
    "💡 **ဗီဒီယို၏ အင်္ဂလိပ် Script (သို့မဟုတ်) စာသားများကို အောက်ပါ Box"
    " ထဲတွင် Copy ကူးထည့်ပါ။ မြန်မာဘာသာသို့ အလိုအလျောက် ပြောင်းပေးပြီး"
    " မြန်မာအသံဖိုင် (MP3) ပါ ထုတ်ပေးပါမည်။**"
)

input_script = st.text_area(
    "✍️ Script / စာသားများ ထည့်သွင်းရန် (Paste here):", height=250
)


def translate_to_myanmar(text):
  if not text.strip():
    return ""
  max_len = 500
  chunks = [text[i : i + max_len] for i in range(0, len(text), max_len)]
  translated_chunks = []
  for chunk in chunks:
    try:
      url = "https://translate.googleapis.com/translate_a/single"
      params = {
          "client": "gtx",
          "sl": "auto",
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
          translated_chunks.append(translated)
    except Exception:
      pass
  return " ".join(translated_chunks) if translated_chunks else text


if st.button("🚀 မြန်မာစာသားနှင့် အသံဖိုင် (MP3) ထုတ်မည်", type="primary"):
  if input_script:
    with st.spinner(
        "⏳ မြန်မာဘာသာသို့ ဘာသာပြန်ခြင်းနှင့် အသံဖိုင် ဖန်တီးနေပါသည်..."
    ):
      myanmar_text = translate_to_myanmar(input_script)

    if not is_vip:
      increment_user_usage(clean_email)

    st.success("✅ အောင်မြင်စွာ ဖန်တီးပြီးပါပြီ!")

    words = len(myanmar_text.split())
    chars = len(myanmar_text)
    m1, m2 = st.columns(2)
    m1.metric("📝 မြန်မာစာလုံးရေ", f"{words:,}")
    m2.metric("🔤 အက္ခရာရေ", f"{chars:,}")

    st.markdown("---")

    tab1, tab2 = st.tabs(
        ["🇲🇲 ရရှိလာသော မြန်မာ Script", "🔊 မြန်မာအသံဖိုင် (MP3 Voiceover)"]
    )

    with tab1:
      st.subheader("မြန်မာဘာသာပြန် Script")
      st.code(myanmar_text, height=350)
      st.download_button(
          "📥 Download မြန်မာ Script (.txt)",
          data=myanmar_text.encode("utf-8-sig"),
          file_name="myanmar_script.txt",
          mime="text/plain; charset=utf-8",
      )

    with tab2:
      st.subheader("🔊 မြန်မာအသံဖိုင် နားဆင်ရန်နှင့် ဒေါင်းလုပ်ဆွဲရန်")
      try:
        # gTTS Character Limit အကန့်အသတ်မရှိစေရန် အပိုင်းလိုက် သို့မဟုတ် အများဆုံး ၃၀၀၀ လုံး ယူမည်
        tts_text = myanmar_text[:3000] if len(myanmar_text) > 3000 else myanmar_text
        tts = gTTS(text=tts_text, lang="my")
        audio_fp = io.BytesIO()
        tts.write_to_fp(audio_fp)
        audio_fp.seek(0)

        st.audio(audio_fp, format="audio/mp3")
        st.download_button(
            "📥 Download MP3 အသံဖိုင်",
            data=audio_fp,
            file_name="myanmar_voiceover.mp3",
            mime="audio/mp3",
        )
      except Exception as e:
        st.error(f"အသံဖိုင် ထုတ်ယူရာတွင် အမှားရှိသည်: {str(e)}")
  else:
    st.warning("⚠️ ကျေးဇူးပြု၍ စာသား သို့မဟုတ် Script ထည့်သွင်းပေးပါ။")
    
