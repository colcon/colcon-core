:: generated from colcon_core/shell/template/command_prefix.bat.em
@@echo off

@[for pkg_name, pkg_install_base in dependencies.items()]@
@{
import os
pkg_script = os.path.join(pkg_install_base, 'share', pkg_name, 'package.bat')
}@
call:call_file "@(pkg_script)"

@[end for]@
if %ERRORLEVEL% NEQ 0 exit /b %ERRORLEVEL%

goto:eof


:: call the specified batch file and output the name when tracing is requested
:: first argument: the batch file
:call_file
  if exist "%~1" (
    if "%COLCON_TRACE%" NEQ "" echo call "%~1"
    call "%~1%"
  ) else (
    if "%COLCON_TRACE%" NEQ "" echo not found: "%~1"
  )
goto:eof
