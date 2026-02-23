:: generated from colcon_core/shell/template/command_prefix.bat.em
@{
import os
from colcon_core.dependency_descriptor import DependencyDescriptor
}@
@@echo off
@[for dep, pkg_install_base in dependencies.items()]@
@{
pkg_name = dep.package_name if isinstance(dep, DependencyDescriptor) else dep
pkg_script = os.path.join(pkg_install_base, 'share', pkg_name, 'package.bat')
}@
call "@(pkg_script)"
@[end for]@
