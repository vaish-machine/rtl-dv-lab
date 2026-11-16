# SPDX-License-Identifier: Apache-2.0
# Stage 3B educational Tiny Tapeout template RTL cocotb candidate.
# Not provider CI/precheck, no gate-level or real clock/CDC signoff.
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, RisingEdge, Timer

CPB = 16

async def sample_after_edges(clk, n):
    await ClockCycles(clk, n)
    await Timer(1, unit="ns")

@cocotb.test()
async def test_uart_wrapper_pin_map_tx_rx(dut):
    dut.rst_n.value = 0
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0x02  # rx_i idle high, tx_valid low
    cocotb.start_soon(Clock(dut.clk, 100, unit="ns").start())
    await sample_after_edges(dut.clk, 5)
    assert int(dut.uio_oe.value) == 0x3C, "Unexpected TT output-enable mask"
    assert int(dut.uio_out.value) & 0x0C == 0x0C, "Expected idle tx_ready and tx_o"
    await FallingEdge(dut.clk)
    dut.rst_n.value = 1
    await sample_after_edges(dut.clk, 3)

    # Transmit 0xA5 serially through TT uio output bit 3.
    await FallingEdge(dut.clk)
    dut.ui_in.value = 0xA5
    dut.uio_in.value = 0x03  # valid asserted; RX idle high
    await sample_after_edges(dut.clk, 1)
    assert int(dut.uio_out.value) & 0x08 == 0, "UART start bit missing"
    assert int(dut.uio_out.value) & 0x04 == 0, "TX ready must deassert"
    await FallingEdge(dut.clk)
    dut.uio_in.value = 0x02
    for bit in range(8):
        await sample_after_edges(dut.clk, CPB)
        actual = (int(dut.uio_out.value) >> 3) & 1
        expected = (0xA5 >> bit) & 1
        assert actual == expected, f"TX bit {bit}: {actual} != {expected}"
    await sample_after_edges(dut.clk, CPB)
    assert int(dut.uio_out.value) & 0x08, "Stop bit must be high"
    await sample_after_edges(dut.clk, CPB)
    assert int(dut.uio_out.value) & 0x04, "tx_ready must return high"

    rx_samples = []
    async def monitor_rx():
        while True:
            await RisingEdge(dut.clk)
            await Timer(1, unit="ns")
            if int(dut.uio_out.value) & 0x10:
                rx_samples.append(int(dut.uo_out.value))
    cocotb.start_soon(monitor_rx())

    async def send_rx_bit(value):
        await FallingEdge(dut.clk)
        dut.uio_in.value = (int(value) & 1) << 1
        await sample_after_edges(dut.clk, CPB)

    await send_rx_bit(0)
    for bit in range(8):
        await send_rx_bit((0x5A >> bit) & 1)
    await send_rx_bit(1)
    await sample_after_edges(dut.clk, 8)
    assert rx_samples == [0x5A], f"Expected one RX 0x5A valid pulse: {rx_samples}"
    assert int(dut.uo_out.value) == 0x5A, "Dedicated outputs miswired"
    assert int(dut.uio_out.value) & 0x20 == 0, "Unexpected framing error"
    assert int(dut.uio_oe.value) == 0x3C, "TT direction mask changed"
