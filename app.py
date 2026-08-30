import streamlit as st
import sqlite3
import os
from youtube_transcript_api import YouTubeTranscriptApi
from gtts import gTTS

st.set_page_config(page_title="YouTube Transcript & Myanmar Audio", page_icon="🎬", layout="centered")

# --- 1. DATABASE SETUP ---
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

# --- 2. LOGIN UI (Gmail) ---
st.title("🎬 YouTube Transcript & Myanmar Audio Generator")

# လောလောဆယ် ရိုးရှင်းလွယ်ကူစေရန် Gmail ထည့်သွင်း login လုပ်သောပုံစံသုံးထားသည်
user_email = st.text_input("ဆက်လက်သုံးစွဲရန် သင့်ရဲ့ Gmail လိပ်စာကို ထည့်ပါ:")

if not user_email:
    st.info("💡 ကျေးဇူးပြု၍ သင်၏ Gmail ဖြင့် ဝင်ရောက်ပါ (အကောင့်သစ်များအတွက် Free ၅ ကြိမ် အလိုအလျောက်ရရှိမည်)။")
else:
    credits, is_vip = get_user_data(user_email)
    
    # Sidebar တွင် အကောင့်အချက်အလက်ပြသခြင်း
    st.sidebar.title("👤 အကောင့်အချက်အလက်")
    st.sidebar.write(f"**Email:** {user_email}")
    
    if is_vip:
        st.sidebar.success("🌟 VIP အဖွဲ့ဝင် (အကန့်အသတ်မရှိ)")
    else:
        st.sidebar.info(f"🎁 ကျန်ရှိသော Free အကြိမ်ရေ: **{credits} / 5** ကြိမ်")
        st.sidebar.markdown("---")
        st.sidebar.subheader("💎 VIP သို့ ပြောင်းရန်")
        st.sidebar.write("ဈေးနှုန်းနှင့် ဝယ်ယူရန် ဆက်သွယ်ရန်:")
        st.sidebar.markdown("👉 Telegram: **@lynn_m2026**")

    # --- 3. MAIN APP LOGIC ---
    st.markdown("---")
    url = st.text_input("YouTube Video URL ကို ထည့်ပါ:", placeholder="https://www.youtube.com/watch?v=...")

    def extract_video_id(url):
        if "youtu.be/" in url:
            return url.split("youtu.be/")[1].split("?")[0]
        elif "watch?v=" in url:
            return url.split("watch?v=")[1].split("&")[0]
        return None

    if st.button("🚀 စာသားနှင့် အသံထုတ်ယူမည်"):
        if not url:
            st.warning("ကျေးဇူးပြု၍ YouTube လင့်ခ် ထည့်ပါ။")
        elif not is_vip and credits <= 0:
            st.error("❌ Free Quota (၅ ကြိမ်) ကုန်ဆုံးသွားပါပြီ။ VIP ဝင်ရန် @lynn_m2026 သို့ ဆက်သွယ်ပါ။")
        else:
            video_id = extract_video_id(url)
            if not video_id:
                st.error("❌ မှန်ကန်သော YouTube လင့်ခ် မဟုတ်ပါ။")
            else:
                with st.spinner("⏳ လုပ်ဆောင်နေပါပြီ၊ ခဏစောင့်ပါ..."):
                    try:
                        # Transcript ဆွဲထုတ်ခြင်း
                        transcript_data = YouTubeTranscriptApi.list_transcripts(video_id)
                        try:
                            transcript = transcript_data.find_transcript(['my', 'en'])
                        except:
                            transcript = transcript_data.find_generated_transcript(['my', 'en'])
                            
                        transcript_list = transcript.fetch()
                        full_text = " ".join([entry['text'] for entry in transcript_list])
                        
                        st.success("အောင်မြင်စွာ ထုတ်ယူပြီးပါပြီ!")
                        st.subheader("📝 Transcript စာသားများ")
                        st.text_area("Transcript Text", full_text, height=150)
                        
                        # အသံဖိုင်ပြောင်းခြင်း
                        audio_path = f"{video_id}.mp3"
                        tts = gTTS(text=full_text[:1000], lang='my', slow=False)
                        tts.save(audio_path)

                        st.audio(audio_path, format='audio/mp3')
                        
                        with open(audio_path, "rb") as audio_file:
                            st.download_button(
                                label="📥 မြန်မာအသံဖိုင်ကို MP3 ဖြင့် Download ဆွဲရန်",
                                data=audio_file,
                                file_name=f"{video_id}_audio.mp3",
                                mime="audio/mp3"
                            )
                        
                        if os.path.exists(audio_path):
                            os.remove(audio_path)

                        # Free user ဆိုလျှင် Quota တစ်ခုလျှော့မည်
                        if not is_vip:
                            new_credits = credits - 1
                            update_credits(user_email, new_credits)
                            st.info(f"ကျန်ရှိသည့် Free အကြိမ်ရေ: {new_credits} ကြိမ်")

                    except Exception as e:
                        st.error(f"❌ အမှားအယွင်း ဖြစ်ပေါ်သွားပါသည်: {str(e)}")
                        
