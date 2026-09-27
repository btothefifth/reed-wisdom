# Task

Recovery marks only the first check that reads a changed input as outdated. Fix
it so all dependent checks are selected and unrelated completed checks remain
usable. Then run the recovery script for the supplied files and leave its report
at `state/recovery.json`. The report must identify the exact implementation and
input bytes it describes. Leave the local tests passing.
