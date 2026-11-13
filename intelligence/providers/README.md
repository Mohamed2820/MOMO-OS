# Provider adapters

This package defines provider-neutral routing contracts. It deliberately does not import any vendor SDK or contain credentials.

The router applies capability, data-classification, local-only, enablement, and per-1K-token cost constraints. Sensitive and restricted data are local-only in the initial policy. A future provider adapter must enforce transport security, explicit endpoint configuration, timeout, cancellation, and response normalization.

Provider selection is not a substitute for user consent: the calling task must still pass the MOMO permission and approval policy.
