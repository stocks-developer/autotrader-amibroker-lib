#!/usr/bin/env python
"""
Catch the AFL mistakes that only real AmiBroker would otherwise catch.

Checks 1 to 3 are PARSE-TIME failures. A formula that trips one does not load at
all, and no part of it runs -- so a user sees a syntax error rather than a
misbehaving strategy. Check 4 is a RUNTIME failure: the formula loads perfectly
and then dies on the first line that reaches it. None is visible by reading the
code, and none is caught by any test that does not involve AmiBroker.

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

    3. Return placement.  AmiBroker's own documentation is explicit: "a return
       statement must be placed at the very end of the function". An early
       return -- the ordinary C habit of returning from inside an if() -- is:

           Error 30. Syntax error, unexpected RETURN

       This is the second real defect of this kind that shipped: atEnsureFresh()
       returned early from four branches, and the direct library could not be
       loaded by anybody until it was rewritten to a single exit. The whole of
       the file-based library obeys the rule (208 functions, one return each),
       which is why it never showed up there.

    4. Built-in price arrays.  O H L C V and Avg are predefined ARRAYS, not
       functions, so they are absent from the reserved-name list and check 1
       cannot see them. AFL is case-insensitive, so a local called `c` IS the
       Close array, and giving it a string fails when the line runs:

           You can only assign ARRAY or NUMERIC value to any of OHLC, V, Avg arrays

       This is the third real defect of this kind that shipped: `c` was the loop
       character variable in atUrlEncode() and atCsvField(), so the direct
       library LOADED correctly and then could not encode a request or read a
       reply -- every getter returned 0 and no order could be placed. Because it
       is a runtime failure, a load test passes and only a real call exposes it.

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

# AmiBroker's predefined PRICE ARRAYS. Deliberately not in
# afl-reserved-names.txt: that file is AmiBroker's function reference, and these
# are arrays, not functions, so no amount of extending it would cover them.
PRICE_ARRAYS = {
    "o", "h", "l", "c", "v",
    "open", "high", "low", "close", "volume",
    "avg", "openint", "oi",
}

# Functions that return a STRING. Assigning one of these to a price array is
# what produces the runtime error; assigning an array to it (C = MA(C, 10)) is
# perfectly legal AFL, so only the string case is reported.
STRING_FUNCS = {
    "strmid", "strleft", "strright", "strextract", "strformat", "numtostr",
    "strtrim", "strreplace", "strtoupper", "strtolower", "writeval", "writeif",
    "datetimetostr", "datetostr", "timetostr", "strtrimleft", "strtrimright",
}

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


# Braces, function headers and the return keyword, in one pass. Everything else
# in the file is irrelevant to check 3, and running one regex over the stripped
# source is what keeps the brace depth honest across `} else {`.
TOKENS = re.compile(r"[{}]|\b(?:function|procedure)\s+(\w+)\s*\(|\breturn\b", re.I)


def check_return_placement():
    """Check 3, over every .afl in the repository, samples included.

    Depth 0 is file scope, depth 1 is a function body. A return at depth 2 or
    deeper sits inside an if(), an else or a loop, and will not parse. More than
    one return in a function cannot all be last, so that is reported too.
    """
    problems = []
    for path in sorted(ROOT.rglob("*.afl")):
        code = strip_noise(path.read_text(encoding="utf-8", errors="replace"))
        rel = path.relative_to(ROOT).as_posix()

        newlines = [m.end() for m in re.finditer(r"\n", code)]

        def line_of(offset):
            lo, hi = 0, len(newlines)
            while lo < hi:
                mid = (lo + hi) // 2
                if newlines[mid] <= offset:
                    lo = mid + 1
                else:
                    hi = mid
            return lo + 1

        depth = 0
        current = None
        functions = []
        for m in TOKENS.finditer(code):
            token = m.group(0)
            if token == "{":
                depth += 1
            elif token == "}":
                depth -= 1
                if depth <= 0:
                    depth = 0
                    if current is not None:
                        functions.append(current)
                        current = None
            elif m.group(1) is not None:
                if depth == 0:
                    if current is not None:
                        functions.append(current)
                    current = {"name": m.group(1), "line": line_of(m.start()),
                               "returns": []}
            elif current is not None:
                current["returns"].append((line_of(m.start()), depth))
        if current is not None:
            functions.append(current)

        for fn in functions:
            nested = [line for line, d in fn["returns"] if d >= 2]
            if nested:
                for line in nested:
                    problems.append(
                        "%s:%d  'return' inside a nested block in %s() -- AFL needs the "
                        "return to be the last statement of the function"
                        % (rel, line, fn["name"]))
            elif len(fn["returns"]) > 1:
                where = ", ".join(str(line) for line, _ in fn["returns"])
                problems.append(
                    "%s:%d  %s() has %d returns (lines %s) -- AFL allows one, at the "
                    "very end" % (rel, fn["line"], fn["name"], len(fn["returns"]), where))
    return problems


def check_price_arrays():
    """Check 4, over every .afl in the repository, samples included.

    O H L C V and Avg are predefined price ARRAYS. AFL is case-insensitive, so a
    local called `c` IS the Close array, and giving it a string fails when the
    line actually runs:

        You can only assign ARRAY or NUMERIC value to any of OHLC, V, Avg arrays

    Unlike checks 1-3 this is a RUNTIME failure, not a parse failure. The
    formula loads perfectly and then dies on the first call that reaches the
    line -- which is exactly how it escaped: `c` was the loop character variable
    in atUrlEncode() and atCsvField(), so the direct library loaded fine and
    then could not encode a request or read a reply.

    Only the string case is reported. `C = MA(C, 10)` is ordinary AFL and must
    not be flagged, so an assignment counts only when its right-hand side is a
    string literal or a known string-returning function, or when the name is
    used as a parameter or a loop counter.
    """
    problems = []
    for path in sorted(ROOT.rglob("*.afl")):
        code = strip_noise(path.read_text(encoding="utf-8", errors="replace"))
        rel = path.relative_to(ROOT).as_posix()
        seen = set()

        def report(name, line, why):
            if (name.lower(), line) in seen:
                return
            seen.add((name.lower(), line))
            problems.append(
                "%s:%d  '%s' is AmiBroker's built-in %s array; %s"
                % (rel, line, name, name.upper(), why)
            )

        # a parameter or loop counter named after a price array
        for m in re.finditer(r"\b(?:function|procedure)\s+\w+\s*\(([^)]*)\)", code, re.I):
            line = code[: m.start()].count("\n") + 1
            for p in m.group(1).split(","):
                p = p.strip()
                if p.lower() in PRICE_ARRAYS:
                    report(p, line, "using it as a parameter overwrites that array")
        for m in re.finditer(r"\bfor\s*\(\s*([A-Za-z_]\w*)\s*=", code, re.I):
            if m.group(1).lower() in PRICE_ARRAYS:
                report(m.group(1), code[: m.start()].count("\n") + 1,
                       "using it as a loop counter overwrites that array")

        # assignment whose right-hand side is text
        for m in re.finditer(r"(?:^|[;{}])\s*([A-Za-z_]\w*)\s*=(?!=)([^;]*)", code, re.M):
            name, rhs = m.group(1), m.group(2).strip()
            if name.lower() not in PRICE_ARRAYS:
                continue
            fn = re.match(r"([A-Za-z_]\w*)\s*\(", rhs)
            is_text = rhs.startswith('""') or (fn and fn.group(1).lower() in STRING_FUNCS)
            if is_text:
                # Line of the NAME, not of the match: the pattern anchors on the
                # preceding ';' or '{', which is usually on the line before.
                report(name, code[: m.start(1)].count("\n") + 1,
                       "assigning a string to it fails at run time")
    return problems


def main():
    reserved = load_reserved()
    print("checking %s against %d built-in AFL names" % (ROOT.name, len(reserved)))

    problems = (check_reserved(reserved) + check_define_before_use(reserved)
                + check_return_placement() + check_price_arrays())
    print()
    if problems:
        for p in problems:
            print("  %s" % p)
        print()
        print("%d problem(s). Each of these stops the formula from loading, or "
              "from running once it has loaded." % len(problems))
        return 1

    print("clean -- no reserved-name collisions, every call follows its definition, "
          "every return is the last statement of its function, and no built-in "
          "price array is used as a variable.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
