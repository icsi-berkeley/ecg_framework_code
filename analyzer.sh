#!/bin/bash
export ECG_FED=FED2
export JYTHONPATH=build/compling.core.jar:src/main/nluas/language
jython -J-Xmx2g -m analyzer ../ecg_grammars/research.prefs #&

#jython -J-Xmx2g -i src/main/nluas/language/analyzer.py ../ecg_grammars/research.prefs #&

#jython -i src/main/nluas/language/analyzer.py ../ecg_grammars/research.prefs #&
#python3 src/main/nluas/language/user_agent.py AgentUI 
