from epics import PV
from lcls_tools.superconducting.sc_linac_utils import (ALL_CRYOMODULES,
                                                       CavityFaultError,
                                                       HW_MODE_ONLINE_VALUE)
from numpy.linalg import LinAlgError

from quench_linac import QUENCH_CRYOMODULES, QuenchCryomodule

WATCHER_PV: PV = PV("PHYS:SYS0:1:SC_CAV_QNCH_RESET_HEARTBEAT")
WATCHER_PV.put(0)

while True:
    for cryomoduleName in ALL_CRYOMODULES:
        quench_cm: QuenchCryomodule = QUENCH_CRYOMODULES[cryomoduleName]
        for quench_cav in quench_cm.cavities.values():
            if quench_cav.hw_mode == HW_MODE_ONLINE_VALUE:
                if (not quench_cav.quench_latch_invalid
                        and quench_cav.quench_latch_pv_obj.get() == 1):
                    try:
                        is_real = quench_cav.validate_quench(wait_for_update=True)
                        
                        if not is_real:
                            quench_cm.logger.info(f"{quench_cav} FAKE quench detected, resetting")
                            quench_cav.reset_interlocks()
                        
                        else:
                            quench_cm.logger.warning(f"{quench_cav} REAL quench detected, not resetting")
                    
                    except(TypeError, LinAlgError, IndexError, CavityFaultError) as e:
                        quench_cm.logger.error(f"{quench_cav} error: {e}")
                        print(f"{quench_cav} error:", e)
    
    WATCHER_PV.put(WATCHER_PV.get() + 1)
