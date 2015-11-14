# framework-code
Core Framework code for NLU system.

System requirements:

* PyEnchant: http://pythonhosted.org/pyenchant/
* Pyre, port of Lyre: uncompress ecg-package.tar.gaz and follow the instructions in INSTALL
* Jython: http://www.jython.org/

Running the system:

* analyzer.sh: This will run the grammars/Analyzer on an RPC server. If you’d like this to run as a background process, you can modify the “jython” command to add a “&” at the end. By default, it runs the “research” grammar from ecg-grammars.
* ntuples.sh: This will run the Specializer (as a separate process/Terminal tab). This will open up a prompt, in which you can enter sentences and view the resulting n-tuples, printed in a cleaner visualization.
* ui.sh: This will run both the grammars/Analyzer and the Agent-UI in one tab. 
* setup.sh: this will run the Problem Solver as a background process. In the “core” framework system, the problem solver simply prints out n-tuples. 


NOTE: You’ll also need to set your PYTHONPATH in your bash_profile to point to {dir_path}/framework-code/src/main. 