# streamlit_app.py

import streamlit as st
import textwrap
from io import StringIO
import sys
from dataclasses import dataclass
from typing import Callable, Dict, List
from PIL import Image, ImageDraw, ImageFont
import base64
import datetime

# ==========================
# App Config & Theming
# ==========================
st.set_page_config(
    page_title="Python Playground for Kids",
    page_icon="🐍",
    layout="wide",
)

# Minimal custom CSS to make it pop a bit
st.markdown(
    """
    <style>
      .stApp {background: linear-gradient(180deg,#fff 0%, #f6f9ff 60%, #eef6ff 100%);} 
      .lesson-card {border-radius: 18px; padding: 20px; background: #ffffffaa; box-shadow: 0 10px 30px rgba(0,0,0,0.08);} 
      .badge {display:inline-block; padding:6px 12px; border-radius: 999px; background:#eef2ff; margin-right:8px; margin-top:6px;}
      .locked {opacity: 0.5; filter: grayscale(0.2);} 
      .success {background:#ecfdf5;border:1px solid #10b98133;padding:12px;border-radius:12px}
      .fail {background:#fff7ed;border:1px solid #f59e0b33;padding:12px;border-radius:12px}
      .codebox .stTextArea textarea {font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; font-size: 0.95rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ==========================
# Lesson Model
# ==========================
@dataclass
class Lesson:
    title: str
    concept: str
    prompt: str
    check: Callable[[str, str], bool]  # (code, stdout) -> passed?
    starter: str
    badge: str
    solution: str


def contains_any(text: str, needles: List[str]) -> bool:
    text_low = text.lower()
    return any(n in text_low for n in needles)


LESSONS: List[Lesson] = [
    Lesson(
        title="Level 1 · Printing",
        concept="Use the print() function to display text on the screen.",
        prompt="Print your name using print().",
        check=lambda code, out: contains_any(code, ["print"]) and len(out.strip())>0,
        starter="""# Try printing your name below\nprint("Hello, World!")\n""",
        badge="🏅 First Program",
        solution='print("My name is Ada!")',
    ),
    Lesson(
        title="Level 2 · Variables",
        concept="Variables store information so you can reuse it later.",
        prompt="Create a variable called age with your age and print it.",
        check=lambda code, out: contains_any(code,["age"]) and contains_any(code,["print"]) and any(ch.isdigit() for ch in code),
        starter="""# Create a variable named age and print it\nage = 10\nprint(age)\n""",
        badge="🏅 Variable Master",
        solution='age = 11\nprint(age)\n',
    ),
    Lesson(
        title="Level 3 · Math",
        concept="You can add (+), subtract (-), multiply (*), and divide (/) numbers.",
        prompt="Add your age to 10 and print the result.",
        check=lambda code, out: contains_any(code,["+ 10","+10"]) and contains_any(code,["print"]) and len(out.strip())>0,
        starter="""# Change age and add 10\nage = 9\nprint(age + 10)\n""",
        badge="🏅 Math Whiz",
        solution='age = 12\nprint(age + 10)\n',
    ),
    Lesson(
        title="Level 4 · If Statements",
        concept="If statements let Python make decisions.",
        prompt="Print 'You are a teenager!' if age is greater than or equal to 13.",
        check=lambda code, out: contains_any(code,["if"]) and "teenager" in out.lower(),
        starter="""# Update age and add an if-statement\nage = 14\nif age >= 13:\n    print("You are a teenager!")\n""",
        badge="🏅 Decision Maker",
        solution='age = 13\nif age >= 13:\n    print("You are a teenager!")\n',
    ),
    Lesson(
        title="Level 5 · Loops",
        concept="Loops repeat actions for you.",
        prompt="Write a loop that prints your name 5 times.",
        check=lambda code, out: contains_any(code,["for"]) and contains_any(code,["range(5)"]) and len(out.strip().splitlines())>=5,
        starter="""# Print your name 5 times\nfor i in range(5):\n    print("Ada")\n""",
        badge="🏅 Loop Master",
        solution='for i in range(5):\n    print("Ada")\n',
    ),
]

# ==========================
# Session State
# ==========================
if "points" not in st.session_state:
    st.session_state.points = 0
if "badges" not in st.session_state:
    st.session_state.badges: List[str] = []
if "unlocked" not in st.session_state:
    st.session_state.unlocked = 1  # first level unlocked
if "code_buffers" not in st.session_state:
    st.session_state.code_buffers = {i: l.starter for i, l in enumerate(LESSONS)}
if "completed" not in st.session_state:
    st.session_state.completed: Dict[int,bool] = {}

# ==========================
# Sidebar: Progress & Controls
# ==========================
with st.sidebar:
    st.header("🎮 Your Progress")
    st.metric("Points", st.session_state.points)
    if st.session_state.badges:
        st.caption("Badges earned:")
        for b in st.session_state.badges:
            st.markdown(f"<span class='badge'>{b}</span>", unsafe_allow_html=True)
    else:
        st.caption("No badges yet. You got this! ✨")

    st.divider()
    if st.button("🔁 Reset Progress", type="secondary"):
        st.session_state.points = 0
        st.session_state.badges = []
        st.session_state.unlocked = 1
        st.session_state.completed = {}
        st.session_state.code_buffers = {i: l.starter for i, l in enumerate(LESSONS)}
        st.experimental_rerun()

# ==========================
# Header
# ==========================
st.title("🐍 Python Playground for Kids")
st.subheader("Learn step-by-step with levels, stars, and badges — all in a friendly sandbox!")
st.write("Complete each level to unlock the next. Earn **10 points** and a **badge** for each success.")

# ==========================
# Utility: Run user code safely (stdout capture)
# ==========================
def run_code_collect_output(code: str) -> str:
    buff = StringIO()
    old_stdout = sys.stdout
    try:
        sys.stdout = buff
        # Isolated namespace for user code
        local_ns = {}
        exec(code, {"__builtins__": __builtins__}, local_ns)
        return buff.getvalue()
    finally:
        sys.stdout = old_stdout

# ==========================
# Certificate Generator (PIL)
# ==========================
def make_certificate_png(name: str, points: int, badges: List[str]) -> bytes:
    width, height = 1200, 800
    img = Image.new("RGB", (width, height), color=(245, 249, 255))
    draw = ImageDraw.Draw(img)

    # Load default fonts (Pillow will fallback if not available)
    try:
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 64)
        name_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 54)
        body_font = ImageFont.truetype("DejaVuSans.ttf", 32)
        small_font = ImageFont.truetype("DejaVuSans.ttf", 24)
    except Exception:
        title_font = ImageFont.load_default()
        name_font = ImageFont.load_default()
        body_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    # Frame
    draw.rectangle([30, 30, width-30, height-30], outline=(40, 70, 170), width=6)

    # Title
    title = "Certificate of Completion"
    tw, th = draw.textsize(title, font=title_font)
    draw.text(((width-tw)//2, 90), title, fill=(30, 50, 120), font=title_font)

    # Name
    subtitle = "awarded to"
    sw, sh = draw.textsize(subtitle, font=body_font)
    draw.text(((width-sw)//2, 200), subtitle, fill=(50, 80, 160), font=body_font)

    nw, nh = draw.textsize(name, font=name_font)
    draw.text(((width-nw)//2, 250), name, fill=(0, 0, 0), font=name_font)

    # Body
    body = f"for completing the Python Playground on {datetime.date.today().isoformat()}"
    bw, bh = draw.textsize(body, font=small_font)
    draw.text(((width-bw)//2, 330), body, fill=(60, 60, 60), font=small_font)

    # Points & badges
    stat = f"Points: {points}  •  Badges: {len(badges)}"
    sw, sh = draw.textsize(stat, font=body_font)
    draw.text(((width-sw)//2, 420), stat, fill=(30, 30, 30), font=body_font)

    # Badges list
    y = 480
    for b in badges:
        draw.text((180, y), b, fill=(20, 20, 20), font=small_font)
        y += 36

    # Signature line
    draw.line([(180, height-160), (600, height-160)], fill=(0, 0, 0), width=2)
    draw.text((180, height-150), "Instructor", fill=(0,0,0), font=small_font)

    # Encode PNG
    buf = StringIO()
    import io
    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()

# ==========================
# Lessons UI
# ==========================
for idx, lesson in enumerate(LESSONS, start=1):
    locked = idx > st.session_state.unlocked

    with st.container():
        cols = st.columns([1, 3])
        with cols[0]:
            st.markdown(f"### {lesson.title} {'🔒' if locked else '🔓'}")
            st.write(lesson.concept)
            st.markdown(f"**Exercise:** {lesson.prompt}")
            if idx in st.session_state.completed:
                st.markdown(f"<div class='success'>✅ Completed! +10 points<br/>{lesson.badge}</div>", unsafe_allow_html=True)
            elif locked:
                st.markdown("<div class='fail'>🔒 Locked. Complete previous level to unlock.</div>", unsafe_allow_html=True)

        with cols[1]:
            box_class = "locked" if locked else ""
            st.markdown(f"<div class='lesson-card {box_class}'>", unsafe_allow_html=True)
            code_key = f"code_{idx}"
            st.session_state.code_buffers[idx-1] = st.text_area(
                "Your Code:",
                value=st.session_state.code_buffers[idx-1],
                key=code_key,
                height=180,
                disabled=locked,
                help="Edit the code and click Run."
            )

            c1, c2, c3, c4 = st.columns([1,1,1,2])
            run_clicked = c1.button("▶️ Run", disabled=locked, key=f"run_{idx}")
            hint_clicked = c2.button("💡 Hint", disabled=locked, key=f"hint_{idx}")
            sol_clicked = c3.button("👀 Show Solution", disabled=locked, key=f"sol_{idx}")

            output_placeholder = st.empty()

            if hint_clicked and not locked:
                st.info("Try to read the prompt again: the solution should **print** something, and match the goal exactly.")

            if sol_clicked and not locked:
                with st.expander("One possible solution"):
                    st.code(lesson.solution, language="python")

            if run_clicked and not locked:
                code = st.session_state.code_buffers[idx-1]
                try:
                    out = run_code_collect_output(code)
                    if out:
                        output_placeholder.code(out)
                    else:
                        output_placeholder.info("(No output) Use print() to show results.")

                    passed = lesson.check(code, out)
                    if passed:
                        if idx not in st.session_state.completed:
                            st.session_state.points += 10
                            st.session_state.badges.append(lesson.badge)
                            st.session_state.completed[idx] = True
                            st.session_state.unlocked = max(st.session_state.unlocked, idx+1)
                            st.balloons()
                        st.success(f"Great job! You earned 10 points and unlocked: {lesson.badge}")
                    else:
                        st.warning("Code ran, but didn't match the goal yet. Adjust and try again!")
                except Exception as e:
                    output_placeholder.error(f"Error: {e}")

            st.markdown("</div>", unsafe_allow_html=True)

    st.divider()

# ==========================
# Final Certificate Section
# ==========================
all_done = len(st.session_state.completed) == len(LESSONS)
if all_done:
    st.success("🏆 You completed all levels! Grab your certificate below.")
    with st.form("cert_form"):
        name = st.text_input("Your Name for the certificate", value="Young Pythonista")
        submit = st.form_submit_button("Generate Certificate 🪪")
    if submit:
        png_bytes = make_certificate_png(name, st.session_state.points, st.session_state.badges)
        st.image(png_bytes, caption="Certificate Preview", use_column_width=True)
        st.download_button(
            label="⬇️ Download Certificate (PNG)",
            data=png_bytes,
            file_name=f"python_playground_certificate_{name.replace(' ','_')}.png",
            mime="image/png",
        )
else:
    st.info("Finish all levels to unlock your certificate!")

# ==========================
# Footer
# ==========================
st.caption("Made with ❤️ in Streamlit. Parents: run `pip install streamlit pillow` then `streamlit run streamlit_app.py`.")
