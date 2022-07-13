import numpy as np
from epics import PV
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
        self.pre_quench_amp = None
    
    def expected_trace(self, time, q_loaded):
        exponential_term = -(np.pi * self.frequency * time) / q_loaded
        return self.pre_quench_amp * np.exp(exponential_term)


QUENCH_CRYOMODULES = scLinac.CryoDict(cavityClass=QuenchCavity)
