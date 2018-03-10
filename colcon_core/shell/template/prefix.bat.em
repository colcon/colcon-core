:: generated from colcon_core/shell/template/prefix.bat.em
@@echo off

@[for pkg_name in pkg_names]@
@{
pkg_prefix = '%%~dp0'
if not merge_install:
    pkg_prefix += pkg_name + '/'
}@
call:call_file "@(pkg_prefix)share/@(pkg_name)/package.bat
@[end for]@

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
