---
status: superseded by ADR-0008
---

# Videos are kept until the Runner deletes them

Videos are personal data, and the privacy-first default would be to delete them right after the Analysis. We keep them instead until the Runner deletes them, because the skeleton is drawn over the original footage, and because keeping Videos leaves open the option of analyzing a Session again when the pipeline improves (re-analysis is not part of the first version). To compensate, all data is hosted in the EU, uploading requires explicit consent, and the Runner can delete a Video at any time while keeping its Analysis.

## Considered Options

- Delete Videos after N days and keep only raw keypoints: Metrics can be recomputed, but pose estimation cannot be rerun and the overlay loses its footage.
- Delete Videos right after the Analysis: rejected for the same reasons, more strongly.
