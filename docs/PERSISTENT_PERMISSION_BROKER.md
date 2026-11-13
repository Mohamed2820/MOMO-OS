# Persistent Permission Broker

The persistent permission broker stores capability grants, expiry, bounded-use
counters, revocation state and authorization decisions in SQLite. Grant use is
serialized in a write transaction so replay limits survive process restarts.

R3/R4 operations still require a separate, exact match on subject, action and
resource for each approval. A stored grant alone cannot authorize those
operations. `never_allowed` grants are always denied.

This component is a policy and audit layer only. It does not execute tools,
provide native sandboxing, authenticate the user interface, or replace Android
permissions, Linux credentials, namespaces, seccomp or other platform controls.
