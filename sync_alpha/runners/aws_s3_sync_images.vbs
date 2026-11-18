Set fso = CreateObject("Scripting.FileSystemObject")
Set WshShell = CreateObject("WScript.Shell")
batPath = fso.GetParentFolderName(WScript.ScriptFullName) & "\aws_s3_sync_images.bat"
WshShell.Run Chr(34) & batPath & Chr(34), 0
Set WshShell = Nothing
