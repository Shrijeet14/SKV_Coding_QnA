import streamlit as st
import os
import json
import zipfile
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from code_analyzer import CodeAnalysisOrchestrator
from qna_agent import QnAOrchestrator
import asyncio
import logging
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("StreamlitApp")

class StreamlitApp:
    def __init__(self):
        logger.info("StreamlitApp initialized.")
        
    def setup_page(self):
        logger.info("Setting up Streamlit page configuration...")
        st.set_page_config(
            page_title="Code Quality Analyzer",
            page_icon=":robot:",
            layout="wide"
        )
        st.title("Code Quality Analyzer")
        
    def upload_section(self):
        st.header("Upload Codebase")
        
        upload_type = st.radio("Select input type:", ["Upload Files", "Upload Folder (ZIP)"])
        logger.info(f"Upload type selected: {upload_type}")
        
        if upload_type == "Upload Files":
            uploaded_files = st.file_uploader(
                "Choose code files",
                accept_multiple_files=True,
                type=['py', 'js', 'jsx', 'ts', 'tsx', 'java', 'cpp', 'c', 'cs', 'go', 'rb', 'php']
            )
            
            if uploaded_files and st.button("Analyze Files"):
                logger.info(f"{len(uploaded_files)} files uploaded for analysis.")
                self.process_files(uploaded_files)
                
        else:
            uploaded_zip = st.file_uploader("Upload ZIP folder", type=['zip'])
            
            if uploaded_zip and st.button("Analyze Folder"):
                logger.info("ZIP folder uploaded for analysis.")
                self.process_zip(uploaded_zip)
    
    def process_files(self, uploaded_files):
        logger.info("Processing uploaded files...")
        temp_dir = "temp_analysis"
        os.makedirs(temp_dir, exist_ok=True)
        
        for file in uploaded_files:
            file_path = os.path.join(temp_dir, file.name)
            with open(file_path, 'wb') as f:
                f.write(file.getvalue())
            logger.debug(f"Saved uploaded file: {file_path}")
        
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            logger.error("GEMINI_API_KEY not found in environment variables.")
            st.error("GEMINI_API_KEY not found in environment variables")
            return
            
        analyzer = CodeAnalysisOrchestrator(api_key)
        qna_agent = QnAOrchestrator(api_key, analyzer)
        
        with st.spinner("Analyzing codebase..."):
            logger.info("Running analyzer on uploaded files...")
            report = asyncio.run(analyzer.analyze(temp_dir))
        
        st.session_state.analyzer = analyzer
        st.session_state.qna_agent = qna_agent
        st.session_state.report = report
        st.session_state.analysis_completed = True
        
        logger.info("File analysis completed and stored in session state.")
        st.success("Analysis completed! Scroll down to view the report.")
        st.rerun()  
    
    def process_zip(self, uploaded_zip):
        logger.info("Processing uploaded ZIP folder...")
        temp_dir = "temp_analysis"
        
        with zipfile.ZipFile(uploaded_zip, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        logger.debug("Extracted ZIP folder to temp_analysis.")
        
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            logger.error("GEMINI_API_KEY not found in environment variables.")
            st.error("GEMINI_API_KEY not found in environment variables")
            return
            
        analyzer = CodeAnalysisOrchestrator(api_key)
        qna_agent = QnAOrchestrator(api_key, analyzer)
        
        with st.spinner("Analyzing codebase..."):
            logger.info("Running analyzer on extracted ZIP folder...")
            report = asyncio.run(analyzer.analyze(temp_dir))
        
        st.session_state.analyzer = analyzer
        st.session_state.qna_agent = qna_agent
        st.session_state.report = report
        st.session_state.analysis_completed = True
        
        logger.info("ZIP analysis completed and stored in session state.")
        st.success("Analysis completed! Scroll down to view the report.")
        st.rerun()  
    
    def display_report(self, report):
        if not report:
            logger.warning("No report available to display.")
            return
            
        logger.info("Displaying analysis report...")
        st.header("Analysis Report")
        

        if st.button("Start New Analysis"):
            self.reset_session_state()
            st.rerun()
        
        tab1, tab2, tab3, tab4 = st.tabs(["Summary", "Import Issues", "Code Issues", "Duplication"])
        
        with tab1:
            st.subheader("Executive Summary")
            st.markdown(report.get("summary", "No summary available"))
            
        with tab2:
            st.subheader("Import Analysis")
            st.markdown(report.get("imports_analysis", "No import analysis available"))
            
        with tab3:
            st.subheader("Code Quality Issues")
            st.markdown(report.get("code_issues", "No code issues analysis available"))
            
        with tab4:
            st.subheader("Code Duplication Analysis")
            st.markdown(report.get("duplication_analysis", "No duplication analysis available"))
        
        if st.button("Download PDF Report"):
            logger.info("Generating PDF report for download...")
            pdf_buffer = self.generate_pdf_report(report)
            st.download_button(
                label="Download Report",
                data=pdf_buffer,
                file_name="code_analysis_report.pdf",
                mime="application/pdf"
            )
    
    def generate_pdf_report(self, report):
        logger.info("Generating PDF report...")
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        y_position = height - 50
        
        p.setFont("Helvetica-Bold", 16)
        p.drawString(50, y_position, "Code Quality Analysis Report")
        y_position -= 40
        
        sections = [
            ("Executive Summary", report.get("summary", "")),
            ("Import Analysis", report.get("imports_analysis", "")),
            ("Code Issues", report.get("code_issues", "")),
            ("Duplication Analysis", report.get("duplication_analysis", ""))
        ]
        
        for title, content in sections:
            p.setFont("Helvetica-Bold", 12)
            p.drawString(50, y_position, title)
            y_position -= 20
            
            p.setFont("Helvetica", 10)
            lines = content.split('\n')
            for line in lines:
                if y_position < 50:
                    p.showPage()
                    y_position = height - 50
                p.drawString(50, y_position, line[:80])
                y_position -= 12
            
            y_position -= 20
        
        p.save()
        buffer.seek(0)
        logger.info("PDF report generation completed.")
        return buffer.getvalue()
    
    def qna_section(self):
        if not st.session_state.get('qna_agent'):
            logger.warning("QnA section skipped (no QnA agent available).")
            return
            
        st.header("Ask Questions")
        st.write("Ask anything about your codebase - architecture, specific functions, patterns, or improvements.")
        
        question = st.text_input("Ask about your codebase:", placeholder="e.g., What security issues should I be most concerned about?")
        
        if question and st.button("Get Answer"):
            logger.info(f"Received QnA question: {question}")
            
            status_placeholder = st.empty()
            answer_placeholder = st.empty()
            
            status_placeholder.info("Analyzing your question...")
            time.sleep(0.5)
            
            status_placeholder.info("Processing codebase...")
            try:
                answer = asyncio.run(st.session_state.qna_agent.process_question(question))
                status_placeholder.success("Answer ready!")
                answer_placeholder.markdown(f"**Answer:** {answer}")
                logger.info("QnA answer generated successfully.")
            except Exception as e:
                logger.error(f"Error in QnA: {e}")
                status_placeholder.error("Error processing question")
                answer_placeholder.error(f"Error processing question: {str(e)}")
    
    def display_structure_info(self):
        """Display codebase structure information"""
        analyzer = st.session_state.get('analyzer')
        if not analyzer or not hasattr(analyzer, 'temp_dir') or not analyzer.temp_dir:
            return  
        try:
            structure_file = os.path.join(analyzer.temp_dir, "codebase_structure.json")
            if os.path.exists(structure_file):
                with st.expander("View Codebase Structure"):
                    with open(structure_file, 'r') as f:
                        structure = json.load(f)
                    st.json(structure)
                    

                    file_count = self._count_files(structure)
                    st.info(f"Total files analyzed: {file_count}")
        except Exception as e:
            logger.error(f"Error displaying structure: {e}")
    
    def _count_files(self, structure, count=0):
        """Recursively count files in structure"""
        for key, value in structure.items():
            if isinstance(value, dict):
                if value.get('type') == 'file':
                    count += 1
                else:
                    count = self._count_files(value, count)
        return count
    
    def reset_session_state(self):
        """Reset all session state variables for a new analysis"""
        st.session_state.analyzer = None
        st.session_state.qna_agent = None
        st.session_state.report = None
        st.session_state.analysis_completed = False
        logger.info("Session state reset for new analysis.")
    
    def run(self):
        logger.info("Streamlit app is starting...")

        if 'analyzer' not in st.session_state:
            st.session_state.analyzer = None
        if 'qna_agent' not in st.session_state:
            st.session_state.qna_agent = None
        if 'report' not in st.session_state:
            st.session_state.report = None
        if 'analysis_completed' not in st.session_state:
            st.session_state.analysis_completed = False
        
        self.setup_page()
        if not st.session_state.analysis_completed:
            self.upload_section()
        
        if st.session_state.analysis_completed and st.session_state.report:
            self.display_report(st.session_state.report)
            self.display_structure_info()
            self.qna_section()
        
        logger.info("Streamlit app finished running.")

if __name__ == "__main__":
    app = StreamlitApp()
    app.run()