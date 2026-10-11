# Bugbot

Bugbot reviews pull requests. It is enabled in the Cursor dashboard for the GitHub repository. This repo does not turn it on, and a review it has not actually run must not be described as a Bugbot finding.

## Prepared branch

`demo/mgb-407-cutoff-regression` is the review branch for MGB-407. It is created from the baseline tag by `make demo-branches`. The daylight-saving cutoff mistake, when present, is only on that branch.

Open a pull request from that branch into `main` and request a Bugbot review from the PR. Existing unit tests use January dates (US standard time), so they can stay green while a March daylight-saving case is wrong. The presenter kit holds the oracle that shows the miss. Do not copy that oracle into this repository.

## If Bugbot does not flag it

That is a possible outcome. Walk the failing March case by hand: 16:30 New York on 18 March 2026 is 20:30 UTC, not 21:30 UTC. The review is still useful if a person, or a later agent, finds the fixed-offset mistake.
