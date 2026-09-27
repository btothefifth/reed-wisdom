# Task

The release candidate normalizes missing values incorrectly even though the
retained evidence says the check passed. Fix the behavior while preserving
normal nonempty values, and leave trustworthy evidence for the exact final
candidate.
