#!/usr/bin/env python3
"""
ASCII visualization for attack chains and data flows.

Creates beautiful box diagrams showing taint flow across files.
"""

from typing import List, Tuple
from pathlib import Path
from lib.taint_tracker import TaintFlow, TaintSource, TaintSink


class FlowVisualizer:
    """Generate ASCII art for attack chains."""
    
    @staticmethod
    def visualize_flow(flow: TaintFlow, width: int = 70) -> str:
        """
        Generate ASCII diagram for a single taint flow.
        
        Uses left-border-only style to avoid alignment issues with varying content widths.
        
        Example output:
        ┌─ ATTACK CHAIN: SQL Injection via User Input
        │  Files: 3 | Hops: 4 | Exploitability: 9/10 | Confidence: 95%
        ├─────────────────────────────────────────────────────────────
        ║                                                                  ║
        ║  📥 SOURCE: routes.py:L45 [http_param]                          ║
        ║     └─ Variable: user_query                                     ║
        ║                                                                  ║
        ║          ↓                                                       ║
        ║                                                                  ║
        ║  🔄 HOP 1: service.py:L102                                      ║
        ║     └─ Passed to search_users(query)                           ║
        ║                                                                  ║
        ║          ↓                                                       ║
        ║                                                                  ║
        ║  🔄 HOP 2: database.py:L67                                      ║
        ║     └─ String concatenation (NO SANITIZATION)                  ║
        ║                                                                  ║
        ║          ↓                                                       ║
        ║                                                                  ║
        ║  💥 SINK: database.py:L70 [sql]                                 ║
        ║     └─ execute(f"SELECT * FROM users WHERE name='{query}'")    ║
        ║                                                                  ║
        ║  ⚠️  NO SANITIZATION DETECTED                                    ║
        ║  ⚡ EXPLOITABILITY: 9/10 (HIGH)                                  ║
        ║  🎯 CONFIDENCE: 95%                                             ║
        ╚══════════════════════════════════════════════════════════════════╝
        """
        lines = []
        
        # Header (left-border only style)
        title = f"ATTACK CHAIN: {flow.sink.sink_type.upper()} Injection"
        stats = f"Files: {flow.file_count} | Hops: {len(flow.hops)} | " \
                f"Exploitability: {flow.exploitability_score}/10 | " \
                f"Confidence: {flow.confidence:.0%}"
        
        lines.append("┌─ " + title)
        lines.append("│  " + stats)
        lines.append("├" + "─" * 70)
        lines.append("│")
        
        # Source
        source_file = Path(flow.source.file).name
        lines.append("│  📥 SOURCE: " + f"{source_file}:L{flow.source.line} [{flow.source.source_type}]")
        lines.append("│     └─ Variable: " + flow.source.variable)
        lines.append("│")
        
        # Hops
        for i, (hop_file, hop_line, hop_desc) in enumerate(flow.hops, 1):
            lines.append("│          ↓")
            lines.append("│")
            
            hop_file_name = Path(hop_file).name
            lines.append("│  🔄 HOP " + f"{i}: {hop_file_name}:L{hop_line}")
            lines.append("│     └─ " + hop_desc)
            lines.append("│")
        
        # Arrow to sink
        lines.append("│          ↓")
        lines.append("│")
        
        # Sink
        sink_file = Path(flow.sink.file).name
        lines.append("│  💥 SINK: " + f"{sink_file}:L{flow.sink.line} [{flow.sink.sink_type}]")
        lines.append("│     └─ " + flow.sink.function)
        lines.append("│")
        
        # Analysis
        if not flow.sanitization_attempts:
            lines.append("│  ⚠️  NO SANITIZATION DETECTED")
        else:
            lines.append("│  ✓ Sanitization: " + ', '.join(flow.sanitization_attempts))
        
        exploit_level = "HIGH" if flow.exploitability_score >= 7 else "MEDIUM" if flow.exploitability_score >= 4 else "LOW"
        lines.append("│  ⚡ EXPLOITABILITY: " + f"{flow.exploitability_score}/10 ({exploit_level})")
        lines.append("│  🎯 CONFIDENCE: " + f"{flow.confidence:.0%}")
        lines.append("└" + "─" * 70)
        
        return "\n".join(lines)
    
    @staticmethod
    def visualize_multiple_flows(flows: List[TaintFlow], max_flows: int = 5) -> str:
        """Visualize multiple attack chains with clean left-border style."""
        if not flows:
            return "No attack chains detected."
        
        output = []
        output.append("")
        output.append("╔" + "═" * 68)
        output.append("║ 🔗 ATTACK CHAINS DETECTED")
        output.append("╚" + "═" * 68)
        output.append("")
        
        # Sort by exploitability
        sorted_flows = sorted(flows, key=lambda f: (f.exploitability_score, f.confidence), reverse=True)
        
        for i, flow in enumerate(sorted_flows[:max_flows], 1):
            output.append("")
            output.append("─" * 70)
            output.append(f"Chain #{i}")
            output.append("─" * 70)
            output.append(FlowVisualizer.visualize_flow(flow))
        
        if len(flows) > max_flows:
            output.append(f"\n... and {len(flows) - max_flows} more attack chains\n")
        
        return "\n".join(output)
    
    @staticmethod
    def create_summary_diagram(flows: List[TaintFlow]) -> str:
        """Create a summary diagram of all flows."""
        if not flows:
            return ""
        
        lines = []
        lines.append("\n" + "═" * 70)
        lines.append("ATTACK CHAIN SUMMARY")
        lines.append("═" * 70 + "\n")
        
        # Group by sink type
        by_type = {}
        for flow in flows:
            sink_type = flow.sink.sink_type
            if sink_type not in by_type:
                by_type[sink_type] = []
            by_type[sink_type].append(flow)
        
        for sink_type, type_flows in sorted(by_type.items(), key=lambda x: len(x[1]), reverse=True):
            lines.append(f"{sink_type.upper()} Injection: {len(type_flows)} chains")
            
            # Show top 3 for this type
            for flow in type_flows[:3]:
                source_file = Path(flow.source.file).name
                sink_file = Path(flow.sink.file).name
                
                if source_file == sink_file:
                    lines.append(f"  • {source_file} (same-file, ⚡{flow.exploitability_score}/10)")
                else:
                    lines.append(f"  • {source_file} → {sink_file} ({flow.file_count} files, ⚡{flow.exploitability_score}/10)")
            
            if len(type_flows) > 3:
                lines.append(f"  ... and {len(type_flows) - 3} more")
            lines.append("")
        
        return "\n".join(lines)
    
    @staticmethod
    def create_simple_flow_diagram(source_file: str, sink_file: str, hops: List[str]) -> str:
        """Create a simple linear flow diagram."""
        files = [Path(source_file).name]
        files.extend(Path(hop).name for hop in hops if hop not in [source_file, sink_file])
        files.append(Path(sink_file).name)
        
        # Deduplicate while preserving order
        seen = set()
        unique_files = []
        for f in files:
            if f not in seen:
                seen.add(f)
                unique_files.append(f)
        
        return " → ".join(unique_files)

