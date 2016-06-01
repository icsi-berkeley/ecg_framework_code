#!/bin/bash
# A user should set PYTHONPATH in their .bash_profile
#export PYTHONPATH=/Users/seantrott/icsi/nlu-core/src/main
export ECG_FED=FED1
python3 src/main/nluas/app/core_solver.py ProblemSolver &
python3 src/main/nluas/language/user_agent.py AgentUI 
#sh ui_setup.sh

