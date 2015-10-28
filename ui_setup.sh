#sh starter.sh &
export ECG_FED=FED2
export JYTHONPATH=build/compling.core.jar:src/main/nluas/language
jython -m analyzer ../grammars/compRobots.prefs #&
#jython -m analyzer ../grammars/compRobots.prefs


export PID=$!
#echo "Analyzer" $PID
#python3 src/main/nluas/language/user_agent.py AgentUI 
