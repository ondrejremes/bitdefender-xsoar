import builtins
import sys
import demistomock

builtins.demisto = demistomock
sys.modules['demisto'] = demistomock
