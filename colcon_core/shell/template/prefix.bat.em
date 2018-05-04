:: generated from colcon_core/shell/template/prefix.bat.em
@@echo off

:: This script extends the environment with all packages contained in this
:: prefix path.

:: add this prefix to the COLCON_PREFIX_PATH
call:_colcon_prefix_bat_prepend_unique_value COLCON_PREFIX_PATH "%%~dp0"
@[if pkg_names]@

:: source packages
@[  for pkg_name in pkg_names]@
call:_colcon_prefix_bat_call_script "%%~dp0@('' if merge_install else (pkg_name + '\\'))share\@(pkg_name)\@(package_script_no_ext).bat"
@[  end for]@
@[end if]@

goto:eof


:: function to prepend a value to a variable
:: which uses semicolons as separators
:: duplicates as well as trailing separators are avoided
:: first argument: the name of the result variable
:: second argument: the value to be prepended
:_colcon_prefix_bat_prepend_unique_value
  setlocal enabledelayedexpansion
  :: arguments
  set "listname=%~1"
  set "value=%~2"

  :: get values from variable
  set "values=!%listname%!"
  :: start with the new value
  set "all_values=%value%"
  :: skip loop if values is empty
  if "%values%" NEQ "" (
    :: iterate over existing values in the variable
    for %%v in ("%values:;=";"%") do (
      :: ignore empty strings
      if "%%~v" NEQ "" (
        :: ignore duplicates of value
        if "%%~v" NEQ "%value%" (
          :: keep non-duplicate values
          set "all_values=!all_values!;%%~v"
        )
      )
    )
  )
  :: set result variable in parent scope
  endlocal & (
    set "%~1=%all_values%"
  )
goto:eof


:: call the specified batch file and output the name when tracing is requested
:: first argument: the batch file
:_colcon_prefix_bat_call_script
  if exist "%~1" (
    if "%COLCON_TRACE%" NEQ "" echo call "%~1"
    call "%~1%"
  ) else (
    echo not found: "%~1" 1>&2
  )
goto:eof
