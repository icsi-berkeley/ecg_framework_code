#!/bin/bash
# USERS should set PYTHONPATH in their .bash_profile
#export PYTHONPATH={PATH_TO_ECG_FRAMEWORK_CODE}/src/main
#export PYTHONPATH=$PYTHONPATH:$(pwd)/src/main


# Sets ECG_FED variable to FED1 by default. This is used for the address for an agent, e.g. FED1_AgentUI
export ECG_FED=FED1
# Initializes core solver, runs as a background process.
python3 src/main/nluas/app/core_solver.py ProblemSolver &
# Initializes core UI-Agent, also runs as a background process.
python3 src/main/nluas/language/user_agent.py AgentUI &
# Initializes Text-Agent as a normal process, which prompts user for input.
python3 src/main/nluas/language/text_agent.py TextAgent

