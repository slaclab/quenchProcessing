from epics import PV
from lcls_tools.superconducting.scLinac import ALL_CRYOMODULES

from quench_linac import QUENCH_CRYOMODULES

WATCHER_PV: PV = PV("PHYS:SYS0:1:SC_CAV_QNCH_RESET_HEARTBEAT")
WATCHER_PV.put(0)

while True:
    for cryomoduleName in ALL_CRYOMODULES:
        quench_cm = QUENCH_CRYOMODULES[cryomoduleName]
        for quench_cav in quench_cm.cavities.values():
            if quench_cav.quench_latch_pv.value == 1:
                is_real = quench_cav.validate_quench(wait_for_update=True)
                if not is_real:
                    quench_cav.reset_interlocks(wait=False)
    WATCHER_PV.put(WATCHER_PV.get() + 1)
