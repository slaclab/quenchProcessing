import logging
from time import sleep

from epics import PV
from numpy.linalg import LinAlgError

from lcls_tools.common.controls.pyepics.utils import PVInvalidError
from lcls_tools.superconducting.sc_linac import Cryomodule
from lcls_tools.superconducting.sc_linac_utils import (
    ALL_CRYOMODULES,
    CavityFaultError,
    HW_MODE_ONLINE_VALUE,
)
from quench_linac import QUENCH_MACHINE

WATCHER_PV: PV = PV("PHYS:SYS0:1:SC_CAV_QNCH_RESET_HEARTBEAT")
WATCHER_PV.put(0)

formatter = logging.Formatter(
    fmt="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("srf_quench_resetter")
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler("srf_quench_resetter.log", mode="w")
handler.setFormatter(formatter)
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)

while True:
    # Flag to know if we tried to reset a false quench
    issued_reset = False

    for cryomoduleName in ALL_CRYOMODULES:
        quench_cm: Cryomodule = QUENCH_MACHINE.cryomodules[cryomoduleName]

        for quench_cav in quench_cm.cavities.values():
            if quench_cav.hw_mode == HW_MODE_ONLINE_VALUE:
                if quench_cav.quench_latch_pv_obj.get() == 1:
                    try:
                        is_real = quench_cav.validate_quench(wait_for_update=True)

                        if not is_real:
                            logger.info(f"{quench_cav} FAKE quench detected, resetting")
                            quench_cav.reset_interlocks()
                            issued_reset = True

                        else:
                            logger.warning(
                                f"{quench_cav} REAL quench detected, not resetting"
                            )

                    except (
                        TypeError,
                        LinAlgError,
                        IndexError,
                        CavityFaultError,
                        PVInvalidError,
                    ) as e:
                        logger.error(f"{quench_cav} error: {e}")
                        print(f"{quench_cav} error:", e)

    # Since the resetter doesn't wait anymore, want to wait in case
    # we keep hammering one faulted cavity
    if issued_reset:
        sleep(3)
        issued_reset = False

    WATCHER_PV.put(WATCHER_PV.get() + 1)
