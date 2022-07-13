import numpy as np
from epics import PV, caget
from lcls_tools.superconducting import scLinac

LOADED_Q_CHANGE_FOR_QUENCH = 0.9


class QuenchCavity(scLinac.Cavity):
    def __init__(self, cavityNum, rackObject, ssaClass=scLinac.SSA,
                 stepperClass=scLinac.StepperTuner, piezoClass=scLinac.Piezo):
        super().__init__(cavityNum, rackObject)
        self.cav_power_pv = self.pvPrefix + "CAV:PWRMEAN"
        self.forward_power_pv = self.pvPrefix + "FWD:PWRMEAN"
        self.reverse_power_pv = self.pvPrefix + "REV:PWRMEAN"
        self.fault_waveform_pv = self.pvPrefix + "CAV:FLTAWF"
        self.decay_ref_pv = self.pvPrefix + "DECAYREFWF"
        self.cav_time_waveform_pv = self.pvPrefix + "CAV:FLTTWF"
        self.quench_latch_pv_obj = PV(self.quench_latch_pv)
    
    def validate_quench(self):
        """
        Parsing the fault waveforms to calculate the loaded Q to try to determine
        if a quench was real.
        
        DERIVATION NOTES
        A(t) = A0 * e^((-2 * pi * cav_freq * t)/(2 * loaded_Q)) = A0 * e ^ ((-pi * cav_freq * t)/loaded_Q)

        ln(A(t)) = ln(A0) + ln(e ^ ((-pi * cav_freq * t)/loaded_Q)) = ln(A0) - ((pi * cav_freq * t)/loaded_Q)
        polyfit(t, ln(A(t)), 1) = [-((pi * cav_freq)/loaded_Q), ln(A0)]

        https://education.molssi.org/python-data-analysis/03-data-fitting/index.html
        :return:
        """
        fault_data = caget(self.fault_waveform_pv)
        time_data = caget(self.cav_time_waveform_pv)
        idx = 0
        
        # Look for time 0 (quench). These waveforms capture data beforehand
        for idx, time in enumerate(time_data):
            if time >= 0:
                break
        
        fault_data = fault_data[idx:]
        time_data = time_data[idx:]
        
        exponential_term = np.polyfit(time_data, np.log(fault_data), 1)[0]
        loaded_q = (-np.pi * self.frequency) / exponential_term
        
        return loaded_q < LOADED_Q_CHANGE_FOR_QUENCH * caget(self.currentQLoadedPV.pvname)


QUENCH_CRYOMODULES = scLinac.CryoDict(cavityClass=QuenchCavity)
