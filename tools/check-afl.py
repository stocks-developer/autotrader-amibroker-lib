#!/usr/bin/env python
"""
Catch the AFL mistakes that only real AmiBroker would otherwise catch.

Both checks below are PARSE-TIME failures. A formula that trips either one does
not load at all, and no part of it runs -- so a user sees a syntax error rather
than a misbehaving strategy. Neither is visible by reading the code, and neither
is caught by any test we can run without AmiBroker installed.

    1. Reserved names.  AFL's lexer turns every built-in function name into a
       FUNCT token. Using one as a variable, a parameter or a loop counter is:

           Error 31. Syntax error, unexpected FUNCT, expecting ')' or ','

       It is not shadowing, and there is no warning. This is a real defect that
       shipped: `status` (AmiBroker's Status() function) was used as a parameter
       and as a local in the direct library, and the library could not be loaded
       by anybody until it was renamed.

    2. Define before use.  AFL is interpreted top-down, so a function must be
       defined earlier in the file, or in an earlier #include, than the line
       that calls it. Reordering includes is enough to break this.

Usage:
    python tools/check-afl.py           # from the repository root
    echo $?                             # 0 = clean, 1 = problems found

The reserved-name list is vendored in tools/afl-reserved-names.txt so this runs
offline and gives the same answer on every machine. That file says how to
refresh it.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INCLUDE = ROOT / "Formulas" / "Include"
NAMES = Path(__file__).resolve().parent / "afl-reserved-names.txt"

# The two entry points. Each pulls its own chain of includes, and the order
# matters for check 2, so the chain is read from the file rather than listed
# here -- a new #include is then covered automatically.
ENTRY_POINTS = ["autotrader-http.afl", "autotrader.afl"]

# Language keywords. Legal to write, never identifiers, so they must not be
# reported even though some of them look like functions.
KEYWORDS = {
    "if", "else", "for", "while", "do", "return", "function", "procedure",
    "global", "local", "true", "false", "and", "or", "not", "break",
    "continue", "switch", "case", "default",
}


def load_reserved():
    names = set()
    for line in NAMES.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            names.add(line.lower())
    if len(names) < 300:
        sys.exit("tools/afl-reserved-names.txt looks truncated (%d names)" % len(names))
    return names


def strip_noise(src):
    """Blank out block comments, line comments and string literals.

    Newlines inside block comments are kept so reported line numbers stay true.
    `status` is ordinary English in a comment and an ordinary substring in
    `statusKey`; only whole identifier tokens in code are of interest here.
    """
    src = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), src, flags=re.S)
    src = re.sub(r"//[^\n]*", " ", src)
    src = re.sub(r'"(?:[^"\\]|\\.)*"', '""', src)
    return src


def chain_for(entry):
    """The include list of `entry`, in order, followed by `entry` itself.

    Comments are stripped first. Both entry points document their own usage
    with a literal `#include <autotrader-http.afl>` line inside the header
    comment, and reading that as a real include puts the entry point at the
    front of its own chain -- which then reports every helper it calls as
    undefined.
    """
    text = strip_noise((INCLUDE / entry).read_text(encoding="utf-8", errors="replace"))
    files = []
    for m in re.finditer(r"#include(?:_once)?\s*<\s*([^>]+?)\s*>", text, re.I):
        name = m.group(1).strip()
        if name != entry and (INCLUDE / name).exists() and name not in files:
            files.append(name)
    files.append(entry)
    return files


def declared_identifiers(code):
    """Every name the file declares or assigns, as (name, line)."""
    found = []
    for m in re.finditer(r"\b(?:function|procedure)\s+(\w+)\s*\(([^)]*)\)", code, re.I):
        line = code[: m.start()].count("\n") + 1
        for p in m.group(2).split(","):
            p = p.strip()
            if re.fullmatch(r"[A-Za-z_]\w*", p):
                found.append((p, line))
    for m in re.finditer(r"\b(?:global|local)\s+([^;]+);", code, re.I):
        line = code[: m.start()].count("\n") + 1
        for p in m.group(1).split(","):
            p = p.strip()
            if re.fullmatch(r"[A-Za-z_]\w*", p):
                found.append((p, line))
    for m in re.finditer(r"(?:^|[;{}])\s*([A-Za-z_]\w*)\s*=(?!=)", code, re.M):
        found.append((m.group(1), code[: m.start()].count("\n") + 1))
    for m in re.finditer(r"\bfor\s*\(\s*([A-Za-z_]\w*)\s*=", code, re.I):
        found.append((m.group(1), code[: m.start()].count("\n") + 1))
    return found


def check_reserved(reserved):
    """Check 1, over every .afl in the repository, samples included."""
    problems = []
    for path in sorted(ROOT.rglob("*.afl")):
        code = strip_noise(path.read_text(encoding="utf-8", errors="replace"))
        seen = set()
        for name, line in declared_identifiers(code):
            low = name.lower()
            if low in reserved and low not in KEYWORDS and (low, path) not in seen:
                seen.add((low, path))
                problems.append(
                    "%s:%d  '%s' is a built-in AFL function and cannot be used as "
                    "an identifier" % (path.relative_to(ROOT).as_posix(), line, name)
                )
    return problems


def check_define_before_use(reserved):
    """Check 2, per entry point, walking that entry point's include order."""
    problems = []
    for entry in ENTRY_POINTS:
        if not (INCLUDE / entry).exists():
            continue
        known = set()
        for fname in chain_for(entry):
            code = strip_noise((INCLUDE / fname).read_text(encoding="utf-8", errors="replace"))
            lines = code.splitlines()

            local = {}
            for i, text in enumerate(lines, 1):
                m = re.search(r"\b(?:function|procedure)\s+(\w+)\s*\(", text, re.I)
                if m:
                    local.setdefault(m.group(1).lower(), i)

            reported = set()
            for i, text in enumerate(lines, 1):
                for m in re.finditer(r"\b([A-Za-z_]\w*)\s*\(", text):
                    low = m.group(1).lower()
                    if low in KEYWORDS or low in reserved or low in known:
                        continue
                    if re.search(r"\b(?:function|procedure)\s+%s\s*\("
                                 % re.escape(m.group(1)), text, re.I):
                        continue
                    if low in local and local[low] < i:
                        continue
                    if low in reported:
                        continue
                    reported.add(low)
                    why = ("defined later in the same file, on line %d" % local[low]
                           if low in local else
                           "not defined anywhere in the %s chain" % entry)
                    problems.append("Formulas/Include/%s:%d  '%s' is called before it "
                                    "exists -- %s" % (fname, i, m.group(1), why))
            known.update(local)
    return problems


def main():
    reserved = load_reserved()
    print("checking %s against %d built-in AFL names" % (ROOT.name, len(reserved)))

    problems = check_reserved(reserved) + check_define_before_use(reserved)
    print()
    if problems:
        for p in problems:
            print("  %s" % p)
        print()
        print("%d problem(s). Each of these stops the formula from loading." % len(problems))
        return 1

    print("clean -- no reserved-name collisions, and every call follows its definition.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
