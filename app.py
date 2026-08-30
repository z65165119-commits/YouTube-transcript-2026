import streamlit as st
import sqlite3
import os
import subprocess
import whisper
from gtts import gTTS

# --- PAGE CONFIG & DARK THEME STYLING ---
st.set_page_config(page_title="Vibe Prompt - AI Video & Subtitle Generator", page_icon="⚡", layout="centered")

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
    h1, h2, h3 {
        color: #ffffff !important;
    }
    .stButton>button {
        background: linear-gradient(90deg, #f59e0b, #d97706);
        color: white;
        font-size: 16px;
        font-weight: bold;
        width: 100%;
        border-radius: 8px;
        height: 50px;
        border: none;
    }
    .stButton>button:hover {
        background: linear-gradient(90deg, #d97706, #b45309);
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

# --- 1. DATABASE SETUP (Credit & VIP System) ---
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

# --- 2. HEADER SECTION ---
st.title("⚡ Vibe Prompt - AI Video & Subtitle Generator")
st.markdown("ဗီဒီယိုများကို Upload တင်ပါ၊ AI ဖြင့် Subtitle နှင့် အနှစ်ချုပ်များ ဖန်တီးပါ၊ Logo တပ်ဆင်ပြီး Download ရယူပါ။")
st.markdown("---")

# --- 3. SIDEBAR (Account & VIP Contact) ---
st.sidebar.title("👤 အကောင့်နှင့် Credit")
user_email = st.sidebar.text_input("သင်၏ Gmail ဖြင့် ဝင်ပါ:")

if user_email:
    credits, is_vip = get_user_data(user_email)
    st.sidebar.write(f"**Email:** {user_email}")
    if is_vip:
        st.sidebar.success("🌟 VIP အဖွဲ့ဝင် (အကန့်အသတ်မရှိ)")
    else:
        st.sidebar.info(f"🎁 ကျန်ရှိသော Credit: **{credits} ကြိမ်**")
        st.sidebar.markdown("---")
        st.sidebar.subheader("💎 VIP သို့ ပြောင်းရန်")
        st.sidebar.write("ဈေးနှုန်းနှင့် ဝယ်ယူရန် ဆက်သွယ်ရန်:")
        st.sidebar.markdown("👉 Telegram: **@lynn_m2026**")

# --- 4. MAIN APP INTERFACE ---
if not user_email:
    st.warning("⚠️ ကျေးဇူးပြု၍ ဘယ်ဘက် Sidebar တွင် သင်၏ Gmail ကို အရင်ထည့်သွင်းပါ။")
else:
    credits, is_vip = get_user_data(user_email)

    st.subheader("📹 Video Upload တင်ရန်")
    uploaded_file = st.file_uploader("MP4 သို့မဟုတ် MOV ဗီဒီယိုဖိုင်ကို ရွေးချယ်ပါ", type=["mp4", "mov", "webm"])

    video_path = "temp_video.mp4"
    if uploaded_file is not None:
        with open(video_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.video(video_path)
        st.success(f"ဖိုင်အမည်: {uploaded_file.name} - အောင်မြင်စွာ တင်ပြီးပါပြီ။")

    st.markdown("---")
    st.subheader("⚙️ Subtitle & AI Options (ဆက်တင်များ)")

    col1, col2 = st.columns(2)
    with col1:
        subtitle_option = st.selectbox("Subtitle ပုံစံ", ["AI Auto Subtitle (Whisper)", "Manual SRT", "Blur Video Subtitle"])
    with col2:
        ai_voice = st.selectbox("မြန်မာ AI အသံ", ["Kore (Female)", "Thura (Male)"])

    mirror_edit = st.checkbox("🪞 Mirror Edit ပြုလုပ်မည်")
    logo_file = st.file_uploader("🖼️ Video တွင် Logo ထည့်ရန် (PNG)", type=["png", "jpg"])

    st.markdown("---")
    
    if st.button("🚀 One Click Recap လုပ်ရန် (Credit 5 ခု)"):
        if uploaded_file is None:
            st.error("❌ ကျေးဇူးပြု၍ ဗီဒီယိုဖိုင် အရင်တင်ပါ။")
        elif not is_vip and credits < 5:
            st.error("❌ Credit မလုံလောက်ပါ။ VIP ဖြစ်ရန် @lynn_m2026 သို့ ဆက်သွယ်ပါ။")
        else:
            with st.spinner("⏳ AI ဖြင့် ဗီဒီယိုကို စီမံနေပါပြီ (Whisper AI ဖြင့် စာသားထုတ်နေသည်)..."):
                try:
                    # 1. Whisper AI ဖြင့် အသံမှ စာသားထုတ်ယူခြင်း (သို့မဟုတ် နမူနာထုတ်ယူခြင်း)
                    # OpenAI Whisper Model ကို Load လုပ်ခြင်း (small model ကို အသုံးပြုသည်)
                    model = whisper.load_model("base")
                    result = model.transcribe(video_path)
                    transcribed_text = result["text"]

                    st.success("✨ အသံမှ စာသားထုတ်ယူခြင်း (Transcription) ပြီးစီးပါပြီ!")
                    st.text_area("ထွက်လာသော စာသားများ:", transcribed_text, height=120)

                    # 2. gTTS ဖြင့် မြန်မာအသံဖိုင် ထုတ်လုပ်ခြင်း
                    audio_path = "output_audio.mp3"
                    tts = gTTS(text="ဗီဒီယိုအတွက် AI မှ ထုတ်ယူထားသော အနှစ်ချုပ် ဖြစ်ပါသည်။", lang='my', slow=False)
                    tts.save(audio_path)

                    # 3. FFmpeg သုံး၍ Logo ထည့်ခြင်းနှင့် ဗီဒီယို ပြင်ဆင်ခြင်း (Logo ရှိမှသာ ပေါင်းမည်)
                    output_video_path = "recap_output.mp4"
                    
                    if logo_file is not None:
                        logo_path = "temp_logo.png"
                        with open(logo_path, "wb") as lf:
                            lf.write(logo_file.getbuffer())
                        
                        # FFmpeg command for overlaying logo at top-right corner
                        cmd = [
                            'ffmpeg', '-y', '-i', video_path, '-i', logo_path,
                            '-filter_complex', 'overlay=W-w-20:20',
                            output_video_path
                        ]
                        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        if os.path.exists(logo_path):
                            os.remove(logo_path)
                    else:
                        # Logo မပါလျှင် မူရင်းအတိုင်း ကူးယူမည်
                        os.rename(video_path, output_video_path)

                    # ရလဒ်များ ပြသခြင်း
                    st.subheader("📥 ရလဒ် ဗီဒီယိုနှင့် အသံဖိုင်")
                    st.audio(audio_path, format='audio/mp3')
                    
                    with open(output_video_path, "rb") as v_file:
                        st.download_button(
                            label="📥 တည်းဖြတ်ပြီးသား ဗီဒီယိုကို Download ဆွဲရန်",
                            data=v_file,
                            file_name="ai_recap_video.mp4",
                            mime="video/mp4"
                        )

                    # Credit ဖြတ်တောက်ခြင်း
                    if not is_vip:
                        new_credits = credits - 5
                        update_credits(user_email, new_credits)
                        st.info(f"ကျန်ရှိသည့် Credit ပမာဏ: {new_credits} ခု")

                    # ဖိုင်များကို သန့်စင်ခြင်း
                    if os.path.exists(audio_path):
                        os.remove(audio_path)

                except Exception as e:
                    st.error(f"❌ အမှားအယွင်း ဖြစ်ပေါ်သွားပါသည်: {str(e)}")
