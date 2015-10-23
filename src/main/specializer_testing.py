from nluas.language.core_specializer import *
from nluas.language.analyzer_proxy import *
a = Analyzer("http://localhost:8090")
c = CoreSpecializer(a)

from nluas.trivial_specializer import *
t = TrivialSpecializer(a)

s = a.parse("the box is red.")