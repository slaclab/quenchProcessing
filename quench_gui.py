from typing import Dict

import numpy as np
from epics import caget
from lcls_tools.common.pydm_tools import pydmPlotUtil
from lcls_tools.superconducting.scLinac import ALL_CRYOMODULES, Cryomodule
from pydm import Display
from scipy.optimize import curve_fit

from quench_linac import LOADED_Q_CHANGE_FOR_QUENCH, QUENCH_CRYOMODULES, QuenchCavity


class QuenchGUI(Display):
    def __init__(self, parent=None, args=None):
        super().__init__(parent=parent, args=args)
        
        self.ui.cm_combobox.addItems(ALL_CRYOMODULES)
        self.ui.cav_combobox.addItems(map(str, range(1, 9)))
        
        self.current_cm = None
        self.current_cav = None
        
        self.waveform_plot_params: Dict[str, pydmPlotUtil.WaveformPlotParams] = {
            "FAULT_WAVEFORMS": pydmPlotUtil.WaveformPlotParams(plot=self.ui.cav_waveform_plot)}
        
        self.timeplot_params: Dict[str, pydmPlotUtil.TimePlotParams] = {
            "LIVE_SIGNALS": pydmPlotUtil.TimePlotParams(plot=self.ui.amp_rad_timeplot)}
        
        self.timeplot_updater: pydmPlotUtil.TimePlotUpdater = pydmPlotUtil.TimePlotUpdater(self.timeplot_params)
        self.waveform_updater: pydmPlotUtil.WaveformPlotUpdater = pydmPlotUtil.WaveformPlotUpdater(
                self.waveform_plot_params)
        
        self.update_cm()
        
        self.ui.cm_combobox.currentIndexChanged.connect(self.update_cm)
        self.ui.cav_combobox.currentIndexChanged.connect(self.update_cm)
    
    def update_cm(self):
        if self.current_cav:
            self.current_cav.quench_latch_pv_obj.clear_callbacks()
        
        self.current_cm: Cryomodule = QUENCH_CRYOMODULES[self.ui.cm_combobox.currentText()]
        self.current_cav: QuenchCavity = self.current_cm.cavities[int(self.ui.cav_combobox.currentText())]
        
        self.ui.button_ssa_on.clicked.connect(self.current_cav.ssa.turnOn)
        self.ui.button_ssa_off.clicked.connect(self.current_cav.ssa.turnOff)
        self.ui.label_ssa_status_rdbk.channel = self.current_cav.ssa.statusPV.pvname
        
        self.ui.combobox_rfmode.channel = self.current_cav.rfModeCtrlPV.pvname
        self.ui.label_rfmode_rdbk.channel = self.current_cav.rfModePV.pvname
        self.ui.button_rf_on.clicked.connect(self.current_cav.turnOn)
        self.ui.button_rf_off.clicked.connect(self.current_cav.turnOff)
        self.ui.label_rfstatus_rdbk.channel = self.current_cav.rfStatePV.pvname
        self.ui.ades_spinbox.channel = self.current_cav.selAmplitudeDesPV.pvname
        self.ui.ades_readback_label.channel = self.current_cav.selAmplitudeActPV.pvname
        self.ui.setup_button.clicked.connect(self.current_cav.setup_SELA)
        
        self.ui.cav_power_label.channel = self.current_cav.cav_power_pv
        self.ui.forward_power_label.channel = self.current_cav.forward_power_pv
        self.ui.rev_power_label.channel = self.current_cav.reverse_power_pv
        
        self.ui.latch_indicator.channel = self.current_cav.quench_latch_pv
        self.ui.latch_label.channel = self.current_cav.quench_latch_pv
        
        self.ui.bypass_button.channel = self.current_cav.quench_bypass_pv
        self.ui.unbypass_button.channel = self.current_cav.quench_bypass_pv
        self.ui.bypass_indicator.channel = self.current_cav.quench_bypass_pv + "_RBV"
        self.ui.bypass_label.channel = self.current_cav.quench_bypass_pv + "_RBV"
        
        self.ui.reset_button.clicked.connect(self.current_cav.reset_interlocks)
        
        self.timeplot_updater.updatePlot("LIVE_SIGNALS", [(self.current_cav.selAmplitudeActPV.pvname, None)])
        self.waveform_updater.updatePlot("FAULT_WAVEFORMS", [(self.current_cav.cav_time_waveform_pv,
                                                              self.current_cav.decay_ref_pv),
                                                             (self.current_cav.cav_time_waveform_pv,
                                                              self.current_cav.fault_waveform_pv)])
        
        self.current_cav.quench_latch_pv_obj.add_callback(self.quench_callback)
        self.quench_callback()
    
    def quench_callback(self):
        if self.validate_quench():
            self.ui.valid_label.setText("Real")
        else:
            self.ui.valid_label.setText("Not Real")
    
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
        cavity = self.current_cav
        fault_data = caget(cavity.fault_waveform_pv)
        time_data = caget(cavity.cav_time_waveform_pv)
        time_0 = 0
        
        # Look for time 0 (quench). These waveforms capture data beforehand
        for time_0, time in enumerate(time_data):
            if time >= 0:
                break
        
        fault_data = fault_data[time_0:]
        time_data = time_data[time_0:]
        
        time_50ms = len(time_data) - 1
        
        for time_50ms, time in enumerate(time_data):
            if time >= 50e-3:
                break
        
        fault_data = fault_data[:time_50ms]
        time_data = time_data[:time_50ms]
        
        saved_loaded_q = caget(cavity.currentQLoadedPV.pvname)
        cavity.pre_quench_amp = fault_data[0]
        
        parameters, covariance = curve_fit(cavity.expected_trace, time_data, fault_data)
        
        q_loaded = parameters[0]
        
        exponential_term, ln_A0 = np.polyfit(time_data, np.log(fault_data), 1)
        loaded_q = (-np.pi * cavity.frequency) / exponential_term
        
        thresh_for_quench = LOADED_Q_CHANGE_FOR_QUENCH * saved_loaded_q
        print(f"\nCM{cavity.cryomodule.name}", f"Cavity {cavity.number}")
        print("Saved Loaded Q: ", "{:e}".format(saved_loaded_q))
        print("Last recorded amplitude: ", fault_data[0])
        print("Threshold: ", "{:e}\n".format(thresh_for_quench))
        
        print("Polyfit")
        print("Calculated Quench Amplitude: ", np.exp(ln_A0))
        print("Calculated Loaded Q: ", "{:e}".format(loaded_q))
        
        print("Curvefit")
        print("Calculated Loaded Q: ", "{:e}".format(q_loaded))
        return loaded_q < thresh_for_quench
    
    def ui_filename(self):
        return "quench_gui.ui"
