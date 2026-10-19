Set oShell = CreateObject("WScript.Shell")
oShell.CurrentDirectory = "C:\Users\spxth71637\Desktop\OB Dashboard"
Set oExec = oShell.Exec("cmd /c netstat -ano | findstr :5000")
strOut = oExec.StdOut.ReadAll()
If InStr(strOut, "LISTENING") = 0 Then
    oShell.Run "py app.py", 0, False
End If
