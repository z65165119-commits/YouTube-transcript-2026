import io
import re
from deep_translator import GoogleTranslator
from google_auth_oauthlib.flow import Flow
from gtts import gTTS
import streamlit as st
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi

st.set_page_config(
    page_title="YouTube AI Studio & Script Suite",
    page_icon="🔴",
    layout="wide",
)

# ---------------------------------------------------------
# 🔑 GOOGLE AUTHENTICATION SETUP (Native OAuth Flow)
# ---------------------------------------------------------
CLIENT_CONFIG = {
    "web": {
        "client_id": st.secrets["google_auth"]["client_id"],
        "client_secret": st.secrets["google_auth"]["client_secret"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": [st.secrets["google_auth"]["redirect_uri"]],
    }
}

SCOPES = [
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "openid",
]

# OAuth Flow ဖန်တီးခြင်း
flow = Flow.from_client_config(
    CLIENT_CONFIG, scopes=SCOPES, redirect_uri=CLIENT_CONFIG["web"]["redirect_uris"][0]
)

# Callback မှ Code ကို စစ်ဆေးခြင်း
query_params = st.query_params
if "code" in query_params and not st.session_state.get("connected"):
  try:
    auth_code = query_params["code"]
    flow.fetch_token(code=auth_code)
    credentials = flow.credentials
    import requests

    user_info_response = requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {credentials.token}"},
    ).json()

    st.session_state["connected"] = True
    st.session_state["user_info"] = user_info_response
    st.query_params.clear()
  except Exception as e:
    st.error(f"Authentication Error: {e}")

# 👑 VIP GMAIL ADDRESS
ALLOWED_EMAILS = [
    "z65165119@gmail.com",
]

FREE_LIMIT = 5

if "usage_count" not in st.session_state:
  st.session_state["usage_count"] = 0

# ---------------------------------------------------------
# 🔝 HEADER BAR WITH GOOGLE SIGN IN
# ---------------------------------------------------------
col_title, col_auth = st.columns([3, 1.2])

with col_title:
  st.title("🔴⚡ YouTube AI Studio & Script Suite")

with col_auth:
  if st.session_state.get("connected"):
    user_info = st.session_state.get("user_info", {})
    user_email = user_info.get("email", "")
    user_name = user_info.get("name", "User")
    user_picture = user_info.get("picture", "")

    st.write(f"👋 **{user_name}**")
    if user_picture:
      st.image(user_picture, width=40)

    if st.button("Sign Out"):
      st.session_state["connected"] = False
      st.session_state.pop("user_info", None)
      st.rerun()
  else:
    auth_url, _ = flow.authorization_url(prompt="consent")
    st.link_button("🔑 Sign In with Google", auth_url, type="primary")

st.markdown("---")

# ---------------------------------------------------------
# 🚨 MANDATORY GOOGLE LOGIN CHECK
# ---------------------------------------------------------
if not st.session_state.get("connected"):
  st.warning(
      "⚠️ App အသုံးပြုရန် ညာဘက်အပေါ်ထောင့်ရှိ **'Sign In with Google'**"
      " ခလုတ်ကို နှိပ်၍ Sign In ဝင်ပေးပါ။"
  )
  st.info(
      "💡 Google Account ဖြင့် ဝင်ရောက်ပြီး အခမဲ့ ၅ ကြိမ် စမ်းသပ်သုံးစွဲနိုင်ပါသည်။"
  )
  st.stop()

user_info = st.session_state.get("user_info", {})
clean_email = user_info.get("email", "").strip().lower()
allowed_emails_lower = [e.strip().lower() for e in ALLOWED_EMAILS]
is_vip = clean_email in allowed_emails_lower

# ---------------------------------------------------------
# ⚙️ SIDEBAR - USER ACCOUNT & OPTIONS
# ---------------------------------------------------------
st.sidebar.header("👤 Account Status")
st.sidebar.write(f"**Email:** {clean_email}")

if is_vip:
  st.sidebar.success("👑 **VIP Unlimited Access**")
else:
  remaining = max(0, FREE_LIMIT - st.session_state["usage_count"])
  st.sidebar.info(f"🎁 Free သုံးစွဲခွင့် ကျန်ရှိသည့်အကြိမ်: {remaining} / {FREE_LIMIT}")

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Options")
show_timestamp = st.sidebar.checkbox("Timestamps ထည့်ရန်", value=False)
summary_length = st.sidebar.select_slider(
    "AI Summary အတိုအရှည်",
    options=["Short", "Medium", "Detailed"],
    value="Medium",
)

if not is_vip and st.session_state["usage_count"] >= FREE_LIMIT:
  st.error("❌ သင့်၏ အခမဲ့ ၅ ကြိမ် အသုံးပြုခွင့် ကုန်ဆုံးသွားပါပြီ။")
  st.info(
      "👉 ဆက်လက်အသုံးပြုလိုပါက Telegram **[@lynn_m2026](https://t.me/lynn_m2026)**"
      " သို့ ဆက်သွယ်၍ VIP Access ရယူနိုင်ပါသည်။"
  )
  st.stop()

# ---------------------------------------------------------
# 🎬 MAIN APP LOGIC
# ---------------------------------------------------------
video_url = st.text_input("🔗 YouTube Video URL ကို ရိုက်ထည့်ပါ:", "")


def extract_video_id(url):
  match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", url)
  return match.group(1) if match else None


def format_time(seconds):
  minutes = int(seconds // 60)
  secs = int(seconds % 60)
  return f"{minutes:02d}:{secs:02d}"


def format_srt_time(seconds):
  hrs = int(seconds // 3600)
  mins = int((seconds % 3600) // 60)
  secs = int(seconds % 60)
  millis = int((seconds % 1) * 1000)
  return f"{hrs:02d}:{mins:02d}:{secs:03d}"


def generate_srt(transcript_data):
  srt_output = ""
  for idx, item in enumerate(transcript_data, 1):
    start = format_srt_time(item["start"])
    end = format_srt_time(item["start"] + item["duration"])
    text = item["text"].strip()
    srt_output += f"{idx}\n{start} --> {end}\n{text}\n\n"
  return srt_output


def fetch_transcript_robust(v_url, v_id):
  try:
    return YouTubeTranscriptApi.get_transcript(
        v_id, languages=["en", "en-US", "my"]
    )
  except Exception:
    pass

  ydl_opts = {
      "skip_download": True,
      "writesubtitles": True,
      "writeautomaticsub": True,
      "subtitleslangs": ["en", "my"],
      "quiet": True,
  }

  with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info(v_url, download=False)
    subtitles = info.get("subtitles") or info.get("automatic_captions")

    if not subtitles:
      raise Exception("No transcript or subtitles found.")

    lang = "en" if "en" in subtitles else list(subtitles.keys())[0]
    sub_data = subtitles[lang]

    import requests

    json_url = next(
        (s["url"] for s in sub_data if s.get("ext") == "json3"), None
    )
    if json_url:
      res = requests.get(json_url).json()
      parsed_transcript = []
      for event in res.get("events", []):
        if "segs" in event:
          text = "".join([s.get("utf8", "") for s in event["segs"]]).strip()
          if text and text != "\n":
            start = event.get("tStartMs", 0) / 1000.0
            dur = event.get("dDurationMs", 0) / 1000.0
            parsed_transcript.append(
                {"text": text, "start": start, "duration": dur}
            )
      return parsed_transcript

  raise Exception("Could not extract transcript.")


if st.button("⚡ Script & AI Processing စတင်မည်", type="primary"):
  if video_url:
    video_id = extract_video_id(video_url)
    if not video_id:
      st.error("❌ YouTube Link မမှန်ပါ။ ပြန်စစ်ပေးပါ။")
    else:
      try:
        st.video(video_url)

        with st.spinner(
            "⏳ Transcript နှင့် AI Data များကို တွက်ချက်နေပါသည်..."
        ):
          fetched_transcript = fetch_transcript_robust(video_url, video_id)

          english_lines = []
          raw_text_combined = ""
          for item in fetched_transcript:
            start_str = format_time(item["start"])
            text = item["text"].strip()
            raw_text_combined += text + " "
            if show_timestamp:
              english_lines.append(f"[{start_str}] {text}")
            else:
              english_lines.append(text)

          full_english_script = "\n".join(english_lines)

          words = len(raw_text_combined.split())
          chars = len(raw_text_combined)
          est_read_time = round(words / 150, 1)

          translator = GoogleTranslator(source="auto", target="my")
          myanmar_translation = translator.translate(raw_text_combined[:4000])

          srt_content = generate_srt(fetched_transcript)

          sentences = raw_text_combined.split(". ")
          summary_sentences = (
              sentences[:3]
              if summary_length == "Short"
              else (sentences[:6] if summary_length == "Medium" else sentences[:10])
          )
          summary_en = ". ".join(summary_sentences) + "."
          summary_my = translator.translate(summary_en[:2000])

          st.success("✅ အားလုံး အောင်မြင်စွာ ထုတ်ယူပြီးပါပြီ!")

          if not is_vip:
            st.session_state["usage_count"] += 1

          m1, m2, m3 = st.columns(3)
          m1.metric("📝 စာလုံးရေ (Words)", f"{words:,}")
          m2.metric("🔤 အက္ခရာရေ (Chars)", f"{chars:,}")
          m3.metric("⏱️ ခန့်မှန်းဖတ်ချိန်", f"{est_read_time} မိနစ်")

          st.markdown("---")

          tab1, tab2, tab3, tab4 = st.tabs([
              "🇬🇧 English Script",
              "🇲🇲 မြန်မာ ဘာသာပြန်",
              "🤖 AI Summary & Recap",
              "📥 Subtitles & TTS Audio",
          ])

          with tab1:
            st.subheader("English Script")
            st.code(full_english_script, language="text")
            st.download_button(
                "📥 Download English Script (.txt)",
                data=full_english_script.encode("utf-8-sig"),
                file_name="english_script.txt",
                mime="text/plain; charset=utf-8",
            )

          with tab2:
            st.subheader("မြန်မာ ဘာသာပြန် Script")
            st.code(myanmar_translation, language="text")
            st.download_button(
                "📥 Download မြန်မာ Script (.txt)",
                data=myanmar_translation.encode("utf-8-sig"),
                file_name="myanmar_script.txt",
                mime="text/plain; charset=utf-8",
            )

          with tab3:
            st.subheader("🤖 AI Script Summary & Story Recap")
            st.write("**English Summary:**")
            st.code(summary_en, language="text")
            st.write("**မြန်မာအနှစ်ချုပ် / ပြန်လည်ဆန်းသစ်ချက်:**")
            st.code(summary_my, language="text")

          with tab4:
            st.subheader("🎬 SRT Subtitle & Myanmar Voiceover (TTS)")
            col_sub, col_audio = st.columns(2)

            with col_sub:
              st.write("📄 **SRT Subtitle File:**")
              st.code(
                  srt_content[:1000] + "...\n[Truncated Preview]",
                  language="text",
              )
              st.download_button(
                  "📥 Download Subtitle (.srt)",
                  data=srt_content.encode("utf-8-sig"),
                  file_name="subtitle.srt",
                  mime="text/plain; charset=utf-8",
              )

            with col_audio:
              st.write("🔊 **Myanmar Text-to-Speech (TTS Voiceover):**")
              try:
                tts_text = summary_my[:300]
                tts = gTTS(text=tts_text, lang="my")
                audio_fp = io.BytesIO()
                tts.write_to_fp(audio_fp)
                audio_fp.seek(0)
                st.audio(audio_fp, format="audio/mp3")
              except Exception as e:
                st.warning(f"Audio TTS Generation မရရှိပါ: {str(e)}")

      except Exception as e:
        st.error(f"❌ Script ထုတ်ယူ၍ မရပါ။ ({str(e)})")
  else:
    st.warning("⚠️ ကျေးဇူးပြု၍ YouTube Link ရိုက်ထည့်ပေးပါ။")
