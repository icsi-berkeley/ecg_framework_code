#!/usr/bin/env python
######################################################################
#
# File: speechagent.py
#
# Initial Version: Jun 1, 2016 Adam Janin
#
# Record audio and call Kaldi to do speech recogntion. Package
# resulting one-best text as as an ntuple, and sends it to the UI
# agent.
#
# Only tested in python2.7, but it should work in python3.
#
# Currently hardwired to talk to "AgentUI", to name yourself
# "SpeechAgent", and to call Kaldi in a particular way to get text.
#
# The program "rec" (from the sox package) must be on your path.
# The program "online2-wav-nnet2-latgen-faster" (from the kaldi
# package) must be on your path.
#
# Various ASR model files must exist in the directory specified
# by -asr. See github wiki for instructions.
#
# The way Kaldi is called is very hacky. See comments below and
# the wiki for details. 
#
# Note: If it seems to hang after recording the audio, it's probably
# a problem with Kaldi. Currently, there's very little error checking
# on Kaldi's output. Search for "readline" in KaldiASR.__next__() for
# where it's probably blocking.
#

from __future__ import print_function

from six.moves import input
import six

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

from nluas.core_agent import CoreAgent

VERSION = 0.1

class SpeechAgent(CoreAgent):
    def __init__(self, args):
        CoreAgent.__init__(self, args)
        self.ui_destination = "%s_%s"%(self.federation, "AgentUI")
        self.transport.subscribe(self.ui_destination, self.callback)
    # end __init__()
# end class SpeechAgent


#
# Details on KaldiASR:
#
# Due to details in the Kaldi code, you need to repeatedly feed input
# to the spk2utt specifier, not the wave specifier. Each utterance
# needs a unique ID. Since the mapping from utterance to wave file
# is read in toto, the code can only run for a fixed number of
# utterances. When that number is reached, KaldiASR will restart.
#
# Once Kaldi is started, this program feeds it likes like:
#
# spk3 utt3
#
# When it receives a line like the above, it'll perform ASR on the
# wavefile associated with "utt3". In KaldiASR, this will be a
# file called input#.wav in a temporary directory. So to get the whole
# thing to work, record audio to input#.wav, then write "spk# utt#" to
# stdin of Kaldi, then read stdout of Kaldi looking for "utt#".
#
# For now, we just ignore the lattices and use the log file to extract
# the one-best.
#
# Huge amounts of stuff are hard coded in KaldiASR. Should probably
# switch to arguments of some sort.
#
# This is all pretty hacky, but I want to avoid forking the Kaldi
# decoder if I can.

class KaldiASR(six.Iterator):
    '''Start up a Kaldi recognizer as an iterator. Return the one-best each time next() is called. Stop when user presses q or an error occurs.'''

    def __init__(self, asrdir='/t/janin/ecg/asr'):

        # Path to where ASR models and other required files are stored.
        self.asrdir = asrdir

        # Make sure required files exist.
        for f in ('HCLG.fst', 'final.mdl', 'mfcc.conf', 'online_nnet2_decoding.conf', 'words.txt'):
            if not os.path.exists(os.path.join(asrdir, f)):
                raise Exception('speechagent: Unable to locate file "%s" in asr directory "%s".\n'%(f, asrdir))

        # Unique uttid
        self.uttid = 0

        # Where to store temporary files
        self.tmpdir = tempfile.mkdtemp(prefix='speechagent.')
        
        # Command to perform speech recognition. See comments above
        # for details on how this works. Quoting is tricky...
        self.kaldicmd = 'online2-wav-nnet2-latgen-faster --print-args=false --online=false --do-endpointing=false --config=%s/online_nnet2_decoding.conf --max-active=7000 --beam=15.0 --lattice-beam=6.0 --acoustic-scale=0.1 --word-symbol-table=%s/words.txt %s/final.mdl %s/HCLG.fst ark:- "scp:for i in {0..9999}; do printf \'utt%%d %s/input%%d.wav\\n\' \$i \$i; done|" ark:/dev/null'%(self.asrdir, self.asrdir, self.asrdir, self.asrdir, self.tmpdir)

        # Command to record audio file. This uses sox, records until
        # it hears a run of silence, and also removes silences at the
        # start end.
        #
        # Note that %s will be replaced later with the path to
        # the audio file. If you want %'s literally in the cmd,
        # they need to be replaced with %% so that the later python
        # format command doesn't interpret them as arguments.
        self.reccmd = 'rec -V0 -c 1 -b 16 -r 16k -q %s silence 1 0.0 0%% 1 2.0 0.9%%'
        # The running kaldi process. Set in start_kaldi()
        self.kaldiproc = None

        self.start_kaldi()
    # end __init__()

    def start_kaldi(self):
        '''Start or restart the kaldi process.'''
        self.uttid = 0
        if self.kaldiproc is not None:
            self.kaldiproc.terminate()

        self.kaldiproc = subprocess.Popen(self.kaldicmd, bufsize=1, shell=True, universal_newlines=True, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    # end start_kaldi()

    def __del__(self):
        '''When iterator goes out of scope, clean temporary directory and stop kaldi process.'''
        shutil.rmtree(self.tmpdir)
        if self.kaldiproc is not None:
            self.kaldiproc.terminate()

    def __iter__(self):
        return self

    def __next__(self):
        '''Call "rec" to record a new audio file, then call Kaldi to do ASR on it. Return the one-best transcription.'''
        
        # Restart if uttid is too high. Should match the for loop in self.kaldicmd.
        if self.uttid >= 9999:
            self.start_kaldi()

        print("Press Enter to record (or q to quit)")
        if (input() == 'q'):
            raise StopIteration()

        print("Recording")
        # Record the audio to input.wav
        audiopath = "%s/input%d.wav"%(self.tmpdir, self.uttid)
        subprocess.check_call(self.reccmd%(audiopath), shell=True)

        print("Running speech recognition")
        # Send string to kaldi that'll cause it to do ASR.
        self.kaldiproc.stdin.write('spkr%d utt%d\n'%(self.uttid, self.uttid))
        self.kaldiproc.stdin.flush()
        
        # Kaldi should only output the transcript and a log message.
        # Note that readline() will block waiting for Kaldi.
        # We should probably do timeouts and more error checking
        # here.

        while True:
            line = self.kaldiproc.stderr.readline()
            print(line)
            # If the above is blocking, it means kaldi
            # never output the expected output line.
            # To debug, uncomment the following line:
            #print('speechagent debug:\n',line)

            # Check for a line starting with utt# and return it.
            # Other lines are silently ignored.
            m = re.match('utt%d (.*)$'%(self.uttid), line)
            if m is not None:
                os.remove(audiopath)
                self.uttid += 1
                return m.group(1).strip()
            elif not re.match("\s*$", line) and not re.match('LOG \(online2-wav-nnet2-latgen-faster:main\(\):online2-wav-nnet2-latgen-faster\.cc.*Decoded utterance utt', line):
                sys.stderr.write('Unexpected line from Kaldi:\n'+line)
    # end __next__()
#end class KaldiASR        

def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('-asr', required=True, help='Path to speech recognition model files.')
    args = parser.parse_args(argv[1:])

    speechagent = SpeechAgent(['SpeechAgent'])

    for asrresult in KaldiASR(args.asr):
        if asrresult != "":
            print("Heard:", asrresult, "\n")
            ntuple = {'type': 'speech', 'text': asrresult}
            speechagent.transport.send(speechagent.ui_destination, ntuple)
        else:
            print("Speech recognition failed")
    speechagent.transport.quit_federation()
# end main()


if __name__ == "__main__":
    main(sys.argv)
