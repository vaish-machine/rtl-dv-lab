# Synchronous FIFO Specification

## 1. Purpose

Define a small, synthesizable, single-clock FIFO for the `rtl-dv-lab` practice repository. The specification is the contract for both the RTL and its self-checking testbench.

## 2. Default configuration

| Parameter | Default | Meaning |
|---|---:|---|
| `DATA_WIDTH` | 8 bits | Width of each data word |
| `DEPTH` | 16 words | Number of words the FIFO can store |

The RTL should be parameterized. `DATA_WIDTH` must be at least 1 and `DEPTH` must be at least 2. `DEPTH` does not need to be a power of two; read and write pointers must wrap at `DEPTH - 1`.

## 3. Clock and reset

- The FIFO uses one rising-edge clock, `clk`.
- `rst_n` is an active-low, synchronous reset. Reset takes effect only on a rising edge where `rst_n == 0`.
- On reset, the read pointer, write pointer, and occupancy become zero; `empty` becomes 1 and `full` becomes 0.
- `rd_data` becomes zero on reset.
- The storage array does not need to be reset. Its contents are invalid while the FIFO is empty and must not be relied on.
- Reset has priority over read and write requests sampled on the same edge.

## 4. Interface

| Signal | Direction | Description |
|---|---|---|
| `clk` | input | Rising-edge clock |
| `rst_n` | input | Active-low synchronous reset |
| `wr_en` | input | Request to write `wr_data` |
| `wr_data[DATA_WIDTH-1:0]` | input | Data to write |
| `rd_en` | input | Request to read the oldest word |
| `rd_data[DATA_WIDTH-1:0]` | output | Registered data from the most recently accepted read |
| `full` | output | FIFO is at capacity |
| `empty` | output | FIFO contains no words |
| `level` | output | Number of stored words, from 0 through `DEPTH` |

`level` requires `$clog2(DEPTH + 1)` bits. `full` and `empty` reflect the current occupancy and update after the active clock edge changes it.

## 5. Request acceptance and boundary behavior

Requests are accepted according to `full` and `empty` immediately before the active clock edge:

- A write is accepted when `wr_en == 1` and `full == 0`.
- A read is accepted when `rd_en == 1` and `empty == 0`.
- A rejected write does not change storage, the write pointer, or `level`.
- A rejected read does not change the read pointer or `level`; `rd_data` holds its previous value.
- `rd_data` updates on an accepted read with the oldest stored word and otherwise holds its value.

| Pre-edge state | `wr_en` | `rd_en` | Result |
|---|---:|---:|---|
| Empty | 0 | 0 | No change |
| Empty | 1 | 0 | Write accepted; `level` becomes 1 |
| Empty | 0 | 1 | Read rejected; `level` remains 0; `rd_data` holds |
| Empty | 1 | 1 | Write accepted, read rejected; `level` becomes 1 |
| Neither full nor empty | 1 | 1 | Both accepted; oldest word read, new word written, `level` unchanged |
| Full | 0 | 1 | Read accepted; `level` decreases by 1 |
| Full | 1 | 0 | Write rejected; `level` remains `DEPTH` |
| Full | 1 | 1 | Read accepted, write rejected; `level` decreases by 1 |

This is a conservative boundary policy: a read on an empty FIFO does not make a simultaneous write acceptable, and a write on a full FIFO does not become acceptable because of a simultaneous read. Acceptance is based on the pre-edge flags.

## 6. Ordering and data behavior

- Accepted words are returned in first-in, first-out order.
- A write stores `wr_data` at the current write pointer, then advances that pointer with wrap at `DEPTH - 1`.
- An accepted read returns the word at the current read pointer, then advances that pointer with wrap at `DEPTH - 1`.
- For an accepted simultaneous read and write away from the full and empty boundaries, the read returns the old head word while the write appends the new word.
- `rd_data` is a registered output, not a combinational view of the storage array.

## 7. Invariants

The implementation and testbench should check:

1. `0 <= level <= DEPTH` at all times after reset.
2. `empty == (level == 0)`.
3. `full == (level == DEPTH)`.
4. `level` increments by one for a write-only accepted operation.
5. `level` decrements by one for a read-only accepted operation.
6. `level` is unchanged when both operations are accepted or neither is accepted.
7. Every accepted read returns the oldest previously accepted, not-yet-read word.
8. Rejected requests do not corrupt FIFO ordering or occupancy.

## 8. Verification scenarios

The self-checking testbench should cover at least:

- Reset from an arbitrary prior state.
- Read while empty, including simultaneous read and write while empty.
- One write followed by one read; check returned data.
- Fill all `DEPTH` entries and check `full` and `level`.
- Attempt a write while full; check that the FIFO remains full and data order is preserved.
- Drain all entries and check `empty` and `level`.
- Attempt a read while empty; check that `rd_data` holds.
- Simultaneous read and write while partially occupied.
- Simultaneous read and write while full; verify read accepted and write rejected per this spec.
- Pointer wrap-around, using more writes and reads than the depth.
- Randomized legal and illegal requests against a software queue/reference model.

## 9. Out of scope for the first version

- Asynchronous or dual-clock FIFO behavior.
- Almost-full/almost-empty thresholds.
- Configurable overflow or underflow error outputs.
- Fall-through/combinational read behavior.
- Memory macros, ECC, or flush support.

