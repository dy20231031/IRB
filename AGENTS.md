# Development guidance

- This project is an IRB submission preparation assistant, not an approval or exemption decision system.
- Keep institution rules separate. CUK here means Seongsim campus; SNUE is not SNU.
- A missing or unknown answer must never mean no. A false positive condition alone must never imply document exclusion.
- Every rule needs an official source and a version. Update source check dates only after actually reviewing the source.
- Never let an LLM directly change requirements. Validate extracted facts and require user confirmation.
- Preserve the bounded question loop and explicit unknown answers.
- Separate requirement status from self-reported readiness. Upload existence is not document completeness.
- Do not commit API keys, real participant data, real submissions, or generated reports.
- Use Python 3.12. Run `python -m pytest` and `python scripts/evaluate.py` after meaningful changes.
- Keep README and development docs accurate about implemented and unimplemented features. Synthetic regression results are not expert-validated accuracy.
