# James Maniscalco

import quench_tools as qt
import datetime as dt

# set time bounds
tmin = dt.datetime(2021, 6, 10, 11, 30, 0)
tmax = dt.datetime(2021, 6, 30)

# get list of all faults in the time bounds, for all cavs
trips = [qt.trips_during_time_period(i + 1, tmin, tmax) for i in range(8)]
# trips = [ [(trip time, trip type, trip path), other cav 1 trips...],
#           [ cavity 2 trips ...] ...]

# downselect to real quenches
quenches = [[trip for trip in cav_trips if qt.is_real_quench(qt.read_fault_file(trip[2])) and trip[1] == 'QUENCH'] for
            cav_trips in trips]

for cavity in range(len(quenches)):
    print('Cavity ' + str(cavity + 1))
    for quench in quenches[cavity]:
        print(quench[0].isoformat() + ', ' + str(qt.quench_gradient(qt.read_fault_file(quench[2]))))
