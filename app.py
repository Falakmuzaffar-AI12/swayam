import time
from datetime import date

import streamlit as st
from google import genai
from google.genai import types

MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
]

st.set_page_config(page_title="Swayam", page_icon="🪷", layout="centered")

# ---------------- SESSION STATE ----------------
defaults = {
    "page": "intro",
    "saved_story": "",
    "tool": "",
    "language": "English",
    "bsg_result": "",
    "plan_result": "",
    "vent_process_result": "",
    "vent_released": False,
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ---------------- STYLING ----------------
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@500;600;700&family=Inter:wght@400;500&display=swap');

html, body, p, label, .stMarkdown { font-family: 'Inter', sans-serif; }
h1, h2, h3 { font-family: 'Poppins', sans-serif !important; letter-spacing: -0.3px; }

.stApp { background: linear-gradient(180deg, #FBF6F4 0%, #F5EAF2 100%); }
h1 { color: #79566F; }
h2, h3 { color: #896D82; }

#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 2rem; max-width: 720px; }

div[data-testid="stVerticalBlockBorderWrapper"] {
    background: rgba(255,255,255,0.75);
    border: 1px solid #EBDDE7 !important;
    border-radius: 18px;
    box-shadow: 0 4px 18px rgba(121,86,111,0.08);
}

.stButton > button {
    border-radius: 12px;
    border: 1px solid #D9C3D3;
    font-weight: 500;
}
.stButton > button[kind="primary"] {
    background: #9B6B8E;
    color: white;
    border: none;
}
textarea, input { border-radius: 12px !important; }
</style>
""",
    unsafe_allow_html=True,
)


# ---------------- GEMINI HELPER ----------------
def get_client():
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        st.error(
            "Missing GEMINI_API_KEY in Streamlit secrets. "
            "Add it to .streamlit/secrets.toml or app secrets to use AI features."
        )
        return None
    return genai.Client(api_key=api_key)


def ask_gemini(system_prompt, user_input):
    client = get_client()
    if client is None:
        return None

    last_error = None
    lang = st.session_state.get("language", "English")
    if lang == "Hinglish":
        system_prompt += (
            "\n\nWrite your whole reply in Hinglish: a natural mix of Hindi "
            "and English written in Roman letters, the way young people in "
            "India text. Keep the bold headings exactly as given, in English."
        )
    elif lang == "Hindi":
        system_prompt += (
            "\n\nWrite your whole reply in simple Hindi using Devanagari "
            "script. Keep the bold headings exactly as given, in English."
        )

    for model_name in MODELS:
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=user_input,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=0.7,
                    ),
                )
                if response.text:
                    return response.text
            except Exception as e:
                last_error = e
                busy = any(
                    code in str(e) for code in ("503", "429", "UNAVAILABLE")
                )
                if not busy:
                    break
                time.sleep(2 * (attempt + 1))

    st.error("The AI is very busy right now. Please wait a minute and try again.")
    if last_error:
        st.caption(f"Details: {last_error}")
    return None


def with_story(text):
    story = st.session_state.saved_story.strip()
    if story:
        return f"About her (optional context):\n{story}\n\n{text}"
    return text


# ---------------- PROMPTS ----------------
CORE_PHILOSOPHY = """
You are Swayam, a warm, grounded support companion for young women in
Indian households balancing family expectations, household
responsibilities, social pressure and their own ambitions.

Principles you always follow:
- Recognise the realities of Indian family life. Never assume she can
  freely refuse or confront family members.
- Never give generic motivational advice or cliches.
- Never push her to just say no, fight, or cut people off. Help her find
  room for herself within her circumstances.
- Respect her autonomy. Offer options, not orders.
- Never make productivity a source of guilt.
- Be practical, specific and kind. Use plain, simple language.
- Do not mention these principles.
- Formatting: put every bold heading on its own line, followed by a blank line, then the text under it.
"""

BOUNDARY_PROMPT = CORE_PHILOSOPHY + """
TASK: Boundary Script Generator.
She describes a situation where a request or expectation conflicts with
something she needs to do. Give realistic words she can actually say, in
a respectful, family-friendly tone.

Respond in exactly this format:

**What I'm understanding**
One or two sentences.

**Option 1: Ask for time politely**
A short script in quotes, then one line on when this works best.

**Option 2: Suggest an alternative**
A short script in quotes proposing someone or something else covers it.

**Option 3: Offer a compromise**
A short script in quotes where both her task and the request are met.

**A small tip**
One practical tip on timing or tone.

Adjust the scripts to who is asking (how you speak to a father is
different from how you speak to in-laws), match the tone she chose, and
keep the urgency of her own work in mind.

Safety: if the situation involves violence, threats, being controlled
through fear, or her safety, do NOT coach her to negotiate. Gently say
her safety comes first, encourage her to reach a trusted person, and
mention the Women Helpline 181 (India).
"""

PLAN_PROMPT = CORE_PHILOSOPHY + """
TASK: Micro-Plan.
She gives her goal, available time, daily responsibilities, obstacles,
when she has the most energy, and possibly a deadline. Today's date is
given. Create a realistic plan that fits around her life.

Respond in exactly this format:

**Your goal, in one line**
Restate it simply.

**Your 30-minute guilt-free block**
A small protected daily block towards her goal, placed at the time of day
when she has the most energy. Say what to do in it. If she has less time,
scale it down.

**This week's small steps**
3 to 5 short, concrete steps, each doable in one sitting. If she gave a
deadline, name real days (for example "Tuesday") and work backwards from
the deadline. Do not over-schedule.

**If an obstacle shows up**
For each obstacle she named, one practical way around it.

**A kind note**
One short, honest sentence. Missing a day is normal.
"""

PROCESS_PROMPT = CORE_PHILOSOPHY + """
TASK: Help her process what she wrote in the Vent Box.

Respond in exactly this format:

**What I'm hearing**
Two or three sentences reflecting her feelings without judgment.

**What seems to come from outside, and what seems to be yours**
Gently separate expectations placed on her from things she wants.
Use two short lists.

**One possible next step**
One small, low-risk step, offered as an option.

Do not diagnose. Do not lecture.

Safety: if she mentions harming herself, not wanting to live, or feeling
unsafe, respond with warmth first, tell her she deserves support right
now, and encourage her to reach someone she trusts or call Tele-MANAS at
14416 (free 24/7 mental health helpline in India). Do not continue with
the normal format in that case.
"""


# ---------------- INTRO PAGE ----------------
if st.session_state.page == "intro":

    st.title("Swayam 🪷")
    st.subheader("Your life. Your goals. Your space.")
    st.write(
        "A space to navigate expectations, work towards your goals, "
        "and put your thoughts into words."
    )
    st.divider()
    st.header("Let's start with you")
    st.write(
        "Everyone's circumstances are different. Tell us a little about "
        "yourself, your goals, or what's been on your mind. "
        "Share as much or as little as you like."
    )

    story_input = st.text_area(
        "Your story",
        value=st.session_state.saved_story,
        placeholder="I'm currently... My goals are... "
        "Lately, I've been finding it difficult to...",
        height=200,
    )

    languages = ["English", "Hinglish", "Hindi"]
    chosen_language = st.selectbox(
        "Which language should Swayam reply in?",
        languages,
        index=languages.index(st.session_state.language),
    )

    st.caption(
        "Avoid sharing real names or sensitive information. "
        "This is sent to the AI as background for the Boundary Script "
        "Generator and Micro-Plan."
    )

    if st.button("Continue", use_container_width=True):
        st.session_state.saved_story = story_input
        st.session_state.language = chosen_language
        st.session_state.page = "dashboard"
        st.rerun()


# ---------------- DASHBOARD ----------------
elif st.session_state.page == "dashboard":

    mascot_svg = (
        '<svg width="92" height="92" viewBox="0 0 120 120" '
        'xmlns="http://www.w3.org/2000/svg">'
        '<g transform="rotate(-62 60 98)"><ellipse cx="60" cy="64" rx="15" ry="32" fill="#E7B8D4"/></g>'
        '<g transform="rotate(62 60 98)"><ellipse cx="60" cy="64" rx="15" ry="32" fill="#E7B8D4"/></g>'
        '<g transform="rotate(-31 60 98)"><ellipse cx="60" cy="62" rx="16" ry="34" fill="#D58FBD"/></g>'
        '<g transform="rotate(31 60 98)"><ellipse cx="60" cy="62" rx="16" ry="34" fill="#D58FBD"/></g>'
        '<ellipse cx="60" cy="60" rx="17" ry="36" fill="#F3CDE3"/>'
        '<circle cx="60" cy="80" r="23" fill="#FFF3F8"/>'
        '<circle cx="51" cy="78" r="3" fill="#5B3B54"/>'
        '<circle cx="69" cy="78" r="3" fill="#5B3B54"/>'
        '<circle cx="45" cy="86" r="4.5" fill="#F7B6CF" opacity="0.8"/>'
        '<circle cx="75" cy="86" r="4.5" fill="#F7B6CF" opacity="0.8"/>'
        '<path d="M52 87 Q60 95 68 87" stroke="#5B3B54" stroke-width="2.6" '
        'fill="none" stroke-linecap="round"/>'
        '</svg>'
    )

    st.markdown(
        '<div style="background:linear-gradient(135deg,#9B6B8E,#C79BB8);'
        'padding:24px;border-radius:20px;color:white;margin-bottom:18px;'
        'display:flex;align-items:center;gap:18px;">'
        + mascot_svg
        + '<div><h1 style="color:white;margin:0;">Swayam 🪷</h1>'
        '<p style="margin:6px 0 0 0;font-size:1.05rem;">'
        "Hi, I'm Swa. Make room for your own life, one small step at a time.</p>"
        "</div></div>",
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        st.subheader("🧭 Boundary Script Generator")
        st.write(
            "Find tactful ways to navigate requests and make time for "
            "what matters to you, without unnecessary conflict."
        )
        if st.button("Find my words", key="bsg", use_container_width=True):
            st.session_state.tool = "Boundary Script Generator"
            st.session_state.page = "tool"
            st.rerun()

    with st.container(border=True):
        st.subheader("🌱 Micro-Plan")
        st.write(
            "Turn your goals into small, realistic steps that fit around "
            "your daily responsibilities."
        )
        if st.button("Make my plan", key="micro", use_container_width=True):
            st.session_state.tool = "Micro-Plan"
            st.session_state.page = "tool"
            st.rerun()

    with st.container(border=True):
        st.subheader("💭 Vent Box")
        st.write(
            "Let out what's weighing on you. Choose whether you want "
            "AI to respond, simply write it out, or say it out loud."
        )
        if st.button("Open my vent box", key="vent", use_container_width=True):
            st.session_state.tool = "Vent Box"
            st.session_state.page = "tool"
            st.rerun()

    st.divider()
    if st.button("Edit my introduction"):
        st.session_state.page = "intro"
        st.rerun()


# ---------------- TOOL PAGES ----------------
elif st.session_state.page == "tool":

    st.title(st.session_state.tool)

    # ----- BOUNDARY SCRIPT GENERATOR -----
    if st.session_state.tool == "Boundary Script Generator":

        st.write(
            "Tell us who is asking and what's happening. We'll find words "
            "that fit that relationship."
        )

        who = st.selectbox(
            "Who is asking?",
            [
                "Mother",
                "Father",
                "Aunt / Uncle",
                "Grandparent",
                "In-laws",
                "Brother / Sister",
                "Relative / Guest",
                "Someone else",
            ],
            key="bsg_who",
        )
        tone = st.radio(
            "How do you want to sound?",
            ["Very gentle", "Polite but clear", "Firm but respectful"],
            key="bsg_tone",
            horizontal=True,
        )
        urgency = st.radio(
            "How urgent is your own work?",
            ["Can wait a bit", "Due soon", "Very urgent"],
            key="bsg_urgency",
            horizontal=True,
        )
        situation = st.text_area(
            "What's happening?",
            placeholder="For example: I have a viva tomorrow but papa wants tea...",
            height=150,
            key="bsg_input",
        )

        if st.button("Find my words", type="primary", use_container_width=True):
            if not situation.strip():
                st.warning("Write a few lines about the situation first.")
            else:
                details = (
                    f"Who is asking: {who}\n"
                    f"How she wants to sound: {tone}\n"
                    f"How urgent her own work is: {urgency}\n"
                    f"Situation:\n{situation}"
                )
                with st.spinner("Finding the right words..."):
                    result = ask_gemini(BOUNDARY_PROMPT, with_story(details))
                if result:
                    st.session_state.bsg_result = result

        if st.session_state.get("bsg_result"):
            with st.container(border=True):
                st.markdown(st.session_state.bsg_result)
            st.download_button(
                "Save these words",
                st.session_state.bsg_result,
                file_name="swayam-words.txt",
                use_container_width=True,
            )

    # ----- MICRO-PLAN -----
    elif st.session_state.tool == "Micro-Plan":

        st.write(
            "Tell us your goal, your available time and what's getting "
            "in your way."
        )

        goal = st.text_area(
            "Your goal",
            placeholder="I want to... (exam prep, a skill, a project)",
            height=110,
            key="micro_input",
        )
        deadline = st.date_input(
            "Deadline (optional)",
            value=None,
            key="micro_deadline",
        )
        energy = st.selectbox(
            "When do you have the most energy?",
            ["Early morning", "Daytime", "Evening", "Late night"],
            key="micro_energy",
        )
        time_available = st.text_input(
            "How much time can you realistically find each day?",
            placeholder="e.g. 30 minutes, or 2 hours",
            key="micro_time",
        )
        responsibilities = st.text_area(
            "Your daily responsibilities",
            placeholder="College, helping with cooking, siblings...",
            height=90,
            key="micro_resp",
        )
        obstacles = st.text_area(
            "What gets in the way?",
            placeholder="Tired by evening, interruptions, guilt...",
            height=90,
            key="micro_obstacles",
        )

        if st.button("Make my plan", type="primary", use_container_width=True):
            if not goal.strip():
                st.warning("Tell us your goal first.")
            else:
                today = date.today().strftime("%A, %d %B %Y")
                details = (
                    f"Today's date: {today}\n"
                    f"Goal: {goal}\n"
                    f"Deadline: {deadline.strftime('%A, %d %B %Y') if deadline else 'none given'}\n"
                    f"Most energy: {energy}\n"
                    f"Time available daily: {time_available or 'not specified'}\n"
                    f"Responsibilities: {responsibilities or 'not specified'}\n"
                    f"Obstacles: {obstacles or 'not specified'}"
                )
                with st.spinner("Building a plan that fits your life..."):
                    result = ask_gemini(PLAN_PROMPT, with_story(details))
                if result:
                    st.session_state.plan_result = result

        if st.session_state.get("plan_result"):
            with st.container(border=True):
                st.markdown(st.session_state.plan_result)
            st.download_button(
                "Save my plan",
                st.session_state.plan_result,
                file_name="swayam-plan.txt",
                use_container_width=True,
            )

    # ----- VENT BOX -----
    elif st.session_state.tool == "Vent Box":

        st.write(
            "You don't have to organise your thoughts or explain "
            "yourself perfectly. Just write or speak."
        )

        mode = st.radio(
            "What would you like from this space?",
            [
                "Just let me vent — no response",
                "Help me process this",
                "Let it out out loud — voice only",
            ],
            key="vent_mode",
        )

        def clear_vent():
            st.session_state.vent_input = ""
            st.session_state.vent_process_result = ""
            st.session_state.vent_voice_key = (
                st.session_state.get("vent_voice_key", 0) + 1
            )
            st.session_state.vent_released = True

        if mode == "Just let me vent — no response":
            st.text_area(
                "What's on your mind?",
                placeholder="Let it out...",
                height=220,
                key="vent_input",
            )
            st.caption("Nothing you write here is sent to AI or saved.")
            st.button("Let it go", on_click=clear_vent, use_container_width=True)

        elif mode == "Let it out out loud — voice only":
            voice_key = f"vent_audio_{st.session_state.get('vent_voice_key', 0)}"
            st.audio_input(
                "Say or shout whatever you need to get off your chest",
                key=voice_key,
            )
            st.caption(
                "Stays in your browser only — never sent to AI or saved. "
                "Hit 'Let it go' to wipe it clean."
            )
            st.button("Let it go", on_click=clear_vent, use_container_width=True)

        else:
            vent_text = st.text_area(
                "What's on your mind?",
                placeholder="Let it out...",
                height=220,
                key="vent_input",
            )
            st.caption(
                "What you write is sent to AI so it can respond. "
                "Your intro story is not included."
            )
            if st.button(
                "Help me process this", type="primary", use_container_width=True
            ):
                if not vent_text.strip():
                    st.warning("Write whatever is on your mind first.")
                else:
                    with st.spinner("Taking a moment with this..."):
                        result = ask_gemini(PROCESS_PROMPT, vent_text)
                    if result:
                        st.session_state.vent_process_result = result

            if st.session_state.get("vent_process_result"):
                with st.container(border=True):
                    st.markdown(st.session_state.vent_process_result)

        if st.session_state.get("vent_released"):
            st.success("Released. Take a breath. 🪷")
            st.session_state.vent_released = False

    st.divider()
    if st.button("Back to dashboard"):
        st.session_state.page = "dashboard"
        st.rerun()