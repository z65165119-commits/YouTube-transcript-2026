import streamlit as st
import os
from youtube_transcript_api import YouTubeTranscriptApi
from gtts import gTTS

st.set_page_config(page_title="YouTube to Transcript & Audio", page_icon="📝", layout="centered")

st.title("🎬 YouTube Transcript & Myanmar Audio Generator")
st.write("YouTube ဗီဒီယို လင့်ခ် (Link) ထည့်ရုံဖြင့် စာသား (Transcript) ထုတ်ယူပြီး မြန်မာအသံဖိုင်ပါ တစ်ခါတည်း ဖန်တီးနိုင်ပါပြီ။")

# YouTube URL ထည့်ရန် Input Box
url = st.text_input("YouTube Video URL ကို ထည့်ပါ:", placeholder="https://www.youtube.com/watch?v=...")

def extract_video_id(url):
    """YouTube URL မှ Video ID ကို ဖြတ်ထုတ်ပေးသော function"""
    if "youtu.be/" in url:
        return url.split("youtu.be/")[1].split("?")[0]
    elif "watch?v=" in url:
        return url.split("watch?v=")[1].split("&")[0]
    return None

if st.button("🚀 စာသားနှင့် အသံထုတ်ယူမည်"):
    if not url:
        st.warning("ကျေးဇူးပြု၍ YouTube လင့်ခ်တစ်ခု ထည့်ပါ။")
    else:
        video_id = extract_video_id(url)
        if not video_id:
            st.error("❌ မှန်ကန်သော YouTube လင့်ခ် မဟုတ်ပါ။")
        else:
            with st.spinner("⏳ ဗီဒီယိုမှ အချက်အလက်များ ဆွဲထုတ်နေပါပြီ၊ ခဏစောင့်ပါ..."):
                try:
                    # ၁။ YouTube Transcript ဆွဲထုတ်ခြင်း
                    transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['my', 'en'])
                    full_text = " ".join([entry['text'] for entry in transcript_list])
                    
                    # ၂။ Website ပေါ်တွင် စာသားပြသခြင်း
                    st.success("အောင်မြင်စွာ ထုတ်ယူပြီးပါပြီ!")
                    
                    st.subheader("📝 Transcript စာသားများ")
                    st.text_area("Transcript Text", full_text, height=200)
                    
                    # စာသားကို ဖိုင်အဖြစ် Download ဆွဲရန် Button
                    st.download_button(
                        label="📥 Transcript ကို Text ဖိုင်ဖြင့် Download ဆွဲရန်",
                        data=full_text,
                        file_name=f"{video_id}_transcript.txt",
                        mime="text/plain"
                    )

                    # ၃။ မြန်မာအသံဖိုင် (Audio) သို့ ပြောင်းလဲခြင်း
                    st.subheader("🎙️ မြန်မာအသံဖိုင် (Voiceover)")
                    audio_path = f"{video_id}.mp3"
                    
                    # စာသားရှည်ပါက gTTS အတွက် အတိုချုပ် (သို့) အပိုင်းလိုက်သုံးနိုင်သည်
                    tts_text = full_text[:1000] 
                    tts = gTTS(text=tts_text, lang='my', slow=False)
                    tts.save(audio_path)

                    # အသံဖိုင်ကို နားထောင်ရန်နှင့် Download ဆွဲရန် ပြသခြင်း
                    st.audio(audio_path, format='audio/mp3')
                    
                    with open(audio_path, "rb") as audio_file:
                        st.download_button(
                            label="📥 မြန်မာအသံဖိုင်ကို MP3 ဖြင့် Download ဆွဲရန်",
                            data=audio_file,
                            file_name=f"{video_id}_audio.mp3",
                            mime="audio/mp3"
                        )
                    
                    # အသုံးပြုပြီး ဖိုင်ကို ဖျက်ပစ်ရန်
                    if os.path.exists(audio_path):
                        os.remove(audio_path)

                except Exception as e:
                    st.error(f"❌ အမှားအယွင်း ဖြစ်ပေါ်သွားပါသည်: {str(e)}")
                    
