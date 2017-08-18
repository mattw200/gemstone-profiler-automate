#!/usr/bin/env python

# Matthew J. Walker
# Created: 14 August 2017


def get_experiment_number_from_full_directory_path(path):
    import os
    dir_name =  os.path.basename(os.path.normpath(path))
    if dir_name.startswith('powmon-experiment-'):
        return int(dir_name.split('-')[2])
    else:
        return None
 
def get_experiment_files(top_search_dir, experiment_numers):
    import os
    # check experiment numbers have been converted to ints:
    experiment_numers = [int(x) for x in experiment_numers]
    match_dirs = [x[0] for x in os.walk(top_search_dir) \
           if get_experiment_number_from_full_directory_path(x[0]) in experiment_numers ]
    print ("The folling directories match:")
    print match_dirs
    return match_dirs

if __name__=='__main__':
    import argparse
    import os
    import pandas as pd
    import postprocess_experiment
    parser = argparse.ArgumentParser()
    parser.add_argument('--experiments',  dest='experiment_numbers_list', required=True, \
               help="A list of which experiment numbers to use")
    parser.add_argument('-d', '--directory',  dest='directory', required=True, \
               help="The directory in which to find the experiments")
    parser.add_argument( '--force-clean',  dest='force_clean', action='store_true', required=False, \
               help="Forces postprocessing to take place even if files already there")
    args=parser.parse_args()

    experiment_dirs = get_experiment_files(args.directory,args.experiment_numbers_list.split(','))
    
    print experiment_dirs
    dfs = []
    for d in experiment_dirs:
        f = os.path.join(d,'consolidated-pmc-runs.csv')
        if (not os.path.isfile(f)) or args.force_clean:
            print(d+":  postprocessing not complete. Doing this now")
            postprocess_experiment.postprocess_new_sytle_experiments(d)
            current_df = pd.read_csv(f,sep='\t')
            current_df.insert(0, 'experiment number', get_experiment_number_from_full_directory_path(f))
            current_df.insert(0, 'experiment name', os.path.basename(os.path.normpath(f)))
        dfs.append(pd.read_csv(f,sep='\t'))

    for i in range(0, len(dfs)):
        # NOTE: this has a new bit where it removes the PMCs from the cluster not being used in the experiment
        # This is done because the same PMC can be included twice if the counter used to count the event 
        # is different. Therefore, to avoid the same PMC included twice, filter out the PMCs for the other
        # cluster. 
        current_df = dfs[i]
        unique_core_masks = current_df['core mask'].unique()
        print("Unique core masks for this experiment: "+str(unique_core_masks))
        if len(unique_core_masks) > 1:
            raise ValueError("More than one core mask in the same experiment!")
        cols = current_df.columns.values
        if unique_core_masks[0] == '0,1,2,3':
            # remove counters for 4,5,6,6
            new_cols = [x for x in cols if not (x.find('cntr') > -1 and (x.find('CPU 4') > -1 or x.find('CPU 5') > -1 or x.find('CPU 6') > -1 or x.find('CPU 7') > -1) ) ]
            current_df = current_df[new_cols]
        elif unique_core_masks[0] == '4,5,6,7':
            new_cols = [x for x in cols if not (x.find('cntr') > -1 and (x.find('CPU 0') > -1 or x.find('CPU 1') > -1 or x.find('CPU 2') > -1 or x.find('CPU 3') > -1) ) ]
            current_df = current_df[new_cols]
        else:
            raise ValueError("Unrecognised core mask")
        if i == 0:
            combined_df = current_df
        else:
            combined_df = combined_df.append(current_df)
    print combined_df
    # in old versions of pandas the cols get mixed up
    #combined_df = combined_df[dfs[0].columns.values]
    combined_df.to_csv(os.path.join(args.directory,'xu3-combined.csv'),sep='\t')

