import json
import re

class AnalysisPrompts:
    
    @staticmethod
    def get_import_analysis_prompt():
        return """
GOAL: Extract and analyze all import/include statements from this code file for dependency tracking.

METHODOLOGY:
1. Identify all import statements (Python: import, from...import; JS: import, require; Java: import; etc.)
2. Categorize imports by type (standard library, third-party, local/relative)
3. Note any conditional or dynamic imports
4. Flag any deprecated or risky imports

GUARDRAILS:
- Only extract actual import statements, not comments about imports
- Include line numbers where possible
- Distinguish between different import types

OUTPUT FORMAT (JSON):
{
    "imports": [
        {
            "statement": "import pandas as pd",
            "type": "third_party",
            "module": "pandas",
            "alias": "pd",
            "line_number": 5
        }
    ],
    "file_path": "relative/path/to/file",
    "import_count": 10,
    "potential_issues": ["circular import risk", "deprecated module"]
}
        """
    
    @staticmethod
    def get_import_summary_prompt(all_imports_data):
        return f"""
GOAL: Analyze import patterns across the entire codebase to identify dependency issues and security risks.

INPUT DATA:
{json.dumps(all_imports_data, indent=2)}

METHODOLOGY:
1. Cross-reference imports to detect missing dependencies
2. Identify unused imports within each file context
3. Map potential circular dependencies between files
4. Flag security-sensitive imports (subprocess, eval, exec, etc.)
5. Check for version conflicts in third-party dependencies

GUARDRAILS:
- Focus on actionable issues, not theoretical problems
- Prioritize security and stability concerns
- Consider project context when flagging issues

OUTPUT FORMAT (Structured Markdown):
## Import Analysis Summary

### Critical Issues
- List high-priority import problems

### Dependency Mapping
- Show key dependencies and their usage patterns

### Security Concerns
- Flag potentially dangerous imports

### Recommendations
- Actionable steps to improve dependency management

### Import Statistics
- Total imports, unique modules, dependency depth
        """
    
    @staticmethod
    def get_code_issues_prompt():
        return """
GOAL: Identify code quality issues, security vulnerabilities, and potential bugs in this code file.

METHODOLOGY:
1. Security analysis: SQL injection, XSS, command injection, hardcoded secrets
2. Performance issues: inefficient loops, memory leaks, blocking operations
3. Code quality: complexity, maintainability, naming conventions
4. Logic errors: null pointer risks, type mismatches, boundary conditions
5. Best practices: error handling, resource management, documentation

GUARDRAILS:
- Focus on realistic, exploitable security issues
- Consider performance impact in production context
- Prioritize maintainability concerns
- Limit response to most critical findings only

OUTPUT FORMAT (JSON):
{
    "security_issues": [
        {"severity": "high", "type": "sql_injection", "line": 45, "description": "User input directly in SQL query"}
    ],
    "performance_issues": [
        {"severity": "medium", "type": "inefficient_loop", "line": 78, "description": "Nested loop with O(n²) complexity"}
    ],
    "quality_issues": [
        {"severity": "low", "type": "naming", "line": 12, "description": "Variable name 'x' is not descriptive"}
    ],
    "logic_errors": [
        {"severity": "high", "type": "null_pointer", "line": 34, "description": "Potential null reference without check"}
    ],
    "overall_score": 7,
    "file_path": "relative/path/to/file"
}
        """
    
    @staticmethod
    def get_code_issues_summary_prompt(all_issues_data):
        return f"""
GOAL: Synthesize individual file analyses into a prioritized, actionable code quality report.

INPUT DATA:
{json.dumps(all_issues_data, indent=2)}

METHODOLOGY:
1. Categorize issues by severity and type across all files
2. Identify patterns of recurring problems
3. Calculate overall codebase health metrics
4. Prioritize fixes based on security, stability, and maintainability impact

GUARDRAILS:
- Focus on high-impact, fixable issues
- Provide specific examples with file locations
- Balance thoroughness with actionability

OUTPUT FORMAT (Structured Markdown):
## Code Quality Analysis

### Critical Security Issues (Immediate Action Required)
- List with file locations and fix priorities

### Performance Bottlenecks
- Most impactful performance issues to address

### Code Quality Concerns
- Maintainability and readability improvements

### Technical Debt Summary
- Overall assessment and refactoring recommendations

### Codebase Health Score: X/10
- Justification for score and improvement roadmap
        """
    
    @staticmethod
    def get_duplication_analysis_prompt():
        return """
GOAL: Identify code duplication, similar patterns, and refactoring opportunities across the entire codebase.

METHODOLOGY:
1. Detect exact code duplicates and near-duplicates
2. Identify similar function signatures and logic patterns
3. Find repeated constants, configurations, or data structures
4. Analyze cross-file dependencies and coupling
5. Suggest consolidation opportunities

GUARDRAILS:
- Focus on meaningful duplications (not trivial similarities)
- Consider refactoring feasibility and benefits
- Identify shared abstractions that could be extracted

OUTPUT FORMAT (Structured Markdown):
## Code Duplication Analysis

### Exact Duplicates
- List code blocks that are identical across files

### Similar Patterns
- Functions/methods with similar logic that could be consolidated

### Repeated Constants/Configurations
- Values that appear multiple times and could be centralized

### Refactoring Opportunities
- Specific suggestions for code consolidation

### Architecture Improvements
- Higher-level structural improvements to reduce duplication
        """

class ResponseCleaner:
    
    @staticmethod
    def clean_json_response(response_text):
        """Clean LLM response to extract valid JSON"""
        if not response_text:
            return {}
            
        # Remove code block markers
        cleaned = re.sub(r'```json\s*', '', response_text)
        cleaned = re.sub(r'```\s*$', '', cleaned)
        
        # Find JSON-like content
        json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
                
        return {"error": "Could not parse JSON from response", "raw_response": response_text[:500]}
    
    @staticmethod
    def clean_markdown_response(response_text):
        """Clean markdown response by removing code block markers"""
        if not response_text:
            return "No response generated"
            
        cleaned = re.sub(r'^```markdown\s*\n', '', response_text)
        cleaned = re.sub(r'\n```\s*$', '', cleaned)
        
        return cleaned.strip()