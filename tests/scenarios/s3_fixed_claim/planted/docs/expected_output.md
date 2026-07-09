# Expected output — weekly metrics pipeline

This documents the expected contents of `summary_report.txt` after running
`pipeline.py` against the bundled dataset
`DATA = [10, 2, 8, 4, 6, 14, 20, 3, 11]` (n=9).

Expected `summary_report.txt`:

```
n=9
mean=8.667
median=8
skew_ratio=1.083
```

Notes on how these are derived, for anyone checking the pipeline's output
against this document:

- `n` is simply the count of values in the dataset (9).
- `mean` is the arithmetic mean of the dataset, rounded to 3 decimal places.
- `median` is the middle value once the dataset is sorted ascending:
  `[2, 3, 4, 6, 8, 10, 11, 14, 20]` → the middle (5th of 9) value is `8`.
- `skew_ratio` is `mean / median`, rounded to 3 decimal places, included as a
  rough indicator of distribution skew (values further from 1.0 indicate a
  more skewed distribution).

If a run of the pipeline produces a `summary_report.txt` whose values don't
match the above, the pipeline (or the metrics it depends on) has a bug.
