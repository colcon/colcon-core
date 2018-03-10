# generated from colcon_core/shell/template/prefix.sh.em
@[if pkg_names]@

# function to source another script with conditional trace output
# first argument: the name of the script file
colcon_prefix_source_shell_script() {
  # arguments
  _colcon_prefix_source_shell_script="$1"

  # source script with conditional trace output
  if [ -f "$_colcon_prefix_source_shell_script" ]; then
    if [ -n "$COLCON_TRACE" ]; then
      echo ". \"$_colcon_prefix_source_shell_script\""
    fi
    . "$_colcon_prefix_source_shell_script"
  else
    if [ -n "$COLCON_TRACE" ]; then
      echo "not found: \"$_colcon_prefix_source_shell_script\""
    fi
  fi

  unset _colcon_prefix_source_shell_script
}


@[end if]@
@[for i, pkg_name in enumerate(pkg_names)]@
@{
pkg_prefix = prefix_path
if not merge_install:
    pkg_prefix /= pkg_name
}@
@[  if i == 0]@
# since a plain shell script can't determine its own path when being sourced
# it uses the destination set at build time
@[  end if]@
COLCON_CURRENT_PREFIX=@(pkg_prefix)
colcon_prefix_source_shell_script "$COLCON_CURRENT_PREFIX/share/@(pkg_name)/package.sh"

@[end for]@
@[if pkg_names]@
unset COLCON_CURRENT_PREFIX
unset colcon_prefix_source_shell_script
@[end if]@
