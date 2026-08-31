import os
import streamlit as st
from moviepy.editor import VideoFileClip
from google import genai
from gtts import gTTS

# Streamlit Page Config
st.set_page_config(page_title="AI Video Recap & Summary Pro", layout="wide")
st.title("🎬 AI Video Recap & Summary App")
st.write("ဗီဒီယိုဖိုင်ကို တင်ပါ၊ Gemini AI ဖြင့် အနှစ်ချုပ် ဇာတ်ညွှန်းနှင့် အသံဖိုင်များကို အလိုအလျောက် ဖန်တီးပါ။")

# Streamlit Secrets မှ Gemini API Key ကို ရယူခြင်း
try:
    gemini_api_key = st.secrets["GEMINI_API_KEY"]
except Exception:
    gemini_api_key = None

if not gemini_api_key:
    st.error("⚠️ Streamlit Cloud ၏ Settings > Secrets တွင် `GEMINI_API_KEY = \"သင့်င့်_key\"` ထည့်သွင်းထားခြင်း မရှိပါ။ ကျေးဇူးပြု၍ ထည့်ပေးပါ။")
else:
    try:
        client = genai.Client(api_key=gemini_api_key)
        
        # File Uploader
        uploaded_file = st.file_uploader("ဗီဒီယိုဖိုင်ကို တင်ပါ (MP4, MOV)", type=["mp4", "mov", "avi"])

        if uploaded_file is not None:
            input_video_path = "temp_input_video.mp4"
            with open(input_video_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📺 မူရင်းဗီဒီယို")
                st.video(input_video_path)
                
            with col2:
                st.subheader("⚙️ ဆက်တင်များ")
                recap_style = st.selectbox(
                    "အနှစ်ချုပ်ပုံစံ ရွေးပါ",
                    ["စိတ်လှုပ်ရှားစရာ (Exciting & Dramatic)", "အတိုချုပ် (Short Summary)", "ဟာသဆန်ဆန် (Funny)"]
                )
                
                if st.button("🚀 အပြည့်အစုံ စတင်ဖန်တီးမည်"):
                    try:
                        with st.status("🔄 လုပ်ဆောင်ချက်များ ဆောင်ရွက်နေပါပြီ...", expanded=True) as status:
                            
                            # Step 1: Extract Audio
                            st.write("🔊 ဗီဒီယိုထဲမှ အသံ (Audio) ကို ထုတ်ယူနေပါပြီ...")
                            audio_path = "temp_extracted_audio.mp3"
                            video_clip = VideoFileClip(input_video_path)
                            video_clip.audio.write_audiofile(audio_path, logger=None)
                            video_clip.close()
                            
                            # Step 2: Gemini Upload & Generate
                            st.write("🤖 Gemini AI သို့ ပို့ဆောင်ပြီး အနှစ်ချုပ် ဇာတ်ညွှန်း ရေးသားနေပါပြီ...")
                            audio_file_gemini = client.files.upload(file=audio_path)
                            
                            prompt = f"""
                            You are a professional video recap creator. 
                            Listen to this audio/video context and create an engaging video recap script in the style of '{recap_style}'. 
                            Make it catchy, fast-paced, and engaging for social media viewers.
                            """
                            
                            response = client.models.generate_content(
                                model='gemini-2.5-flash',
                                contents=[audio_file_gemini, prompt]
                            )
                            final_script = response.text
                            
                            # Step 3: Text to Speech
                            st.write("🎙️ အသံဖိုင်အသစ် (Voiceover) ဖန်တီးနေပါပြီ...")
                            tts = gTTS(text=final_script[:1500], lang='en', slow=False)
                            voiceover_path = "temp_voiceover.mp3"
                            tts.save(voiceover_path)
                            
                            status.update(label="✨ အားလုံး အောင်မြင်စွာ ပြီးစီးပါပြီ!", state="complete", expanded=False)
                        
                        # Results
                        st.success("🎉 AI Video Recap ထွက်ရှိလာပါပြီ!")
                        st.subheader("📄 ထွက်လာသည့် အနှစ်ချုပ် ဇာတ်ညွှန်း (Script)")
                        st.text_area("Script:", final_script, height=200)
                        
                        st.subheader("🎧 ထွက်လာသည့် AI Voiceover အသံဖိုင်")
                        st.audio(voiceover_path)
                        
                    except Exception as e:
                        st.error(f"လုပ်ဆောင်ချက်အတွင်း အမှားဖြစ်ပေါ်သွားပါပြီ: {e}")
                    
                    finally:
                        if os.path.exists(input_video_path):
                            os.remove(input_video_path)
                        if os.path.exists("temp_extracted_audio.mp3"):
                            os.remove("temp_extracted_audio.mp3")

    except Exception as e:
        st.error(f"Gemini Client ချိတ်ဆက်ရာတွင် အမှားရှိနေပါသည်: {e}")
        
