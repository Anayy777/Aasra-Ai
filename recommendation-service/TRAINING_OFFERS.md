# Connecting NQR qualifications to real training

The NQR workbook describes qualifications. It does not prove that a centre is
running a batch or has an open seat. Keep batch data in a separate file named
`data/training_offerings.csv`, following the header in
`data/training_offerings.example.csv`.

One row is one currently open batch. `qualification_id` must match the NQR ID
used by the recommender. Record the source page in `source_url` and the date
the team checked it in `verified_at` (`YYYY-MM-DD`). Entries without a recent
verification date are excluded after 30 days. `start_date` also uses
`YYYY-MM-DD`. Use `open` in `status`; other values are excluded.

`employment_pathway` can be `self_employment`, `wage_employment`, `both`, or
blank if the outcome is unknown. `accessibility_confirmed` can be `yes`, `no`,
or blank; blank is explicitly shown as unverified when a beneficiary has an
access need. Coordinates allow distance filtering against a stated travel
limit. Without coordinates, the beneficiary's location must match the row's
district or state exactly. Collect district explicitly for reliable matching.

Suggested workflow: use the Skill India Digital Hub to find current PMKVY
batches and their centre, partner, date and batch ID; use the NCVT MIS ITI
directory to find centres. Verify the job role or qualification ID, contact the
centre to confirm that the batch and enrollment link are current, then add the
row. Do not copy a centre directory entry into this file as an open batch.

If the file is absent or no row passes these checks, the API returns
`training_availability: "unverified"` or an empty `training_options` list.
The qualification recommendation still works, but does not claim a place is
available.
