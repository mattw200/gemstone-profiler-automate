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
FILENAME_CORE_MASK_OUT = 'core-mask.txt'

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
    # New - freq_mhz can be list. divides every 4 by default
    # (in future can add a cluster size option for 2 big and 2 little etc.)
    res = int(os.sysconf('SC_NPROCESSORS_ONLN'))
    print('Number of cpus: '+str(res))
    print('Setting the CPU frequency (needs sudo)')
    os.system('sudo cpufreq-set -g userspace')
    if isinstance(freq_mhz, (int, long)):
        for i in range(0, res):
            os.system('sudo cpufreq-set -c '+str(i)+' -f '+str(freq_mhz)+'Mhz')
    else:
        cluster_size = 4
        freq_array = freq_mhz.split(',')
        freq_array = [int(f) for f in freq_array]
        cpu_id = 0
        for f in freq_array:
            os.system('sudo cpufreq-set -c '+str(cpu_id)+' -f '+str(f)+'Mhz')
            cpu_id += cluster_size

def run_experiment(
        experiment_dir,
        freq_mhz,
        core_mask,
        workloads_config,
        command_args,
        experiment_subdir=None,
        pmc_config_filename=None,
        iterations=1,
        pre_sleep=None,
        post_sleep=None,
        workload_timeout=None
        ):
    import time
    import datetime
    import sys
    experiment_top_directory = experiment_dir
    if not os.path.exists(experiment_top_directory):
        os.makedirs(experiment_top_directory)    
    if experiment_subdir:
        # create a subdirectory and make this the experiment directory
        experiment_top_directory = os.path.join(experiment_dir, experiment_subdir)
        if not os.path.exists(experiment_top_directory):
            os.makedirs(experiment_top_directory)
        print('experiment_top_directory: '+experiment_top_directory)
    with open(os.path.join(experiment_top_directory, FILENAME_CORE_MASK_OUT), 'w') as f:
        f.write(core_mask)
    f.closed
    # now deal with iterations
    iterations = int(iterations)
    if not (iterations > 0 and iterations < 20):
        print("Invalid number of iterations, must be between 0 and 20")
        raise ValueError("Invalid number of iterations ("+str(iterations)+")." \
                + " Must be between 0 and 20")
    for i_iter in range(0, iterations):
        iteration_dir_name = "iteration-{0:0>2}".format(i_iter)
        experiment_directory = os.path.join(experiment_top_directory, iteration_dir_name)
        if not os.path.exists(experiment_directory):
            os.makedirs(experiment_directory)
        if not pmc_config_filename:
            os.system('bin/pmc-setup')
        else:
            os.system('bin/pmc-setup '+pmc_config_filename)
        os.system('bin/pmc-get-header > '+experiment_directory \
                +'/'+FILENAME_PMC_EVENTS_LOG)
        loggingThread = ContinuousLogging(0, experiment_directory, SAMPLE_PERIOD_US)
        loggingThread.start()
        #os.system('bin/pmc-get-header > '+experiment_directory+'/pmc-log.out')
        set_frequency(freq_mhz)
        # open workloads config file
        workloads_df = pd.read_csv(workloads_config, sep='\t')
        print workloads_df
        # change home dir so it works on other platforms
        original_home_dir = '/home/odroid'
        home_dir = os.path.expanduser('~')
        workloads_df['Directory'] = workloads_df['Directory'].apply(lambda x: x.replace(original_home_dir,home_dir))
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
            pre_sleep_shell_text = None
            post_sleep_shell_text = None
            try:
                current_name = workloads_df['Name'].iloc[i]
                current_dir = workloads_df['Directory'].iloc[i]
                current_command = workloads_df['Command'].iloc[i]
                os.chdir(current_dir)
                if pre_sleep:
                    pre_sleep_command = 'sleep '+str(int(pre_sleep))
                    pre_sleep_name = 'prelseep-'+current_name
                    pre_sleep_shell_text = '#!/usr/bin/env bash\n'
                    pre_sleep_shell_text += 'echo "-------POWMON WORKLOAD: '+pre_sleep_name \
                            +'" | tee -a '+owd+'/'+experiment_directory+'/'+FILENAME_PROGRAM_OUT+'\n'
                    pre_sleep_shell_text += 'echo "-------POWMON DIR: '+current_dir \
                            +'" | tee -a '+owd+'/'+experiment_directory+'/'+FILENAME_PROGRAM_OUT+'\n'
                    pre_sleep_shell_text += 'echo "-------POWMON COMMAND: '+pre_sleep_command \
                            +'" | tee -a '+owd+'/'+experiment_directory+'/'+FILENAME_PROGRAM_OUT+'\n'
                    #shell_text += "sleep 1\n"
                    pre_sleep_shell_text += 'echo "-------POWMON TIME START: '+str(datetime.datetime.now())+" (" \
                                                    +str(int(round(time.time() * 1000)))+")" \
                            +'" | tee -a '+owd+'/'+experiment_directory+'/'+FILENAME_PROGRAM_OUT+'\n'
                    pre_sleep_shell_text += ''+owd+'/bin/pmc-get-pmcs "'+pre_sleep_name \
                            + ' start" >> '+owd+'/'+experiment_directory+'/'+FILENAME_PMC_EVENTS_LOG+'\n'
                    pre_sleep_shell_text += 'taskset -c '+core_mask+' '+pre_sleep_command \
                            +' |& tee -a '+owd+'/'+experiment_directory+'/'+FILENAME_PROGRAM_OUT+'\n'
                    pre_sleep_shell_text += ''+owd+'/bin/pmc-get-pmcs "'+pre_sleep_name \
                            + ' end" >> '+owd+'/'+experiment_directory+'/'+FILENAME_PMC_EVENTS_LOG+'\n'
                    pre_sleep_shell_text += 'echo "-------POWMON TIME END: '+str(datetime.datetime.now())+" (" \
                                                +str(int(round(time.time() * 1000)))+")" \
                            +'" | tee -a '+owd+'/'+experiment_directory+'/'+FILENAME_PROGRAM_OUT+'\n'
                    with open('temp_shell_pre_sleep.sh', 'w') as f:
                        f.write(pre_sleep_shell_text)
                    f.closed
                if workload_timeout:
                    ## use the timeout command and repeat the workload
                    #workload_timeout = int(workload_timeout) # confirm it is int
                    ## 1. wrap the command in a while loop
                    ## 2. use the timout command
                    #current_command = 'timeout '+str(workload_timeout)+ \
                    #        '  while true; do '+current_command+'; done  '
                    # Do repeats:
                    # taskset -c 4,5,6,7 $(while true; do ./basicmath_large > output_large.txt; done) |& tee -a /home/odroid/temperature/powmon-pmc-armv8/powmon-experiment-013/pmc-run-02-0x11-0x12-0x13-0x14-0x15-0x16/iteration-00/program-output.log
                    inner_command = '$(while true; do '+current_command+'; done)'
                    inner_shell_text = '#!/usr/bin/env bash\n'+inner_command+'\n'
                    with open('inner_shell.sh', 'w') as f:
                        f.write(inner_shell_text)
                    f.closed
                    current_command = 'timeout -s SIGKILL '+str(int(workload_timeout))+'s bash inner_shell.sh'
                shell_text = '#!/usr/bin/env bash\n'
                shell_text += 'echo "-------POWMON WORKLOAD: '+current_name \
                        +'" | tee -a '+owd+'/'+experiment_directory+'/'+FILENAME_PROGRAM_OUT+'\n'
                shell_text += 'echo "-------POWMON DIR: '+current_dir \
                        +'" | tee -a '+owd+'/'+experiment_directory+'/'+FILENAME_PROGRAM_OUT+'\n'
                shell_text += 'echo "-------POWMON COMMAND: '+current_command \
                        +'" | tee -a '+owd+'/'+experiment_directory+'/'+FILENAME_PROGRAM_OUT+'\n'
                #shell_text += "sleep 1\n"
                shell_text += 'echo "-------POWMON TIME START: '+str(datetime.datetime.now())+" (" \
                                                +str(int(round(time.time() * 1000)))+")" \
                        +'" | tee -a '+owd+'/'+experiment_directory+'/'+FILENAME_PROGRAM_OUT+'\n'
                shell_text += ''+owd+'/bin/pmc-get-pmcs "'+current_name \
                        + ' start" >> '+owd+'/'+experiment_directory+'/'+FILENAME_PMC_EVENTS_LOG+'\n'
                shell_text += 'taskset -c '+core_mask+' '+current_command \
                        +' |& tee -a '+owd+'/'+experiment_directory+'/'+FILENAME_PROGRAM_OUT+'\n'
                shell_text += ''+owd+'/bin/pmc-get-pmcs "'+current_name \
                        + ' end" >> '+owd+'/'+experiment_directory+'/'+FILENAME_PMC_EVENTS_LOG+'\n'
                shell_text += 'echo "-------POWMON TIME END: '+str(datetime.datetime.now())+" (" \
                                                +str(int(round(time.time() * 1000)))+")" \
                        +'" | tee -a '+owd+'/'+experiment_directory+'/'+FILENAME_PROGRAM_OUT+'\n'
                with open('temp_shell.sh', 'w') as f:
                    f.write(shell_text)
                f.closed
                if post_sleep:
                    post_sleep_command = 'sleep '+str(int(post_sleep))
                    post_sleep_name = 'postslseep-'+current_name
                    post_sleep_shell_text = '#!/usr/bin/env bash\n'
                    post_sleep_shell_text += 'echo "-------POWMON WORKLOAD: '+post_sleep_name \
                            +'" | tee -a '+owd+'/'+experiment_directory+'/'+FILENAME_PROGRAM_OUT+'\n'
                    post_sleep_shell_text += 'echo "-------POWMON DIR: '+current_dir \
                            +'" | tee -a '+owd+'/'+experiment_directory+'/'+FILENAME_PROGRAM_OUT+'\n'
                    post_sleep_shell_text += 'echo "-------POWMON COMMAND: '+post_sleep_command \
                            +'" | tee -a '+owd+'/'+experiment_directory+'/'+FILENAME_PROGRAM_OUT+'\n'
                    #shell_text += "sleep 1\n"
                    post_sleep_shell_text += 'echo "-------POWMON TIME START: '+str(datetime.datetime.now())+" (" \
                                                    +str(int(round(time.time() * 1000)))+")" \
                            +'" | tee -a '+owd+'/'+experiment_directory+'/'+FILENAME_PROGRAM_OUT+'\n'
                    post_sleep_shell_text += ''+owd+'/bin/pmc-get-pmcs "'+post_sleep_name \
                            + ' start" >> '+owd+'/'+experiment_directory+'/'+FILENAME_PMC_EVENTS_LOG+'\n'
                    post_sleep_shell_text += 'taskset -c '+core_mask+' '+post_sleep_command \
                            +' |& tee -a '+owd+'/'+experiment_directory+'/'+FILENAME_PROGRAM_OUT+'\n'
                    post_sleep_shell_text += ''+owd+'/bin/pmc-get-pmcs "'+post_sleep_name \
                            + ' end" >> '+owd+'/'+experiment_directory+'/'+FILENAME_PMC_EVENTS_LOG+'\n'
                    post_sleep_shell_text += 'echo "-------POWMON TIME END: '+str(datetime.datetime.now())+" (" \
                                                +str(int(round(time.time() * 1000)))+")" \
                            +'" | tee -a '+owd+'/'+experiment_directory+'/'+FILENAME_PROGRAM_OUT+'\n'
                    with open('temp_shell_post_sleep.sh', 'w') as f:
                        f.write(post_sleep_shell_text)
                    f.closed
                # Run generated shell scripts
                if pre_sleep:
                    os.system('bash temp_shell_pre_sleep.sh')
                os.system('bash temp_shell.sh')
                if post_sleep:
                    os.system('bash temp_shell_post_sleep.sh')
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

def get_pmcs_to_run_over(pmcs_file, pmcs_cpu):
    file_lines = []
    with open(pmcs_file, 'r') as f:
       file_lines = f.read().split('\n') 
    f.closed
    for line in file_lines:
        fields = line.split(':')
        if len(fields) == 2:
            if fields[0] == pmcs_cpu:
                return [x.strip() for x in fields[1].split(',') if x.find('0x') > -1]
    raise ValueError("Couldn't find the cpu ("+pmcs_cpu+") in the pmcs-file (" \
            +pmcs_file+")!")

if __name__ == "__main__":
    import argparse
    import sys
    platforms = ['RPi3','O-XU3','O-C2']
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--freq', dest='freq_mhz',  required=False, \
                  help='The frequency in MHz, e.g. -f 1000')
    parser.add_argument('-m', '--core-mask', dest='core_mask', required=False, \
                  help="The core mask, e.g. -m '0,1,2,3'")
    parser.add_argument('-p', '--platform', dest='platform', required=True, \
                  help="Specify the platform on which the experiment is run" \
                  +". Available: "+str(platforms))
    parser.add_argument('-c', '--workloads-config', dest='workloads_config', \
                  required=True, \
                  help="The workload config file, e.g. -c 'workloads.config'")
    # NOTE: have made pmcs-file and pmcs-cpu required as it doesnt create the
    # correct file structure without these. 
    parser.add_argument('--pmcs-file', dest='pmcs_file', required=True, \
                  help="Specifies the pmcs-setup.txt file to use.")
    parser.add_argument('--pmcs-cpu', dest='pmcs_cpu', required=True, \
                  help="Selects the CPU type (e.g. Cortex-A15) for which" \
                  +" to iterate the PMCs over. Works with the --pmcs-file")
    parser.add_argument('--iterations', dest='iterations', required=False, \
                  help="Number of times to run each experiment")
    parser.add_argument('--pre-sleep', dest='pre_sleep', required=False, \
                  help="If present, sleeps and records before workload. " \
                  +"E.g. --pre-sleep 30 : adds 30 seconds of pre sleep workload")
    parser.add_argument('--post-sleep', dest='post_sleep', required=False, \
                  help="If present, sleeps and records after workload. " \
                  +"E.g. --pre-sleep 30 : adds 30 seconds of post sleep workload")
    parser.add_argument('--workload-timeout', dest='workload_timeout', required=False, \
                 help="If present, the workload is repeated and terminated so " \
                 +"that it runs for the exact time specified (seconds)" \
                 +" e.g. --workload-timeout 30 : runs workload for exactly " \
                 +" 30 seconds")
    parser.add_argument('--label', dest='label', required=False, \
                  help="If present, adds label to top experiment directory" )
    args=parser.parse_args()
    if args.platform not in platforms:
        print("Did not recognise the platform! ('-p') "\
            +"Supported: "+str(platforms))
        parser.print_help()
        sys.exit()
    freq = 1000
    if args.freq_mhz:
        freq = args.freq_mhz
    core_mask = '0,1,2,3'
    if args.core_mask:
        core_mask = args.core_mask
    command_args_text = ""
    for clarg in sys.argv:
        command_args_text += clarg+' '
    if not args.iterations:
        args.iterations = 1
    args.iterations = int(args.iterations)
    if args.iterations % 2 == 0:
        print("iterations must be an odd number! (e.g. 1,3,5 or 7)")
        parser.print_help()
        sys.exit()
    # derive experiment directory:
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
    experiment_dir_label = '-p_'+args.platform+'-'+'c_'+core_mask.replace(',','_')+'-f_'+freq.replace(',','_')
    if args.label:
        experiment_dir_label += '-'+args.label.strip().replace(' ','_').replace('-','_')
    experiment_directory += experiment_dir_label
    # check for PMCs
    if args.pmcs_file or args.pmcs_cpu:
        if args.pmcs_file and args.pmcs_cpu:
            print("Running experiment multiple times to capture different PMCs")
            print("Repeating PMCs for the "+args.pmcs_cpu+" cpu type.")
            pmcs = get_pmcs_to_run_over(args.pmcs_file, args.pmcs_cpu)
            print("Capturing the following pmcs: "+str(pmcs))
            num_counters = cpu_num_counters[args.pmcs_cpu]
            print("Number of counters: "+str(num_counters))
            pmc_sets = [ pmcs[x:x+num_counters] for x in \
                    range(0, len(pmcs), num_counters)]
            print("Running the following experiments:")
            for i in range(0, len(pmc_sets)):
                print(str(i)+": "+str(pmc_sets[i]))
            # create new events.config
            for pmc_i in range(0, len(pmc_sets)):
                print("Running PMC Set "+str(pmc_i)+": "+str(pmc_sets[pmc_i])+"")
                lines = []
                with open('events.config', 'r') as f:
                    lines = f.read().split('\n')
                    for i in range(0, len(lines)):
                        fields = lines[i].split(',')
                        if len(fields) > 1:
                            if fields[1] == args.pmcs_cpu:
                                lines[i] = fields[0]+','+fields[1]
                                for pmc in pmc_sets[pmc_i]:
                                    lines[i]+=','+pmc
                f.closed
                for line in lines:
                    print line
                with open('temp-events.config', 'w') as f:
                    f.write('\n'.join(lines))
                f.closed
                with open('temp-events.config', 'r') as f:
                    print("Opening 'temp-events.config'")
                    print(f.read())
                f.closed
                pmc_subdir_name = 'pmc-run-{0:0>2}'.format(pmc_i)
                for pmc in pmc_sets[pmc_i]:
                    pmc_subdir_name += '-'+pmc
                print pmc_subdir_name
                run_experiment(
                        experiment_directory,
                        freq,
                        core_mask,
                        args.workloads_config, 
                        command_args_text,
                        experiment_subdir=pmc_subdir_name,
                        pmc_config_filename='temp-events.config',
                        iterations=args.iterations,
                        pre_sleep=args.pre_sleep,
                        post_sleep=args.post_sleep,
                        workload_timeout=args.workload_timeout
                        )
        else:
            print("If specifying PMCs, both --pmcs-file and --pmcs-cpu " \
                    +"are required.")
            parser.print_help()
            sys.exit()
    else:
        run_experiment(experiment_directory,freq, core_mask, args.workloads_config, command_args_text, iterations=args.iterations,pre_sleep=args.pre_sleep,post_sleep=args.post_sleep,workload_timeout=args.workload_timeout)
