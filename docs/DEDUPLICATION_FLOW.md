# Deduplication Code Flow

This document explains exactly where and when deduplication happens in the SCRYNET codebase.

**⚠️ IMPORTANT: Deduplication is OPT-IN only!**

Deduplication **only runs** if you explicitly enable it with the `--deduplicate` flag. By default, all findings from all profiles are shown separately. This gives you full visibility into what each profile found, even if there's overlap.

## High-Level Flow

```
┌────────────────────────────────────────────────────────────
│                    orchestrator.run()                       
└────────────────────────────────────────────────────────────
                            │
                            ▼
        ┌──────────────────────────────────────
        │  Stage 0: Static Scanner              
        │  - Runs Go scanner                    
        │  - Returns: static_findings[]         
        │  - Each finding tagged: source='scrynet' 
        └──────────────────────────────────────
                            │
                            ▼
        ┌──────────────────────────────────────
        │  Stage 1: Prioritization (optional)   
        │  - AI selects top N files            
        │  - Returns: prioritized_files[]      
        └──────────────────────────────────────
                            │
                            ▼
        ┌──────────────────────────────────────
        │  Stage 2: Deep Dive Analysis          
        │  - For each profile in self.profiles: 
        │    * Analyze each file with Claude    
        │    * Tag findings: source='claude-{profile}' 
        │  - Returns: ai_findings[]             
        │    (contains findings from ALL profiles) 
        └──────────────────────────────────────
                            │
                            ▼
        ┌──────────────────────────────────────
        │  Stage 3: Merging Results             
        │  ═══════════════════════════════════  
        │                                       
        │  1. Combine static + AI findings      
        │     combined = static_findings + ai_findings 
        │                                       
        │  2. Basic exact-match deduplication  
        │     (ALWAYS runs)                     
        │     - Remove exact duplicates         
        │     - Key: (file, category, title, line) 
        │                                       
        │  3. Intelligent deduplication        
        │     ⚠️ ONLY if user enables --deduplicate flag
        │     ┌─────────────────────────────
        │     │ if self.deduplicate and      
        │     │    len(self.profiles) > 1:  
        │     │                              
        │     │   combined =                 
        │     │     deduplicate_findings(    
        │     │       combined,              
        │     │       threshold=0.7,         
        │     │       strategy='keep_highest_severity' 
        │     │     )                         
        │     └─────────────────────────────
        │     (If --deduplicate NOT set, skip this step)
        │                                       
        │  4. Sort by severity                 
        │                                       
        │  5. Export reports                   
        │     (JSON, CSV, Markdown, HTML)      
        └──────────────────────────────────────
                            │
                            ▼
        ┌──────────────────────────────────────
        │  Stage 4: Payload Generation          
        │  (if --generate-payloads)             
        └──────────────────────────────────────
                            │
                            ▼
        ┌──────────────────────────────────────
        │  Stage 5: Code Annotation              
        │  (if --annotate-code)                
        └──────────────────────────────────────
```

## Exact Code Location

### File: `orchestrator.py`

**Method**: `run()` (line 887)

**Stage 3: Merging Results** (lines 903-931)

```python
def run(self) -> None:
    """Execute static scan, AI analysis, merge, and export findings."""
    
    # Stage 0: Static Scanner
    static_findings = self.run_static_scanner()
    # ... save static_findings.json ...
    
    # Stage 2: AI Scanner (runs all profiles)
    ai_findings = self.run_ai_scanner()
    # ... save ai_findings.json ...
    
    # ═══════════════════════════════════════════════════════
    # Stage 3: Merging Results
    # ═══════════════════════════════════════════════════════
    self.console.print("\n[bold cyan]📊 Stage 3: Merging Results[/bold cyan]")
    
    if self.deduplicate:
        self.console.print(f"[dim]Merging and deduplicating findings...[/dim]")
    else:
        self.console.print("[dim]Merging findings (basic deduplication)...[/dim]")
    
    # Step 1: Combine all findings
    # static_findings + ai_findings = all findings from all sources
    
    # Step 2: Basic exact-match deduplication (ALWAYS runs)
    combined: List[Finding] = []
    seen: set[Tuple[Any, ...]] = set()
    for f in static_findings + ai_findings:
        key = (
            Path(f.get('file', '')).as_posix(),
            f.get('category', '').lower().strip(),
            f.get('title', f.get('rule_name', '')).lower().strip(),
            str(f.get('line_number', f.get('line', '')))
        )
        if key in seen:
            continue  # Skip exact duplicate
        seen.add(key)
        combined.append(f)
    
    # Step 3: Intelligent deduplication (ONLY if enabled)
    if self.deduplicate and len(self.profiles) > 1:
        original_count = len(combined)
        combined = deduplicate_findings(  # <-- HERE IS WHERE IT HAPPENS
            combined,
            similarity_threshold=self.dedupe_threshold,
            merge_strategy=self.dedupe_strategy
        )
        deduped_count = original_count - len(combined)
        if deduped_count > 0:
            self.console.print(f"[dim]   Deduplicated {deduped_count} similar findings[/dim]")
    
    # Step 4: Sort by severity
    combined.sort(key=lambda x: Severity[x.get("severity", "LOW").upper()].value)
    
    # Step 5: Export reports
    # ... save combined_findings.json, .csv, .md, .html ...
```

## When Deduplication Runs

### ⚠️ OPT-IN ONLY - User Must Explicitly Enable

**Deduplication is DISABLED by default.** It only runs if you explicitly enable it.

### Condition Check (Line 925)

```python
if self.deduplicate and len(self.profiles) > 1:
    # Deduplication runs
```

**Requirements** (BOTH must be true):
1. **User must set `--deduplicate` flag** (or `self.deduplicate = True`)
   - Without this flag, deduplication is skipped entirely
   - All findings from all profiles are shown separately
2. Multiple profiles must be used (`len(self.profiles) > 1`)
   - With a single profile, there's no cross-profile duplication
   - Basic exact-match dedup is sufficient

**Default Behavior (without --deduplicate)**:
- All findings from all profiles are shown
- No intelligent similarity matching
- Only basic exact-match deduplication (same file, category, title, line)
- Full visibility into what each profile found

**Why the profile check?**
- With a single profile, there's no cross-profile duplication
- Basic exact-match dedup is sufficient
- Intelligent dedup only needed when multiple profiles find similar issues

## What Happens Before Deduplication

### Stage 2: AI Scanner (lines 400-450)

```python
def run_ai_scanner(self) -> List[Finding]:
    """Run AI analysis for each profile."""
    ai_findings: List[Finding] = []
    
    file_profiles = [p for p in self.profiles if p != 'attacker']
    for profile in file_profiles:  # Loop through each profile
        profile_findings: List[Finding] = []
        
        for file in files:
            # Analyze file with Claude using profile-specific prompt
            result = analyze_file_with_claude(file, profile)
            
            for finding in result:
                finding['source'] = f'claude-{profile}'  # Tag with profile
                profile_findings.append(finding)
        
        ai_findings.extend(profile_findings)  # Add to master list
    
    return ai_findings  # Contains findings from ALL profiles
```

**Key Point**: Each finding is tagged with its profile:
- `source='claude-owasp'`
- `source='claude-ctf'`
- `source='claude-soc2'`
- etc.

## Deduplication Function

### File: `lib/deduplication.py`

**Function**: `deduplicate_findings()` (line 75)

```python
def deduplicate_findings(
    findings: List[Dict[str, Any]],
    similarity_threshold: float = 0.7,
    merge_strategy: str = "keep_highest_severity"
) -> List[Dict[str, Any]]:
    """
    Deduplicate findings by merging similar ones.
    
    This function:
    1. Compares each finding with all others
    2. Uses are_findings_similar() to detect duplicates
    3. Merges based on strategy
    4. Returns deduplicated list
    """
    # ... implementation ...
```

**Similarity Detection**: `are_findings_similar()` (line 12)

```python
def are_findings_similar(
    finding1: Dict[str, Any],
    finding2: Dict[str, Any],
    similarity_threshold: float = 0.7
) -> bool:
    """
    Determine if two findings represent the same vulnerability.
    
    Checks:
    1. Same file (required)
    2. Same line (within 5 lines)
    3. Title similarity (using difflib)
    4. Security term matching
    """
    # ... implementation ...
```

## Example Timeline

```
Time 0:00 - Start orchestrator.run()
Time 0:05 - Stage 0 complete: 236 static findings
Time 0:10 - Stage 1 complete: 15 files prioritized
Time 2:30 - Stage 2 complete: 
            - Profile 'owasp': 45 findings
            - Profile 'ctf': 38 findings
            - Total: 83 AI findings
Time 2:31 - Stage 3 starts: Merging Results
Time 2:31 - Basic dedup: 83 → 80 (3 exact duplicates removed)
Time 2:32 - Intelligent dedup: 80 → 65 (15 similar findings merged)
Time 2:32 - Stage 3 complete: 65 combined findings
Time 2:33 - Reports exported (JSON, CSV, Markdown, HTML)
Time 2:35 - Stage 4: Payload generation (if enabled)
Time 2:50 - Stage 5: Code annotation (if enabled)
Time 2:55 - Complete!
```

## Key Points

1. **⚠️ Deduplication is OPT-IN ONLY**
   - **Default**: All findings shown separately (no intelligent deduplication)
   - **With `--deduplicate`**: Intelligent similarity-based deduplication enabled
   - User must explicitly enable with `--deduplicate` flag

2. **Deduplication happens AFTER all analysis is complete**
   - Static findings are collected
   - AI findings from all profiles are collected
   - Then deduplication runs on the combined list (if enabled)

3. **Two-stage deduplication**:
   - **Stage 1 (always)**: Exact-match deduplication
     - Removes identical findings (same file, category, title, line)
     - This always runs, regardless of `--deduplicate` flag
   - **Stage 2 (OPT-IN only)**: Intelligent deduplication
     - **Only runs if user sets `--deduplicate` flag AND multiple profiles used**
     - Uses similarity matching to find near-duplicates
     - Without `--deduplicate`, this step is skipped

4. **Profile tagging happens during analysis**:
   - Each finding gets `source='claude-{profile}'` tag
   - This allows deduplication to track which profiles found what

5. **Deduplication preserves profile information**:
   - When findings are merged, `source` field shows all profiles
   - `profiles` field lists individual profiles that found it

## Code References

- **Entry point**: `orchestrator.py:887` - `run()` method
- **Deduplication trigger**: `orchestrator.py:925` - Condition check
- **Deduplication call**: `orchestrator.py:927` - `deduplicate_findings()`
- **Similarity logic**: `lib/deduplication.py:12` - `are_findings_similar()`
- **Merge logic**: `lib/deduplication.py:75` - `deduplicate_findings()`

## Summary

**⚠️ IMPORTANT: Deduplication is OPT-IN ONLY!**

**When**: Stage 3 (Merging Results), after all analysis is complete

**Where**: `orchestrator.py`, line 925-931

**Condition**: `if self.deduplicate and len(self.profiles) > 1`
- **User must explicitly enable with `--deduplicate` flag**
- Without this flag, intelligent deduplication is skipped
- All findings from all profiles are shown separately

**Function**: `lib/deduplication.py::deduplicate_findings()`

**Input**: Combined list of static + AI findings from all profiles

**Output**: Deduplicated list with merged findings showing all source profiles

**Default Behavior**: Without `--deduplicate`, all findings are shown separately, giving full visibility into what each profile found.

