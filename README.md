# The Machine — companion repository

**Article:** [Quest for Entropy #2 — "The Machine"](https://questforentropy.substack.com/p/the-machine)

**Series:** ← [#1 The Universe with No Dice](https://github.com/masteris777/quest-for-entropy-the-universe-with-no-dice) · [#3 The Machine Takes a Quantum Exam](https://github.com/masteris777/quest-for-entropy-quantum-exam) →

Evidence repo for **Quest for Entropy #2: [“The Machine”](article.md)** — the piece that
takes the clockwork apart. Ninety-six free-running rotors, a three-number state, and the
one move that makes the whole thing quantum-looking: **the fold**.

This is the *run it yourself and check every number* pack. Every mechanism number the
article quotes — including the fully worked fold at tick 1000, digit for digit — is
re-measured here from the machine itself and printed next to what the article claims.

## Run it

```
pip install -r requirements.txt
python run_all.py
```

That is the whole thing. It takes **about two seconds**, needs no arguments and no
network, and writes nothing to disk. Verified working command on the author's machine
(Windows 11, CPython 3.12.11, numpy 2.3.5, scipy 1.16.3, sympy 1.14.0, matplotlib 3.10.7):

```
cd quest-for-entropy-the-machine
python run_all.py
```

Compare against `expected_output/run_all.txt`, which is the captured output of a real
successful run:

```
python run_all.py > mine.txt
diff mine.txt expected_output/run_all.txt
```

Only the final timing line should differ.

## Scope: this pack is about the MECHANISM

The article has two halves. This repository certifies the first one — **how the machine
works**. The twenty-question quantum exam, its eighteen passes, and the interference
floor the machine cannot get past are **episode 3's** subject, and their evidence ships
with episode 3. No exam lab is pulled in here, on purpose.

## What each article claim maps to

| the article says | checked by |
|---|---|
| “Ninety-six of them, in sixteen groups of six”; speeds `ω = 2π·frac(√n)`; “the numbers under the root must be square-free — 2, 3, 5, 6, 7, 10, 11, skipping 4, 8, 9, 12”; “the speeds never line up” | **check 1** — counts the pool, verifies every accepted integer is distinct and square-free, verifies the rate law to machine zero, verifies the candidate stream skips 4/8/9/12, and proves no two rates are rationally locked *at any order* (exact integer test: for distinct square-free `n_i, n_j`, `n_i·n_j` is never a perfect square, so `p·√n_i − q·√n_j` is never an integer) |
| “The three arrows have lengths 1.425, 0.378 and 0.417… The first one wins.” / “a thousand divided by sixteen leaves eight, so it read group eight” / “The winner's direction gets a big size — 1.31. The two others get smaller ones — 0.93 and 0.50.” / “the three arrows now measure exactly 1.31, 0.93 and 0.50. The arrows *are* the state.” | **check 2** — replays the certified run to tick 1000 and reproduces all nine numbers, the winner index, and the generator index |
| “The winner's size is almost perfectly pinned… The losers' sizes *wander* widely… they roam from almost nothing to nearly the winner's size.” | **check 3** — 5000 folds; winner spread vs loser spreads and the ratio between them |
| “the winner sits about **two and a half times** the losers on average, while single events scatter well above and below that” | **check 4** — median per-event lean, its definition stated explicitly in the output, and the per-event range |
| “And the rotors? Untouched… We checked this to the last decimal place: the pool's path is identical whether the observer measures or not.” | **check 5** — the rotor-pool trajectory with folds minus the trajectory without, over 5000 ticks × 96 rotors. Prints `0.0` |
| “Measure twice in a row, get the same result… That is the collapse postulate, and we never wrote it down anywhere.” | **check 6** — re-measures each fold immediately, before the substrate turn |
| “It can be derived from the geometry, and when we did that, the number the maths puts there is the number an optimizer had found hundreds of experiments earlier.” | **check 7** — the derived fixed point `r* = 2.505144` against the certified recipe's ratio `2.505757`, recomputed live from the frozen recipe. **See the honesty note below** |

### One honest caveat, stated up front

**Check 7 is the only item that is not re-derived from scratch here.** Deriving `r*`
is Lab 167b's job; it needs the Lab 122 three-channel-lift chain and about seven minutes
of certified quadrature, which is a different pack's weight class. What runs here reads
the frozen `metrics_167b.json`, recomputes the *certified recipe's* ratio live from
`theta_91`, and checks the two against each other and against Lab 167b's own declared
tolerance. The derivation script ships alongside so you can diff it line-by-line against
the research repo, but to re-run it you need the full lab tree. `run_all.py` says this in
its own output too — it is not hidden in a README.

## What is in here

```
run_all.py                the runner and the claim checker - the whole point
machine/                  the certified lab code, mirrored from the research repo with
                          the executable code untouched; folder names preserved
expected_output/          the captured output of a real successful run
article.md, assets/       the article as published, and its figures
MANIFEST.sha256           checksums of everything above
.gitattributes            disables EOL conversion, so those checksums verify on
                          Windows, macOS and Linux alike
```

The numbered folder names (`88_`, `91_`, `93_`…) are the research lab numbers, kept
because the import chain resolves by folder name — renaming them would break it. They
are a filing system, not a claim about anything.

**Source headers were normalized for public release**: comment and docstring references
to the private research tree — internal run commands, lab-goal and feedback documents,
cross-lab report names — were replaced with plain descriptions of what each file does.
**The executable logic is unmodified.** Only comments and docstrings changed, with one
stated exception: a single diagnostic *message string* in `ratio_surface_167b.py` named an
internal review document, and that name was removed. No control flow, no arithmetic, no
constant used by any calculation was touched anywhere. `run_all.py` re-verifies every
number against the stripped files that actually ship.

`machine/` contains only the files the fold actually needs, nothing else — no reports,
no figures, no unrelated stages:

```
100_repreparation_fold/repreparation_fold_100_v2.py   THE fold
                                                      (build_state_from_pool, run_model_two)
95_reservoir_bank_scout/reservoir_bank_scout_95.py    the import chain, in order:
94_fold_reservoir_scout/fold_reservoir_scout_94.py      100v2 -> 95 -> 94 -> {93v2, 91v2} -> 88
93_embedded_fold_scout/embedded_fold_scout_93_v2.py   the substrate turn U_S and z0
91_two_time_conditional_born/two_time_conditional_born_91_v2.py   the frame and the counters
88_forced_complex_structure/forced_complex_structure_88.py        the forced complex structure
92_classical_completion/metrics_92.json               frozen constants lab 93 v2 reads at import
99_variational_floor/metrics_99.json                  the recipe theta_91 - frozen before any
                                                      number in this article was measured
167_ratio_fixed_point/metrics_167b.json               the derived fixed point r* (frozen record)
167_ratio_fixed_point/ratio_surface_167b.py           its derivation, for reading and diffing
```

Verify the mirror:

```
sha256sum -c MANIFEST.sha256          # or: shasum -a 256 -c MANIFEST.sha256
```

## What this does NOT claim

> This is a **demonstration of a mechanism, not a claim about nature.** It does not say
> our universe is a clockwork, does not reinterpret quantum mechanics, and does not dodge
> Bell's theorem — the hidden machinery is *global*, not local, exactly because Bell rules
> out the local kind. The recipe was found by an optimizer and only later shown to sit at
> a fixed point of the geometry; the build is engineering, and we say so. The claim is
> only this: quantum-looking behaviour *can* come out of a deterministic machine plus a
> physical measurement — not that this is *why* our world is quantum. Everything here
> describes one family of machines at the settings we tested.

Specifically **not** claimed by anything in this repository: that the machine passes the
quantum exam (that is episode 3's evidence, not this pack's); that the fold is unique;
that any of this beats quantum mechanics anywhere. It does not — and where it falls short,
episode 3 measures by how much.

## How this was made

The author is a software architect, not a physicist. The direction, the questions and
the calls are his; the heavy lifting — the math, the physics checks, the code, the sums —
is AI. To keep that honest, the work runs through a harness: **every experiment declares
its pass marks before it runs**, a mark may be made harder afterwards but never softer,
results are challenged by independent adversarial AI review, and every mistake caught goes
into a **public honesty ledger** rather than quietly out of the record. Nothing in this
repository comes from a model's memory: every number is printed by code you can run, and
`run_all.py` fails loudly if any of them stops reproducing.

## License

Code: MIT. Article text and figures: CC BY 4.0. See `LICENSE`.
