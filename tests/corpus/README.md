# The corpus holds 16 real prototype repos and 221 hand labels

- `corpus.lock.json` pins each public repo to one commit. All are MIT or Apache-2.0.
- `make corpus` clones them into `.cache/corpus/`. This repo does not copy their code.
- `labels/` holds the answer key. A reviewer who never saw the rules marked each fake part and risk by file and line.
- Never edit a label to make a test pass. Fix the rule, or record the disagreement in the commit body.
