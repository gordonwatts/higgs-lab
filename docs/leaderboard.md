# Workshop leaderboard

The table below refreshes from `leaderboard.json` every 30 seconds. Use **Refresh now** to request the latest published snapshot. The page reports when it last fetched data and when the publisher says the results were updated. A status message remains visible if loading fails.

The hosted leaderboard uses the versioned `score-v1` metric on a 30-case sealed suite with 10 null-signal cases and 20 signal cases at varied injected μ and background normalization β. The score combines the submitted fit's RMS μ residual relative to the shared baseline, uncertainty calibration, and valid-case fraction. It is set to zero when fewer than 80% of cases are valid, the μ recovery slope is at most 0.2, the false-discovery fraction exceeds 20%, the pull mean exceeds one in magnitude, the pull width is undefined, or the residual RMS is zero. The score is not classifier AUC alone. The publisher supplies the exact score definition with each JSON snapshot.

False discoveries are measured over a finite set of 10 null cases, so a zero observed fraction is not a precise rare-event limit. Compare only results from the same workshop suite and score version. Baseline rows provide reference points. The table shows the latest status for each team and links completed submissions to the exact commit. Previous attempts remain available in the history table.

<p><button id="leaderboard-refresh" type="button">Refresh now</button> <span id="leaderboard-status" role="status" aria-live="polite">Waiting for first update.</span></p>
<p id="leaderboard-updated">Results updated: not loaded</p>

## Latest results

<div id="leaderboard-latest" aria-live="polite">Loading leaderboard…</div>

## μ recovery

<div id="leaderboard-plot"></div>

## Attempt history

<div id="leaderboard-history"></div>

If a browser cannot load the data, use the instructor-linked results issue or try again later. The publisher serves aggregate result records; individual sealed-suite truth values are not published.

<script src="../assets/leaderboard.js" defer></script>
