"""
Minimal KISS parser for armips-style assembly files.
Goal: Parse scriptmacros.s to understand macro definitions for deassembly.
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict


# Line type patterns (checked in order - first match wins)
PATTERNS = [
    # Empty line or whitespace only
    ('empty', re.compile(r'^\s*$')),
    
    # Full-line comment: // comment
    ('comment', re.compile(r'^\s*//(.*)$')),
    
    # Constant definition: NAME equ VALUE or .equ NAME, VALUE
    ('equ', re.compile(r'^(\w+)\s+equ\s+(.+)$')),
    ('equ_dot', re.compile(r'^\.equ\s+(\w+)\s*,\s*(.+)$')),
    
    # Macro definition start: .macro name or .macro name,arg1,arg2
    ('macro_start', re.compile(r'^\.macro\s+(\w+)(?:\s*,\s*(.+))?$')),
    
    # Macro definition end: .endmacro
    ('macro_end', re.compile(r'^\.endmacro\s*$')),
    
    # Conditional directives: .if, .else, .endif, .elseif
    ('if', re.compile(r'^\.if\s+(.+)$')),
    ('else', re.compile(r'^\.else\s*$')),
    ('elseif', re.compile(r'^\.elseif\s+(.+)$')),
    ('endif', re.compile(r'^\.endif\s*$')),
    
    # Data directives: .byte, .halfword, .word with value
    ('directive', re.compile(r'^\.(byte|halfword|word)\s+(.+)$')),
    
    # Macro invocation: macroname or macroname arg1,arg2
    # This is a catch-all for lines that look like macro calls
    ('invocation', re.compile(r'^(\w+)(?:\s+(.+))?$')),
]


@dataclass
class ParsedLine:
    """Result of parsing a single line."""
    line_type: str          # Key from PATTERNS that matched
    groups: Tuple           # Captured groups from the regex match
    raw: str                # Original line text
    line_num: int           # 1-based line number


@dataclass
class Macro:
    """A parsed macro definition."""
    name: str                       # Macro name (e.g., 'wait', 'loadbyte')
    params: List[str]               # Parameter names (e.g., ['frames', 'var'])
    body: List[ParsedLine]          # Lines inside the macro (directives, invocations, etc.)
    line_num: int                   # Line number where macro starts


@dataclass 
class ParamSlot:
    """A parameter slot in a macro's binary encoding."""
    size: int           # Size in bytes: 1=byte, 2=halfword, 4=word
    name: Optional[str] # Parameter name if this references a param, None if literal
    value: Optional[int] # Literal value if this is a constant, None if param reference
    is_relative: bool = False  # True if expression contains relative offset (e.g., dest-.-4)


@dataclass
class MacroSignature:
    """
    Deassembly signature for a macro.
    Used to match binary data back to macro calls.
    """
    name: str                   # Macro name
    cmd_id: Optional[int]       # Command ID (first literal halfword), None if complex
    slots: List[ParamSlot]      # Parameter slots after cmd_id
    is_simple: bool             # True if no conditionals/invocations (can be deassembled)
    complexity_reason: Optional[str]  # Why it's not simple, if applicable


def strip_trailing_comment(text: str) -> Tuple[str, Optional[str]]:
    """
    Strip trailing // comment from a line.
    Returns (content, comment) where comment is None if no trailing comment.
    """
    # Simple approach: find // not inside a string
    # For now, assume no strings in expressions
    idx = text.find('//')
    if idx >= 0:
        return text[:idx].rstrip(), text[idx+2:].strip()
    return text, None


def parse_line(line: str, line_num: int) -> ParsedLine:
    """
    Parse a single line and return its type and captured groups.
    """
    # Strip trailing comment first (but preserve full-line comments)
    stripped = line.strip()
    
    # Check each pattern in priority order
    for line_type, pattern in PATTERNS:
        # For most line types, we strip trailing comments first
        # But for 'comment' type, we match the original
        if line_type == 'comment':
            match = pattern.match(stripped)
        elif line_type == 'empty':
            match = pattern.match(stripped)
        else:
            # Strip trailing comment for content lines
            content, _ = strip_trailing_comment(stripped)
            match = pattern.match(content)
        
        if match:
            return ParsedLine(
                line_type=line_type,
                groups=match.groups(),
                raw=line,
                line_num=line_num
            )
    
    # Should not reach here if patterns are exhaustive
    return ParsedLine(
        line_type='unknown',
        groups=(),
        raw=line,
        line_num=line_num
    )


def parse_file(filepath: str) -> List[ParsedLine]:
    """
    Parse an entire file and return list of ParsedLine objects.
    """
    results = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f, start=1):
            results.append(parse_line(line, i))
    return results


def parse_params(params_str: Optional[str]) -> List[str]:
    """
    Parse comma-separated parameter string into list of parameter names.
    E.g., 'frames,var' -> ['frames', 'var']
    """
    if not params_str:
        return []
    return [p.strip() for p in params_str.split(',')]


def extract_macros(lines: List[ParsedLine]) -> Dict[str, Macro]:
    """
    Extract all macro definitions from parsed lines.
    Returns dict mapping macro name -> Macro object.
    """
    macros = {}
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        if line.line_type == 'macro_start':
            name = line.groups[0]
            params = parse_params(line.groups[1])
            start_line = line.line_num
            body = []
            i += 1
            
            # Collect body lines until .endmacro
            while i < len(lines) and lines[i].line_type != 'macro_end':
                body_line = lines[i]
                # Skip empty lines and comments in body
                if body_line.line_type not in ('empty', 'comment'):
                    body.append(body_line)
                i += 1
            
            macros[name] = Macro(
                name=name,
                params=params,
                body=body,
                line_num=start_line
            )
        
        i += 1
    
    return macros


DIRECTIVE_SIZES = {'byte': 1, 'halfword': 2, 'word': 4}


def try_parse_literal(expr: str) -> Optional[int]:
    """
    Try to parse an expression as a literal integer.
    Returns the integer value, or None if it's not a simple literal.
    """
    expr = expr.strip()
    try:
        # Handle hex (0x...), decimal, negative
        if expr.startswith('0x') or expr.startswith('0X'):
            return int(expr, 16)
        elif expr.startswith('-'):
            return int(expr)
        elif expr.isdigit():
            return int(expr)
    except ValueError:
        pass
    return None


def analyze_macro(macro: Macro) -> MacroSignature:
    """
    Analyze a macro to extract its deassembly signature.
    
    A 'simple' macro has:
    - First line is .halfword with a literal (the command ID)
    - Remaining lines are .byte/.halfword/.word with either literals or param refs
    - No conditionals (.if/.else) or macro invocations
    """
    slots = []
    cmd_id = None
    is_simple = True
    complexity_reason = None
    
    for i, line in enumerate(macro.body):
        # Check for complexity
        if line.line_type in ('if', 'else', 'elseif', 'endif'):
            is_simple = False
            complexity_reason = f"has conditional: {line.line_type}"
            continue
        
        if line.line_type == 'invocation':
            is_simple = False
            complexity_reason = f"has invocation: {line.groups[0]}"
            continue
        
        if line.line_type != 'directive':
            continue
        
        directive_type = line.groups[0]  # 'byte', 'halfword', 'word'
        expr = line.groups[1]            # The value expression
        size = DIRECTIVE_SIZES[directive_type]
        
        # Try to parse as literal
        literal = try_parse_literal(expr)
        
        # Check if expression contains relative offset marker (.)
        is_relative = '.-' in expr or '-.' in expr or expr.strip() == '.'
        
        if literal is not None:
            # It's a literal value
            if i == 0 and directive_type == 'halfword' and cmd_id is None:
                # First halfword literal is the command ID
                cmd_id = literal
            else:
                # Subsequent literal - still a slot but with fixed value
                slots.append(ParamSlot(size=size, name=None, value=literal, is_relative=is_relative))
        else:
            # It's a parameter reference or expression
            # Check if expr matches a parameter name
            param_name = None
            for p in macro.params:
                if p in expr:
                    param_name = p
                    break
            
            slots.append(ParamSlot(size=size, name=param_name, value=None, is_relative=is_relative))
    
    return MacroSignature(
        name=macro.name,
        cmd_id=cmd_id,
        slots=slots,
        is_simple=is_simple,
        complexity_reason=complexity_reason
    )


def prefer_name(name_a: str, name_b: str) -> str:
    """
    Choose the preferred macro name when there's a collision.
    Heuristics:
    - Prefer names starting with uppercase (readable names like 'JumpIf')
    - Prefer names without underscores (CamelCase over snake_case)
    - Prefer shorter names if tied
    """
    def score(name: str) -> tuple:
        starts_upper = name[0].isupper() if name else False
        has_underscore = '_' in name
        is_generic = name.startswith('scrcmd_') or name.startswith('CMD_')
        return (not is_generic, starts_upper, not has_underscore, -len(name))
    
    return name_a if score(name_a) >= score(name_b) else name_b


def build_cmd_lookup(macros: Dict[str, Macro]) -> Dict[int, MacroSignature]:
    """
    Build a lookup table: cmd_id -> MacroSignature.
    Only includes simple macros with valid command IDs.
    On collision, prefer the "better" name.
    """
    lookup = {}
    for macro in macros.values():
        sig = analyze_macro(macro)
        if sig.is_simple and sig.cmd_id is not None:
            if sig.cmd_id in lookup:
                existing = lookup[sig.cmd_id]
                preferred = prefer_name(existing.name, sig.name)
                if preferred == sig.name:
                    lookup[sig.cmd_id] = sig
                # else keep existing
            else:
                lookup[sig.cmd_id] = sig
    return lookup


def main():
    """Test the parser on scriptmacros.s"""
    import os
    
    # Find the scriptmacros.s file relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)
    target_file = os.path.join(repo_root, 'armips', 'include', 'scriptmacros.s')
    
    if not os.path.exists(target_file):
        print(f"File not found: {target_file}")
        return
    
    parsed = parse_file(target_file)
    macros = extract_macros(parsed)
    
    print(f"Extracted {len(macros)} macros")
    
    # Build command lookup
    cmd_lookup = build_cmd_lookup(macros)
    print(f"Built lookup table with {len(cmd_lookup)} simple macros\n")
    
    # Show macros with relative offsets
    print("Macros with relative offset slots:")
    rel_count = 0
    for name, macro in macros.items():
        sig = analyze_macro(macro)
        rel_slots = [s for s in sig.slots if s.is_relative]
        if rel_slots and rel_count < 10:
            slots_str = ', '.join(
                f"{s.size}B:{s.name}{'(REL)' if s.is_relative else ''}" for s in sig.slots
            )
            print(f"  {sig.name}: cmd={sig.cmd_id}, slots=[{slots_str}]")
            rel_count += 1
    
    # Summary stats
    total_with_rel = sum(1 for m in macros.values() 
                        if any(s.is_relative for s in analyze_macro(m).slots))
    print(f"\nTotal macros with relative offsets: {total_with_rel}")
    
    # Show cmd_id range
    cmd_ids = sorted(cmd_lookup.keys())
    print(f"Command ID range: {min(cmd_ids)} - {max(cmd_ids)}")


if __name__ == '__main__':
    main()
