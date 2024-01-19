from datetime import datetime
from time import sleep

import numpy as np
from lcls_tools.common.controls.pyepics.utils import PV
from lcls_tools.superconducting import scLinac

LOADED_Q_CHANGE_FOR_QUENCH = 0.6


class QuenchCavity(scLinac.Cavity):
    def __init__(
        self,
        cavityNum,
        rackObject,
        ssaClass=scLinac.SSA,
        stepperClass=scLinac.StepperTuner,
        piezoClass=scLinac.Piezo,
    ):
        super().__init__(cavityNum, rackObject)
        self.cav_power_pv = self.pv_addr("CAV:PWRMEAN")
        self.forward_power_pv = self.pv_addr("FWD:PWRMEAN")
        self.reverse_power_pv = self.pv_addr("REV:PWRMEAN")

        self.fault_waveform_pv = self.pv_addr("CAV:FLTAWF")
        self._fault_waveform_pv_obj: PV = None

        self.decay_ref_pv = self.pv_addr("DECAYREFWF")

        self.cav_time_waveform_pv = self.pv_addr("CAV:FLTTWF")
        self._cav_time_waveform_pv_obj: PV = None

        self.srf_max_pv = self.pv_addr("ADES_MAX_SRF")
        self.pre_quench_amp = None
        self._quench_bypass_rbck_pv: PV = None
        self._current_q_loaded_pv_obj: PV = None

    @property
    def current_q_loaded_pv_obj(self):
        if not self._current_q_loaded_pv_obj:
            self._current_q_loaded_pv_obj = PV(self.current_q_loaded_pv)
        return self._current_q_loaded_pv_obj

    @property
    def hw_mode_pv_obj(self) -> PV:
        if not self._hw_mode_pv_obj:
            self._hw_mode_pv_obj = PV(self.hw_mode_pv)
        return self._hw_mode_pv_obj

    @property
    def hw_mode(self):
        return self.hw_mode_pv_obj.get()

    @property
    def quench_latch_pv_obj(self) -> PV:
        if not self._quench_latch_pv_obj:
            self._quench_latch_pv_obj = PV(self.quench_latch_pv)
        return self._quench_latch_pv_obj

    @property
    def quench_intlk_bypassed(self) -> bool:
        if not self._quench_bypass_rbck_pv:
            self._quench_bypass_rbck_pv = PV(self.pv_addr("QUENCH_BYP_RBV"))
        return self._quench_bypass_rbck_pv.get() == 1

    @property
    def fault_waveform_pv_obj(self) -> PV:
        if not self._fault_waveform_pv_obj:
            self._fault_waveform_pv_obj = PV(self.pv_addr("CAV:FLTAWF"))
        return self._fault_waveform_pv_obj

    @property
    def cav_time_waveform_pv_obj(self) -> PV:
        if not self._cav_time_waveform_pv_obj:
            self._cav_time_waveform_pv_obj = PV(self.cav_time_waveform_pv)
        return self._cav_time_waveform_pv_obj

    def reset_interlocks(self, wait: int = 0, attempt: int = 0):
        """Overwriting base function to skip wait/reset cycle"""
        print(f"Resetting interlocks for {self}")

        if not self._interlock_reset_pv_obj:
            self._interlock_reset_pv_obj = PV(self.interlock_reset_pv)

        self._interlock_reset_pv_obj.put(1)

    def validate_quench(self, wait_for_update: bool = False):
        """
        Parsing the fault waveforms to calculate the loaded Q to try to determine
        if a quench was real.

        DERIVATION NOTES
        A(t) = A0 * e^((-2 * pi * cav_freq * t)/(2 * loaded_Q)) = A0 * e ^ ((-pi * cav_freq * t)/loaded_Q)

        ln(A(t)) = ln(A0) + ln(e ^ ((-pi * cav_freq * t)/loaded_Q)) = ln(A0) - ((pi * cav_freq * t)/loaded_Q)
        polyfit(t, ln(A(t)), 1) = [-((pi * cav_freq)/loaded_Q), ln(A0)]
        polyfit(t, ln(A0/A(t)), 1) = [(pi * f * t)/Ql]

        https://education.molssi.org/python-data-analysis/03-data-fitting/index.html

        :param wait_for_update: bool
        :return:
        """

        if wait_for_update:
            print(f"Waiting 0.1s to give {self} waveforms a chance to update")
            sleep(0.1)

        time_data = self.cav_time_waveform_pv_obj.value
        fault_data = self.fault_waveform_pv_obj.value
        time_0 = 0

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

        saved_loaded_q = self.current_q_loaded_pv_obj.get()

        self.pre_quench_amp = fault_data[0]

        exponential_term = np.polyfit(
            time_data, np.log(self.pre_quench_amp / fault_data), 1
        )[0]
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


QUENCH_CRYOMODULES = scLinac.CryoDict(cavityClass=QuenchCavity)
