;NSIS Modern User Interface
;Basic Example Script
;Written by Joost Verburg

;--------------------------------
;Include Modern UI

  !include "MUI2.nsh"

;--------------------------------
;General

  ;Name and file
  Name "Ufit"
  OutFile "dist\ufit-install.exe"

  ;Default installation folder
  InstallDir "$PROGRAMFILES64\ufit"

  ;Get installation folder from registry if available
  InstallDirRegKey HKCU "Software\Ufit" ""

  ;Request application privileges for Windows Vista
  RequestExecutionLevel admin

  ;Compress with LZMA
  SetCompressor /SOLID lzma

;--------------------------------
;Variables

  Var StartMenuFolder

;--------------------------------
;Interface Settings

  !define MUI_ABORTWARNING

;--------------------------------
;Pages

;  !insertmacro MUI_PAGE_WELCOME
  !insertmacro MUI_PAGE_LICENSE "..\License.txt"
  !insertmacro MUI_PAGE_COMPONENTS
  !insertmacro MUI_PAGE_DIRECTORY

  ;Start Menu Folder Page Configuration
  !define MUI_STARTMENUPAGE_REGISTRY_ROOT "HKCU"
  !define MUI_STARTMENUPAGE_REGISTRY_KEY "Software\Ufit"
  !define MUI_STARTMENUPAGE_REGISTRY_VALUENAME "Ufit"
  !insertmacro MUI_PAGE_STARTMENU Application $StartMenuFolder

  !insertmacro MUI_PAGE_INSTFILES

  ;Finish page
  !define MUI_FINISHPAGE_TITLE "Installation is finished"
  !define MUI_FINISHPAGE_TEXT "Congratulations, Ufit was successfully installed on your system."
  !define MUI_FINISHPAGE_NOREBOOTSUPPORT
  !define MUI_FINISHPAGE_RUN "$INSTDIR\ufit.exe"
  !define MUI_FINISHPAGE_RUN_TEXT "Start Ufit"
  !insertmacro MUI_PAGE_FINISH

  !insertmacro MUI_UNPAGE_CONFIRM
  !insertmacro MUI_UNPAGE_INSTFILES

;--------------------------------
;Languages

  !insertmacro MUI_LANGUAGE "English"

;--------------------------------
;Installer Sections

Section "!Ufit Core files" SecMain

  SetOutPath "$INSTDIR"

  FILE /r dist\ufit\*

  ;Store installation folder
  WriteRegStr HKCU "Software\Ufit" "" $INSTDIR

  ;Create uninstaller
  WriteUninstaller "$INSTDIR\Uninstall.exe"

  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Ufit" "DisplayName" "Ufit"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Ufit" "UninstallString" "$INSTDIR\Uninstall.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Ufit" "InstallLocation" "$INSTDIR"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Ufit" "Publisher" "Georg Brandl"
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Ufit" "NoModify" 1
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Ufit" "NoRepair" 1

  !insertmacro MUI_STARTMENU_WRITE_BEGIN Application

    ;Create shortcuts
    CreateDirectory "$SMPROGRAMS\$StartMenuFolder"
    CreateShortcut "$SMPROGRAMS\$StartMenuFolder\Ufit.lnk" "$INSTDIR\ufit.exe"
    CreateShortcut "$SMPROGRAMS\$StartMenuFolder\Uninstall.lnk" "$INSTDIR\Uninstall.exe"

  !insertmacro MUI_STARTMENU_WRITE_END

SectionEnd

;--------------------------------
;Descriptions

  ;Language strings
  LangString DESC_SecMain ${LANG_ENGLISH} "Installs the Ufit graphical user interface."

  ;Assign language strings to sections
  !insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
    !insertmacro MUI_DESCRIPTION_TEXT ${SecMain} $(DESC_SecMain)
  !insertmacro MUI_FUNCTION_DESCRIPTION_END

;--------------------------------
;Uninstaller Section

Section "Uninstall"

  ;ADD YOUR OWN FILES HERE...

  Delete "$INSTDIR\Uninstall.exe"
  RMDir /r "$INSTDIR"

  Delete "$SMPROGRAMS\$StartMenuFolder\Uninstall.lnk"
  Delete "$SMPROGRAMS\$StartMenuFolder\Ufit.lnk"
  RMDir "$SMPROGRAMS\$StartMenuFolder"

  DeleteRegKey /ifempty HKCU "Software\Modern UI Test"
  DeleteRegValue HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Ufit" "DisplayName"
  DeleteRegValue HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Ufit" "UninstallString"
  DeleteRegValue HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Ufit" "InstallLocation"
  DeleteRegValue HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Ufit" "Publisher"
  DeleteRegValue HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Ufit" "NoModify"
  DeleteRegValue HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Ufit" "NoRepair"
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Ufit"

SectionEnd
