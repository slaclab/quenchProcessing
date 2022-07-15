from typing import Dict

from PyQt5.QtCore import Qt
from epics import camonitor, camonitor_clear
from lcls_tools.common.pydm_tools import pydmPlotUtil
from lcls_tools.superconducting.scLinac import ALL_CRYOMODULES, Cryomodule
from pydm import Display
from qtpy.QtCore import Signal, Slot

from quench_linac import QUENCH_CRYOMODULES, QuenchCavity


class QuenchGUI(Display):
    quench_signal = Signal(int)
    
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
        self.quench_signal.connect(self.quench_slot, Qt.QueuedConnection)
    
    def update_cm(self):
        if self.current_cav:
            camonitor_clear(self.current_cav.quench_latch_pv)
        
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
        self.ui.srf_max_spinbox.channel = self.current_cav.srf_max_pv
        self.ui.srf_max_label.channel = self.current_cav.srf_max_pv
        
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
        
        camonitor(self.current_cav.quench_latch_pv,
                  callback=self.quench_callback, writer=print)
    
    @Slot(int)
    def quench_slot(self, value: int):
        if value == 0:
            return
        is_real = self.current_cav.validate_quench()
        if is_real is None:
            self.ui.valid_label.setText("Unknown")
        elif is_real:
            self.ui.valid_label.setText("Real")
        else:
            self.ui.valid_label.setText("Not Real")
            if self.ui.auto_reset_fake_checkbox.isChecked():
                self.current_cav.reset_interlocks()
        
        if self.ui.auto_reset_all_checkbox.isChecked():
            self.current_cav.reset_interlocks()
    
    def quench_callback(self, value, **kwargs):
        self.quench_signal.emit(value)
    
    def ui_filename(self):
        return "quench_gui.ui"
