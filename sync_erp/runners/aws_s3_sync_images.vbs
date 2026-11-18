Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
currentDir = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.Run chr(34) & currentDir & "\aws_s3_sync_images.bat" & chr(34), 0
Set WshShell = Nothing

