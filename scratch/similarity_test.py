from numpy import exp, linspace, pi


def expected_trace(time, pre_quench_amp, cav_freq, q_loaded):
    rt = -(pi * cav_freq * time) / q_loaded
    return pre_quench_amp * exp(rt)


def sum_square(trace1, trace2):
    if len(trace1) != len(trace2):
        print("arrays not same size")
    else:
        deltas = []
        for idx, element in enumerate(trace1):
            deltas.append((element - trace2[idx]) ** 2)
        return sum(deltas)


def main():
    times = linspace(start=-30e-3, stop=30e-3, num=10)
    trace1 = [expected_trace(pre_quench_amp=18e6, cav_freq=1.3e9, time=t, q_loaded=4e7) for t in times]
    trace2 = [expected_trace(pre_quench_amp=18e6, cav_freq=1.3e9, time=t, q_loaded=1e7) for t in times]
    print(times)
    print(trace1)
    print(trace2)
    
    print(sum_square(trace1, trace2))


main()
