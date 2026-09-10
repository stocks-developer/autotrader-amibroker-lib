' Executes one AFL formula in real AmiBroker via OLE automation.
'
' Usage: cscript //nologo run-formula.vbs <absolute-afl-path>
'
' VBScript, not PowerShell, on purpose: PowerShell's late binding against
' AmiBroker's IDispatch returns blank for every property (measured on 6.93),
' while VBScript reads them correctly. AmiBroker's own docs automate this way.
'
' Uses the LEGACY Analysis object, also on purpose. Broker.chm (objects.html) is
' the authority and says:
'   Analysis    -> Sub Explore(), Sub Scan(), Function LoadFormula(name).
'                  There is NO Run() - calling it returns error 438.
'   AnalysisDoc -> Function Run(Action), but the only way to GET one is
'                  AnalysisDocs.Open(<file>.apx). There is no AnalysisDocs.New(),
'                  and handing Open() a plain .afl pops "Failed to open file ...
'                  incorrect format" AND freezes every later OLE call behind that
'                  modal.
'
' Explore() runs the formula top to bottom, so a parse failure never reaches the
' marker line at the end of the test formula.

Option Explicit
Dim AB, AA, formula, args

Set args = WScript.Arguments
If args.Count < 1 Then
    WScript.Echo "HARNESS-ERROR: no formula path given"
    WScript.Quit 2
End If
formula = args(0)

On Error Resume Next
Set AB = CreateObject("Broker.Application")
If Err.Number <> 0 Then
    WScript.Echo "HARNESS-ERROR: CreateObject failed: " & Err.Number & " " & Err.Description
    WScript.Quit 3
End If
On Error GoTo 0

WScript.Echo "version  = " & AB.Version
WScript.Echo "database = " & AB.DatabasePath
WScript.Echo "formula  = " & formula

Set AA = AB.Analysis

On Error Resume Next
If Not AA.LoadFormula(formula) Then
    WScript.Echo "HARNESS-ERROR: LoadFormula returned False"
    WScript.Quit 5
End If
If Err.Number <> 0 Then
    WScript.Echo "HARNESS-ERROR: LoadFormula raised: " & Err.Number & " " & Err.Description
    WScript.Quit 5
End If
On Error GoTo 0
WScript.Echo "LoadFormula ok"

' One symbol, a short range: we are testing whether the code RUNS, not
' measuring anything, so keep it fast.
AA.ApplyTo   = 1     ' current symbol
AA.RangeMode = 1     ' n last quotations
AA.RangeN    = 20

On Error Resume Next
AA.Explore
If Err.Number <> 0 Then
    WScript.Echo "HARNESS-ERROR: Explore raised: " & Err.Number & " " & Err.Description
    WScript.Quit 6
End If
On Error GoTo 0

WScript.Echo "Explore returned"
WScript.Quit 0
