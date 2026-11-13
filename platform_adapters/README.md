# Platform Adapter Contract Implementation

The Python contracts in contracts.py define platform identity, capability states, typed operation specifications, requests, results, and a protocol for adapters.

The implementation is deliberately non-executing. It does not include Android Binder/HAL calls, D-Bus calls, root, shell, or direct device access.

The central runtime must authorize each operation through the permission broker before delegating to an adapter. The adapter itself must enforce its platform boundary and return a verifiable result with an audit ID.

Tests verify that unsupported, unknown, temporarily unavailable, and permission-denied capabilities are never silently treated as supported.
