# framework-code
Core Framework code for NLU system, can be extended for different tasks.

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

See [Scripts](https://github.com/icsi-berkeley/framework_code/wiki/Scripts) for information on running the system.

**NOTE**: You’ll also need to set your PYTHONPATH in your bash_profile to point to {dir_path}/framework-code/src/main. 