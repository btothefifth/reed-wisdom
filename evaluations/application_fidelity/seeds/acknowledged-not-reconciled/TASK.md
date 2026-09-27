# Task

After a remote cancellation request succeeds, the application can start a
conflicting replacement even though the original item is still active remotely.
Fix the defect. A replacement must remain possible once cancellation is truly
confirmed, and the small test suite should pass.
