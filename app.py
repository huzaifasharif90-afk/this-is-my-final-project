import os
import re
import streamlit as st
import pytesseract
from pdf2image import convert_from_path
from langchain_community.document_loaders import PyPDFLoader
from google import genai  # Modern official Google library

st.set_page_config(page_title="Quranic AI Study Assistant", page_icon="📖", layout="wide")

st.title("📖 Quranic AI Study Assistant")
st.markdown("Upload any Surah translation PDF (supports both standard text and scanned image PDFs) to automatically generate study insights using premium Gemini 1.5 Flash!")

# Streamlit will pull your key securely from the vault behind the scenes
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

# Correct modern client initialization
try:
    client = genai.Client(api_key=GEMINI_API_KEY)
except Exception as e:
    client = None

uploaded_file = st.file_uploader("Choose a Surah PDF file", type=["pdf"])

def clean_text(text):
    text = re.sub(r'(?i)https?://\S+|www\.\S+|alkalam\.pk|alkalam', '', text)
    text = re.sub(r'\b\d{3,4}\b', '', text)
    text = re.sub(r' +', ' ', text)
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    return "\n".join(lines)

if uploaded_file is not None:
    with open("temp_surah.pdf", "wb") as f:
        f.write(uploaded_file.getbuffer())

    with st.spinner("Reading and parsing your Surah PDF..."):
        try:
            loader = PyPDFLoader("temp_surah.pdf")
            raw_documents = loader.load()
            documents = []
            for doc in raw_documents:
                cleaned_content = clean_text(doc.page_content)
                if cleaned_content:
                    doc.page_content = cleaned_content
                    documents.append(doc)

            full_text = "\n".join([doc.page_content for doc in documents])

            # Apply OCR on Scanned image PDFs if standard text extraction yields nothing
            if len(full_text.strip()) < 100:
                st.info("🔍 Scanned PDF detected! Running high-resolution OCR scanner...")
                pages = convert_from_path('temp_surah.pdf', 150)
                extracted_paragraphs = []
                for page in pages[:5]:
                    page_text = pytesseract.image_to_string(page)
                    clean_lines = [line.strip() for line in page_text.split('\n') if len(line.strip()) > 15]
                    filtered_lines = [l for l in clean_lines if "alkalam" not in l.lower() and "www." not in l.lower()]
                    if filtered_lines:
                        extracted_paragraphs.append(" ".join(filtered_lines))
                full_text = "\n\n".join(extracted_paragraphs)

            st.success("Successfully loaded Surah context!")

            questions_list = [
                "What are the central themes and moral teachings discussed in this Surah?",
                "Who are the main figures, messengers, or nations mentioned in these verses?",
                "What specific commands or ethical guidelines are laid out for believers?",
                "How does the Surah describe the ultimate rewards of righteousness and faith?",
                "What warnings, consequences, or past events are highlighted for reflection?",
                "How is patience, perseverance, or trust in Divine wisdom illustrated?",
                "What attributes of creation, nature, or the universe are cited as signs?",
                "What specific prayers, invocations, or words of remembrance are recommended?",
                "What does the text instruct regarding societal justice and treating others?",
                "How can the concluding passages of this Surah be applied to modern daily life?"
            ]

            st.markdown("### 📋 Top 10 Study Questions from this Surah")
            selected_q = st.selectbox("Choose a study question to investigate:", ["-- Select a Question --"] + questions_list)

            if selected_q and selected_q != "-- Select a Question --":
                st.markdown(f"### 📝 Analysis for: *{selected_q}*")

                if client:
                    with st.spinner("Generating AI Analysis using Gemini..."):
                        prompt = f"""
                        You are an expert Quranic scholar and academic study assistant.
                        Use the following parsed text from a Surah translation to answer the study question.
                        If the text is noisy or contains OCR transcription errors, ignore the gibberish, extract the true essence/meanings, and provide an accurate, clear scholarly answer.

                        --- START SURAH TEXT ---
                        {full_text[:3000]}
                        --- END SURAH TEXT ---

                        STUDY QUESTION: {selected_q}

                        Format your response beautifully with 3 parts:
                        1. "Key Passage Insight": A clear, readable English translation of relevant verses.
                        2. "Detailed Academic Analysis": Explaining the context, core concepts, and grammar/narrative keys.
                        3. "Modern Takeaway / Application": Practical actions a modern believer can implement in daily life.
                        """
                        try:
                            # Correct modern API call syntax
                            response = client.models.generate_content(
                                model='gemini-3.8-flash',
                                contents=prompt,
                            )
                            st.markdown(response.text)
                        except Exception as api_err:
                            st.error(f"Gemini API request failed: {api_err}")
                else:
                    st.error("Gemini client initialization failed. Check your API Key Secrets setup.")

            st.markdown("---")
            st.markdown("### 💬 Ask the Surah Any Custom Question")
            user_query = st.text_input("Type your custom question here:", placeholder="e.g., What does the Surah say about mercy or the flight of birds?")

            if user_query:
                if client:
                    st.markdown("### 🤖 Live AI Scholar Response")
                    with st.spinner("Querying Gemini..."):
                        prompt = f"""
                        You are an expert Quranic scholar. Use the parsed text of this Surah to answer the user's custom question.
                        Provide references to verse content and explanations in clear English.

                        --- START SURAH TEXT ---
                        {full_text[:3000]}
                        --- END SURAH TEXT ---

                        USER QUESTION: {user_query}
                        """
                        try:
                            # Correct modern API call syntax
                            response = client.models.generate_content(
                                model='gemini-3.8-flash',
                                contents=prompt,
                            )
                            st.success(response.text)
                        except Exception as api_err:
                            st.error(f"Gemini API request failed: {api_err}")

        except Exception as e:
            st.error(f"An error occurred while reading the PDF: {e}")
