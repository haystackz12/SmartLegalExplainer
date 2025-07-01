import streamlit as st
import fitz  # PyMuPDF
import openai
import os
from dotenv import load_dotenv
from docx import Document
import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image
from io import BytesIO # For handling file-like objects for downloads
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import sys # Import sys to exit if key is missing

# Load API key from .env file (for local development)
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# --- CRITICAL DEBUGGING STEP ---
# This will explicitly check the API key and print a clear message to logs.
# If the key is missing, it will stop the app with a clear error.
if not OPENAI_API_KEY:
    st.error("ERROR: OpenAI API key is missing! Please set it in Streamlit Cloud secrets.")
    st.info("Go to your app on share.streamlit.io -> 'Settings' -> 'Secrets' and add OPENAI_API_KEY='your_key_here'")
    # For local testing, you might want to comment out sys.exit()
    # For deployment, sys.exit() ensures the app doesn't crash with a redacted error.
    sys.exit("OpenAI API key not found. Exiting application.")
else:
    st.sidebar.success("OpenAI API Key Loaded (first 5 chars: " + OPENAI_API_KEY[:5] + "...)")
    # You can also print to the actual logs for more detail (not shown on UI)
    print(f"DEBUG: API Key successfully loaded. Length: {len(OPENAI_API_KEY)}, Starts with: {OPENAI_API_KEY[:5]}...")


# Initialize the OpenAI client
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# --- Helper function to generate PDF for download ---
def create_pdf(text_content, title="Document Insight"):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Add title
    story.append(Paragraph(title, styles['h1']))
    story.append(Spacer(1, 0.2 * 100)) # Space after title

    # Add content
    for paragraph_text in text_content.split('\n'):
        if paragraph_text.strip(): # Only add non-empty paragraphs
            story.append(Paragraph(paragraph_text, styles['Normal']))
            story.append(Spacer(1, 0.1 * 100)) # Small space between paragraphs

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

# --- App Configuration ---
st.set_page_config(page_title="Smart Legal Doc Explainer", layout="wide", initial_sidebar_state="auto")

# Custom CSS for black background and updated button styles
st.markdown(
    """
    <style>
    .stApp {
        background-color: #1a1a1a; /* Very Dark Gray / Near Black */
        color: white; /* Ensure text is readable on dark background */
    }
    .stApp header {
        background-color: #1a1a1a; /* Keep header consistent */
    }
    .stApp [data-testid="stHeader"] {
        background-color: rgba(0,0,0,0); /* Make Streamlit header transparent */
    }
    .stApp [data-testid="stSidebar"] {
        background-color: #2c2c2c; /* Slightly lighter dark gray for sidebar */
    }
    h1, h2, h3, h4, h5, h6 {
        color: #87CEEB; /* Sky Blue for headers */
    }
    .stButton>button {
        background-color: #4682B4; /* Steel Blue for buttons */
        color: white;
        border-radius: 8px;
        border: none;
        padding: 10px 20px;
        font-size: 16px;
        cursor: pointer;
        transition: background-color 0.3s ease, transform 0.2s ease;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.3); /* Subtle shadow */
    }
    .stButton>button:hover {
        background-color: #5F9EA0; /* Cadet Blue on hover */
        transform: translateY(-2px); /* Slight lift effect */
        box-shadow: 4px 4px 10px rgba(0,0,0,0.5); /* Enhanced shadow on hover */
    }
    .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stSelectbox>div>div {
        background-color: #333333; /* Darker gray for input fields and selectbox */
        color: white;
        border-radius: 8px;
        border: 1px solid #4682B4;
        box-shadow: inset 1px 1px 3px rgba(0,0,0,0.4); /* Inner shadow for depth */
    }
    .stSelectbox>div>div>div {
        color: white;
    }
    .stAlert {
        background-color: #444444; /* Medium dark gray for alerts */
        color: white;
        border-radius: 8px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.3);
    }
    /* Style for download buttons */
    .stDownloadButton>button {
        background-color: #28a745; /* Green for download */
        color: white;
        border-radius: 8px;
        border: none;
        padding: 8px 15px;
        font-size: 14px;
        cursor: pointer;
        transition: background-color 0.3s ease;
        margin-left: 10px; /* Space from other buttons */
        box-shadow: 2px 2px 5px rgba(0,0,0,0.3);
    }
    .stDownloadButton>button:hover {
        background-color: #218838; /* Darker green on hover */
        transform: translateY(-1px);
    }
    /* Styling for the tab container */
    .stTabs [data-testid="stTabContent"] {
        background-color: #2c2c2c; /* Slightly lighter dark gray for tab content area */
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0px 0px 10px rgba(0,0,0,0.5); /* Shadow for the whole tab area */
    }
    /* Styling for individual tabs */
    .stTabs [data-testid="stTab"] {
        background-color: #333333; /* Darker gray for inactive tabs */
        color: #ADD8E6; /* Light blue text for inactive tabs */
        border-radius: 8px 8px 0 0;
        margin-right: 5px;
        padding: 10px 15px;
        transition: background-color 0.3s ease, color 0.3s ease;
    }
    .stTabs [data-testid="stTab"][aria-selected="true"] {
        background-color: #4682B4; /* Steel Blue for active tab */
        color: white;
        font-weight: bold;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("📄 Smart Legal Doc Explainer")
st.markdown("Upload a legal document (.pdf, .docx, .txt) to get comprehensive summaries, key takeaways, and answers to your questions.")

# --- How to Use and Section Explanations ---
with st.expander("💡 How to Use This Application & Section Guide"):
    st.markdown("""
    Welcome to the Smart Legal Doc Explainer! This tool helps you understand complex legal documents quickly and efficiently.

    **Here's how to use it:**
    1.  **Upload Your Document:** Use the file uploader to select your legal document (PDF, DOCX, or TXT). If it's a scanned PDF, check the 'Force OCR' option for better text extraction.
    2.  **Review Extracted Content & Detailed Insights:** The left column displays the full document text and provides tools for detailed analysis like Q&A, entity extraction, and clause explanations.
    3.  **Explore Overall AI Insights:** The right column offers high-level summaries, risk analysis, and document comparison, now organized into convenient tabs.
    4.  **Customize AI:** Use the sidebar on the left to provide custom instructions or define the AI's persona for all analyses.
    5.  **Download Insights:** After generating an insight, look for the download buttons to save the text as a PDF or TXT file.
    6.  **Clear & Start Over:** Use the "Clear Document & Start Over" button to reset the app and upload a new document.

    ---

    **Understanding the Sections:**

    * **1. Upload Your Document:**
        * **Purpose:** Where you provide the legal document for analysis.
        * **Features:** File uploader for PDF, DOCX, TXT; checkbox for Optical Character Recognition (OCR) for scanned PDFs; **NEW: "Clear Document & Start Over" button.**

    * **2. Extracted Document Content & Detailed Insights (Left Column):**
        * **Purpose:** Displays the raw text and provides tools for in-depth analysis of specific parts or aspects of the document.
        * **Features:**
            * **Full Document Text:** A large text area showing the complete document content.
            * **Ask a Question:** Allows you to ask specific questions about the document and get answers based on its content.
            * **Explain a Specific Clause:** Helps you understand individual complex clauses by selecting them from a dropdown.
            * **Key Entities & Data Extraction:** Identifies and lists important entities like parties, dates, and monetary values.
            * **Obligations & Rights:** Clearly outlines what each party must do and can do.
            * **Legal Term Glossary:** Provides plain-English definitions for legal jargon found in the document.
            * **Document Outline:** Generates a structured table of contents for the document.

    * **3. Overall AI Insights (Right Column - Now Tabbed!):**
        * **Purpose:** Contains high-level intelligent analysis tools for understanding the document as a whole or comparing it, now organized into logical tabs.
        * **Tabs & Features:**
            * **Summaries & Takeaways:** Contains "Full Document Summary" and "Key Takeaways."
            * **Detailed Extraction:** Contains "Key Entities & Data Extraction," "Obligations & Rights," "Legal Term Glossary," and "Document Outline."
            * **Q&A & Clause Explanation:** Contains "Ask a Question" and "Explain a Specific Clause."
            * **Comparison & Context:** Contains "Document Comparison," "Jurisdiction & Governing Law," and "Sentiment Analysis."

    * **AI Customization (Sidebar):**
        * **Purpose:** Allows you to guide the AI's behavior and style of explanation.
        * **Features:** A text area where you can input instructions like "Explain like a business owner" or "Be very concise."
    """)

# --- Sidebar for Custom AI Instructions ---
st.sidebar.header("AI Customization")
custom_ai_instruction = st.sidebar.text_area(
    "Provide Custom AI Instructions/Persona:",
    value="You are a legal expert who explains complex clauses in simple terms.",
    help="e.g., 'Explain like a 5th grader', 'Focus on financial implications', 'Be very concise.'"
)

# Initialize session state for full_text and uploaded_file, and all AI results
if 'full_text' not in st.session_state:
    st.session_state.full_text = ""
if 'uploaded_file_name' not in st.session_state:
    st.session_state.uploaded_file_name = None
# Initialize AI results
if 'summary_result' not in st.session_state: st.session_state.summary_result = ""
if 'takeaways_result' not in st.session_state: st.session_state.takeaways_result = ""
if 'qa_answer_result' not in st.session_state: st.session_state.qa_answer_result = ""
if 'clause_explanation_result' not in st.session_state: st.session_state.clause_explanation_result = ""
if 'entities_result' not in st.session_state: st.session_state.entities_result = ""
if 'obligations_rights_result' not in st.session_state: st.session_state.obligations_rights_result = ""
if 'glossary_result' not in st.session_state: st.session_state.glossary_result = ""
if 'outline_result' not in st.session_state: st.session_state.outline_result = ""
if 'risk_opportunity_result' not in st.session_state: st.session_state.risk_opportunity_result = ""
if 'comparison_result' not in st.session_state: st.session_state.comparison_result = ""
if 'jurisdiction_result' not in st.session_state: st.session_state.jurisdiction_result = ""
if 'sentiment_result' not in st.session_state: st.session_state.sentiment_result = ""

# --- Initialize input field session state keys ---
if 'q_a_input_tab' not in st.session_state: st.session_state.q_a_input_tab = ""
if 'clause_select_tab' not in st.session_state: st.session_state.clause_select_tab = ""
if 'compare_input_tab' not in st.session_state: st.session_state.compare_input_tab = ""

# --- File Uploader Widget (Moved to ensure it's always defined) ---
uploaded_file = st.file_uploader("Choose a legal document", type=["pdf", "docx", "txt"], key="main_file_uploader")
use_ocr = st.checkbox("Force Optical Character Recognition (OCR) for scanned PDFs (may take longer)")


# Logic to handle new file upload vs. existing file in session state
if uploaded_file and (st.session_state.uploaded_file_name is None or st.session_state.uploaded_file_name != uploaded_file.name):
    # New file uploaded, process it
    st.session_state.uploaded_file_name = uploaded_file.name
    file_type = uploaded_file.name.split(".")[-1].lower()
    processed_text = ""

    with st.spinner("Processing document..."):
        if file_type == "pdf":
            if use_ocr:
                try:
                    images = convert_from_bytes(uploaded_file.read())
                    text_list = []
                    for i, img in enumerate(images):
                        text_list.append(pytesseract.image_to_string(img))
                    processed_text = "\n".join(text_list)
                    st.success("OCR completed successfully!")
                except Exception as e:
                    st.error(f"OCR failed: {e}. Please ensure Tesseract and Poppler are correctly installed and configured.")
                    st.info("You can try unchecking 'Force OCR' if it's a searchable PDF.")
            else:
                try:
                    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
                    for page in doc:
                        processed_text += page.get_text()
                    st.success("Text extracted from PDF.")
                except Exception as e:
                    st.error(f"Failed to extract text from PDF: {e}. It might be a scanned document. Try checking 'Force OCR'.")

        elif file_type == "docx":
            try:
                doc = Document(uploaded_file)
                processed_text = "\n".join([p.text for p in doc.paragraphs])
                st.success("Text extracted from DOCX.")
            except Exception as e:
                st.error(f"Failed to process DOCX file: {e}")

        elif file_type == "txt":
            try:
                processed_text = uploaded_file.read().decode("utf-8")
                st.success("Text extracted from TXT.")
            except Exception as e:
                st.error(f"Failed to read TXT file: {e}. Ensure it's a valid UTF-8 text file.")
    st.session_state.full_text = processed_text # Store processed text in session state
    # Clear all AI results when a new file is uploaded
    st.session_state.summary_result = ""
    st.session_state.takeaways_result = ""
    st.session_state.qa_answer_result = ""
    st.session_state.clause_explanation_result = ""
    st.session_state.entities_result = ""
    st.session_state.obligations_rights_result = ""
    st.session_state.glossary_result = ""
    st.session_state.outline_result = ""
    st.session_state.risk_opportunity_result = ""
    st.session_state.comparison_result = ""
    st.session_state.jurisdiction_result = ""
    st.session_state.sentiment_result = ""
    # Also clear input fields that might hold old values
    st.session_state.q_a_input_tab = ""
    st.session_state.clause_select_tab = ""
    st.session_state.compare_input_tab = ""


elif st.session_state.uploaded_file_name and uploaded_file is None:
    # This case handles when a file was previously uploaded (and stored in session_state)
    # but the user has now cleared the file uploader widget.
    # In this scenario, we want to keep the full_text from session_state until the clear button is pressed.
    pass
else:
    # No file uploaded yet, or file is the same as before, and not explicitly cleared.
    pass

full_text = st.session_state.full_text # Use text from session state

# --- Clear Document Button ---
if st.button("Clear Document & Start Over", key="clear_doc_button"):
    st.session_state.full_text = ""
    st.session_state.uploaded_file_name = None
    # Clear all AI results
    st.session_state.summary_result = ""
    st.session_state.takeaways_result = ""
    st.session_state.qa_answer_result = ""
    st.session_state.clause_explanation_result = ""
    st.session_state.entities_result = ""
    st.session_state.obligations_rights_result = ""
    st.session_state.glossary_result = ""
    st.session_state.outline_result = ""
    st.session_state.risk_opportunity_result = ""
    st.session_state.comparison_result = ""
    st.session_state.jurisdiction_result = ""
    st.session_state.sentiment_result = ""
    # Also clear input fields that might hold old values
    st.session_state.q_a_input_tab = ""
    st.session_state.clause_select_tab = ""
    st.session_state.compare_input_tab = ""

    st.rerun() # Rerun the app to clear all outputs

# --- Display Extracted Text and AI Features ---
if full_text:
    # Create two columns for an even 50/50 split
    col_left, col_right = st.columns(2)

    with col_left:
        st.header("2. Extracted Document Content & Detailed Insights")
        st.text_area("Full Document Text", full_text, height=600, help="This is the full text extracted from your document.")

        if not OPENAI_API_KEY:
            st.error("OpenAI API key is not set. Please ensure OPENAI_API_KEY is in your .env file.")
        else:
            # --- Detailed Insights (Left Column) ---
            # Grouping detailed insights into their own tabs within the left column
            tab_qa, tab_clause, tab_entities, tab_obligations, tab_glossary, tab_outline = st.tabs([
                "Ask a Question", "Explain Clause", "Key Entities", "Obligations & Rights", "Legal Glossary", "Document Outline"
            ])

            with tab_qa:
                st.subheader("❓ Ask a Question")
                # Use value from session state for text input
                user_question = st.text_input("Enter your question about the document:", key="q_a_input_tab", value=st.session_state.q_a_input_tab)
                if st.button("Get Answer", key="q_a_button_tab") and user_question:
                    with st.spinner("Searching for an answer..."):
                        qa_prompt = f"""
{custom_ai_instruction}
Your task is to answer questions about a legal document.
Read the entire document provided below, and then answer the user's question concisely and accurately based *only* on the information present in the document.
If the information is not in the document, state that clearly.

Legal Document:
---
{full_text}
---

User's Question: "{user_question}"

Answer:
"""
                        try:
                            response = client.chat.completions.create(
                                model="gpt-4o",
                                messages=[
                                    {"role": "system", "content": custom_ai_instruction},
                                    {"role": "user", "content": qa_prompt}
                                ],
                                temperature=0.5,
                                max_tokens=300
                            )
                            st.session_state.qa_answer_result = response.choices[0].message.content.strip()
                            st.success("Answer Found!")
                        except openai.APIError as e:
                            st.error(f"OpenAI API Error: {e.status_code} - {e.response}")
                            st.info("Please check your API key and network connection.")
                            st.session_state.qa_answer_result = "" # Clear result on error
                        except Exception as e:
                            st.error(f"An unexpected error occurred during Q&A: {e}")
                            st.session_state.qa_answer_result = "" # Clear result on error
                
                if st.session_state.qa_answer_result:
                    st.write(st.session_state.qa_answer_result)
                    col_qa_dl1, col_qa_dl2 = st.columns(2)
                    with col_qa_dl1:
                        st.download_button(
                            label="Download Q&A (TXT)",
                            data=st.session_state.qa_answer_result,
                            file_name="qa_answer.txt",
                            mime="text/plain",
                            key="download_qa_txt_tab"
                        )
                    with col_qa_dl2:
                        st.download_button(
                            label="Download Q&A (PDF)",
                            data=create_pdf(st.session_state.qa_answer_result, "Q&A Answer"),
                            file_name="qa_answer.pdf",
                            mime="application/pdf",
                            key="download_qa_pdf_tab"
                        )

            with tab_clause:
                st.subheader("📜 Explain a Specific Clause")
                clauses = [p.strip() for p in full_text.split("\n") if len(p.strip()) > 50]
                if not clauses:
                    st.warning("No substantial clauses (paragraphs longer than 50 characters) were found for individual explanation.")
                else:
                    # Set default value for selectbox only if it's not already set or if full_text changes
                    # Ensure the default index is valid for the current list of clauses
                    current_clause_index = 0
                    if 'clause_select_tab' in st.session_state and st.session_state.clause_select_tab in clauses:
                        current_clause_index = clauses.index(st.session_state.clause_select_tab)
                    # If the previous selected clause is no longer in the list (e.g., after a clear),
                    # default to the first clause if available, otherwise 0.
                    elif clauses:
                        current_clause_index = 0
                    else:
                        current_clause_index = 0 # No clauses, index 0 is safe but won't display a selectbox

                    selected_clause = st.selectbox("Select a clause to explain in plain English:", clauses, key="clause_select_tab", index=current_clause_index)
                    
                    if st.button("Explain Selected Clause", key="explain_clause_button_tab"):
                        with st.spinner("Asking AI for a clear explanation..."):
                            prompt = f"""
{custom_ai_instruction}
Read the following legal clause and explain it in plain English:

Clause:
---
{selected_clause}
---

Explanation:
"""
                            try:
                                response = client.chat.completions.create(
                                    model="gpt-4o",
                                    messages=[
                                        {"role": "system", "content": custom_ai_instruction},
                                        {"role": "user", "content": prompt}
                                    ],
                                    temperature=0.7,
                                    max_tokens=500
                                )
                                st.session_state.clause_explanation_result = response.choices[0].message.content.strip()
                                st.success("Here's your explanation:")
                            except openai.APIError as e:
                                st.error(f"OpenAI API Error: {e.status_code} - {e.response}")
                                st.info("Please check your API key and network connection.")
                                st.session_state.clause_explanation_result = "" # Clear result on error
                            except Exception as e:
                                st.error(f"An unexpected error occurred during AI explanation: {e}")
                                st.session_state.clause_explanation_result = "" # Clear result on error
                
                if st.session_state.clause_explanation_result:
                    st.write(st.session_state.clause_explanation_result)
                    col_clause_dl1, col_clause_dl2 = st.columns(2)
                    with col_clause_dl1:
                        st.download_button(
                            label="Download Clause (TXT)",
                            data=st.session_state.clause_explanation_result,
                            file_name="clause_explanation.txt",
                            mime="text/plain",
                            key="download_clause_txt_tab"
                        )
                    with col_clause_dl2:
                        st.download_button(
                            label="Download Clause (PDF)",
                            data=create_pdf(st.session_state.clause_explanation_result, "Clause Explanation"),
                            file_name="clause_explanation.pdf",
                            mime="application/pdf",
                            key="download_clause_pdf_tab"
                        )

            with tab_entities:
                st.subheader("📊 Key Entities & Data Extraction")
                if st.button("Extract Key Entities", key="extract_entities_button_tab"):
                    with st.spinner("Extracting key entities (parties, dates, values)..."):
                        ner_prompt = f"""
{custom_ai_instruction}
From the following legal document, identify and list key entities such as:
- Parties involved (e.g., company names, individual names, roles like "Lessor", "Lessee")
- Dates (e.g., "Effective Date", specific dates)
- Monetary Values
- Addresses
- Defined Terms (terms explicitly defined within the document, often capitalized)
Present them as a clear, categorized list.

Legal Document:
---
{full_text}
---

Extracted Entities:
"""
                        try:
                            response = client.chat.completions.create(
                                model="gpt-4o",
                                messages=[
                                    {"role": "system", "content": custom_ai_instruction},
                                    {"role": "user", "content": ner_prompt}
                                ],
                                temperature=0.3,
                                max_tokens=700
                            )
                            st.session_state.entities_result = response.choices[0].message.content.strip()
                            st.success("Key Entities Extracted!")
                        except openai.APIError as e:
                            st.error(f"OpenAI API Error: {e.status_code} - {e.response}")
                            st.info("Please check your API key and network connection.")
                            st.session_state.entities_result = "" # Clear result on error
                        except Exception as e:
                            st.error(f"An unexpected error occurred during entity extraction: {e}")
                            st.session_state.entities_result = "" # Clear result on error
                
                if st.session_state.entities_result:
                    st.markdown(st.session_state.entities_result)
                    col_entities_dl1, col_entities_dl2 = st.columns(2)
                    with col_entities_dl1:
                        st.download_button(
                            label="Download Entities (TXT)",
                            data=st.session_state.entities_result,
                            file_name="extracted_entities.txt",
                            mime="text/plain",
                            key="download_entities_txt_tab"
                        )
                    with col_entities_dl2:
                        st.download_button(
                            label="Download Entities (PDF)",
                            data=create_pdf(st.session_state.entities_result, "Extracted Entities"),
                            file_name="extracted_entities.pdf",
                            mime="application/pdf",
                            key="download_entities_pdf_tab"
                        )

            with tab_obligations:
                st.subheader("⚖️ Obligations & Rights")
                if st.button("Extract Obligations & Rights", key="extract_obligations_button_tab"):
                    with st.spinner("Identifying obligations and rights..."):
                        obligations_rights_prompt = f"""
{custom_ai_instruction}
From the following legal document, identify and list the specific obligations (what each party MUST do) and rights (what each party CAN do).
Organize them clearly, preferably by party if applicable, or as a general list if not party-specific.

Legal Document:
---
{full_text}
---

Obligations and Rights:
"""
                        try:
                            response = client.chat.completions.create(
                                model="gpt-4o",
                                messages=[
                                    {"role": "system", "content": custom_ai_instruction},
                                    {"role": "user", "content": obligations_rights_prompt}
                                ],
                                temperature=0.5,
                                max_tokens=800
                            )
                            st.session_state.obligations_rights_result = response.choices[0].message.content.strip()
                            st.success("Obligations and Rights Identified!")
                        except openai.APIError as e:
                            st.error(f"OpenAI API Error: {e.status_code} - {e.response}")
                            st.info("Please check your API key and network connection.")
                            st.session_state.obligations_rights_result = "" # Clear result on error
                        except Exception as e:
                            st.error(f"An unexpected error occurred during extraction: {e}")
                            st.session_state.obligations_rights_result = "" # Clear result on error
                
                if st.session_state.obligations_rights_result:
                    st.markdown(st.session_state.obligations_rights_result)
                    col_obligations_dl1, col_obligations_dl2 = st.columns(2)
                    with col_obligations_dl1:
                        st.download_button(
                            label="Download Obligations (TXT)",
                            data=st.session_state.obligations_rights_result,
                            file_name="obligations_rights.txt",
                            mime="text/plain",
                            key="download_obligations_txt_tab"
                        )
                    with col_obligations_dl2:
                        st.download_button(
                            label="Download Obligations (PDF)",
                            data=create_pdf(st.session_state.obligations_rights_result, "Obligations & Rights"),
                            file_name="obligations_rights.pdf",
                            mime="application/pdf",
                            key="download_obligations_pdf_tab"
                        )

            with tab_glossary:
                st.subheader("📚 Legal Term Glossary")
                if st.button("Generate Legal Glossary", key="generate_glossary_button_tab"):
                    with st.spinner("Generating glossary of legal terms..."):
                        glossary_prompt = f"""
{custom_ai_instruction}
From the following legal document, identify key legal terms or jargon. For each term, provide a concise, plain-English definition.
If the term is explicitly defined in the document, use that definition. Otherwise, provide a general legal definition.
Present as a list of "Term: Definition".

Legal Document:
---
{full_text}
---

Legal Glossary:
"""
                        try:
                            response = client.chat.completions.create(
                                model="gpt-4o",
                                messages=[
                                    {"role": "system", "content": custom_ai_instruction},
                                    {"role": "user", "content": glossary_prompt}
                                ],
                                temperature=0.3,
                                max_tokens=800
                            )
                            st.session_state.glossary_result = response.choices[0].message.content.strip()
                            st.success("Legal Glossary Generated!")
                        except openai.APIError as e:
                            st.error(f"OpenAI API Error: {e.status_code} - {e.response}")
                            st.info("Please check your API key and network connection.")
                            st.session_state.glossary_result = "" # Clear result on error
                        except Exception as e:
                            st.error(f"An unexpected error occurred during glossary generation: {e}")
                            st.session_state.glossary_result = "" # Clear result on error
                
                if st.session_state.glossary_result:
                    st.markdown(st.session_state.glossary_result)
                    col_glossary_dl1, col_glossary_dl2 = st.columns(2)
                    with col_glossary_dl1:
                        st.download_button(
                            label="Download Glossary (TXT)",
                            data=st.session_state.glossary_result,
                            file_name="legal_glossary.txt",
                            mime="text/plain",
                            key="download_glossary_txt_tab"
                        )
                    with col_glossary_dl2:
                        st.download_button(
                            label="Download Glossary (PDF)",
                            data=create_pdf(st.session_state.glossary_result, "Legal Glossary"),
                            file_name="legal_glossary.pdf",
                            mime="application/pdf",
                            key="download_glossary_pdf_tab"
                        )

            with tab_outline:
                st.subheader("📄 Document Outline")
                if st.button("Generate Document Outline", key="generate_outline_button_tab"):
                    with st.spinner("Generating document outline..."):
                        outline_prompt = f"""
{custom_ai_instruction}
Generate a structured outline or table of contents for the following legal document based on its headings, subheadings, and logical sections.
Use clear indentation to show hierarchy. Do not include page numbers.

Legal Document:
---
{full_text}
---

Document Outline:
"""
                        try:
                            response = client.chat.completions.create(
                                model="gpt-4o",
                                messages=[
                                    {"role": "system", "content": custom_ai_instruction},
                                    {"role": "user", "content": outline_prompt}
                                ],
                                temperature=0.3,
                                max_tokens=700
                            )
                            st.session_state.outline_result = response.choices[0].message.content.strip()
                            st.success("Document Outline Generated!")
                        except openai.APIError as e:
                            st.error(f"OpenAI API Error: {e.status_code} - {e.response}")
                            st.info("Please check your API key and network connection.")
                            st.session_state.outline_result = "" # Clear result on error
                        except Exception as e:
                            st.error(f"An unexpected error occurred during outline generation: {e}")
                            st.session_state.outline_result = "" # Clear result on error
                
                if st.session_state.outline_result:
                    st.markdown(st.session_state.outline_result)
                    col_outline_dl1, col_outline_dl2 = st.columns(2)
                    with col_outline_dl1:
                        st.download_button(
                            label="Download Outline (TXT)",
                            data=st.session_state.outline_result,
                            file_name="document_outline.txt",
                            mime="text/plain",
                            key="download_outline_txt_tab"
                        )
                    with col_outline_dl2:
                        st.download_button(
                            label="Download Outline (PDF)",
                            data=create_pdf(st.session_state.outline_result, "Document Outline"),
                            file_name="document_outline.pdf",
                            mime="application/pdf",
                            key="download_outline_pdf_tab"
                        )


    with col_right:
        st.header("3. Overall AI Insights")

        if not OPENAI_API_KEY:
            st.error("OpenAI API key is not set. Please ensure OPENAI_API_KEY is in your .env file.")
        else:
            # --- Overall Insights (Right Column) ---
            tab_summaries, tab_comparison, tab_context = st.tabs([
                "Summaries & Takeaways", "Comparison", "Contextual Analysis"
            ])

            with tab_summaries:
                st.subheader("📄 Full Document Summary")
                if st.button("Generate Executive Summary", key="generate_summary_button_tab"):
                    with st.spinner("Generating executive summary..."):
                        summary_prompt = f"""
{custom_ai_instruction}
Read the entire document provided below and summarize its core purpose, key parties, main agreements, and critical outcomes.
The summary should be no more than 200 words and written in plain, professional English.

Legal Document:
---
{full_text}
---

Executive Summary:
"""
                        try:
                            response = client.chat.completions.create(
                                model="gpt-4o",
                                messages=[
                                    {"role": "system", "content": custom_ai_instruction},
                                    {"role": "user", "content": summary_prompt}
                                ],
                                temperature=0.7,
                                max_tokens=250
                            )
                            st.session_state.summary_result = response.choices[0].message.content.strip()
                            st.success("Executive Summary Generated!")
                        except openai.APIError as e:
                            st.error(f"OpenAI API Error: {e.status_code} - {e.response}")
                            st.info("Please check your API key and network connection.")
                            st.session_state.summary_result = "" # Clear result on error
                        except Exception as e:
                            st.error(f"An unexpected error occurred during summary generation: {e}")
                            st.session_state.summary_result = "" # Clear result on error
                
                if st.session_state.summary_result:
                    st.write(st.session_state.summary_result)
                    col_summary_dl1, col_summary_dl2 = st.columns(2)
                    with col_summary_dl1:
                        st.download_button(
                            label="Download Summary (TXT)",
                            data=st.session_state.summary_result,
                            file_name="executive_summary.txt",
                            mime="text/plain",
                            key="download_summary_txt_tab"
                        )
                    with col_summary_dl2:
                        st.download_button(
                            label="Download Summary (PDF)",
                            data=create_pdf(st.session_state.summary_result, "Executive Summary"),
                            file_name="executive_summary.pdf",
                            mime="application/pdf",
                            key="download_summary_pdf_tab"
                        )

                st.subheader("💡 Key Takeaways")
                if st.button("Extract Key Takeaways", key="extract_takeaways_button_tab"):
                    with st.spinner("Extracting key takeaways..."):
                        takeaways_prompt = f"""
{custom_ai_instruction}
Read the following legal document and identify the most important points, obligations, rights, and responsibilities.
Present these as a concise bulleted list of key takeaways. Each takeaway should be a single, clear sentence. Aim for 5-10 key points.

Legal Document:
---
{full_text}
---

Key Takeaways:
"""
                        try:
                            response = client.chat.completions.create(
                                model="gpt-4o",
                                messages=[
                                    {"role": "system", "content": custom_ai_instruction},
                                    {"role": "user", "content": takeaways_prompt}
                                ],
                                temperature=0.7,
                                max_tokens=400
                            )
                            st.session_state.takeaways_result = response.choices[0].message.content.strip()
                            st.success("Key Takeaways Extracted!")
                        except openai.APIError as e:
                            st.error(f"OpenAI API Error: {e.status_code} - {e.response}")
                            st.info("Please check your API key and network connection.")
                            st.session_state.takeaways_result = "" # Clear result on error
                        except Exception as e:
                            st.error(f"An unexpected error occurred during key takeaways extraction: {e}")
                            st.session_state.takeaways_result = "" # Clear result on error
                
                if st.session_state.takeaways_result:
                    st.markdown(st.session_state.takeaways_result)
                    col_takeaways_dl1, col_takeaways_dl2 = st.columns(2)
                    with col_takeaways_dl1:
                        st.download_button(
                            label="Download Takeaways (TXT)",
                            data=st.session_state.takeaways_result,
                            file_name="key_takeaways.txt",
                            mime="text/plain",
                            key="download_takeaways_txt_tab"
                        )
                    with col_takeaways_dl2:
                        st.download_button(
                            label="Download Takeaways (PDF)",
                            data=create_pdf(st.session_state.takeaways_result, "Key Takeaways"),
                            file_name="key_takeaways.pdf",
                            mime="application/pdf",
                            key="download_takeaways_pdf_tab"
                        )

                st.subheader("⚠️ Risk & Opportunity Analysis")
                if st.button("Analyze Risks & Opportunities", key="analyze_risks_button_tab"):
                    with st.spinner("Analyzing potential risks and opportunities..."):
                        risk_opportunity_prompt = f"""
{custom_ai_instruction}
Read the following legal document and identify potential risks, liabilities, or unfavorable clauses, as well as any advantageous clauses or opportunities for the parties involved.
Present these as two separate lists (Risks and Opportunities).

Legal Document:
---
{full_text}
---

Analysis:
"""
                        try:
                            response = client.chat.completions.create(
                                model="gpt-4o",
                                messages=[
                                    {"role": "system", "content": custom_ai_instruction},
                                    {"role": "user", "content": risk_opportunity_prompt}
                                ],
                                temperature=0.7,
                                max_tokens=700
                            )
                            st.session_state.risk_opportunity_result = response.choices[0].message.content.strip()
                            st.success("Risk and Opportunity Analysis Complete!")
                        except openai.APIError as e:
                            st.error(f"OpenAI API Error: {e.status_code} - {e.response}")
                            st.info("Please check your API key and network connection