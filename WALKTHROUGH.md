# Walkthrough: measure a scanner yourself

A complete worked example, for a person, with every command and what you should see. It measures
**VaultLint**, a tool we have already measured, so you can compare your result to ours and know
whether you did it right.

Roughly 40 minutes, most of it a container build you can walk away from.

**Before you start**, read one paragraph in [`GETTING-STARTED.md`](GETTING-STARTED.md): the concept
of **real recall**. Without it the numbers below are meaningless.

---

## What you need

- Python 3, already required for everything here
- **Docker**, and this is the one hard rule: a scanner you did not write never runs on your machine
  directly. It runs in a container with the corpus mounted read-only.
- About 2 GB of disk for the container image

---

## Step 0. Prove the harness works before you trust it

```bash
git clone https://github.com/halobartku/scannertruth
cd scannertruth
python test_all.py
```

Expect `81 passed, 0 failed`. **If anything fails, stop.** A harness that cannot check itself cannot
tell you anything about somebody else's tool, and reporting a number from a broken harness is how
this project produced a retraction.

---

## Step 1. Find the tool's real home before downloading anything

Do not search a package registry and install the first name that matches. `cargo install radar`
would have installed **an unrelated 2021 crate by a different author**, and we would have measured a
random package and called it a competitor.

For VaultLint: the crate on crates.io, its listed repository, and the version. Check that the name
maps to the project you think it is.

**If a name does not map to a repository that mentions the tool, stop and say so.** That is a
finding, not an obstacle.

---

## Step 2. Write the mapping BEFORE you run anything

This is the step that makes the result honest. You are deciding, in advance, **which of the tool's
rules is supposed to catch which class of bug** - and you decide it from the tool's own
documentation, never from which rules turn out to fire.

```bash
cp mappings/vaultlint.json mappings/my-vaultlint.json
# now edit it: read the tool's rule list and map each rule to a corpus class
git add mappings/my-vaultlint.json
git commit -m "pre-register mapping for vaultlint"
```

**Commit it on its own, before the run.** The commit timestamp is the pre-registration, and it is
the only thing that stops you from quietly adjusting the mapping once you dislike the score.

Two outcomes are allowed and you should use them:
- `no-rule`: the tool never claimed to cover this class. A coverage gap, not a failure.
- `unmappable`: the rule's description is too broad to tie to one class.

**A trap we fell into.** X-Ray has a rule called "the account may not be properly validated". We
mapped it to one narrow class because the vendor's blog presented it as catching one specific hack.
That was an example of the rule, not its scope. It detected a real vulnerability and our mapping
scored it zero. Map from the rule's own name and docs, not from marketing.

---

## Step 3. Build the tool in a container

```bash
docker build -t vaultlint-runner:local - <<'EOF'
FROM rust:slim
RUN apt-get update && apt-get install -y --no-install-recommends \
      pkg-config libssl-dev ca-certificates && rm -rf /var/lib/apt/lists/*
RUN cargo install vaultlint --version 0.1.1 --locked
ENTRYPOINT ["vaultlint"]
EOF
```

Ten to twenty minutes. Pin the version: an unpinned build measures whatever shipped today and your
number stops being comparable to anyone else's.

Then find out how it wants to be called, because guessing wastes a whole run:

```bash
docker run --rm --entrypoint vaultlint vaultlint-runner:local --help
docker run --rm --entrypoint vaultlint vaultlint-runner:local scan --help
```

**We got this wrong and it cost 18 runs.** We passed `--format json` to the binary when it belongs
to the `scan` subcommand. All 18 failed identically. The harness correctly recorded them as
**unavailable rather than as zeros**, which is the whole point of the distinction, but the run was
still wasted.

---

## Step 4. Run it per case, per variant, with a log per run

**This is the step whose absence caused us to retract a published headline.** Do not run the tool
once over the whole corpus. Run it separately on each case and each variant, and write down what
happened each time.

Why: a findings file cannot prove a case was analysed. **A tool that ran and found nothing leaves
exactly the same silence as a tool that never saw the case.** We published "0 of 8" for two
scanners when the data behind it covered one case, because nothing recorded the difference.

```bash
mkdir -p out
for d in corpus2/*/; do
  n=$(basename "$d")
  for v in insecure secure; do
    [ -d "$d/$v" ] || continue
    docker run --rm --network none -v "$PWD/$d/$v":/work:ro -w /work \
      vaultlint-runner:local scan --format json --fail-on never /work \
      > "out/$n.$v.json" 2> "out/$n.$v.log"
    echo "$n $v rc=$?" >> out/run.log
  done
done
```

Note `--network none`: the tool has no reason to reach the internet while reading local files.

### Classifying each run, and this is where people get it wrong in both directions

| What happened | What it is |
|---|---|
| Output exists and parses | a result |
| **Exit 0, no output, tool says it found nothing** | **a clean zero** |
| Error, timeout, crash, bad arguments | **unavailable, never zero** |

We have made both mistakes. We scored invocation errors as "did not detect" (a retraction), and
then, in the harness written to prevent that, we scored a clean zero as unavailable. **Read the
tool's own last log line before deciding which one you are looking at.**

---

## Step 5. Score it

```bash
python score2.py --scanner my-vaultlint --kind sol-audit --findings out/merged.json
python unmapped_check.py --findings out/merged.json --kind sol-audit
```

You will get one verdict per case:

- **`detected`** - the mapped rule fired at the site the fix changed, and stayed silent on the fix
- **`unlocated`** - it fired in the right file but not at the bug. Neither a hit nor a clean miss,
  and the category exists so you cannot quietly pick whichever suits you
- **`missed`** - the mapped rule never fired
- **`no-rule`** - the tool has no rule for this class at all

`unmapped_check.py` asks the complementary question: **did something detect the bug under a rule
your mapping missed?** Run it. It is how we found the only real detection in the whole corpus, under
a rule we had mapped to the wrong class.

---

## Step 6. Compare to ours

Our published result: **VaultLint scores 0 of 8 on the real-vulnerability corpus, with 7 of those 8
being `no-rule`** - a stated coverage limit rather than a failure. On the teaching corpus it scores
2/11 real recall with 4 findings across 35 files, and **its precision claim held**: everything it
detected, it detected correctly.

If your numbers differ, one of us is wrong and we would like to know which. Open an issue.

---

## Step 7. Sanity-check yourself against the controls

Before believing any number you just produced:

```bash
python control_c2.py
```

The noisy control flags every non-empty line: **424,170 findings, and it must score zero.** If your
method would give it anything above zero, your method is counting volume. This is the check that
separates a measurement from a marketing figure.

---

## What a finished measurement contains

Not just the number. All five:

1. the numbers, with **real recall separated from nominal**
2. the **per-run log** proving each case was analysed, or an explicit list of what was not
3. the mapping you pre-registered, **unedited**
4. what you could not run, and why, kept **separate** from what found nothing
5. what would change the answer

**If you cannot produce item 2, you do not have a measurement yet.** Say that instead of publishing
a number. We learned this the expensive way and it is written into
[`PROTOCOL.md`](PROTOCOL.md).

---

## And one rule that outranks the rest

**If changing a threshold, a mapping, or a target would turn a zero into a number, the zero is the
finding.**

This benchmark exists because vendors tune against the corpus they are measured on. The moment you
do the same, your measurement is worth exactly what theirs is.
