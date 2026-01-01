#!/usr/bin/env python3
"""
SCRYNET - Unified Security Scanner Entry Point

A unified command-line interface for all SCRYNET scanning modes:
- static: Fast Go-based static analysis
- analyze: AI-powered multi-stage analysis
- ctf: CTF-focused vulnerability discovery
- hybrid: Combines static scanner with AI analysis
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="SCRYNET - Unified Security Scanner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Static scanning (Go scanner only)
  python3 scrynet.py static /path/to/repo --severity HIGH
  
  # AI-powered analysis
  python3 scrynet.py analyze /path/to/repo "find security vulnerabilities"
  
  # CTF mode (exploitation-focused)
  python3 scrynet.py ctf /path/to/ctf "find all vulnerabilities" --generate-payloads
  
  # Hybrid mode (static + AI)
  python3 scrynet.py hybrid /path/to/repo ./scanner --profile owasp

For more information on each mode, use:
  python3 scrynet.py <mode> --help
        """
    )
    
    subparsers = parser.add_subparsers(dest='mode', help='Scanning mode')
    
    # Static mode (Go scanner)
    static_parser = subparsers.add_parser(
        'static',
        help='Run static Go scanner only (fast, no AI)',
        description='Fast static analysis using the Go scanner binary'
    )
    static_parser.add_argument('repo_path', help='Path to repository to scan')
    static_parser.add_argument('scanner_bin', help='Path to scanner binary', nargs='?', default='./scanner')
    static_parser.add_argument('--rules', help='Comma-separated rule files')
    static_parser.add_argument('--severity', choices=['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'], help='Minimum severity')
    static_parser.add_argument('--output', choices=['text', 'json', 'markdown'], default='text', help='Output format')
    static_parser.add_argument('--verbose', action='store_true', help='Show remediation advice')
    static_parser.add_argument('--git-diff', action='store_true', help='Scan only changed files')
    static_parser.add_argument('--ignore', help='Comma-separated glob patterns to ignore')
    
    # Analyze mode (smart analyzer)
    analyze_parser = subparsers.add_parser(
        'analyze',
        help='Run AI-powered multi-stage analysis',
        description='Comprehensive AI analysis with prioritization, deep dive, and synthesis'
    )
    analyze_parser.add_argument('repo_path', help='Path to repository to analyze')
    analyze_parser.add_argument('question', nargs='?', help='Analysis question')
    # Pass through all smart_analyzer arguments
    analyze_parser.add_argument('--cache-dir', default='.scrynet_cache', help='Cache directory')
    analyze_parser.add_argument('--no-cache', action='store_true', help='Disable cache')
    analyze_parser.add_argument('--include-yaml', action='store_true', help='Include YAML files')
    analyze_parser.add_argument('--include-helm', action='store_true', help='Include Helm templates')
    analyze_parser.add_argument('--max-file-bytes', type=int, default=500_000, help='Max file size')
    analyze_parser.add_argument('--max-files', type=int, default=400, help='Max files to analyze')
    analyze_parser.add_argument('--prioritize-top', type=int, default=15, help='Top N files to prioritize')
    analyze_parser.add_argument('--format', nargs='*', default=['console'], choices=['console', 'html', 'markdown', 'json'])
    analyze_parser.add_argument('--model', default='claude-3-5-haiku-20241022', help='Claude model')
    analyze_parser.add_argument('--max-tokens', type=int, default=4000, help='Max tokens per response')
    analyze_parser.add_argument('--temperature', type=float, default=0.0, help='Sampling temperature')
    analyze_parser.add_argument('--top-n', type=int, default=5, help='Top N findings for payloads/annotations')
    analyze_parser.add_argument('--threshold', choices=['HIGH', 'MEDIUM'], help='Filter findings by relevance')
    analyze_parser.add_argument('--generate-payloads', action='store_true', help='Generate payloads')
    analyze_parser.add_argument('--annotate-code', action='store_true', help='Generate code annotations')
    analyze_parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    analyze_parser.add_argument('--debug', action='store_true', help='Debug mode')
    analyze_parser.add_argument('--enable-review-state', action='store_true', help='Enable review state tracking')
    analyze_parser.add_argument('--resume-last', action='store_true', help='Resume last review')
    analyze_parser.add_argument('--resume-review', metavar='ID', help='Resume review by ID')
    analyze_parser.add_argument('--list-reviews', action='store_true', help='List all reviews')
    analyze_parser.add_argument('--cache-info', action='store_true', help='Show cache stats')
    analyze_parser.add_argument('--cache-clear', action='store_true', help='Clear cache')
    analyze_parser.add_argument('--help-examples', action='store_true', help='Show usage examples')
    
    # CTF mode
    ctf_parser = subparsers.add_parser(
        'ctf',
        help='Run CTF-focused vulnerability discovery',
        description='Optimized for Capture The Flag challenges - quick vulnerability discovery'
    )
    ctf_parser.add_argument('repo_path', help='Path to CTF challenge')
    ctf_parser.add_argument('question', nargs='?', help='Analysis question')
    # Similar args to analyze mode
    ctf_parser.add_argument('--cache-dir', default='.scrynet_cache', help='Cache directory')
    ctf_parser.add_argument('--no-cache', action='store_true', help='Disable cache')
    ctf_parser.add_argument('--max-file-bytes', type=int, default=500_000, help='Max file size')
    ctf_parser.add_argument('--max-files', type=int, default=400, help='Max files to analyze')
    ctf_parser.add_argument('--prioritize-top', type=int, default=15, help='Top N files to prioritize')
    ctf_parser.add_argument('--format', nargs='*', default=['console'], choices=['console', 'html', 'markdown', 'json'])
    ctf_parser.add_argument('--top-n', type=int, default=10, help='Top N findings for payloads')
    ctf_parser.add_argument('--generate-payloads', action='store_true', help='Generate exploitation payloads')
    ctf_parser.add_argument('--annotate-code', action='store_true', help='Generate code annotations')
    ctf_parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    ctf_parser.add_argument('--debug', action='store_true', help='Debug mode')
    ctf_parser.add_argument('--enable-review-state', action='store_true', help='Enable review state tracking')
    ctf_parser.add_argument('--resume-last', action='store_true', help='Resume last review')
    
    # Hybrid mode (orchestrator)
    hybrid_parser = subparsers.add_parser(
        'hybrid',
        help='Run hybrid analysis (static scanner + AI)',
        description='Combines fast static scanning with AI-powered contextual analysis'
    )
    hybrid_parser.add_argument('repo_path', help='Path to repository to scan')
    hybrid_parser.add_argument('scanner_bin', help='Path to scanner binary', nargs='?', default='./scanner')
    hybrid_parser.add_argument('--profile', default='owasp', help='AI analysis profile (comma-separated)')
    hybrid_parser.add_argument('--static-rules', help='Comma-separated static rule files')
    hybrid_parser.add_argument('--severity', choices=['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'], help='Minimum severity')
    hybrid_parser.add_argument('--threat-model', action='store_true', help='Perform threat modeling')
    hybrid_parser.add_argument('--parallel', action='store_true', help='Run AI analysis in parallel')
    hybrid_parser.add_argument('--verbose', action='store_true', help='Verbose output with colors and details')
    hybrid_parser.add_argument('--debug', action='store_true', help='Debug mode')
    hybrid_parser.add_argument('--model', help='Claude model to use (default: claude-3-5-haiku-20241022)')
    hybrid_parser.add_argument('--prioritize', action='store_true', help='Enable AI prioritization (recommended for large repos)')
    hybrid_parser.add_argument('--prioritize-top', type=int, default=15, help='Number of top files to prioritize (default: 15)')
    hybrid_parser.add_argument('--question', help='Analysis question for prioritization')
    hybrid_parser.add_argument('--generate-payloads', action='store_true', help='Generate Red/Blue team payloads for top findings')
    hybrid_parser.add_argument('--annotate-code', action='store_true', help='Generate annotated code snippets showing flaws and fixes')
    hybrid_parser.add_argument('--top-n', type=int, default=5, help='Number of top findings for payload/annotation generation (default: 5)')
    
    args = parser.parse_args()
    
    if not args.mode:
        parser.print_help()
        sys.exit(1)
    
    # Dispatch to appropriate mode
    if args.mode == 'static':
        # Run Go scanner directly
        import subprocess
        cmd = [args.scanner_bin, '--dir', args.repo_path, '--output', args.output]
        if args.rules:
            cmd.extend(['--rules', args.rules])
        if args.severity:
            cmd.extend(['--severity', args.severity])
        if args.verbose:
            cmd.append('--verbose')
        if args.git_diff:
            cmd.append('--git-diff')
        if args.ignore:
            cmd.extend(['--ignore', args.ignore])
        
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            sys.exit(e.returncode)
        except FileNotFoundError:
            print(f"Error: Scanner binary '{args.scanner_bin}' not found", file=sys.stderr)
            sys.exit(1)
    
    elif args.mode == 'analyze':
        # Import and run smart_analyzer
        from smart_analyzer import main as analyze_main
        # Convert argparse namespace to sys.argv for smart_analyzer
        sys.argv = ['smart_analyzer.py', args.repo_path]
        if args.question:
            sys.argv.append(args.question)
        
        # Add all other arguments
        for key, value in vars(args).items():
            if key in ('mode', 'repo_path', 'question') or value is None:
                continue
            if isinstance(value, bool) and value:
                sys.argv.append(f'--{key.replace("_", "-")}')
            elif not isinstance(value, bool):
                sys.argv.append(f'--{key.replace("_", "-")}')
                if isinstance(value, list):
                    sys.argv.extend(str(v) for v in value)
                else:
                    sys.argv.append(str(value))
        
        analyze_main()
    
    elif args.mode == 'ctf':
        # Import and run ctf_analyzer
        from ctf_analyzer import main as ctf_main
        # Similar conversion for CTF mode
        sys.argv = ['ctf_analyzer.py', args.repo_path]
        if args.question:
            sys.argv.append(args.question)
        
        for key, value in vars(args).items():
            if key in ('mode', 'repo_path', 'question') or value is None:
                continue
            if isinstance(value, bool) and value:
                sys.argv.append(f'--{key.replace("_", "-")}')
            elif not isinstance(value, bool):
                sys.argv.append(f'--{key.replace("_", "-")}')
                if isinstance(value, list):
                    sys.argv.extend(str(v) for v in value)
                else:
                    sys.argv.append(str(value))
        
        ctf_main()
    
    elif args.mode == 'hybrid':
        # Import and run orchestrator
        try:
            from orchestrator import main as hybrid_main
        except ImportError as e:
            print(f"Error: Failed to import orchestrator: {e}", file=sys.stderr)
            print("Make sure all dependencies are installed: pip install -r requirements.txt", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error loading orchestrator: {e}", file=sys.stderr)
            sys.exit(1)
        
        # Build sys.argv for orchestrator
        sys.argv = ['orchestrator.py', args.repo_path, args.scanner_bin]
        
        for key, value in vars(args).items():
            if key in ('mode', 'repo_path', 'scanner_bin') or value is None:
                continue
            if isinstance(value, bool) and value:
                sys.argv.append(f'--{key.replace("_", "-")}')
            elif not isinstance(value, bool):
                sys.argv.append(f'--{key.replace("_", "-")}')
                sys.argv.append(str(value))
        
        hybrid_main()


if __name__ == '__main__':
    main()

