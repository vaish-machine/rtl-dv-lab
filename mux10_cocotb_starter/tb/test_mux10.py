import random

import cocotb
from cocotb.triggers import Timer


WIDTH = 10
MASK = (1 << WIDTH) - 1


async def drive_and_check(dut, a: int, b: int, sel: int) -> None:
    a &= MASK
    b &= MASK
    sel &= MASK

    dut.a.value = a
    dut.b.value = b
    dut.sel.value = sel
    await Timer(1, unit="ns")

    expected = (a & (~sel & MASK)) | (b & sel)
    actual = int(dut.y.value)
    assert actual == expected, (
        f"Mismatch: a=0x{a:03x} b=0x{b:03x} sel=0x{sel:03x} "
        f"y=0x{actual:03x} expected=0x{expected:03x}"
    )


@cocotb.test()
async def mux10_directed_and_random(dut):
    # Exercise all eight one-bit truth-table combinations on every lane.
    for combo in range(8):
        a = MASK if combo & 0b001 else 0
        b = MASK if combo & 0b010 else 0
        sel = MASK if combo & 0b100 else 0
        await drive_and_check(dut, a, b, sel)

    # Select each lane individually to expose lane swaps/cross-coupling.
    for lane in range(WIDTH):
        sel = 1 << lane
        a = (0x155 ^ (1 << lane)) & MASK
        b = (0x2AA ^ (1 << lane)) & MASK
        await drive_and_check(dut, a, b, sel)

    # Reproducible randomized input vectors.
    rng = random.Random(0x10A5)
    for _ in range(500):
        await drive_and_check(
            dut,
            rng.getrandbits(WIDTH),
            rng.getrandbits(WIDTH),
            rng.getrandbits(WIDTH),
        )

    dut._log.info("PASS: directed and 500 randomized mux vectors")
