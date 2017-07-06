#!/usr/bin/env python

# Matthew J. Walker
# Created: 5 June 2017

import sys
import os
import run_experiment
import pandas as pd

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
    for i in range(0, len(workloads_temp_df.index)):
        current_workload = workloads_temp_df['label'].iloc[i].split()[0]
        print ('\nAnalaysing workload: '+current_workload)
        # get the start time stamp and end time stamp (milli)
        start_row = pmc_events_log_df[pmc_events_log_df['label'] == current_workload+' start']
        end_row = pmc_events_log_df[pmc_events_log_df['label'] == current_workload+' end']
        start_time = int(start_row['milliseconds'])
        end_time = int(end_row['milliseconds'])
        print start_time
        print end_time
        # now get pmcs



    
