import json
import asyncio
import logging
from typing import Dict, List, Any, Optional
import google.generativeai as genai
from analysis_prompts import ResponseCleaner

logger = logging.getLogger("QnAAgent")

class QnAOrchestrator:
    def __init__(self, api_key: str, orchestrator):
        self.api_key = api_key
        self.orchestrator = orchestrator
        genai.configure(api_key=api_key)
        
    async def process_question(self, question: str) -> str:
        """Main entry point for processing user questions"""
        logger.info(f"Processing question: {question}")
        plan = await self._analyze_question(question)
        if plan.get("use_codebase_engine", False):
            return await self._query_codebase_engine(question, plan.get("enhanced_prompt", question))

        return await self._execute_plan(question, plan)
    
    async def _analyze_question(self, question: str) -> Dict[str, Any]:
        """Analyze question to determine which files/engines to query"""
        structure_info = self._get_structure_summary()
        
        analysis_prompt = f"""
Analyze this question and determine the best strategy to answer it using the codebase structure.

QUESTION: {question}

CODEBASE STRUCTURE:
{structure_info}

Determine:
1. Should we use the full codebase engine (for general architecture, patterns, cross-file analysis)?
2. Or target specific files (for specific implementation details, functions, classes)?
3. What enhanced prompt would get the best answer?

OUTPUT JSON:
{{
    "use_codebase_engine": true/false,
    "target_files": ["file1.py", "file2.js"],
    "enhanced_prompt": "Enhanced version of the original question with context",
    "reasoning": "Why this approach was chosen"
}}
        """
        model = genai.GenerativeModel('models/gemini-2.0-flash-exp')
        
        try:
            response = model.generate_content(analysis_prompt)
            plan = ResponseCleaner.clean_json_response(response.text)
            logger.info(f"Question analysis plan: {plan.get('reasoning', 'No reasoning provided')}")
            return plan
        except Exception as e:
            logger.error(f"Error analyzing question: {e}")
            return {
                "use_codebase_engine": True,
                "enhanced_prompt": question,
                "reasoning": "Fallback to codebase engine due to analysis error"
            }
    
    def _get_structure_summary(self) -> str:
        """Get a summary of the codebase structure for question analysis"""
        try:
            structure_path = f"{self.orchestrator.temp_dir}/codebase_structure.json"
            with open(structure_path, 'r') as f:
                structure = json.load(f)
            return json.dumps(structure, indent=2)[:2000]  # Limit size
        except:
            files = list(self.orchestrator.query_engines.keys())
            return f"Available files: {', '.join(files[:20])}"
    
    async def _query_codebase_engine(self, original_question: str, enhanced_prompt: str) -> str:
        """Use the full codebase query engine"""
        logger.info("Using codebase-wide query engine")
        
        if not self.orchestrator.codebase_query_engine:
            return "Codebase query engine not available. Please analyze the codebase first."
        try:
            response = await asyncio.to_thread(
                self.orchestrator.codebase_query_engine.query, 
                enhanced_prompt
            )
            return str(response)
        except Exception as e:
            logger.error(f"Error querying codebase engine: {e}")
            return f"Error processing question: {str(e)}"
    
    async def _execute_plan(self, original_question: str, plan: Dict[str, Any]) -> str:
        """Execute plan by querying specific file engines"""
        target_files = plan.get("target_files", [])
        enhanced_prompt = plan.get("enhanced_prompt", original_question)
        
        if not target_files:
            target_files = list(self.orchestrator.query_engines.keys())
        logger.info(f"Querying {len(target_files)} specific files")
        

        tasks = []
        for file_path in target_files:
            if file_path in self.orchestrator.query_engines:
                task = self._query_file_engine(file_path, enhanced_prompt)
                tasks.append(task)
        if not tasks:
            return "No relevant files found to answer your question."
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return await self._combine_results(original_question, results, target_files)
    
    async def _query_file_engine(self, file_path: str, prompt: str) -> Dict[str, str]:
        """Query a specific file's engine"""
        try:
            engine = self.orchestrator.query_engines[file_path]
            response = await asyncio.to_thread(engine.query, prompt)
            return {
                "file": file_path,
                "response": str(response),
                "status": "success"
            }
        except Exception as e:
            logger.error(f"Error querying {file_path}: {e}")
            return {
                "file": file_path,
                "response": f"Error: {str(e)}",
                "status": "error"
            }
    
    async def _combine_results(self, original_question: str, results: List[Dict], file_paths: List[str]) -> str:
        """Combine results from multiple file queries"""
        successful_results = [r for r in results if isinstance(r, dict) and r.get("status") == "success"]
        if not successful_results:
            return "Unable to get responses from any relevant files."
        
        combined_context = []
        for result in successful_results:
            combined_context.append(f"From {result['file']}:\n{result['response']}\n")
        
        synthesis_prompt = f"""
Original Question: {original_question}
Context from multiple files:
{''.join(combined_context)}

Synthesize a comprehensive answer from the above information. Be specific and reference files when relevant.
        """
        model = genai.GenerativeModel('models/gemini-2.0-flash-exp')
        try:
            response = model.generate_content(synthesis_prompt)
            return response.text
        except Exception as e:
            logger.error(f"Error synthesizing results: {e}")
            return f"Based on analysis of {len(successful_results)} files:\n\n" + '\n\n'.join([r['response'] for r in successful_results])