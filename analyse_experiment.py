#!/usr/bin/env python

# Matthew J. Walker
# Created: 5 June 2017

import sys
import os
import run_experiment
import pandas as pd

REG_MAX = 2**32

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

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--experiment-dir', dest='experiment_dir', \
            required=False, \
            help='The path to the experiment directory to analyse, ' \
            + 'e.g. "../powmon-experiment-000/"')
    args=parser.parse_args()
    pmc_events_log_df = pd.read_csv(
        os.path.join(args.experiment_dir, run_experiment.FILENAME_PMC_EVENTS_LOG), 
        sep='\t'
        )
    pmc_continuous_log_df = pd.read_csv(
        os.path.join(args.experiment_dir, run_experiment.FILENAME_PMC_CONTINUOUS_LOG),
        sep='\t'
        )
    print pmc_events_log_df
    print pmc_continuous_log_df

    # count number of overflows 
    # need the workload names!
    workloads_temp_df = pmc_events_log_df[pmc_events_log_df['label'].str.contains(" start")]
    print workloads_temp_df
    # identify PMC columns
    pmc_cols = [i for i in pmc_events_log_df.columns.values if i.find('cntr') > -1 or i.find('count') > -1]
    for i in range(0, len(workloads_temp_df.index)):
        current_workload = workloads_temp_df['label'].iloc[i].split()[0]
        print ('\nAnalaysing workload: '+current_workload)
        # get the start time stamp and end time stamp (milli)
        start_row = pmc_events_log_df[pmc_events_log_df['label'] == current_workload+' start']
        end_row = pmc_events_log_df[pmc_events_log_df['label'] == current_workload+' end']
        start_time = long(start_row['milliseconds'])
        end_time = long(end_row['milliseconds'])
        delta_time = end_time - start_time
        print ('Delta time (ms): ' + str(delta_time))
        # now use the continuous log to get the in between times
        continuous_df = pmc_continuous_log_df[pmc_continuous_log_df['milliseconds'] > start_time]
        continuous_df = continuous_df[continuous_df['milliseconds'] < end_time]
        print ('Start time: '+str(start_time))
        for j in range(0, len(continuous_df.index)):
            print ('    '+str(continuous_df['milliseconds'].iloc[j]))
        print ('End time: '+str(end_time))
        # now get pmcs
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
    print pmc_cols
