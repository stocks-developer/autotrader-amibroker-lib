# Watches Broker.exe for modal dialogs, RECORDS their text, dismisses them.
#
# This is the harness's error channel. An AFL parse failure opens a dialog
# captioned "AFL Error" holding the offending source line, a caret, and the
# AmiBroker error code. While it is up,
# every OLE call blocks, so capturing and clearing it is what turns a 120s
# TIMEOUT into a fast FAIL with a diagnosis.
#
# Three things had to be right, each found the hard way:
#   1. The caption is "AFL Error", not "AmiBroker" and not blank. An earlier
#      filter accepted only the latter two and skipped the one that mattered.
#   2. The message sits in an Edit control and only WM_GETTEXT reads it;
#      GetWindowText returns empty across the process boundary.
#   3. Its button is "Close" with control id 2 (IDCANCEL), not IDOK, so a
#      blanket IDOK post does not dismiss it. Post the button's OWN id.
#
# AmiBroker's Automatic Analysis window is ALSO class #32770; closing it broke
# an earlier version. Only small, message-box-shaped dialogs are touched, and
# the DEMO nag's "Register" button is never clicked.

param(
    [int]$Seconds = 30,
    [string]$LogFile,
    [switch]$Once,
    [switch]$ReportOnly
)

if (-not $LogFile) { $LogFile = Join-Path $PSScriptRoot 'out\dialogs.log' }
$logDir = Split-Path $LogFile
if ($logDir -and -not (Test-Path $logDir)) { New-Item -ItemType Directory -Force -Path $logDir | Out-Null }

Add-Type @'
using System;
using System.Text;
using System.Collections.Generic;
using System.Runtime.InteropServices;
public class Dlg {
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc p, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr p, EnumProc c, IntPtr l);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern bool IsWindowEnabled(IntPtr h);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowTextW(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetClassNameW(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern IntPtr SendMessageW(IntPtr h, uint msg, IntPtr w, StringBuilder l);
  [DllImport("user32.dll")] public static extern int GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll")] public static extern bool PostMessageW(IntPtr h, uint msg, IntPtr w, IntPtr l);
  [DllImport("user32.dll")] public static extern int GetDlgCtrlID(IntPtr h);

  public static string Txt(IntPtr h){ var sb=new StringBuilder(8192); GetWindowTextW(h,sb,8192); return sb.ToString(); }
  public static string Cls(IntPtr h){ var sb=new StringBuilder(256);  GetClassNameW(h,sb,256);  return sb.ToString(); }
  public static string WmText(IntPtr h){ var sb=new StringBuilder(8192); SendMessageW(h, 0x000D, (IntPtr)8192, sb); return sb.ToString(); }

  public class Kid { public string Cls; public string Text; public string WmText; public int Id; public bool Enabled; }
  public static List<Kid> Kids(IntPtr dlg){
    var list = new List<Kid>();
    EnumChildWindows(dlg, delegate(IntPtr c, IntPtr l){
      list.Add(new Kid { Cls=Cls(c), Text=Txt(c), WmText=WmText(c), Id=GetDlgCtrlID(c), Enabled=IsWindowEnabled(c) });
      return true;
    }, IntPtr.Zero);
    return list;
  }

  public static List<IntPtr> VisibleDialogs(uint pid){
    var list = new List<IntPtr>();
    EnumWindows(delegate(IntPtr h, IntPtr l){
      uint p; GetWindowThreadProcessId(h, out p);
      if (p == pid && IsWindowVisible(h) && Cls(h) == "#32770") list.Add(h);
      return true;
    }, IntPtr.Zero);
    return list;
  }
}
'@

$WM_COMMAND = 0x0111

function Sweep {
    $proc = Get-Process Broker -ErrorAction SilentlyContinue
    if (-not $proc) { return 0 }
    $pid0 = [uint32]$proc[0].Id
    $dismissed = 0

    foreach ($h in [Dlg]::VisibleDialogs($pid0)) {
        $caption = [Dlg]::Txt($h)
        $kids    = [Dlg]::Kids($h)
        $buttons = @($kids | Where-Object { $_.Cls -eq 'Button' })

        # Message-box shaped: a handful of buttons and a known caption. The
        # Automatic Analysis window has ~30 buttons and its own caption.
        $isMsgBox = ($buttons.Count -le 4) -and
                    ($caption -eq '' -or $caption -eq 'AmiBroker' -or $caption -eq 'AFL Error')
        if (-not $isMsgBox) { continue }

        # The message may be in Static labels or in an Edit control; the Edit
        # only answers WM_GETTEXT.
        $parts = @()
        foreach ($k in $kids) {
            if ($k.Cls -eq 'Button') { continue }
            $t = if ($k.WmText) { $k.WmText } elseif ($k.Text) { $k.Text } else { '' }
            if ($t) { $parts += $t }
        }
        $body  = ($parts -join ' || ') -replace '\s+', ' '
        $btns  = ($buttons | ForEach-Object { $_.Text }) -join ','
        $stamp = (Get-Date).ToString('HH:mm:ss')
        $line  = "[$stamp] DIALOG caption=[$caption] buttons=[$btns]"
        Write-Host $line
        Add-Content -Path $LogFile -Value $line
        if ($body) {
            Write-Host "           text: $body"
            Add-Content -Path $LogFile -Value "           text: $body"
        }

        # Dismissing an AFL Error lets AmiBroker carry on and trip over the
        # wreckage of the first one, so a single real fault produces a cascade
        # of twenty follow-on dialogs. Only the FIRST is the actual defect -
        # keep it on its own so the verdict can quote it.
        if ($caption -eq 'AFL Error') {
            $firstFile = Join-Path (Split-Path $LogFile) 'first-error.txt'
            if (-not (Test-Path $firstFile)) { Set-Content -Path $firstFile -Value $body }
        }

        if ($ReportOnly) { continue }

        # Post the dismiss button's OWN control id. "AFL Error" closes with
        # id 2 (Close/IDCANCEL); a blanket IDOK leaves it up and everything
        # stays blocked. Never Register.
        $btn = $buttons | Where-Object { $_.Text -match '^&?(OK|Close)$' -and $_.Enabled } | Select-Object -First 1
        if ($btn) {
            [void][Dlg]::PostMessageW($h, $WM_COMMAND, [IntPtr]$btn.Id, [IntPtr]::Zero)
            Write-Host ("           -> dismissed via [{0}] id={1}" -f $btn.Text, $btn.Id)
            Add-Content -Path $LogFile -Value ("           -> dismissed via [{0}] id={1}" -f $btn.Text, $btn.Id)
            $dismissed++
        } else {
            Write-Host '           -> no enabled OK/Close button (left alone)'
            Add-Content -Path $LogFile -Value '           -> no enabled OK/Close button (left alone)'
        }
    }
    return $dismissed
}

if ($Once -or $ReportOnly) {
    $n = Sweep
    Write-Host "swept, dismissed=$n"
    exit 0
}

$deadline = (Get-Date).AddSeconds($Seconds)
$total = 0
while ((Get-Date) -lt $deadline) {
    $total += (Sweep)
    Start-Sleep -Milliseconds 400
}
Write-Host "watch finished, dismissed=$total"
