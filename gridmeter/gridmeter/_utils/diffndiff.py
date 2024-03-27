import numpy as np
import pandas as pd

def pct_correction_factor(df,obs_col='obs',cf_col='predicted' )
    '''
    Compute the diff n diff correction factor given a data frame and two columns.
    Takes a dataframe of comparison group 
    '''
    df['correction_factor'] = df[obs_col]/ df[cf_col]
    return (df)

def correct_treatment(df, t_obs_col = 't_obs', t_cf_col='t_cf', c_obs_col='c_obs',c_cf_col='c_cf'):
    '''
    Given a dataframe compute the corrected counterfactual
    
    Takes a dataframe with treatment and comparison group observed and counterfactuals
    '''
    
    df_corrected = pct_correction_factor(df, c_obs_col, c_cf_col)
    df_corrected['t_cf_corrected'] = df_corrected['correction_factor']*df[t_cf_col]
    
    return df_corrected

