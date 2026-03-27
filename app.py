import streamlit as st
import json
import requests
import uuid
from datetime import datetime
import os
import base64

# ================== DATA FILE ==================
DATA_FILE = "data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"users": {}}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

db = load_data()

# ================== OLLAMA AI ==================
def ask_ollama(prompt):
    try:
        # ===============================
        # SYSTEM GUARDRAIL PROMPT (SHORT)
        # ===============================
        system_prompt = """
You are an AI creative co-writer. Your ONLY purpose is to create fictional stories.

RULES YOU MUST ALWAYS FOLLOW:

1. You must NEVER give:
   - code of any kind
   - programming help
   - math answers or calculations
   - technical explanations
   - factual information
   - real-world advice or definitions
   - hacker, bypass, or unsafe responses

2. If the user asks for anything NOT related to storytelling,
   you must reply with EXACTLY ONE of these short messages:

   A) "I am your story co-writer, and I can only continue the story. Let's focus on what happens next."
   B) "I can only help with storytelling. Let's continue the tale together."

3. If the user asks for harmful, violent, sexual, hateful, explosive, or unsafe content,  
   reply ONLY with this message:

   "I am your story co-writer, and I cannot create harmful or inappropriate content. Let's continue the story instead."

4. If the user mentions code, formulas, math, Python, Java, calculations, or technical topics:
   → IMMEDIATELY give one blocking message (no story).

5. When the user DOES give story-related input:
   → Write ONLY fictional story prose.
   → 1–5 sentences max.
   → Stay in genre, tone, and continuity.
"""

        # Build final prompt
        final_prompt = f"""
{system_prompt}

### USER INPUT ###
{prompt}

### ASSISTANT RESPONSE (STORY OR BLOCKING MESSAGE ONLY) ###
"""

        # Send to Ollama
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "tinyllama",
                "prompt": final_prompt,
                "stream": True
            },
            stream=True,
        )

        # Stream handling
        full_response = ""
        for line in response.iter_lines():
            if line:
                try:
                    data = json.loads(line.decode("utf-8"))
                    full_response += data.get("response", "")
                except:
                    continue

        text = full_response.strip()

        if not text:
            return "⚠️ No response from AI."

        return text

    except requests.exceptions.ConnectionError:
        return "❌ Cannot connect to Ollama."

    except Exception as e:
        return f"❌ Unexpected error: {str(e)}"
# ================== STREAMLIT CONFIG ==================
st.set_page_config(page_title="Storywriter Pro", page_icon="📖", layout="wide")

# ================== SESSION STATE ==================
if "page" not in st.session_state: st.session_state.page = "login"
if "users" not in st.session_state: st.session_state.users = db["users"]
if "current_user" not in st.session_state: st.session_state.current_user = None
if "guest_mode" not in st.session_state: st.session_state.guest_mode = False

def sync_user_data():
    db["users"] = st.session_state.users
    save_data(db)

# ================== THEME ==================
THEME_CSS = """
<style>
:root {
    --parchment: #f4e6c1;
    --parchment-dark: #e4d2ab;
    --ink: #3b2f22;
    --deep-brown: #4a3728;
    --accent-brown: #6d5846;
    --golden: #c4a484;
    --header-bar: #b49779;
}
.stApp { background-color: var(--parchment) !important; }
header[data-testid="stHeader"] { background-color: var(--header-bar) !important; border-bottom: 3px solid var(--golden); height: 60px !important; padding-top: 5px !important; box-shadow: 0 3px 6px rgba(0,0,0,0.15);}
section[data-testid="stSidebar"] { background-color: var(--parchment-dark) !important; border-right: 2px solid var(--golden);}
section[data-testid="stSidebar"] * { color: black !important; font-family: 'Georgia', serif !important; font-size: 17px !important;}
h1,h2,h3 { color: var(--deep-brown) !important; font-family:'Times New Roman', serif !important;}
.stTextArea textarea { background-color: #fcf8ec !important; color: var(--ink) !important; border:2px solid var(--golden)!important; border-radius:8px!important; padding:20px!important; font-family:'Georgia', serif!important; font-size:1.15rem!important; line-height:1.7!important;}
.stButton>button, .stDownloadButton>button, section[data-testid="stSidebar"] button { background-color: var(--deep-brown) !important; color:white !important; font-size:18px !important; font-family:'Georgia',serif!important; border-radius:8px !important; border:none!important; padding:10px 20px !important;}
.stButton>button span, .stDownloadButton>button span, section[data-testid="stSidebar"] button span { color:white !important; }
.stButton>button svg, .stDownloadButton>button svg, section[data-testid="stSidebar"] button svg { fill:white !important; }
.stButton>button:hover, .stDownloadButton>button:hover { background-color: var(--accent-brown) !important; color:#ffffff !important; }
</style>
"""
st.markdown(THEME_CSS, unsafe_allow_html=True)

# ================== STORY MANAGEMENT ==================
def get_story_db():
    if st.session_state.guest_mode:
        if "guest_stories" not in st.session_state: st.session_state.guest_stories = {}
        return st.session_state.guest_stories
    else:
        return st.session_state.users[st.session_state.current_user]["stories"]

def start_new_story():
    story_db = get_story_db()
    new_id = str(uuid.uuid4())
    story_db[new_id] = {
        "title": "Untitled Tale",
        "manuscript": "",
        "chat_history": [],
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    st.session_state.active_id = new_id
    sync_user_data()

# ================== LOGIN/REGISTER ==================
def login_page():
    st.title("📖 Storywriter  — Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Login"):
            if username in st.session_state.users:
                if st.session_state.users[username]["password"] == password:
                    st.session_state.current_user = username
                    st.session_state.guest_mode = False
                    st.session_state.page = "app"
                    st.rerun()
                else: st.error("Incorrect password.")
            else: st.error("User does not exist.")
    with col2:
        if st.button("Register"): st.session_state.page = "register"; st.rerun()
    with col3:
        if st.button("Continue as Guest"):
            st.session_state.guest_mode = True
            st.session_state.page = "app"
            st.rerun()

def register_page():
    st.title("📝 Create New Account")
    username = st.text_input("Choose a username")
    password = st.text_input("Choose a password", type="password")
    if st.button("Create Account"):
        if username in st.session_state.users:
            st.error("Username already exists.")
        else:
            db["users"][username] = {"password": password, "stories": {}}
            save_data(db)
            st.session_state.users = db["users"]
            st.success("Account created! Please login.")
            st.session_state.page = "login"
            st.rerun()
    if st.button("⬅ Back to Login"):
        st.session_state.page = "login"
        st.rerun()

# ================== MOOD THEMES ==================
BACKGROUND_IMAGES = {
    "Dark Forest": "dark_forest.png",
    "Fantasy Magic": "fantasy_magic.png",
    "Happy Sunshine": "happy_sunshine.png",
    "Romance Clouds": "romance_clouds.png",
    "Sad Rain": "sad_rain.png"
}

def get_base64_image(path):
    with open(path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

def set_background(image_path):
    encoded_img = get_base64_image(image_path)
    st.markdown(f"""
        <style>
        .stApp {{background: url("data:image/png;base64,{encoded_img}") !important;
        background-size: cover !important; background-repeat: no-repeat !important;
        background-attachment: fixed !important;}}
        </style>
    """, unsafe_allow_html=True)

def apply_text_theme(mood):
    if mood in ["Romance Clouds", "Happy Sunshine", "Default"]:
        text_color = "black"; ai_color="black"; text_shadow="none"
    else:
        text_color="white"; ai_color="white"; text_shadow="1px 1px 2px black"
    st.markdown(f"""
        <style>
        h1,h2,h3,label,p,.stTextInput label,.stTextArea label {{color:{text_color}!important; text-shadow:{text_shadow}!important;}}
        .stSidebar, section[data-testid="stSidebar"] * {{color:{text_color}!important; text-shadow:{text_shadow}!important;}}
        textarea, .stTextArea textarea, input[placeholder="Story Title"], input[placeholder="Search title"], textarea[placeholder="Ask your co-writer..."] {{color:black!important;}}
        .stTextInput>div>label, .stTextInput input, .stTextArea>div>label {{color:black!important;}}
        .stChatMessage.stChatMessage-assistant > div {{color:{ai_color}!important; font-weight:400!important;}}
        .stChatMessage.stChatMessage-user > div {{color:black!important;}}
        .stButton>button,.stDownloadButton>button,section[data-testid="stSidebar"] button {{color:white!important; fill:white!important;}}
        .stButton>button span,.stDownloadButton>button span,section[data-testid="stSidebar"] button span {{color:white!important;}}
        .stButton>button svg,.stDownloadButton>button svg,section[data-testid="stSidebar"] button svg {{fill:white!important;}}
        </style>
    """, unsafe_allow_html=True)

# ================== MAIN APP ==================
def story_app():
    story_db = get_story_db()
    if "active_id" not in st.session_state or st.session_state.active_id not in story_db:
        if len(story_db)==0: start_new_story()
        else: st.session_state.active_id = list(story_db.keys())[0]
    current_story = story_db[st.session_state.active_id]

    # ----- Sidebar -----
    with st.sidebar:
        if st.button("🔄 Logout"): st.session_state.page="login"; st.rerun()
        st.header("📚 Stories")
        if st.button("➕ New Story", use_container_width=True): start_new_story(); st.rerun()
        search = st.text_input("🔍 Search title").lower()
        for sid, data in story_db.items():
            if search in data["title"].lower():
                label = f"⭐ {data['title']}" if sid==st.session_state.active_id else data['title']
                if st.button(label, key=sid, use_container_width=True):
                    st.session_state.active_id = sid; st.rerun()
        # Mood Selector
        st.header("🎭 Mood Theme")
        mood = st.selectbox("Choose mood background:", ["Default"] + list(BACKGROUND_IMAGES.keys()))
    if mood != "Default": set_background(BACKGROUND_IMAGES[mood])
    apply_text_theme(mood)

    # ----- Main Layout -----
    st.title("📖 STORYWRITER")
    col1, col2 = st.columns([1.2, 1.0])

    # AI Chat
    with col1:
        st.subheader("💬 Co-Writer Assistant")
        chat_window = st.container()
        with chat_window:
            for msg in current_story["chat_history"]:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])
        user_msg = st.chat_input("Ask your co-writer...")
        if user_msg:
            current_story["chat_history"].append({"role":"user","content":user_msg})
            ai_response = ask_ollama(user_msg)
            current_story["chat_history"].append({"role":"assistant","content":ai_response})
            sync_user_data(); st.rerun()
        colA, colB = st.columns(2)
        with colA:
            if st.button("✨ Append AI to Manuscript", use_container_width=True):
                for m in reversed(current_story["chat_history"]):
                    if m["role"]=="assistant":
                        current_story["manuscript"] += "\n\n"+m["content"]; break
                sync_user_data(); st.rerun()
        with colB:
            if st.button("🗑️ Clear Chat", use_container_width=True):
                current_story["chat_history"] = []; sync_user_data(); st.rerun()

    # Manuscript Panel
    with col2:
        st.subheader("📝 Manuscript")
        current_story["title"] = st.text_input("Story Title", current_story["title"])
        manuscript_text = st.text_area("", current_story["manuscript"], height=600, label_visibility="collapsed")
        if manuscript_text != current_story["manuscript"]:
            current_story["manuscript"] = manuscript_text; sync_user_data()
        st.download_button("📥 Download (.txt)", data=current_story["manuscript"], file_name=f"{current_story['title']}.txt", mime="text/plain", use_container_width=True)

# ================== PAGE ROUTER ==================
if st.session_state.page == "login": login_page()
elif st.session_state.page == "register": register_page()
else: story_app()


import streamlit as st
import base64
import os

# ================== BACKGROUND IMAGES ==================
# Place your images in an "assets" folder
BACKGROUND_IMAGES = {
    "Dark Forest": "assets/dark_forest.png",
    "Fantasy Magic": "assets/fantasy_magic.png",
    "Happy Sunshine": "assets/happy_sunshine.png",
    "Romance Clouds": "assets/romance_clouds.png",
    "Sad Rain": "assets/sad_rain.png"
}

# ================== UTILITY FUNCTIONS ==================
def get_base64_image(path):
    """Convert image file to base64 string."""
    if not os.path.exists(path):
        st.warning(f"Background image not found: {path}")
        return None
    with open(path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

def set_background(image_path):
    """Set Streamlit background to a given image."""
    encoded_img = get_base64_image(image_path)
    if encoded_img:
        st.markdown(f"""
        <style>
        .stApp {{
            background: url("data:image/png;base64,{encoded_img}") !important;
            background-size: cover !important;
            background-repeat: no-repeat !important;
            background-attachment: fixed !important;
        }}
        </style>
        """, unsafe_allow_html=True)

def apply_text_theme(mood):
    """
    Apply text color theme based on mood:
    - Light moods → black text
    - Dark moods → white text with shadow
    """
    if mood in ["Romance Clouds", "Happy Sunshine", "Default"]:
        text_color = "black"
        text_shadow = "none"
    else:
        text_color = "white"
        text_shadow = "1px 1px 2px black"

    st.markdown(f"""
    <style>
    h1, h2, h3, label, p, .stTextInput label, .stTextArea label {{
        color: {text_color} !important;
        text-shadow: {text_shadow} !important;
    }}
    .stSidebar, section[data-testid="stSidebar"] * {{
        color: {text_color} !important;
        text-shadow: {text_shadow} !important;
    }}
    textarea, input {{
        color: black !important;  /* Keep inputs/manuscript always readable */
    }}
    </style>
    """, unsafe_allow_html=True)

# ================== MOOD SELECTOR UI ==================
def mood_selector():
    """Display mood selector in the sidebar and apply theme/background."""
    st.sidebar.header("🎭 Mood Theme")
    mood = st.sidebar.selectbox(
        "Choose mood background:",
        ["Default"] + list(BACKGROUND_IMAGES.keys())
    )
    if mood != "Default":
        set_background(BACKGROUND_IMAGES[mood])
    apply_text_theme(mood)
    return mood