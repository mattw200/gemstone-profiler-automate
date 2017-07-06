#!/usr/bin/env python

# Matthew J. Walker
# Created: 5 June 2017

import sys
import os
import run_experiment
import pandas as pd

REG_MAX = 2**32

def combine_event_and_log_vals_float(start_row, end_row, continuous_df, col_header):
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
        row_dict['start date'] = start_row['datetime']
        row_dict['end date'] = end_row['datetime']
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
        os.path.join(args.experiment_dir, run_experiment.FILENAME_PMC_EVENTS_LOG+'-analysed.csv'), 
        sep='\t'
        )


