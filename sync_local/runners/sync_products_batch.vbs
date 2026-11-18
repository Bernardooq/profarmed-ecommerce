Set fso = CreateObject("Scripting.FileSystemObject")
Set WshShell = CreateObject("WScript.Shell")
batPath = fso.GetParentFolderName(WScript.ScriptFullName) & "\sync_products_batch.bat"
WshShell.Run Chr(34) & batPath & Chr(34), 0
Set WshShell = Nothing
