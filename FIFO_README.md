# FIFO starter project

This bundle contains a parameterized synchronous FIFO, a self-checking testbench, a Makefile, and the design specification.

## Copy into `rtl-dv-lab`

Copy the contents of this bundle into the matching locations in the repository:

```text
rtl/fifo.sv          -> rtl/fifo.sv
verif/tb_fifo.sv     -> verif/tb_fifo.sv
Makefile             -> Makefile (repo root)
FIFO_SPEC.md         -> FIFO_SPEC.md (repo root)
```

The Makefile defines `build/fifo/` for its generated simulation executables, so it will not overwrite the existing counter simulation output in `build/`.

## Run

From the repository root:

```bash
make sim
```

This compiles and runs the self-checking testbench at the default depth of 16 and again at a non-power-of-two depth of 5. Both runs should print `PASS` and coverage counters. The testbench includes reset checks, empty/full boundary tests, simultaneous read/write checks, fill/drain ordering, and deterministic pseudo-random traffic.

Run RTL lint with Verilator if installed:

```bash
make lint
```

If you use Git, consider adding `/build/` to the existing `.gitignore` so generated simulator output stays untracked. Review the existing file before editing it.

## Contract notes

- One rising-edge clock and synchronous active-low reset.
- Default capacity is 16 words, 8 bits per word; both are parameters.
- Reads are registered in `rd_data`.
- Reads while empty and writes while full are rejected.
- At empty, simultaneous read/write accepts only the write.
- At full, simultaneous read/write accepts only the read.
- Away from both boundaries, simultaneous read/write accepts both and preserves FIFO order.

This is a practice design and testbench, not a proof of bug-free behavior. Expand the tests and review the RTL before relying on it in a product.
