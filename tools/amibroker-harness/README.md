# Running the library in real AmiBroker

`../check-afl.py` catches the AFL parse-time rules we know about, in a second, without
AmiBroker. It is still only a model of AmiBroker, and a mistake it does not model stops
the entire library from loading — every function, for every user, on the first run.

This harness runs the library in the real program, so that answer comes from AmiBroker
itself rather than from our model of it.

Use both. **`check-afl.py` tells you where. The harness tells you whether.**

## Setup

You need AmiBroker on Windows. The free 30-day trial from
[amibroker.com/download.html](https://www.amibroker.com/download.html) is enough — the
harness uses only OLE automation, which the trial supports.

If AmiBroker is not in `C:\Program Files\AmiBroker`, point the harness at it:

```
set SD_AMIBROKER_HOME=C:\Program Files\AmiBroker693
```

Install this library into that AmiBroker first, the same way a user would: copy
`Formulas\` over the AmiBroker `Formulas\` folder.

## Run it

```
powershell -ExecutionPolicy Bypass -File tools/amibroker-harness/run-test.ps1
```

It writes a small formula that does nothing but `#include <autotrader-http.afl>`, runs it
as an Exploration, and reports:

```
--- AFL errors: 0   marker: True   elapsed: 0s ---
PASS - the library loaded and ran in real AmiBroker with no errors.
```

On a failure it quotes AmiBroker's own message, with the offending source line:

```
FAIL - reached the end but AmiBroker raised 5 AFL error(s)
FIRST AFL ERROR (the real defect - the ones after it are fallout):
    if(fetchedAt > 0 AND DateTimeDiff(Now(5), fetchedAt) < atTtlFor(dataset)) { r --^
    Error 30. Syntax error, unexpected RETURN
```

Pass `-Formula <path.afl>` to run something else instead of the self-test.

## Keeping the harness honest

```
bash tools/amibroker-harness/three-point.sh
```

Replays two earlier revisions that each contain a known parse error, and checks that
master still passes. Expect `FAIL, FAIL, PASS`.

**Run this after any change to the harness.** A harness that has quietly stopped
detecting failure looks exactly like a harness reporting success — which is not
hypothetical. Once the dialog watcher started dismissing errors, AmiBroker carried on
past the broken code, reached the end of the formula, and *both* known-bad refs turned
green. This script is what caught it.

Note that it replaces `Formulas\Include` in your AmiBroker install with each revision in
turn (restoring master at the end), so do not point it at an AmiBroker you use for real
work.

## How it works, and why it is shaped this way

Every one of these was learned by getting it wrong first.

**Use the legacy `Analysis` OLE object.** `Broker.chm` is the authority. `Analysis` has
`Explore()`, `Scan()` and `LoadFormula()` but **no `Run()`** — calling it returns error
438. `Run()` belongs to `AnalysisDoc`, and the only way to obtain one is
`AnalysisDocs.Open()` on a saved `.apx` project. There is no `AnalysisDocs.New()`, and
handing `Open()` a plain `.afl` raises *"Failed to open file … incorrect format"* and
then freezes every later OLE call behind that modal.

**Drive COM from VBScript, not PowerShell.** PowerShell's late binding against
AmiBroker's IDispatch returns blank for every property; VBScript reads them correctly.

**A modal dialog blocks all OLE.** AmiBroker must be dialog-free before the first COM
call, and the watcher has to run *concurrently* with the formula — an error modal blocks
`Explore()`, so a watcher that ran afterwards would wait forever.

**The error dialog is captioned `AFL Error`** — not `AmiBroker`, not blank. Its message
lives in an `Edit` control that answers only `WM_GETTEXT`; `GetWindowText` returns empty
across the process boundary. Its button is `Close` with control id 2, not `IDOK`, so a
blanket IDOK post leaves it up and everything stays frozen.

**PASS requires the marker *and* zero AFL errors.** See the warning above.

**Restart AmiBroker between revisions.** It caches compiled includes, so without a
restart a later run can silently execute an earlier revision's code.

**Launch AmiBroker with its install folder as the working directory.** It resolves
`Formulas\...` relative to the current directory.

## What it does not cover

The harness proves the library **loads and runs**. It does not place orders, and it
cannot prove behaviour on an AmiBroker version other than the one you run it against.

## tests/

`run-test.ps1` on its own answers *does the library load*. The formulas here
answer *does it behave*, by seeding the library's own cache instead of asking
the server, so they make no request, need no API key, and place no orders.

```
powershell -ExecutionPolicy Bypass -File tools/amibroker-harness/run-test.ps1 `
    -Formula <repo>/tools/amibroker-harness/tests/at-empty-then-filled.afl
```

Each writes its checks into `out/marker.txt`, so that one file carries both
"execution reached the end" and what was actually checked. Read it after the
run; the last line is `SELFTEST-RESULT: PASS n of n`.

> AFL cannot read an environment variable, so each test spells out the absolute
> path it writes to. Edit that line if this repository lives somewhere else.

**Static variables outlive the formula that set them.** A test that seeds the
cache must clear its own keys first, or the second run reads what the first one
left and passes on state it never created. Every test here starts with a
`StaticVarRemove` of its own prefix for that reason.

| Test | What it pins down |
|---|---|
| `at-empty-then-filled.afl` | A dataset that is empty when first read and has rows later. Column names must resolve on the second read — the case that decides whether the first order of the day can be read back. |
