#!/usr/bin/env python3
"""
Cross-file taint tracking for vulnerability chain detection.

Traces data flow from sources (user input) through transformations
to sinks (dangerous functions) across multiple files.
"""

from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass
import re


@dataclass
class TaintSource:
    """Represents a source of tainted (user-controlled) data."""
    file: str
    line: int
    variable: str
    source_type: str  # 'http_param', 'file_upload', 'cookie', 'header', etc.
    function: Optional[str] = None
    
    def __str__(self):
        return f"{Path(self.file).name}:L{self.line} [{self.source_type}] {self.variable}"


@dataclass
class TaintSink:
    """Represents a dangerous function that uses tainted data."""
    file: str
    line: int
    function: str  # 'execute()', 'system()', 'eval()', etc.
    sink_type: str  # 'sql', 'command', 'file', 'code_exec', 'template'
    variable: Optional[str] = None
    
    def __str__(self):
        return f"{Path(self.file).name}:L{self.line} [{self.sink_type}] {self.function}"


@dataclass
class TaintFlow:
    """Represents a data flow from source to sink."""
    source: TaintSource
    sink: TaintSink
    hops: List[Tuple[str, int, str]]  # [(file, line, description), ...]
    sanitization_attempts: List[str]  # List of sanitization seen
    exploitability_score: int  # 0-10
    confidence: float  # 0.0-1.0
    
    @property
    def is_exploitable(self) -> bool:
        """Check if flow is likely exploitable."""
        return len(self.sanitization_attempts) == 0 and self.confidence > 0.7
    
    @property
    def file_count(self) -> int:
        """Number of files in the chain."""
        files = {self.source.file, self.sink.file}
        files.update(hop[0] for hop in self.hops)
        return len(files)


class TaintTracker:
    """Track taint flow across multiple files."""
    
    # Common taint sources by language
    TAINT_SOURCES = {
        'python': {
            'http_param': [
                r'request\.(args|form|json|data|files|values|get_json)',
                r'request\.GET\[', r'request\.POST\[',
                r'flask\.request\.',
                r'request\.query_params',  # FastAPI
            ],
            'file_upload': [r'request\.files', r'FileStorage'],
            'cookie': [r'request\.cookies', r'request\.COOKIES'],
            'header': [r'request\.headers'],
        },
        'javascript': {
            'http_param': [
                r'req\.(body|query|params|files)',
                r'request\.(body|query|params)',
            ],
            'cookie': [r'req\.cookies', r'document\.cookie'],
            'header': [r'req\.(headers|get)'],
        },
        'php': {
            'http_param': [
                r'\$_GET\[', r'\$_POST\[', r'\$_REQUEST\[',
                r'\$_FILES\[',
            ],
            'cookie': [r'\$_COOKIE\['],
            'header': [r'\$_SERVER\['],
        },
        'java': {
            'http_param': [
                r'request\.getParameter',
                r'@RequestParam',
                r'@RequestBody',
                r'@PathVariable',
            ],
            'cookie': [r'request\.getCookies'],
            'header': [r'request\.getHeader'],
        },
        'go': {
            'http_param': [
                r'r\.URL\.Query',
                r'r\.FormValue',
                r'r\.PostFormValue',
                r'gin\.Context\.',
            ],
            'cookie': [r'r\.Cookie'],
            'header': [r'r\.Header'],
        }
    }
    
    # Common dangerous sinks by language
    TAINT_SINKS = {
        'python': {
            'sql': [
                r'execute\s*\(',
                r'executemany\s*\(',
                r'cursor\.execute',
                r'\.raw\s*\(',  # Django/SQLAlchemy
                r'filter\s*\(',  # Potentially unsafe
            ],
            'command': [
                r'os\.system\s*\(',
                r'subprocess\.(call|run|Popen)',
                r'exec\s*\(',
                r'eval\s*\(',
            ],
            'file': [r'open\s*\(', r'file\s*\(', r'Path\s*\('],
            'template': [r'render_template_string', r'\.format\s*\('],
        },
        'javascript': {
            'sql': [r'query\s*\(', r'execute\s*\(', r'\.sql`'],
            'command': [r'exec\s*\(', r'eval\s*\(', r'child_process'],
            'code_exec': [r'eval\s*\(', r'Function\s*\(', r'setTimeout\s*\('],
            'template': [r'innerHTML\s*=', r'\.html\s*\('],
        },
        'php': {
            'sql': [
                r'mysqli_query\s*\(',
                r'mysql_query\s*\(',
                r'\->query\s*\(',
                r'PDO::query',
            ],
            'command': [
                r'shell_exec\s*\(',
                r'exec\s*\(',
                r'system\s*\(',
                r'passthru\s*\(',
            ],
            'file': [r'file_get_contents\s*\(', r'fopen\s*\(', r'include\s*\('],
            'code_exec': [r'eval\s*\(', r'unserialize\s*\('],
        },
        'java': {
            'sql': [
                r'createQuery\s*\(',
                r'createNativeQuery\s*\(',
                r'\.execute\s*\(',
                r'Statement\.execute',
            ],
            'command': [r'Runtime\.exec', r'ProcessBuilder'],
            'template': [r'\.setExpression', r'SpelExpressionParser'],
        },
        'go': {
            'sql': [r'db\.Exec\s*\(', r'db\.Query\s*\(', r'\.Exec\s*\('],
            'command': [r'exec\.Command\s*\(', r'os\.Exec'],
            'file': [r'os\.Open\s*\(', r'ioutil\.ReadFile'],
        }
    }
    
    @staticmethod
    def detect_language(file_path: Path) -> Optional[str]:
        """Detect programming language from file extension."""
        ext_map = {
            '.py': 'python',
            '.js': 'javascript', '.ts': 'javascript', '.jsx': 'javascript', '.tsx': 'javascript',
            '.php': 'php',
            '.java': 'java',
            '.go': 'go'
        }
        return ext_map.get(file_path.suffix.lower())
    
    @staticmethod
    def find_sources_in_file(file_path: Path, content: str) -> List[TaintSource]:
        """Find taint sources (user input) in a file."""
        lang = TaintTracker.detect_language(file_path)
        if not lang or lang not in TaintTracker.TAINT_SOURCES:
            return []
        
        sources = []
        source_patterns = TaintTracker.TAINT_SOURCES[lang]
        
        lines = content.split('\n')
        for line_num, line in enumerate(lines, 1):
            for source_type, patterns in source_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        # Extract variable name if possible
                        var_match = re.search(r'(\w+)\s*=', line)
                        var_name = var_match.group(1) if var_match else 'input'
                        
                        sources.append(TaintSource(
                            file=str(file_path),
                            line=line_num,
                            variable=var_name,
                            source_type=source_type
                        ))
                        break  # One source per line
        
        return sources
    
    @staticmethod
    def find_sinks_in_file(file_path: Path, content: str) -> List[TaintSink]:
        """Find taint sinks (dangerous functions) in a file."""
        lang = TaintTracker.detect_language(file_path)
        if not lang or lang not in TaintTracker.TAINT_SINKS:
            return []
        
        sinks = []
        sink_patterns = TaintTracker.TAINT_SINKS[lang]
        
        lines = content.split('\n')
        for line_num, line in enumerate(lines, 1):
            for sink_type, patterns in sink_patterns.items():
                for pattern in patterns:
                    match = re.search(pattern, line, re.IGNORECASE)
                    if match:
                        function_name = match.group(0)
                        sinks.append(TaintSink(
                            file=str(file_path),
                            line=line_num,
                            function=function_name,
                            sink_type=sink_type
                        ))
                        break  # One sink per line
        
        return sinks
    
    @staticmethod
    def find_function_calls(content: str, lang: str) -> List[Tuple[str, int]]:
        """Find function calls in code (for tracing flow between files)."""
        function_calls = []
        
        # Language-specific function call patterns
        patterns = {
            'python': r'(\w+)\s*\(',
            'javascript': r'(\w+)\s*\(',
            'php': r'(\w+)\s*\(',
            'java': r'(\w+)\s*\(',
            'go': r'(\w+)\s*\('
        }
        
        if lang not in patterns:
            return []
        
        lines = content.split('\n')
        for line_num, line in enumerate(lines, 1):
            matches = re.finditer(patterns[lang], line)
            for match in matches:
                func_name = match.group(1)
                # Filter out common non-function words
                if func_name not in ['if', 'for', 'while', 'return', 'def', 'class', 'import']:
                    function_calls.append((func_name, line_num))
        
        return function_calls


class TaintAnalyzer:
    """Analyze taint flows across multiple files using AI."""
    
    def __init__(self, repo_path: Path, files_to_analyze: List[Path]):
        self.repo_path = repo_path
        self.files = files_to_analyze
        self.sources: List[TaintSource] = []
        self.sinks: List[TaintSink] = []
        self.flows: List[TaintFlow] = []
    
    def analyze(self) -> List[TaintFlow]:
        """Perform cross-file taint analysis."""
        # Phase 1: Find all sources and sinks
        self._find_all_sources_and_sinks()
        
        # Phase 2: Build potential flows (sources near sinks)
        potential_flows = self._build_potential_flows()
        
        # Phase 3: AI verification of flows (done separately via Claude)
        # This will be called by orchestrator with AI context
        
        return potential_flows
    
    def _find_all_sources_and_sinks(self):
        """Scan all files for sources and sinks."""
        for file_path in self.files:
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                
                # Find sources
                sources = TaintTracker.find_sources_in_file(file_path, content)
                self.sources.extend(sources)
                
                # Find sinks
                sinks = TaintTracker.find_sinks_in_file(file_path, content)
                self.sinks.extend(sinks)
            
            except Exception:
                continue
    
    def _build_potential_flows(self) -> List[TaintFlow]:
        """Build potential taint flows from sources to sinks."""
        flows = []
        
        # For each sink, find related sources
        for sink in self.sinks:
            for source in self.sources:
                # Same file - high confidence
                if source.file == sink.file:
                    flow = TaintFlow(
                        source=source,
                        sink=sink,
                        hops=[],
                        sanitization_attempts=[],
                        exploitability_score=8,  # Same-file flows are often exploitable
                        confidence=0.8
                    )
                    flows.append(flow)
                
                # Different files - needs AI verification
                elif self._files_likely_related(source.file, sink.file):
                    flow = TaintFlow(
                        source=source,
                        sink=sink,
                        hops=[],  # Will be filled by AI
                        sanitization_attempts=[],
                        exploitability_score=7,  # Cross-file needs verification
                        confidence=0.6
                    )
                    flows.append(flow)
        
        return flows
    
    def _files_likely_related(self, file1: str, file2: str) -> bool:
        """Check if two files are likely related (same module/directory)."""
        path1 = Path(file1)
        path2 = Path(file2)
        
        # Same directory
        if path1.parent == path2.parent:
            return True
        
        # Common naming (routes.py and user_routes.py)
        if any(part in path2.name for part in path1.stem.split('_')):
            return True
        
        # Parent-child relationship (app/ and app/routes/)
        try:
            path2.relative_to(path1.parent)
            return True
        except ValueError:
            pass
        
        return False


def generate_taint_analysis_context(
    sources: List[TaintSource],
    sinks: List[TaintSink],
    file_contents: Dict[str, str]
) -> str:
    """Generate context for AI taint analysis."""
    context_parts = []
    
    context_parts.append("TAINT ANALYSIS REQUEST")
    context_parts.append("=" * 70)
    context_parts.append("")
    
    context_parts.append(f"Found {len(sources)} potential taint sources (user input)")
    context_parts.append(f"Found {len(sinks)} potential taint sinks (dangerous functions)")
    context_parts.append("")
    
    context_parts.append("SOURCES (User-Controlled Input):")
    for source in sources[:10]:  # Limit to top 10
        context_parts.append(f"  • {source}")
    if len(sources) > 10:
        context_parts.append(f"  ... and {len(sources) - 10} more")
    
    context_parts.append("")
    context_parts.append("SINKS (Dangerous Functions):")
    for sink in sinks[:10]:  # Limit to top 10
        context_parts.append(f"  • {sink}")
    if len(sinks) > 10:
        context_parts.append(f"  ... and {len(sinks) - 10} more")
    
    context_parts.append("")
    context_parts.append("TASK:")
    context_parts.append("For each sink, determine if tainted data from a source can reach it.")
    context_parts.append("Trace the data flow across files, functions, and transformations.")
    context_parts.append("Identify any sanitization or validation attempts.")
    context_parts.append("")
    
    return "\n".join(context_parts)

