import afl, os, sys
sys.path.append("../")
import ekcc

afl.init()

try:
    ekcc.fuzztest(sys.stdin.read())
except NameError as e:
    raise NameError()
except:
    pass

os._exit(0)