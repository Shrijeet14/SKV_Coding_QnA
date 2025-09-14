import os
import json
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional
import concurrent.futures
from dataclasses import dataclass
import google.generativeai as genai
from llama_index.llms.gemini import Gemini
from llama_index.core import Document, SummaryIndex
from llama_index.embeddings.openai import OpenAIEmbedding
from dotenv import load_dotenv
import asyncio
import logging
from llama_index.core import DocumentSummaryIndex
from analysis_prompts import AnalysisPrompts, ResponseCleaner

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("CodeAnalysis")

load_dotenv()

@dataclass
class FileInfo:
    path: str
    content: str
    size: int
    query_engine: Any = None

class CodebaseStructurer:
    def __init__(self, temp_dir: str):
        self.temp_dir = temp_dir
        
    def create_structure(self) -> Dict[str, Any]:
        logger.info("Creating codebase structure from temp directory...")
        structure = {}
        code_extensions = {'.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.cpp', '.c', '.cs', '.go', '.rb', '.php'}
        
        for root, dirs, files in os.walk(self.temp_dir):
            rel_path = os.path.relpath(root, self.temp_dir)
            if "__MACOSX" in root:
                logger.debug(f"Skipping macOS metadata directory: {root}")
                continue

            current_level = structure
            if rel_path != '.':
                path_parts = rel_path.split(os.sep)
                for part in path_parts:
                    if part not in current_level:
                        current_level[part] = {}
                    current_level = current_level[part]
            
            for file in files:
                if file.startswith("._"):
                    logger.debug(f"Skipping macOS metadata file: {file}")
                    continue

                file_path = os.path.join(root, file)
                if Path(file).suffix.lower() in code_extensions:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        current_level[file] = {
                            'type': 'file',
                            'path': file_path,
                            'content': content,
                            'size': len(content)
                        }
                        logger.debug(f"Loaded file: {file_path}")
                    except Exception as e:
                        logger.warning(f"Could not read file {file_path}: {e}")
                        continue
                        
        logger.info("Finished creating structure.")
        return structure
    
    def save_structure(self, structure: Dict[str, Any], output_path: str):
        """Save the structure as JSON file"""
        structure_file = os.path.join(output_path, "codebase_structure.json")
        try:
            clean_structure = self._create_clean_structure(structure)
            with open(structure_file, 'w', encoding='utf-8') as f:
                json.dump(clean_structure, f, indent=2, ensure_ascii=False)
            logger.info(f"Codebase structure saved to: {structure_file}")
        except Exception as e:
            logger.error(f"Failed to save structure: {e}")
    
    def _create_clean_structure(self, structure: Dict[str, Any]) -> Dict[str, Any]:
        """Create structure without content for JSON saving"""
        clean = {}
        for key, value in structure.items():
            if isinstance(value, dict):
                if value.get('type') == 'file':
                    clean[key] = {
                        'type': 'file',
                        'path': value['path'],
                        'size': value['size']
                    }
                else:
                    clean[key] = self._create_clean_structure(value)
        return clean

class QueryEngineManager:
    def __init__(self, api_key: str):
        logger.info("Initializing QueryEngineManager...")
        genai.configure(api_key=api_key)
        self.llm = Gemini(model="gemini-1.5-flash")
        self.embed_model = OpenAIEmbedding(model="text-embedding-3-small")
        
    def create_query_engine(self, content: str):
        logger.debug("Creating query engine for file content...")
        try:
            documents = [Document(text=content)]
            index = DocumentSummaryIndex.from_documents(documents, embed_model=self.embed_model, llm=self.llm)
            return index.as_query_engine()
        except Exception as e:
            logger.error(f"Error creating query engine: {e}")
            return None

class CodeAnalysisOrchestrator:
    def __init__(self, api_key: str):
        logger.info("Initializing CodeAnalysisOrchestrator...")
        self.api_key = api_key
        self.temp_dir = None
        self.structure = {}
        self.query_engines = {}
        self.codebase_query_engine = None
        self.report = {
            "imports_analysis": {},
            "code_issues": {},
            "duplication_analysis": {},
            "summary": {}
        }
        self.qe_manager = QueryEngineManager(api_key)
        genai.configure(api_key=api_key)
        
    def setup_temp_directory(self, input_path: str) -> str:
        logger.info(f"Setting up temp directory for input: {input_path}")
        self.temp_dir = tempfile.mkdtemp()
        
        if os.path.isfile(input_path):
            shutil.copy2(input_path, self.temp_dir)
            logger.info("Copied single file to temp directory.")
        elif os.path.isdir(input_path):
            if os.path.basename(input_path) == "temp_analysis":
                for item in os.listdir(input_path):
                    src = os.path.join(input_path, item)
                    dst = os.path.join(self.temp_dir, item)
                    if os.path.isdir(src):
                        shutil.copytree(src, dst)
                    else:
                        shutil.copy2(src, dst)
            else:
                shutil.copytree(input_path, os.path.join(self.temp_dir, "codebase"))
            logger.info("Copied directory to temp directory.")
            
        return self.temp_dir
    
    def create_structure_and_engines(self):
        logger.info("Creating structure and query engines for files...")
        structurer = CodebaseStructurer(self.temp_dir)
        self.structure = structurer.create_structure()
        
        structurer.save_structure(self.structure, self.temp_dir)
        
        def create_engine_for_file(file_info):
            path, data = file_info
            if isinstance(data, dict) and data.get('type') == 'file':
                engine = self.qe_manager.create_query_engine(data['content'])
                if engine:
                    logger.info(f"Query engine created successfully for: {os.path.basename(path)}")
                    return path, engine
                else:
                    logger.warning(f"Failed to create query engine for: {os.path.basename(path)}")
            return path, None
        
        file_items = self._get_all_files(self.structure)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(create_engine_for_file, file_items))
            
        for path, engine in results:
            if engine:
                self.query_engines[path] = engine
        
        self._create_codebase_query_engine()
    
    def _create_codebase_query_engine(self):
        """Create a single query engine for the entire codebase"""
        logger.info("Creating codebase-wide query engine...")
        all_code_content = ""
        
        for path, data in self._get_all_files(self.structure):
            all_code_content += f"\n\n=== FILE: {path} ===\n{data['content']}"
        
        if all_code_content.strip():
            self.codebase_query_engine = self.qe_manager.create_query_engine(all_code_content)
            if self.codebase_query_engine:
                logger.info("Codebase-wide query engine created successfully")
            else:
                logger.error("Failed to create codebase-wide query engine")
        else:
            logger.warning("No code content found for codebase query engine")
    
    def _get_all_files(self, structure: Dict, prefix: str = "") -> List[tuple]:
        files = []
        for key, value in structure.items():
            current_path = f"{prefix}/{key}" if prefix else key
            if isinstance(value, dict):
                if value.get('type') == 'file':
                    files.append((current_path, value))
                else:
                    files.extend(self._get_all_files(value, current_path))
        return files
    
    def analyze_imports(self):
        logger.info("Analyzing imports...")
        import_prompt = AnalysisPrompts.get_import_analysis_prompt()
        
        def analyze_file_imports(item):
            path, engine = item
            try:
                response = engine.query(import_prompt)
                cleaned_response = ResponseCleaner.clean_json_response(str(response))
                return path, cleaned_response
            except Exception as e:
                logger.error(f"Error analyzing imports for {path}: {e}")
                return path, {"error": f"Error analyzing imports: {str(e)}"}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(analyze_file_imports, self.query_engines.items()))
        
        all_imports = {path: imports_data for path, imports_data in results}
        
        model = genai.GenerativeModel('models/gemini-2.0-flash-exp')
        summary_prompt = AnalysisPrompts.get_import_summary_prompt(all_imports)
        
        try:
            response = model.generate_content(summary_prompt)
            self.report["imports_analysis"] = ResponseCleaner.clean_markdown_response(response.text)
        except Exception as e:
            logger.error(f"Error in import analysis: {e}")
            self.report["imports_analysis"] = "Error in import analysis"
    
    def analyze_code_issues(self):
        logger.info("Analyzing code issues...")
        issues_prompt = AnalysisPrompts.get_code_issues_prompt()
        
        def analyze_file_issues(item):
            path, engine = item
            try:
                response = engine.query(issues_prompt)
                cleaned_response = ResponseCleaner.clean_json_response(str(response))
                return path, cleaned_response
            except Exception as e:
                logger.error(f"Error analyzing issues for {path}: {e}")
                return path, {"error": f"Error analyzing issues: {str(e)}"}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(analyze_file_issues, self.query_engines.items()))
        
        all_issues = {path: issues for path, issues in results}
        
        model = genai.GenerativeModel('models/gemini-2.0-flash-exp')
        summary_prompt = AnalysisPrompts.get_code_issues_summary_prompt(all_issues)
        
        try:
            response = model.generate_content(summary_prompt)
            self.report["code_issues"] = ResponseCleaner.clean_markdown_response(response.text)
        except Exception as e:
            logger.error(f"Error in code issues analysis: {e}")
            self.report["code_issues"] = "Error in code issues analysis"
    
    def analyze_duplication(self):
        logger.info("Analyzing code duplication using codebase-wide query engine...")
        
        if not self.codebase_query_engine:
            logger.error("Codebase query engine not available for duplication analysis")
            self.report["duplication_analysis"] = "Error: Codebase query engine not available"
            return
        
        duplication_prompt = AnalysisPrompts.get_duplication_analysis_prompt()
        
        try:
            response = self.codebase_query_engine.query(duplication_prompt)
            self.report["duplication_analysis"] = ResponseCleaner.clean_markdown_response(str(response))
            logger.info("Duplication analysis completed successfully")
        except Exception as e:
            logger.error(f"Error in duplication analysis: {e}")
            self.report["duplication_analysis"] = f"Error in duplication analysis: {str(e)}"
    
    def generate_final_report(self):
        logger.info("Generating final report...")
        model = genai.GenerativeModel('models/gemini-2.0-flash-exp')
        summary_prompt = f"""
Create executive summary from these analyses:

IMPORTS: {self.report["imports_analysis"]}

CODE ISSUES: {self.report["code_issues"]}

DUPLICATION: {self.report["duplication_analysis"]}

Provide:
1. Overall assessment
2. Top 5 priority actions
3. Risk level (Low/Medium/High)
4. Recommendations
        """
        
        try:
            response = model.generate_content(summary_prompt)
            self.report["summary"] = ResponseCleaner.clean_markdown_response(response.text)
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            self.report["summary"] = "Error generating summary"
    
    async def analyze(self, input_path: str) -> Dict[str, Any]:
        logger.info("Starting analysis pipeline...")
        self.setup_temp_directory(input_path)
        self.create_structure_and_engines()
        self.analyze_imports()
        self.analyze_code_issues()
        self.analyze_duplication()
        self.generate_final_report()
        
        logger.info("Analysis completed successfully.")
        return self.report
    
    async def ask_question(self, question: str) -> str:
        logger.info(f"Processing question: {question}")
        
        if not self.query_engines and not self.codebase_query_engine:
            return "No query engines available. Please analyze codebase first."
        
        if self.codebase_query_engine:
            try:
                response = await asyncio.to_thread(self.codebase_query_engine.query, question)
                return str(response)
            except Exception as e:
                logger.error(f"Error processing question with codebase engine: {e}")
        
        try:
            documents = []
            for path, data in self._get_all_files(self.structure):
                doc = Document(
                    text=f"File: {path}\n\n{data['content']}",
                    metadata={"file_path": path}
                )
                documents.append(doc)
            
            combined_index = SummaryIndex(documents, embed_model=self.qe_manager.embed_model)
            combined_engine = combined_index.as_query_engine(response_mode="tree_summarize")
            
            response = await asyncio.to_thread(combined_engine.query, question)
            return str(response)
        except Exception as e:
            logger.error(f"Error processing question '{question}': {e}")
            return f"Error processing question: {str(e)}"