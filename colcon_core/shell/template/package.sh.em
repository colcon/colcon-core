# generated from colcon_core/shell/template/package.sh.em
@[if hooks]@

# since a plain shell script can't determine its own path when being sourced
# either use the provided COLCON_CURRENT_PREFIX
# or fall back to the destination set at build time
: ${COLCON_CURRENT_PREFIX:=@(prefix_path)}


# function to prepend a value to a variable
# which uses colons as separators
# duplicates as well as trailing separators are avoided
# first argument: the name of the result variable
# second argument: the value to be prepended
colcon_prepend_unique_value() {
  # arguments
  _listname="$1"
  _value="$2"

  # get values from variable
  eval _values=\"\$$_listname\"
  # backup the field separator
  _colcon_prepend_unique_value_IFS=$IFS
  IFS=":"
  # while this file should only consider plain shell
  # this is the easiest way to reuse the plain shell logic for zsh
  if [ "$COLCON_SHELL" = "zsh" ]; then
    colcon_zsh_to_array _values
  fi
  # start with the new value
  _all_values="$_value"
  # iterate over existing values in the variable
  for _item in $_values; do
    # ignore empty strings
    if [ -z "$_item" ]; then
      continue
    fi
    # ignore duplicates of _value
    if [ "$_item" = "$_value" ]; then
      continue
    fi
    # keep non-duplicate values
    _all_values="$_all_values:$_item"
  done
  unset _item
  # restore the field separator
  IFS=$_colcon_prepend_unique_value_IFS
  unset _colcon_prepend_unique_value_IFS
  # export the updated variable
  eval export $_listname=\"$_all_values\"
  unset _all_values
  unset _values

  unset _value
  unset _listname
}


# function to source another script with conditional trace output
# first argument: the name of the script file
# additional arguments: arguments to the script
colcon_package_source_shell_script() {
  # arguments
  _colcon_package_source_shell_script="$1"

  # source script with conditional trace output
  if [ -f "$_colcon_package_source_shell_script" ]; then
    if [ -n "$COLCON_TRACE" ]; then
      echo ". \"$_colcon_package_source_shell_script\""
    fi
    . $@@
  else
    if [ -n "$COLCON_TRACE" ]; then
      echo "not found: \"$_colcon_package_source_shell_script\""
    fi
  fi

  unset _colcon_package_source_shell_script
}


@[end if]@
@[for hook in hooks]@
colcon_package_source_shell_script "$COLCON_CURRENT_PREFIX/@(hook[0])"@
@[  for hook_arg in hook[1]]@
 @(hook_arg)@
@[  end for]
@[end for]@
@[if hooks]@

unset colcon_package_source_shell_script
unset colcon_prepend_unique_value
unset COLCON_CURRENT_PREFIX
@[end if]@
