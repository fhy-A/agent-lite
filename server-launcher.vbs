Set shell = CreateObject("WScript.Shell")
shell.CurrentDirectory = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
' pythonw.exe runs without a console window (included with every Python on Windows)
On Error Resume Next
shell.Run "pythonw server.py", 0, False
If Err.Number <> 0 Then
  Err.Clear
  shell.Run "python server.py", 0, False
End If
