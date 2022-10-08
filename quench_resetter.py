from quench_linac import QUENCH_CRYOMODULES

while True:
    for quench_cm in QUENCH_CRYOMODULES:
        for quench_cav in quench_cm.cavities.values:
            if quench_cav.quench_latch_pv.value == 1:
                is_real = quench_cav.validate_quench(wait_for_update=True)
                if not is_real:
                    quench_cav.reset_interlocks()
