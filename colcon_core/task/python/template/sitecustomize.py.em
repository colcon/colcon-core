import sys
if sys.prefix == sys.base_prefix:
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = @repr(site_prefix)
