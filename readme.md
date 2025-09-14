# Code Quality Analyzer

An AI-powered static code analysis tool that provides comprehensive insights into your codebase including dependency analysis, code quality issues, duplication detection, and interactive Q&A capabilities.

## Features

- **Multi-language Support**: Supports Python, JavaScript/TypeScript, Java, C/C++, C#, Go, Ruby, and PHP
- **Comprehensive Analysis**: Import dependency analysis, code quality assessment, and duplication detection
- **Interactive Q&A**: Ask questions about your codebase using natural language
- **Professional Reports**: Generate detailed PDF reports with actionable insights
- **Intuitive UI**: Clean Streamlit-based web interface

## Architectures 

### System Architecture - Analysis Report
![Alt text](https://github.com/Shrijeet14/SKV_Coding_QnA/blob/main/system_architecture_analysis.jpeg)

### QnA Bot Architecture - Analysis Report
![Alt text](https://github.com/Shrijeet14/SKV_Coding_QnA/blob/main/QnA-Architecture.jpeg)

## Quick Start

### Prerequisites

- Python 3.8+
- Google Gemini API key
- OpenAI API key (for embeddings)

### Installation

1. Clone the repository:

```bash
git clone https://github.com/Shrijeet14/SKV_Coding_QnA.git
cd code-quality-analyzer
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set up environment variables:

```bash
# Create .env file
GEMINI_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
```

### Usage

1. Start the application:

```bash
streamlit run app.py
```

2. Open your browser to `http://localhost:8501`
3. Upload your code files or ZIP folder
4. Wait for analysis to complete
5. Explore the results and ask questions about your code

## Supported File Types

- Python: `.py`
- JavaScript/TypeScript: `.js`, `.jsx`, `.ts`, `.tsx`
- Java: `.java`
- C/C++: `.c`, `.cpp`
- C#: `.cs`
- Go: `.go`
- Ruby: `.rb`
- PHP: `.php`

## Analysis Features

### Import Analysis

- Detects all import statements across your codebase
- Identifies missing dependencies and circular imports
- Flags security-sensitive imports
- Provides dependency mapping

### Code Quality Assessment

- Security vulnerability detection (SQL injection, XSS, etc.)
- Performance issue identification
- Code complexity analysis
- Best practices compliance checking

### Duplication Detection

- Identifies exact and near-duplicate code blocks
- Suggests refactoring opportunities
- Analyzes cross-file dependencies

### Interactive Q&A

- Ask natural language questions about your code
- Get contextual answers based on your specific codebase
- Understand architecture decisions and patterns

## Report Structure

Generated reports include:

1. **Executive Summary**: High-level assessment and priority actions
2. **Import Analysis**: Dependency issues and recommendations
3. **Code Quality Issues**: Security, performance, and maintainability concerns
4. **Duplication Analysis**: Code reuse opportunities

## Configuration

The system uses several configurable components:

- **LLM Model**: Gemini 2.0 Flash for analysis
- **Embedding Model**: OpenAI text-embedding-3-small
- **Concurrency**: Configurable thread pools for parallel processing
- **File Limits**: Automatic handling of large codebases
