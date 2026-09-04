import streamlit as st
import sqlite3
import os
from youtube_transcript_api import YouTubeTranscriptApi
from gtts import gTTS

# --- PAGE CONFIG & STYLING ---
st.set_page_config(page_title="Youtube to Transcribe", page_icon="📝", layout="centered")

st.markdown("""
    <style>
    .main {
        background-color: #0f1117;
        color: #ffffff;
    }
    .stApp {
        background-color: #0f1117;
        color: #ffffff;
    }
    h1 {
        color: #ffffff;
        text-align: center;
        font-weight: 800;
        font-size: 2.2rem;
    }
    .subtitle {
        text-align: center;
        color: #a0aec0;
        font-size: 15px;
        margin-bottom: 25px;
    }
    .stButton>button {
        background: linear-gradient(90deg, #2563eb, #1d4ed8);
        color: white;
        font-size: 16px;
        font-weight: bold;
        width: 100%;
        border-radius: 8px;
        height: 48px;
        border: none;
    }
    .stButton>button:hover {
        background: linear-gradient(90deg, #1d4ed8, #1e40af);
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            credits INTEGER DEFAULT 5,
            is_vip INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_user_data(email):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT credits, is_vip FROM users WHERE email = ?', (email,))
    user = c.fetchone()
    if not user:
        c.execute('INSERT INTO users (email, credits, is_vip) VALUES (?, 5, 0)', (email,))
        conn.commit()
        user = (5, 0)
    conn.close()
    return user

def update_credits(email, credits):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('UPDATE users SET credits = ? WHERE email = ?', (credits, email))
    conn.commit()
    conn.close()

# --- UI HEADER ---
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("<h1>YouTube Transcript & English Audio Generator</h1>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>YouTube ဗီဒီယိုလင့်ခ်ထည့်ရုံဖြင့် အင်္ဂလိပ်စာသား (Transcript) နှင့် အင်္ဂလိပ်အသံဖိုင်ပါ တစ်ခါတည်း ထုတ်ယူနိုင်ပါပြီ။</div>", unsafe_allow_html=True)
st.markdown("---")

# --- SIDEBAR ---
st.sidebar.title("👤 အကောင့်အချက်အလက်")
user_email = st.sidebar.text_input("သင့်ရဲ့ Gmail လိပ်စာကို ထည့်ပါ:")

if user_email:
    credits, is_vip = get_user_data(user_email)
    st.sidebar.write(f"**Email:** {user_email}")
    if is_vip:
        st.sidebar.success("🌟 VIP အဖွဲ့ဝင် (အကန့်အသတ်မရှိ)")
    else:
        st.sidebar.info(f"🎁 ကျန်ရှိသော Free အကြိမ်ရေ: **{credits} / 5**")
        st.sidebar.markdown("---")
        st.sidebar.subheader("💎 VIP သို့ ပြောင်းရန်")
        st.sidebar.write("ဈေးနှုန်းနှင့် ဝယ်ယူရန် ဆက်သွယ်ရန်:")
        st.sidebar.markdown("👉 Telegram: **@lynn_m2026**")

# --- MAIN FORM ---
with st.form("transcript_form"):
    url = st.text_input("YouTube Video URL ကို ထည့်ပါ:", placeholder="https://www.youtube.com/watch?v=...")
    submitted = st.form_submit_button("🚀 Get English Transcript & Audio")

def extract_video_id(url):
    if "youtu.be/" in url:
        return url.split("youtu.be/")[1].split("?")[0]
    elif "watch?v=" in url:
        return url.split("watch?v=")[1].split("&")[0]
    return None

if submitted:
    if not user_email:
        st.warning("⚠️ ကျေးဇူးပြု၍ ဘယ်ဘက် Sidebar တွင် Gmail ထည့်ပါ။")
    elif not url:
        st.warning("⚠️ ကျေးဇူးပြု၍ YouTube လင့်ခ် ထည့်ပါ။")
    else:
        credits, is_vip = get_user_data(user_email)
        
        if not is_vip and credits <= 0:
            st.error("❌ Free Quota (၅ ကြိမ်) ကုန်ဆုံးသွားပါပြီ။ VIP ဝင်ရန် @lynn_m2026 သို့ ဆက်သွယ်ပါ။")
        else:
            video_id = extract_video_id(url)
            if not video_id:
                st.error("❌ မှန်ကန်သော YouTube လင့်ခ် မဟုတ်ပါ။")
            else:
                with st.spinner("⏳ စာသားများကို ထုတ်ယူနေပါပြီ၊ ခဏစောင့်ပါ..."):
                    try:
                        # YouTube Transcript API ဖြင့် အင်္ဂလိပ်မူရင်းစာသား ရယူခြင်း
                        fetched_data = YouTubeTranscriptApi.get_transcript(video_id)
                        full_text = " ".join([entry['text'] for entry in fetched_data])
                        
                        st.success("✨ အောင်မြင်စွာ ထုတ်ယူပြီးပါပြီ!")
                        st.subheader("📝 English Transcript Text")
                        st.text_area("Transcript Text", full_text, height=150)
                        
                        # gTTS ဖြင့် အင်္ဂလိပ်အသံဖိုင် (English Audio) ဖန်တီးခြင်း (lang='en')
                        audio_path = f"{video_id}_en.mp3"
                        tts = gTTS(text=full_text[:1000], lang='en', slow=False)
                        tts.save(audio_path)

                        st.subheader("🔊 English Audio Preview")
                        st.audio(audio_path, format='audio/mp3')
                        
                        with open(audio_path, "rb") as audio_file:
                            st.download_button(
                                label="📥 Download English MP3 Audio",
                                data=audio_file,
                                file_name=f"{video_id}_english.mp3",
                                mime="audio/mp3"
                            )
                        
                        if os.path.exists(audio_path):
                            os.remove(audio_path)

                        # Credit လျှော့ချခြင်း
                        if not is_vip:
                            new_credits = credits - 1
                            update_credits(user_email, new_credits)
                            st.info(f"ကျန်ရှိသည့် Free အကြိမ်ရေ: {new_credits} ကြိမ်")

                    except Exception as e:
                        st.error(f"❌ အမှားအယွင်း ဖြစ်ပေါ်သွားပါသည်: {str(e)}")
