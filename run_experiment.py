#!/usr/bin/env python

# Matthew J. Walker
# Created: 14 June 2017

import sys
import os
import pandas as pd
import threading
import kill_pmc_runs

experiment_number_filename = 'experiment-number.txt'
script_path = os.path.dirname(__file__)
experiment_number_path = os.path.join(script_path, experiment_number_filename)

FILENAME_PMC_EVENTS_LOG = 'pmc-events-log.out'
FILENAME_PMC_CONTINUOUS_LOG = 'pmc-continuous-log.out'
FILENAME_PROGRAM_OUT = 'program-output.log'
FILENAME_ARGS = 'command-line-args.txt'

# PMC continuous collection sample period in microseconds (us)
SAMPLE_PERIOD_US = 700000

cpu_ids = {
    'Cortex-A8' : '0x00',
    'Cortex-A7' : '0x07',
    'Cortex-A15' : '0x0F',
    'Cortex-A53' : '0x03',
    'Cortex-A57' : '0x01',
    'Cortex-A72' : '0x02', 
    'Cortex-A73' : '0x04'
    }

cpu_num_counters = {
    'Cortex-A8' : 4,
    'Cortex-A7' : 4,
    'Cortex-A15' : 6,
    'Cortex-A53' : 6,
    'Cortex-A57' : 6,
    'Cortex-A72' : 6, 
    'Cortex-A73' : 6
    }


class ContinuousLogging(threading.Thread): 
    def __init__(self, threadID, experiment_directory, time_period_us):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.experiment_directory = experiment_directory
        self.time_period_us = time_period_us
    def run(self):
        print ("Starting thread: "+str(self.threadID))
        os.system('./bin/pmc-run '+str(self.time_period_us)+' > ' \
                +self.experiment_directory+'/'+FILENAME_PMC_CONTINUOUS_LOG)
        print("Finished thread: "+str(self.threadID))
        print("Exiting as logging has stopped")
        sys.exit()

def set_frequency(freq_mhz):
    res = int(os.sysconf('SC_NPROCESSORS_ONLN'))
    print('Number of cpus: '+str(res))
    print('Setting the CPU frequency (needs sudo)')
    os.system('sudo cpufreq-set -g userspace')
    for i in range(0, res):
        os.system('sudo cpufreq-set -c '+str(i)+' -f '+str(freq_mhz)+'Mhz')

def run_experiment(freq_mhz, core_mask, workloads_config, command_args):
    import time
    import datetime
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
    os.system('bin/pmc-setup')
    os.system('bin/pmc-get-header > '+experiment_directory \
            +'/'+FILENAME_PMC_EVENTS_LOG)
    loggingThread = ContinuousLogging(0, experiment_directory, SAMPLE_PERIOD_US)
    loggingThread.start()
    #os.system('bin/pmc-get-header > '+experiment_directory+'/pmc-log.out')
    set_frequency(freq_mhz)
    # open workloads config file
    workloads_df = pd.read_csv(workloads_config, sep='\t')
    print workloads_df
    with open(experiment_directory+'/'+FILENAME_ARGS, 'w') as f:
        f.write(command_args)
    f.closed
    program_out_text = "-------POWMON Start of experiment: "
    program_out_text += str(datetime.datetime.now())+" (" \
                        +str(int(round(time.time() * 1000)))+")\n"
    with open(experiment_directory+'/'+FILENAME_PROGRAM_OUT, 'w') as f:
        f.write(program_out_text)
    f.closed
    for i in range(0, len(workloads_df.index)):
        print 'Working on: '+ workloads_df['Name'].iloc[i]
        print 'Switching directory to: '+workloads_df['Directory'].iloc[i]
        owd = os.getcwd()
        try:
            os.chdir(workloads_df['Directory'].iloc[i])
            shell_text = '#!/usr/bin/env bash\n'
            shell_text += 'echo "-------POWMON WORKLOAD: '+workloads_df['Name'].iloc[i] \
                    +'" | tee -a '+owd+'/'+experiment_directory+'/'+FILENAME_PROGRAM_OUT+'\n'
            shell_text += 'echo "-------POWMON DIR: '+workloads_df['Directory'].iloc[i] \
                    +'" | tee -a '+owd+'/'+experiment_directory+'/'+FILENAME_PROGRAM_OUT+'\n'
            shell_text += 'echo "-------POWMON COMMAND: '+workloads_df['Command'].iloc[i] \
                    +'" | tee -a '+owd+'/'+experiment_directory+'/'+FILENAME_PROGRAM_OUT+'\n'
            shell_text += "sleep 1\n"
            shell_text += 'echo "-------POWMON TIME START: '+str(datetime.datetime.now())+" (" \
                                            +str(int(round(time.time() * 1000)))+")" \
                    +'" | tee -a '+owd+'/'+experiment_directory+'/'+FILENAME_PROGRAM_OUT+'\n'
            shell_text += ''+owd+'/bin/pmc-get-pmcs "'+workloads_df['Name'].iloc[i] \
                    + ' start" >> '+owd+'/'+experiment_directory+'/'+FILENAME_PMC_EVENTS_LOG+'\n'
            shell_text += 'taskset -c '+core_mask+' '+workloads_df['Command'].iloc[i] \
                    +' |& tee -a '+owd+'/'+experiment_directory+'/'+FILENAME_PROGRAM_OUT+'\n'
            shell_text += ''+owd+'/bin/pmc-get-pmcs "'+workloads_df['Name'].iloc[i] \
                    + ' end" >> '+owd+'/'+experiment_directory+'/'+FILENAME_PMC_EVENTS_LOG+'\n'
            shell_text += 'echo "-------POWMON TIME END: '+str(datetime.datetime.now())+" (" \
                                            +str(int(round(time.time() * 1000)))+")" \
                    +'" | tee -a '+owd+'/'+experiment_directory+'/'+FILENAME_PROGRAM_OUT+'\n'
            with open('temp_shell.sh', 'w') as f:
                f.write(shell_text)
            f.closed
            #print (shell_text)
            os.system('bash temp_shell.sh')
        finally:
            os.chdir(owd)
    print ("Finished at: "+str(datetime.datetime.now())+" (" \
            +str(int(round(time.time() * 1000)))+")")
    print ("Waiting for logging thread to finish")
    os.system("echo '0' | tee PMC_RUN_CHECK") # Stop data logging
    loggingThread.join()
    print ("Exiting at: "+str(datetime.datetime.now())+" (" \
            +str(int(round(time.time() * 1000)))+")")

#def parse_pmcs_string(pmcs_string_dict):
    # pmc_strings string is an array of strings

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--freq', dest='freq_mhz',  required=False, \
                  help='The frequency in MHz, e.g. -f 1000')
    parser.add_argument('-m', '--core-mask', dest='core_mask', required=False, \
                  help="The core mask, e.g. -m '0,1,2,3'")
    parser.add_argument('-c', '--workloads-config', dest='workloads_config', \
                  required=True, \
                  help="The workload config file, e.g. -c 'workloads.config'")
    parser.add_argument('--pmcs-file', dest='pmcs_file', required=False, \
                  help="Specifies the pmcs-setup.txt file to use.")
    '''
    parser.add_argument('--pmcs-a7', dest='pmcs_a7', required=False \
                  help="Set PMCs for Cortex-A7. E.g. "
                  +'--pmcs-a7 "0x1b,0x50,0x6A,0x73"'
    parser.add_argument('--pmcs-a15', dest='pmcs_a15', required=False \
                  help="Set PMCs for Cortex-A15. E.g. "
                  +'--pmcs-a15 "0x1b,0x50,0x6A,0x73,0x14,0x19"'
    '''
    args=parser.parse_args()
    freq = 1000
    if args.freq_mhz:
        freq = args.freq_mhz
    core_mask = '0,1,2,3'
    if args.core_mask:
        core_mask = args.core_mask
    # TODO
    '''
    if args.pmcs_file:
    '''
    command_args_text = ""
    for clarg in sys.argv:
        command_args_text += clarg+' '
    run_experiment(freq, core_mask, args.workloads_config, command_args_text)
