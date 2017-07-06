#!/usr/bin/env python

# Matthew J. Walker
# Created: 14 June 2017

import sys
import os
import pandas as pd
import threading

experiment_number_filename = 'experiment-number.txt'
script_path = os.path.dirname(__file__)
experiment_number_path = os.path.join(script_path, experiment_number_filename)

FILENAME_PMC_EVENTS_LOG = 'pmc-events-log.out'
FILENAME_PMC_CONTINUOUS_LOG = 'pmc-continuous-log.out'

class ContinuousLogging(threading.Thread): 
    def __init__(self, threadID, experiment_directory, time_period_us):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.experiment_directory = experiment_directory
        self.time_period_us = time_period_us
    def run(self):
        print ("Starting thread: "+str(self.threadID))
        os.system('sudo ./bin/pmc-run '+str(self.time_period_us)+' > ' \
                +self.experiment_directory+'/'+FILENAME_PMC_CONTINUOUS_LOG)

def set_frequency(freq_mhz):
    res = int(os.sysconf('SC_NPROCESSORS_ONLN'))
    print('Number of cpus: '+str(res))
    os.system('sudo cpufreq-set -g userspace')
    for i in range(0, res):
        os.system('sudo cpufreq-set -c '+str(i)+' -f '+str(freq_mhz)+'Mhz')

def run_experiment(freq_mhz, core_mask, workloads_config):
    # setup experiment directory
    experiment_num = 0
    try:
        with open(experiment_number_path, 'r') as f:
            experiment_num = int(f.read())
        f.closed
    except IOError:
        pass # first experiment
    with open(experiment_number_path, 'w') as f:
        f.write(str(experiment_num+1))
    f.closed
    experiment_directory = 'powmon-experiment-{0:0>3}'.format(experiment_num)
    if not os.path.exists(experiment_directory):
        os.makedirs(experiment_directory)    
    os.system('sudo bin/pmc-setup')
    os.system('sudo bin/pmc-get-header > '+experiment_directory \
            +'/'+FILENAME_PMC_EVENTS_LOG)
    loggingThread = ContinuousLogging(0, experiment_directory, 200000)
    loggingThread.start()
    #os.system('bin/pmc-get-header > '+experiment_directory+'/pmc-log.out')
    set_frequency(freq_mhz)
    # open workloads config file
    workloads_df = pd.read_csv(workloads_config, sep='\t')
    print workloads_df
    # pmc setup
    for i in range(0, len(workloads_df.index)):
        print 'Working on: '+ workloads_df['Name'].iloc[i]
        print 'Switching directory to: '+workloads_df['Directory'].iloc[i]
        owd = os.getcwd()
        try:
            os.chdir(workloads_df['Directory'].iloc[i])
            shell_text = '#!/usr/bin/env bash\n'
            shell_text += ''+owd+'/bin/pmc-get-pmcs "'+workloads_df['Name'].iloc[i] \
                    + ' start" >> '+owd+'/'+experiment_directory+'/'+FILENAME_PMC_EVENTS_LOG+'\n'
            shell_text += 'taskset -c '+core_mask+' '+workloads_df['Command'].iloc[i] + '\n'
            shell_text += ''+owd+'/bin/pmc-get-pmcs "'+workloads_df['Name'].iloc[i] \
                    + ' end" >> '+owd+'/'+experiment_directory+'/'+FILENAME_PMC_EVENTS_LOG+'\n'
            with open('temp_shell.sh', 'w') as f:
                f.write(shell_text)
            f.closed
            os.system('bash temp_shell.sh')
        finally:
            os.chdir(owd)
    print ("Waiting for logging thread to finish")
    os.system("echo '0' | sudo tee PMC_RUN_CHECK") # Stop data logging
    loggingThread.join()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--freq', dest='freq_mhz',  required=False, \
                  help='The frequency in MHz, e.g. -f 1000')
    parser.add_argument('-m', '--core-mask', dest='core_mask',  required=False, \
                  help="The core mask, e.g. -m '0,1,2,3'")
    parser.add_argument('-c', '--workloads-config', dest='workloads_config', required=True, \
                  help="The workload config file, e.g. -c 'workloads.config'")
    args=parser.parse_args()
    freq = 1000
    if args.freq_mhz:
        freq = args.freq_mhz
    core_mask = '0,1,2,3'
    if args.core_mask:
        core_mask = args.core_mask
    run_experiment(freq, core_mask, args.workloads_config)
