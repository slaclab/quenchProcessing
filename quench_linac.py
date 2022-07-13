from datetime import datetime

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
        self.srf_max_pv = self.pvPrefix + "ADES_MAX_SRF"
        self.quench_latch_pv_obj = PV(self.quench_latch_pv)
        self.pre_quench_amp = None
    
    def validate_quench(self):
        """
        Parsing the fault waveforms to calculate the loaded Q to try to determine
        if a quench was real.
        
        DERIVATION NOTES
        A(t) = A0 * e^((-2 * pi * cav_freq * t)/(2 * loaded_Q)) = A0 * e ^ ((-pi * cav_freq * t)/loaded_Q)

        ln(A(t)) = ln(A0) + ln(e ^ ((-pi * cav_freq * t)/loaded_Q)) = ln(A0) - ((pi * cav_freq * t)/loaded_Q)
        polyfit(t, ln(A(t)), 1) = [-((pi * cav_freq)/loaded_Q), ln(A0)]
        polyfit(t, ln(A0/A(t)), 1) = [(pi * f * t)/Ql]

        https://education.molssi.org/python-data-analysis/03-data-fitting/index.html
        :return:
        """
        fault_data = caget(self.fault_waveform_pv)
        time_data = caget(self.cav_time_waveform_pv)
        time_0 = 0
        try:
            # Look for time 0 (quench). These waveforms capture data beforehand
            for time_0, time in enumerate(time_data):
                if time >= 0:
                    break
            
            fault_data = fault_data[time_0:]
            time_data = time_data[time_0:]
            
            end_decay = len(fault_data) - 1
            
            # Find where the amplitude decays to "zero"
            for end_decay, amp in enumerate(fault_data):
                if amp < 0.002:
                    break
            
            fault_data = fault_data[:end_decay]
            time_data = time_data[:end_decay]
            
            saved_loaded_q = caget(self.currentQLoadedPV.pvname)
            self.pre_quench_amp = fault_data[0]
        except TypeError as e:
            print(e)
            return None
        
        try:
            exponential_term = np.polyfit(time_data, np.log(self.pre_quench_amp / fault_data), 1)[0]
            loaded_q = (np.pi * self.frequency) / exponential_term
            
            thresh_for_quench = LOADED_Q_CHANGE_FOR_QUENCH * saved_loaded_q
            print(f"\nCM{self.cryomodule.name}", f"Cavity {self.number}", datetime.now())
            print("Saved Loaded Q: ", "{:e}".format(saved_loaded_q))
            print("Last recorded amplitude: ", fault_data[0])
            print("Threshold: ", "{:e}".format(thresh_for_quench))
            print("Calculated Loaded Q: ", "{:e}\n".format(loaded_q))
            
            is_real = loaded_q < thresh_for_quench
            print("Validation: ", is_real)
            
            return is_real
        except np.linalg.LinAlgError as e:
            print(e)
            return None


QUENCH_CRYOMODULES = scLinac.CryoDict(cavityClass=QuenchCavity)
