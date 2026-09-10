#!/usr/bin/env bash
#
# Control group for the harness itself.
#
# A harness that cannot reproduce a KNOWN failure proves nothing. Before you
# trust a green run - and after ANY change to the harness - replay two earlier
# revisions with known parse errors and check master still passes:
#
#   f9b546a  "status" used as an identifier    -> expect FAIL (Error 31)
#   c80d81b  return not last in its function   -> expect FAIL (Error 30)
#   master   both fixed                        -> expect PASS
#
# Anything other than FAIL,FAIL,PASS means the harness has stopped measuring
# what we think it does. That is not hypothetical: after the dialog watcher
# started dismissing errors, AmiBroker ran on past the broken code, reached the
# marker, and this script was the only thing that noticed both bad refs had
# turned green.
#
#   SD_AMIBROKER_HOME   AmiBroker folder (default C:/Program Files/AmiBroker)
#
# WARNING: this REPLACES Formulas/Include in your AmiBroker install with each
# ref in turn. It restores master at the end. Do not point it at an AmiBroker
# you use for real work.

set -u

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
AB="${SD_AMIBROKER_HOME:-/c/Program Files/AmiBroker}"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

if [ ! -f "$AB/Broker.exe" ]; then
    echo "No Broker.exe under [$AB]. Set SD_AMIBROKER_HOME."
    exit 2
fi

stage_ref() {
    local ref="$1"
    rm -rf "${STAGE:?}/x"; mkdir -p "$STAGE/x"
    # git archive never touches the working tree, so the repo stays as you left it.
    ( cd "$REPO" && git archive "$ref" Formulas ) | tar -x -C "$STAGE/x" || return 1
    [ -d "$STAGE/x/Formulas/Include" ] || { echo "stage failed for $ref"; return 1; }
    rm -rf "$AB/Formulas/Include"
    mkdir -p "$AB/Formulas/Include"
    cp -r "$STAGE/x/Formulas/Include/." "$AB/Formulas/Include/"
    echo "  staged $ref ($(ls "$AB/Formulas/Include" | wc -l) include files)"
}

run_one() {
    local ref="$1" label="$2" expect="$3"
    echo ""
    echo "=== $ref -- $label (expect $expect) ==="
    stage_ref "$ref" || return 1
    # AmiBroker caches compiled includes; without a restart a later run can
    # silently execute an earlier ref's code.
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$HERE/restart-ab.ps1" >/dev/null 2>&1
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$HERE/run-test.ps1" 2>&1 | sed 's/^/  /'
    local rc=${PIPESTATUS[0]}
    local got; got=$([ "$rc" -eq 0 ] && echo PASS || echo FAIL)
    RESULTS="$RESULTS\n  $ref  expected=$expect  got=$got  $([ "$got" = "$expect" ] && echo OK || echo '<-- WRONG')"
}

RESULTS=""
run_one f9b546a '"status" as an identifier'  FAIL
run_one c80d81b 'nested return'              FAIL
run_one master  'current master'             PASS

echo ""
echo "=== SUMMARY ==="
printf "$RESULTS\n"

echo ""
echo "restoring master into AmiBroker"
stage_ref master >/dev/null 2>&1 && echo "  done"

echo "$RESULTS" | grep -q 'WRONG' && { echo ""; echo "CONTROL GROUP FAILED - do not trust this harness until it is fixed."; exit 1; }
echo ""
echo "control group intact."
exit 0
