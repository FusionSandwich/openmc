# StellarCSG next-research handoff index

Qualified implementation preserved at:

```text
Commit: c67b68fdaf7be2049308db7da449f14a25123847
Archive branch: archive/stellarcsg-qualified-c67b68fd-20260831
```

The archive branch is a recovery point and must not be rewritten.

## Execution prompt

`TORUS_CLASS_IMPLEMENTATION_CODEX_PROMPT.md`

Use this when the next Codex agent is expected to implement, compile, test, benchmark, commit, and push the targeted torus-class performance work. It preserves the current implementation as selectable baselines and directs high-risk work to a child worktree/branch before validated commits are brought back.

## Open-ended research handoff

`OPEN_ENDED_RESEARCH_HANDOFF.md`

Use this when the next agent should independently reassess the problem, conduct a broad primary-source literature review, identify alternative mathematical and computational-geometry approaches, and recommend research directions without being constrained to the current proposed Bézier, algebraic-proxy, BVH, or coil-intersection methods.

## Repository constraints

- Work only inside `FusionSandwich/openmc`.
- Do not modify default or upstream OpenMC branches.
- Do not create a pull request or draft pull request.
- Keep `OPENMC_ENABLE_EXPERIMENTAL_STELLARCSG=OFF` by default.
- Preserve current tests, raw results, plots, source hashes, negative results, geometry-debug findings, and independent oracles.
- Do not call a method qualified until it has been compiled and executed.
