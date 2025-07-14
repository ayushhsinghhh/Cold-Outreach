import streamlit as st
import pdfplumber
import requests
from docx import Document

# --- Streamlit page setup ---
st.set_page_config(page_title="Internship Outreach Assistant", layout="centered")
st.title("🎯 Internship Outreach Assistant")
st.write("Upload your resume and paste the job description to generate a tailored cold email or cover letter.")

# --- Upload Inputs ---
resume_file = st.file_uploader("📄 Upload Resume (PDF only)", type=["pdf"])
jd_text = st.text_area("💼 Paste Job Description Here", height=200)
email_type = st.selectbox("✉️ Select Output Type", ["Cold Email", "Cover Letter"])

# --- Helper Functions ---
def extract_resume_text(pdf_file):
    text = ''
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + '\n'
    return text.strip()

def extract_text_from_docx(file_path):
    try:
        doc = Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
    except Exception as e:
        st.error(f"Error reading template: {e}")
        return ""

def load_prompt_template(path):
    try:
        with open(path, "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        st.error(f"Prompt template '{path}' not found.")
        return ""

def call_groq(prompt):
    api_key = "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"  # ⚠️ Replace or move to secrets.toml
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama3-8b-8192",
        "messages": [{"role": "user", "content": prompt}]
    }

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json=payload
    )

    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        st.error(f"Error from Groq API: {response.status_code} - {response.text}")
        return ""

# --- Main Logic ---
if resume_file and jd_text.strip():
    if st.button("🚀 Generate"):
        with st.spinner(f"Creating your {email_type.lower()}..."):
            resume_text = extract_resume_text(resume_file)

            if email_type == "Cold Email":
                email_template = extract_text_from_docx("email.docx")
                prompt_template = load_prompt_template("prompt.txt")

                final_prompt = prompt_template.format(
                    resume_text=resume_text,
                    jd_text=jd_text,
                    email_template=email_template
                )

                output = call_groq(final_prompt)
                st.subheader("✅ Generated Cold Email")
                st.write(output)

            elif email_type == "Cover Letter":
                st.subheader("🛠️ Cover Letter")
                st.info("Cover letter generation is under development. Coming soon!")
else:
    st.info("Please upload your resume and paste the job description to proceed.")
