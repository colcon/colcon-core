import sys
sys.real_prefix = sys.prefix
sys.prefix = sys.exec_prefix = @repr(site_prefix)
