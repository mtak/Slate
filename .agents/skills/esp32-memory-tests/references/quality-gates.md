# Quality gates and evidence

## Assertions must have a reason

1. **Semantic behavior:** production feature returns correct result and handles errors/boundaries. Every generated suite must test this, not only allocator metrics.
2. **Host memory safety:** ASan/UBSan/LSan exercise the correct source code and process exits successfully; sanitizer configuration and runtime are shown in results.
3. **Device resource health:** after warm-up and fully completed cleanup, memory remains within documented/observed steady-state limits. A single before/after heap sample is insufficient to declare a leak.
4. **Fragmentation risk:** compare largest free block across repeated variable-size workloads and account for total heap occupancy. Never assert a universal ratio without a contract.
5. **Task headroom:** collect stack high-water readings, units and budget per task while it's alive and representative workloads run.
6. **Soak:** bounded loop/time; periodic samples or summary slopes and results. Identify if test duration is insufficient to evaluate long-term drift.
7. **Reproducibility:** commands, environmental assumptions, seed, cycle count, warm-up phases, tolerance and board/SDK are discoverable.

## Calibrating thresholds

- Prefer preexisting repo requirements. Otherwise establish a stable warm baseline with a few repeated measurements in quiescent conditions.
- Distinguish transient allocation churn and asynchronous cleanup from sustained unreclaimed ownership.
- For functional operations with a known zero-retention contract, a strict (or small allocator-alignment-aware) threshold may be justified; otherwise explain any tolerance.
- Make thresholds configurable and board-specific if necessary. If no trustworthy budget exists, record measurements and mark regression thresholds as **provisional** rather than silently declaring a PASS based on arbitrary numbers.
- Document any external factors (Wi-Fi, tasks, displays) that cause nondeterminism; isolate to prevent flaky tests where practical.

## Execution statuses

| Status | Meaning |
|---|---|
| PASS | The test was executed and all assertions / sanitizer checks passed. |
| FAIL | The test was executed and failed, with evidence. |
| NOT RUN | Test was created but execution was not attempted (e.g. no physical device). |
| BLOCKED | Execution was attempted but could not run (e.g. missing toolchain, compile failure). |
| BUILD ONLY | Test firmware compiled but no runtime assertions executed. |

Never conflate these states. No board is not a reason to fabricate passing on-device results.

## Suggested reporting format

```markdown
### Memory test coverage
| Production component | Risk | Environment | Test file | Status |
|---|---|---|---|---|

### Commands and results
- `<command>` — PASS/FAIL/NOT RUN/BLOCKED/BUILD ONLY
- Toolchain and sanitizer versions: ...
- Board, framework, SDK (if applicable): ...

### Measurements (if executed)
| Scenario | Cycles | Warm-up | Free 8-bit before/after | Largest block before/after | Stack headroom | Interpretation |
|---|---:|---|---:|---:|---|---|

### Bugs and remaining gaps
- ...
```

Don't commit reports containing environment variables, secrets, access tokens, SSIDs or passwords. Do not create a PR or commit automatically unless the user asks and repository guidance permits it.
