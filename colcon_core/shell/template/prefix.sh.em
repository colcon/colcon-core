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
@[if pkg_names]@

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

# source package specific scripts
@[  for pkg_name in pkg_names]@
# setting COLCON_CURRENT_PREFIX avoids relying on the build time prefix of the sourced script
COLCON_CURRENT_PREFIX="${_colcon_prefix_sh_COLCON_CURRENT_PREFIX}@('' if merge_install else ('/' + pkg_name))"
_colcon_prefix_sh_source_script "$COLCON_CURRENT_PREFIX/share/@(pkg_name)/@(package_script_no_ext).sh"

@[  end for]@
unset _colcon_prefix_sh_source_script
@[end if]@

unset COLCON_CURRENT_PREFIX
unset _colcon_prefix_sh_COLCON_CURRENT_PREFIX
