# generated from colcon_core/shell/template/prefix.sh.em

# This script extends the environment with all packages contained in this
# prefix path.

# since a plain shell script can't determine its own path when being sourced
# either use the provided COLCON_CURRENT_PREFIX
# or fall back to the build time prefix (if it exists)
_colcon_prefix_sh_COLCON_CURRENT_PREFIX="@(prefix_path)"
if [ -z "$COLCON_CURRENT_PREFIX" ]; then
  if [ ! -d "$_colcon_prefix_sh_COLCON_CURRENT_PREFIX" ]; then
    echo "The build time path \"$_colcon_prefix_sh_COLCON_CURRENT_PREFIX\" doesn't exist. Either source a script for a different shell or set the environment variable \"COLCON_CURRENT_PREFIX\" explicitly." 1>&2
    unset _colcon_prefix_sh_COLCON_CURRENT_PREFIX
    return 1
  fi
else
  _colcon_prefix_sh_COLCON_CURRENT_PREFIX="$COLCON_CURRENT_PREFIX"
fi

# function to prepend a value to a variable
# which uses colons as separators
# duplicates as well as trailing separators are avoided
# first argument: the name of the result variable
# second argument: the value to be prepended
_colcon_prefix_sh_prepend_unique_value() {
  # arguments
  _listname="$1"
  _value="$2"

  # get values from variable
  eval _values=\"\$$_listname\"
  # backup the field separator
  _colcon_prefix_sh_prepend_unique_value_IFS="$IFS"
  IFS=":"
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
  IFS="$_colcon_prefix_sh_prepend_unique_value_IFS"
  unset _colcon_prefix_sh_prepend_unique_value_IFS
  # export the updated variable
  eval export $_listname=\"$_all_values\"
  unset _all_values
  unset _values

  unset _value
  unset _listname
}

# add this prefix to the COLCON_PREFIX_PATH
_colcon_prefix_sh_prepend_unique_value COLCON_PREFIX_PATH "$_colcon_prefix_sh_COLCON_CURRENT_PREFIX"
unset _colcon_prefix_sh_prepend_unique_value

# use the Python executable known at configure time
_colcon_python_executable="@(python_executable)"
# allow overriding it with a custom location
if [ -n "$COLCON_PYTHON_EXECUTABLE" ]; then
  _colcon_python_executable="$COLCON_PYTHON_EXECUTABLE"
fi
# if the Python executable doesn't exist try another fall back
if [ ! -f "$_colcon_python_executable" ]; then
  if /usr/bin/env python3 --version > /dev/null
  then
    _colcon_python_executable=`/usr/bin/env python3 -c "import sys; print(sys.executable)"`
  else
    echo "error: unable to find fallback python3 executable"
    return 1
  fi
fi

# function to source another script with conditional trace output
# first argument: the path of the script
_colcon_prefix_sh_source_script() {
  if [ -f "$1" ]; then
    if [ -n "$COLCON_TRACE" ]; then
      echo ". \"$1\""
    fi
    . "$1"
  else
    echo "not found: \"$1\"" 1>&2
  fi
}

# get all packages in topological order
_colcon_ordered_packages="$(@
$_colcon_python_executable "$_colcon_prefix_sh_COLCON_CURRENT_PREFIX/_local_setup_util.py"@
@[if merge_install]@
 --merged-install@
@[end if]@
)"
unset _colcon_python_executable

# source package specific scripts in topological order
for _colcon_package_name in $_colcon_ordered_packages; do
  # setting COLCON_CURRENT_PREFIX avoids relying on the build time prefix of the sourced script
  COLCON_CURRENT_PREFIX="${_colcon_prefix_sh_COLCON_CURRENT_PREFIX}@('' if merge_install else '/${_colcon_package_name}')"
  _colcon_prefix_sh_source_script "$COLCON_CURRENT_PREFIX/share/${_colcon_package_name}/@(package_script_no_ext).sh"
done
unset _colcon_package_name
unset _colcon_prefix_sh_source_script
unset _colcon_ordered_packages

unset COLCON_CURRENT_PREFIX
unset _colcon_prefix_sh_COLCON_CURRENT_PREFIX
