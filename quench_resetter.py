from lcls_tools.superconducting.scLinac import ALL_CRYOMODULES

from quench_linac import QUENCH_CRYOMODULES

while True:
    for cryomoduleName in ALL_CRYOMODULES:
        quench_cm = QUENCH_CRYOMODULES[cryomoduleName]
        for quench_cav in quench_cm.cavities.values:
            print(f"Checking {quench_cav}")
            if quench_cav.quench_latch_pv.value == 1:
                is_real = quench_cav.validate_quench(wait_for_update=True)
                if not is_real:
                    quench_cav.reset_interlocks()
