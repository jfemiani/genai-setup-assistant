import base64
import streamlit as st
from openai import OpenAI
import json
import os
import re
from base64 import b64encode, b64decode
import io
import zipfile
from datetime import datetime
from streamlit_paste_button import paste_image_button as pbutton
import html
import subprocess
import tempfile
import os

st.set_page_config(page_title="GenAI Setup Tutor", layout="wide")

CHAT_HISTORY_FILE = "chat_history.json"
IMG_DIR = "chat_images"

os.makedirs(IMG_DIR, exist_ok=True)



def generate_pdf_from_markdown(md_text):
    with tempfile.TemporaryDirectory() as tmpdir:
        md_path = os.path.join(tmpdir, "chat.md")
        pdf_path = os.path.join(tmpdir, "chat.pdf")

        with open(md_path, "w") as f:
            f.write(md_text)

        result = subprocess.run(
            [
                "pandoc",
                md_path,
                "-o",
                pdf_path,
                "--pdf-engine=tectonic",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=os.environ,  # 🔑 preserve the conda environment
        )

        if result.returncode != 0:
            raise RuntimeError(f"PDF generation failed:\n{result.stderr.decode()}")

        with open(pdf_path, "rb") as f:
            return f.read()


def strip_html_comments(text):
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)

# --- Load chat history from disk ---
def load_messages():
    if os.path.exists(CHAT_HISTORY_FILE):
        with open(CHAT_HISTORY_FILE, "r") as f:
            return json.load(f)
    else:
        with open("system-prompt.md", "r") as f:
            system_prompt = f.read()
        return [
            {"role": "system", "content": system_prompt},
            {"role": "assistant", "content":
                "Welcome! Let's get started. What operating system are you using? <!--[[Windows]], [[macOS Intel]], [[macOS Apple Silicon]], [[Linux]]-->"}
        ]

# --- Save chat history to disk ---
def save_messages(messages):
    with open(CHAT_HISTORY_FILE, "w") as f:
        json.dump(messages, f, indent=2)

# --- Initialize chat messages in session ---
if "messages" not in st.session_state:
    st.session_state.messages = load_messages()

# --- API Key Input ---


st.text("Pandoc version:")
st.code(subprocess.getoutput("pandoc --version"))

st.text("Tectonic version:")
st.code(subprocess.getoutput("tectonic --version"))



st.title("✨ Lab 0 AI Assistant")
st.caption("Your interactive helper for getting started with the development environment.")

st.subheader("🔐 OpenAI API Key")
st.info("Paste your OpenAI key below. This will not be saved. You can use a password manager.  \n"
        "Your key is not saved. You can get one at https://platform.openai.com/account/api-keys.")
user_api_key = st.text_input(
    "API Key",
    type="password",
    key="api_key_input",
    placeholder="sk-...",
    help="Your key is not saved. You can get one at https://platform.openai.com/account/api-keys."
)

if not user_api_key or not user_api_key.startswith("sk-"):
    st.warning("Please enter a valid OpenAI API key to begin.")
    st.stop()

# --- Sidebar Info ---
st.sidebar.header("ℹ️ About This Tutor")
st.sidebar.info(
    "This assistant will walk you through setting up a development environment "
    "for CSE 4/534. Each step is tailored to your OS and environment. "
    "Ask questions if anything goes wrong!"
)

# --- Model Selection ---
st.sidebar.header("🧠 Model Selection")
model = "gpt-4o"
is_gpt4o = model == "gpt-4o"


# --- Chat Log Download (Markdown + images zipped) ---
def generate_chat_markdown():
    """Generates markdown text and image asset paths from the chat history."""
    md_lines = []
    assets = []
    for i, msg in enumerate(st.session_state.messages):
        if msg["role"] == "system":
            continue
        role = msg["role"].capitalize()
        content = msg["content"]
        md_lines.append(f"## {role}\n")
        if isinstance(content, list):
            for block in content:
                if block["type"] == "text":
                    md_lines.append(block["text"] + "\n")
                elif block["type"] == "image_url":
                    filename = f"image_{i}.png"
                    img_path = os.path.join(IMG_DIR, filename)
                    with open(img_path, "wb") as f:
                        f.write(b64decode(block["image_url"]["url"].split(",")[-1]))
                    assets.append(img_path)
                    md_lines.append(f"![Image]({filename})\n")
        else:
            md_lines.append(content + "\n")
    return "\n".join(md_lines), assets


def export_chat_as_markdown_zip():
    """Zips up the generated markdown file and image assets for download."""
    md_text, assets = generate_chat_markdown()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr("chat.md", md_text)
        for asset in assets:
            z.write(asset, os.path.basename(asset))
    return buffer.getvalue()



if "zip_data" not in st.session_state:
    st.session_state.zip_data = None

# Step 1: Prepare zip (generate on click)
if st.sidebar.button("📦 Prepare Zip"):
    st.session_state.zip_data = export_chat_as_markdown_zip()

# Step 2: Show download button only if zip is ready
if st.session_state.zip_data:
    st.sidebar.download_button(
        label="⬇️ Download Zip",
        data=st.session_state.zip_data,
        file_name="chat_export.zip",
        mime="application/zip"
    )

st.sidebar.write("")
if st.sidebar.button("📄 Generate PDF"):
    markdown_text, assets = generate_chat_markdown()  # You define this
    try:
        pdf_data = generate_pdf_from_markdown(markdown_text)
        st.session_state.chat_pdf = pdf_data
    except Exception as e:
        st.error(str(e))

if "chat_pdf" in st.session_state:
    st.sidebar.download_button(
        label="⬇️ Download PDF",
        data=st.session_state.chat_pdf,
        file_name="chat_export.pdf",
        mime="application/pdf"
    )


st.sidebar.write("")

# --- Restart Button ---
if st.sidebar.button("🔄 Restart Chat"):
    if os.path.exists(CHAT_HISTORY_FILE):
        os.remove(CHAT_HISTORY_FILE)
    for key in ["messages", "pending_user_input", "pasted_image"]:
        st.session_state.pop(key, None)
    st.rerun()

# --- Show System Prompt (Optional) ---
if st.sidebar.checkbox("Show setup instructions (system prompt)"):
    for msg in st.session_state.messages:
        if msg["role"] == "system":
            with st.chat_message("assistant"):
                st.markdown(msg["content"])

# --- Display Chat History ---


def render_buttons_from_text(text):
    buttons = re.findall(r"\[\[(.*?)\]\]", text)
    if buttons:
        st.write("**Choose an option:**")
        cols = st.columns(len(buttons))  
        for i, label in enumerate(buttons):
            if cols[i].button(label.strip()):
                st.session_state.pending_user_input = label.strip()
                save_messages(st.session_state.messages)
                st.rerun()


for i, msg in enumerate(st.session_state.messages):
    if msg["role"] == "system":
        continue
    with st.chat_message(msg["role"]):
        content = msg["content"]
        if isinstance(content, list):
            for block in content:
                if block["type"] == "text":
                    visible = strip_html_comments(block["text"])
                    st.markdown(visible, unsafe_allow_html=True)
                elif block["type"] == "image_url":
                    st.image(block["image_url"]["url"])
        else:
            visible = strip_html_comments(content)
            st.markdown(visible, unsafe_allow_html=True)
            if msg["role"] == "assistant" and i == len(st.session_state.messages) -1:
                render_buttons_from_text(content)
                

# --- Chat interaction ---
client = OpenAI(api_key=user_api_key)

pending = st.session_state.pop("pending_user_input", None)
image_data = st.session_state.pop("pasted_image", None)

if pending:
    if is_gpt4o and image_data:
        b64_image = b64encode(image_data).decode("utf-8")
        content = [
            {"type": "text", "text": pending},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_image}"}}
        ]
    else:
        content = pending

    st.session_state.messages.append({"role": "user", "content": content})
    with st.chat_message("user"):
        if isinstance(content, list):
            for block in content:
                if block.get("type") == "text":
                    st.markdown(block["text"])
                elif block.get("type") == "image_url":
                    st.image(block["image_url"]["url"])
        else:
            st.markdown(content)

    with st.chat_message("assistant"):
        try:
            stream = client.chat.completions.create(
                model=model,
                messages=st.session_state.messages,
                stream=True,
            )
            response = st.write_stream(stream)
        except Exception as e:
            response = f"⚠️ Error: {e}"
            st.error(response)

    st.session_state.messages.append({"role": "assistant", "content": response})
    save_messages(st.session_state.messages)
    if "pasted_image" in st.session_state:
        del st.session_state["pasted_image"]
    st.session_state["paste_widget_key"] = "paste" + str(datetime.now().timestamp())
    st.rerun()

# --- Paste Image + Input ---
if is_gpt4o:
    col1, col2 = st.columns([4, 1])
    with col1:
        user_input = st.chat_input("Your response")
    with col2:
        paste_key = st.session_state.get("paste_widget_key", "paste1")
        pasted = pbutton("📋 Paste Image", key=paste_key)

    if pasted.image_data:
        buffer = io.BytesIO()
        pasted.image_data.save(buffer, format="PNG")
        st.session_state.pasted_image = buffer.getvalue()
    elif "pasted_image" not in st.session_state:
        st.session_state.pasted_image = None

    if st.session_state.pasted_image:
        st.image(st.session_state.pasted_image, caption="Image will be sent with your next message", output_format="PNG", width=100)

    if user_input:
        st.session_state.pending_user_input = user_input
        st.rerun()
else:
    user_input = st.chat_input("Your response")
    if user_input:
        st.session_state.pending_user_input = user_input
        st.rerun()
