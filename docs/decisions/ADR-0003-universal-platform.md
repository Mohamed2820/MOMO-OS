# ADR-0003: Device-adaptive universal mobile platform

- Status: Accepted
- Date: 2026-11-13

## Context

MOMO OS must not be architecturally constrained to one handset or Android release. Commercial phones differ substantially in boot chains, kernels, HALs, vendor components and firmware. Android and mainline Linux also expose different user-space and application ecosystems.

## Decision

Maintain one MOMO product experience and shared service/AI/security contracts over two separately integrated platform tracks: Android-compatible first, mainline Linux as a distinct track. Use per-device profiles and versioned adapters. Publish evidence-based support tiers and feature matrices.

## Consequences

- Common MOMO code can progress without a selected phone.
- Device support remains explicit and testable rather than assumed.
- Android app compatibility is a benefit of the Android track, not a property of every Linux-native port.
- A device-specific port remains necessary for each supported hardware family.
- No universal flashable image is promised.
- Multi-device claims require testing more than one distinct device family.
