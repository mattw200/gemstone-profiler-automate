#!/usr/bin/env python

# Matthew J. Walker
# Created: 5 June 2017

import sys
import os
import run_experiment
import pandas as pd

REG_MAX = 2**32


# This method derives basic stats from post-processed data
# E.g. adding the sum of the counts and the average of the rates
def add_cluster_sum_and_average_counts(input_df):
    # assumption: clusters have 4 CPUs each: BAD ASSUMPTION! Fix this later
    # (proposed solution: get experimental platform software to dervice this
    # and encode into headers). overhead only in pmc-get-header
    # pmc-setup dervices which cores need to report frequency

    # this bit of code assumes that CPUs of the same type (e.g. A7) are in the 
    # same cluster (not necessarily true, depending on the device)

    # 1. Find all CPUs of the same type (e.g. A7 or A15)
    # 2. Find the PMC events (assumption that CPUs of the same type measure the 
    # same counters). This assumption is valid for the experimental platform sw
    # 3. Create columns 'Total Cortex-A17 Counts' and 'Average Cortex-A7 Rate'
    # for each event and cycle count
    pass

def combine_event_and_log_vals_float(start_row, end_row, continuous_df, 
        col_header):
    vals = []
    vals.append(float(start_row[col_header]))
    for i in range(0, len(continuous_df.index)):
        vals.append(float(continuous_df[col_header].iloc[i]))
    vals.append(float(end_row[col_header]))
    return vals

# This method accepts a list of the raw PMC observations
# and finds the different between the first value and the last
# (checking for overflows)
def get_pmc_diff_from_list(pmc_vals):
    overflows = 0
    for i in range(1, len(pmc_vals)):
        if pmc_vals[i] < pmc_vals[i-1]:
            # overflow!
            overflows+=1;
    print('Overflows: '+str(overflows))
    if not overflows:
        return pmc_vals[-1] - pmc_vals[0]
        raise ValueError("Overflow!")
    else:
        return REG_MAX-pmc_vals[0] + pmc_vals[-1] + REG_MAX*overflows


def postprocess_experiment(experiment_dir, output_filepath):
    pmc_events_log_df = pd.read_csv(
        os.path.join(experiment_dir, run_experiment.FILENAME_PMC_EVENTS_LOG), 
        sep='\t'
        )
    pmc_continuous_log_df = pd.read_csv(
        os.path.join(experiment_dir, run_experiment.FILENAME_PMC_CONTINUOUS_LOG),
        sep='\t'
        )
    print pmc_events_log_df
    print pmc_continuous_log_df

    # count number of overflows 
    # need the workload names!
    workloads_temp_df = pmc_events_log_df[pmc_events_log_df['label'].str.contains(" start")]
    print workloads_temp_df
    # identify PMC columns
    all_cols = [i for i in pmc_events_log_df.columns.values]
    pmc_cols = [i for i in pmc_events_log_df.columns.values if i.find('cntr') > -1 or i.find('count') > -1]
    new_df_cols = ['workload name', 'duration (s)', 'no. samples', \
            'start time (ms)', 'end time (ms)', 'start date', 'end date']
    freq_cols = [i for i in pmc_events_log_df.columns.values if i.find('Freq (MHz)') > -1]
    for freq in freq_cols:
        new_df_cols.append(freq)
    for pmc in pmc_cols:
        new_df_cols.append(pmc+' diff')
    for pmc in pmc_cols:
        new_df_cols.append(pmc+' rate')
    new_df = pd.DataFrame(columns=new_df_cols) 
    for i in range(0, len(workloads_temp_df.index)):
        current_workload = workloads_temp_df['label'].iloc[i].split()[0]
        print ('\nAnalaysing workload: '+current_workload)
        # get the start time stamp and end time stamp (milli)
        start_row = pmc_events_log_df[pmc_events_log_df['label'] == current_workload+' start']
        end_row = pmc_events_log_df[pmc_events_log_df['label'] == current_workload+' end']
        start_time = long(start_row['milliseconds'])
        end_time = long(end_row['milliseconds'])
        delta_time = float(end_time - start_time)/1000.0
        print ('Delta time (s): ' + str(delta_time))
        # now use the continuous log to get the in between times
        #print (pmc_continuous_log_df['milliseconds'].dtype)
        continuous_df = pmc_continuous_log_df[pmc_continuous_log_df['milliseconds'] > start_time]
        continuous_df = continuous_df[continuous_df['milliseconds'] < end_time]
        print ('Start time: '+str(start_time))
        for j in range(0, len(continuous_df.index)):
            print ('    '+str(continuous_df['milliseconds'].iloc[j]))
        print ('End time: '+str(end_time))
        # now get pmcs
        num_samples = 0
        row_dict = {}
        for pmc in pmc_cols:
            print('PMC: '+pmc)
            pmc_vals = []
            pmc_vals.append(long(start_row[pmc]))
            for j in range(0, len(continuous_df.index)):
                pmc_vals.append(long(continuous_df[pmc].iloc[j]))
            pmc_vals.append(long(end_row[pmc]))
            print('    PMC values: '+str(pmc_vals))
            pmc_diff = get_pmc_diff_from_list(pmc_vals)
            print pmc_diff
            row_dict[pmc+' diff']=pmc_diff
            row_dict[pmc+' rate']=pmc_diff/delta_time
            num_samples = len(pmc_vals)
        row_dict['workload name'] = current_workload
        row_dict['duration (s)'] = delta_time
        row_dict['no. samples'] = num_samples
        row_dict['start time (ms)'] = start_time
        row_dict['end time (ms)'] = end_time
        row_dict['start date'] = start_row['datetime'].iloc[0]
        row_dict['end date'] = end_row['datetime'].iloc[0]
        freq_cols = [i for i in pmc_events_log_df.columns.values if i.find('Freq (MHz)') > -1]
        for f in freq_cols:
            freq_vals = combine_event_and_log_vals_float(start_row, end_row, continuous_df, f)
            first_freq = freq_vals[0]
            for j in range(1, len(freq_vals)):
                if freq_vals[j] != first_freq:
                    raise ValueError("Frequency changes in middle of workload! ("+current_workload+")")
            row_dict[f] = first_freq
        new_df = new_df.append(row_dict, ignore_index=True)
        print row_dict
    print new_df
    new_df.to_csv(
        os.path.join(output_filepath), 
        sep='\t'
        )


def consolidate_iterations(files_list):
    # This method takes the postprocessed iteration files,
    # goes through each workload in turn, comparing between
    # the iterations, and chooses one of them to include in
    # the single end file. 
    import pandas as pd
    iteration_dfs = [pd.read_csv(x,sep='\t') for x in files_list]
    print files_list
    # check workloads and execution
    # go through workload by workload:
    # assumption: workloads should be identical in all dfs
    workloads = iteration_dfs[0]['workload name'].tolist()
    combined_df = pd.DataFrame(columns=iteration_dfs[0].columns.values)
    for wl_i in range(0, len(workloads)):
        print("\nFinding best sample for workload: "+workloads[wl_i])
        execution_times = [df['duration (s)'].iloc[wl_i] for df in iteration_dfs]
        print("Execution times: "+str(execution_times))
        ordered_execution_times = sorted(execution_times)
        chosen_time = ordered_execution_times[len(execution_times)/2]
        chosen_index = execution_times.index(chosen_time)
        print("Chosen time: "+str(execution_times[chosen_index])+" (index="+str(chosen_index)+')')
        df_row = iteration_dfs[chosen_index].iloc[wl_i]
        print(df_row)
        combined_df = combined_df.append(df_row, ignore_index=True)
    return combined_df


def combine_pmc_runs(pmc_files):
    import os
    import pandas as pd
    import math
    combined_df = None
    is_df_created = False
    execution_times = []
    for pmc_i in range(0, len(pmc_files)):
        print("Working on PMC file: "+pmc_files[pmc_i])
        pmc_filename = os.path.basename(pmc_files[pmc_i])
        print("PMC filename: "+pmc_filename)
        pmc_dirname = os.path.basename(os.path.normpath(os.path.dirname(pmc_files[pmc_i])))
        print("PMC dirname: "+pmc_dirname)
        if not is_df_created:
            combined_df = pd.read_csv(pmc_files[pmc_i],sep='\t')
            execution_times.append(combined_df['duration (s)'].tolist())
            is_df_created = True
            continue
        temp_df = pd.read_csv(pmc_files[pmc_i],sep='\t')
        execution_times.append(temp_df['duration (s)'].tolist())
        # check data is the same
        # find the deviation
        new_cntr_cols = [x for x in temp_df.columns.values if ( x.find('cntr') > -1 and x not in combined_df.columns.values ) ]
        # just check that one of the new columns is not named the same as in combined_df
        for col in new_cntr_cols:
            if col in combined_df.columns.values:
                raise ValueError("Error: "+col+" is already in the DF (adding: "+pmc_dirname+")")
        # check workloads
        combined_workloads = combined_df['workload name'].tolist()
        temp_workloads = temp_df['workload name'].tolist()
        if not combined_workloads == temp_workloads:
            print("Combined: "+combined_workloads)
            print("Temp: "+temp_workloads)
            raise ValueError("Workloads are not the same!!!")
        # add to df
        print("combined df:")
        print combined_df
        combined_df = pd.concat([combined_df, temp_df[new_cntr_cols]], axis=1)
    print("Analysing the S.D. between exeuction times between PMC runs:")
    mean_list = []
    sd_list = []
    for wl_i in range(0, len(combined_df.index)):
        total = 0
        row_string = combined_df['workload name'].iloc[wl_i] + ":  "
        for run_i in range(0, len(execution_times)):
            row_string += str(execution_times[run_i][wl_i]) + "   "
            total += execution_times[run_i][wl_i]
        mean = total/len(execution_times)
        row_string += " mean: "+str(mean) + "  "
        accum = 0
        for run_i in range(0, len(execution_times)):
            accum += (execution_times[run_i][wl_i] - mean) * (execution_times[run_i][wl_i] - mean)
        variance = accum / len(execution_times)
        row_string += "var: "+str(variance)+ "  "
        sd = math.sqrt(variance)
        row_string += "SD:  "+str(sd)
        mean_list.append(mean)
        sd_list.append(sd)
        print row_string
    print combined_df
    workload_duration_col_index = (combined_df.columns.values).tolist().index('duration (s)')
    combined_df.insert(workload_duration_col_index, 'duration SD (s)', sd_list)
    combined_df.insert(workload_duration_col_index, 'duration mean (s)', mean_list)
    return combined_df


def postprocess_new_sytle_experiments(experiment_top_dir):
    import os
    import pandas as pd
    pmc_dirs  = [x for x in os.listdir(args.experiment_dir)
             if ( os.path.isdir(os.path.join(args.experiment_dir, x)) \
                     and x.find('pmc-run') > -1 )]
    pmc_files_to_combine = []
    for pmc_run_i in range(0, len(pmc_dirs)):
        # NOTE: pmc_dirs are not in correct order!
        current_pmc_dir = None
        for pmc_dir in pmc_dirs:
            if pmc_dir.startswith('pmc-run-{0:0>2}'.format(pmc_run_i)):
                current_pmc_dir = pmc_dir
                break
        if not current_pmc_dir:
            raise IOError("Could not find directory for pmc-run-{0:0>2}".format(pmc_run_i))
        print('Working on PMC run: '+str(current_pmc_dir)+'...')
        current_pmc_dir = os.path.join(experiment_top_dir, current_pmc_dir)
        iteration_dirs  = [x for x in os.listdir(current_pmc_dir)
             if ( os.path.isdir(os.path.join(current_pmc_dir, x)) \
                     and x.find('iteration-') > -1 )]
        iteration_files_to_consolidate = []
        for iter_i in range(0, len(iteration_dirs)):
            current_iter_dir = None
            for iter_dir in iteration_dirs:
                if iter_dir.startswith('iteration-{0:0>2}'.format(iter_i)):
                    current_iter_dir = iter_dir
                    break
            if not current_iter_dir:
                raise IOError("Could not find directory for iteration-{0:0>2}".format(iter_i))
            current_iter_dir = os.path.join(current_pmc_dir, current_iter_dir)
            print("Working on iteration: "+str(current_iter_dir))
            # first process each of the iterations, and then combine them
            iteration_postprocessed_filename = os.path.join(current_iter_dir, 'postprocessed.csv')
            postprocess_experiment(current_iter_dir, iteration_postprocessed_filename)
            iteration_files_to_consolidate.append(iteration_postprocessed_filename)
        combined_iterations_df = consolidate_iterations(iteration_files_to_consolidate)
        combined_iterations_df.to_csv(os.path.join(current_pmc_dir, 'consolidated-iterations.csv'), sep='\t')
        pmc_files_to_combine.append(os.path.join(current_pmc_dir, 'consolidated-iterations.csv'))
    combined_pmcs_df = combine_pmc_runs(pmc_files_to_combine)
    print combined_pmcs_df
    combined_pmcs_df.to_csv(os.path.join(experiment_top_dir, "consolidated-pmc-runs.csv"))
           

# Three stages:
# 1) post processing (i.e. convert raw output files to df (including calculating pmc rate)
# 2) (for new experiments with multiple pmc runs and iterations) consolidating
# 3) elaborating/enriching - add key stats to existing data (e.g. average cluster PMCs, quick utilisating view)
if __name__ == "__main__":
    import argparse
    import os
    import sys
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--experiment-dir', dest='experiment_dir', \
            required=True, \
            help='The path to the experiment directory to analyse, ' \
            + 'e.g. "../powmon-experiment-000/"')
    parser.add_argument('--elaborate-only', dest='elaborate_only', \
            required=False,action='store_true', \
            help='Only runs the final elaboration stage without re-running ' \
            + 'the post-processing and consolidating')
    args=parser.parse_args()

    # Works in two cases:
    # 1) it is an 'old-style', single-run experiment with the files under the top experiment directory
    # 2) it has the top directory, pmc-run directories inside, with iteration directories inside each of these
    # (it doesn't to different combinations). 

    subdirs = [x for x in os.listdir(args.experiment_dir)
            if os.path.isdir(os.path.join(args.experiment_dir, x))]

    is_new_style_experiment = False
    for dir in subdirs:
        if dir.find('pmc-run') > -1:
            is_new_style_experiment = True
            break
    if is_new_style_experiment:
        # go through discovering directories, consolidating etc. 
        if not args.elaborate_only:
            postprocess_new_sytle_experiments(args.experiment_dir)
        elaborate(args.experiment_dir)
    else:
        if not args.elaborate_only:
            postprocess_experiment(args.experiment_dir, 
                     os.path.join(args.experiment_dir,run_experiment.FILENAME_PMC_EVENTS_LOG+'-analysed.csv'))
        elaborate(args.experiment_dir)
