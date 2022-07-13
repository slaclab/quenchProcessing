# James Maniscalco

import os
import datetime as dt
import numpy as np
import matplotlib.pyplot as pp

QUENCH_DIR = '/home/lcls-data/rf_lcls2/fault_data/'
CAV_DIRS = [QUENCH_DIR + 'ACCL_L1B_H1' + '%s' % (i + 1) + '0/' for i in range(8)]

CAV_ACTIVE_LENGTH = 1.038  # active length of cavity
QL_QUENCH_THRESHOLD = 1e7  # if QL is lower than this, it's probably a real quench


# determine if trip was a real quench
def is_real_quench(fault_data):
    # method 1: fit QL, see if it's below threshold
    QL = calc_QL_from_decay(fault_data)
    return QL < QL_QUENCH_THRESHOLD


'''method 2: look at power ratio after 1 time constant at QL threshold.
 Not as good because it doesn't detect quenches where the QL changes over
 time (for example a quench that spreads). Could be fixed maybe by looking
 at power ratio after 10 taus.
(CAVT, CAV, FWD, REV) = fault_data
tau_for_quench_QL = QL_QUENCH_THRESHOLD / 2 / np.pi / 1.3e9
#i_quench = REV.index(max(REV))  # look for peak in reflected power at time of trip
i_quench = round(len(CAVT)/2)+1  # I think the quench files are always split on either side of the detected quench
if CAVT[-1] > CAVT[i_quench] + 2*tau_for_quench_QL: # times two because we are looking at voltage
   i_tau = next(CAVT.index(t) for t in CAVT if t > CAVT[i_quench] + 2*tau_for_quench_QL)
   # if the voltage drops by more than a factor of e, then it's probably a real quench.
   return CAV[i_tau]/CAV[i_quench] < 1/np.e
else:  # else if the quench file is too short, use the max time and figure out how far it would have dropped at the threshold QL
   return CAV[-1]/CAV[i_quench] < np.exp(-1/2/tau_for_quench_QL * (CAVT[-1] - CAVT[i_quench]))'''


# get trips for a certain cavity 
def trips_during_time_period(cavity, tmin, tmax):
    # list the trips that happened (search directory) - each is a directory
    trips = [f for f in os.listdir(CAV_DIRS[cavity - 1]) if
             os.path.isdir(os.path.join(CAV_DIRS[cavity - 1], f)) and f[0:4] == 'ACCL']
    
    # figure out trip type and time, and gradient
    trip_types = [trip[30:] for trip in trips]
    trip_times = [dt.datetime.strptime(trip[14:29], '%Y%m%d_%H%M%S') for trip in trips]
    
    # return list of tuples of time, type, and filepath
    return [(trip_times[i], trip_types[i], os.path.join(QUENCH_DIR, CAV_DIRS[cavity - 1], trips[i], trips[i] + '.txt'))
            for i in range(len(trips)) if trip_times[i] >= tmin and trip_times[i] <= tmax]


# grab the data from a fault file
def read_fault_file(filepath):
    # open the file
    with open(filepath) as f:
        file_contents = [line.split() for line in f]
    
    # loop through to get line labels (PVs)
    row_variables = [line[0] for line in file_contents]
    
    # find the row indices
    CAVT_row = [row_variables.index(i) for i in row_variables if 'CAV:FLTTWF' in i][0]
    CAV_row = [row_variables.index(i) for i in row_variables if 'CAV:FLTAWF' in i][0]
    FWD_row = [row_variables.index(i) for i in row_variables if 'FWD:FLTAWF' in i][0]
    REV_row = [row_variables.index(i) for i in row_variables if 'REV:FLTAWF' in i][0]
    
    # get the data from the rows - convert from string to float
    CAVT = [float(i) for i in file_contents[CAVT_row][2:]]
    CAV = [float(i) for i in file_contents[CAV_row][2:]]
    FWD = [float(i) for i in file_contents[FWD_row][2:]]
    REV = [float(i) for i in file_contents[REV_row][2:]]
    
    return CAVT, CAV, FWD, REV


# get the QL post quench
def calc_QL_from_decay(fault_data):  # wants a tuple of lists of floats: (CAVT, CAV, FWD, REV)
    (CAVT, CAV, FWD, REV) = fault_data
    tmax = 0.01  # look at first 10 ms after quench
    
    # slice the data - first points that are greater than target times
    # imin = REV.index(max(REV))  # look for a spike in reflected power
    imin = round(len(CAVT) / 2) + 1  # I think the quench files are always split on either side of the detected quench
    if CAVT[-1] > CAVT[imin] + tmax:
        imax = next(CAVT.index(t) for t in CAVT if t > CAVT[imin] + tmax)
    else:
        imax = len(CAVT)
    
    # add a minuscule offset in case the power meter reads zero at some point
    if min(CAV[imin:imax]) <= 0:
        CAV = [cav - min(CAV[imin:imax]) + 0.001 for cav in CAV]
    
    # linearize the quench data and fit decay constant to get QL
    try:
        QL = -2 * np.pi * 1.3e9 / np.polyfit(CAVT[imin:imax], np.log(CAV[imin:imax]), 1)[0] / 2
    except:
        QL = 0  # at low power or high noise, the max of rev power may not be at time of quench
    
    return QL


# get the gradient just before quench - returns MV/m
def quench_gradient(fault_data):
    (CAVT, CAV, FWD, REV) = fault_data
    tmax = 0  # quench moment
    
    # slice the data - just want points up to quench
    imax = next(CAVT.index(i) for i in CAVT if i > tmax) - 1
    
    # average of voltage times scaling factor to get gradient
    return np.mean(CAV[:imax]) / CAV_ACTIVE_LENGTH


# plot a trip
def plot_trip(fault_data):
    (CAVT, CAV, FWD, REV) = fault_data
    pp.plot(CAVT, CAV)
    pp.plot(CAVT, FWD)
    pp.plot(CAVT, REV)
    pp.legend(['CAV', 'FWD', 'REV'])
    ax = pp.gca()
    return ax
