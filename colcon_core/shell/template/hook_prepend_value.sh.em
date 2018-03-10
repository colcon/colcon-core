# generated from colcon_core/shell/template/hook_prepend_value.sh.em

@{
value = '$COLCON_CURRENT_PREFIX'
if subdirectory:
    value += '/' + subdirectory
}@
colcon_prepend_unique_value @(name) "@(value)"
