# framework-code
Core Framework code for NLU system, can be extended for different tasks.

* General description of original system: https://www.icsi.berkeley.edu/pubs/ai/naturallanguage15.pdf
* Extension/Implementation for multi-agent collaboration: ftp://ftp.icsi.berkeley.edu/pub/feldman/AI-HRI.pdf

See the [Wiki](https://github.com/icsi-berkeley/framework_code/wiki) for more detailed information on this code.

System requirements:

* PyEnchant: http://pythonhosted.org/pyenchant/ 
    * Used for a spell-check module (src/main/nluas/language/spell_checker.py), which is currently inactive
* Pyre, port of Lyre: uncompress ecg-package.tar.gaz and follow the instructions in INSTALL
    * Used for n-tuple Transport (src/main/nluas/Transport.py)
* Jython: http://www.jython.org/
    * Used to run ECG analyzer JAR (build/compling.core.jar) via Python (src/main/nluas/language/analyzer.py)
* ecg-grammars: https://github.com/icsi-berkeley/ecg-grammars
    * Used to load ECG Analyzer with a grammar to parse input 
* six: https://pypi.python.org/pypi/six
    * Used to make code compatible with python2 and python3

Running the system:

* analyzer.sh: This will run the grammars/Analyzer on an RPC server. If you’d like this to run as a background process, you can modify the “jython” command to add a “&” at the end. By default, it runs the “research” grammar from ecg-grammars.
* ntuples.sh: This will run the Specializer (as a separate process/Terminal tab). This will open up a prompt, in which you can enter sentences and view the resulting n-tuples, printed in a cleaner visualization.
* ui.sh: This will run both the grammars/Analyzer and the Agent-UI in one tab. 
* setup.sh: this will run the Problem Solver as a background process. In the “core” framework system, the problem solver simply prints out n-tuples. 
* tests.sh: This runs a suite of sentences and makes sure they match ‘gold standard’ n-tuples. Note that analyzer.sh must already be running.


**NOTE**: You’ll also need to set your PYTHONPATH in your bash_profile to point to {dir_path}/framework-code/src/main. 