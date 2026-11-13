# Device Inventory Service

The runtime inventory service reports facts observable from the running kernel
and operating system: platform track metadata, architecture, kernel release,
OS identity, hostname and device model when exported by device tree or DMI.

It deliberately does not infer camera, modem, GPU, biometric or other hardware
support from a device name or CPU architecture. Without a profile whose exact
device identity has been verified by the caller, all hardware capabilities
remain `unknown`.

A verified profile can mark a feature supported only when its evidence state
is `functional` or `regression_tested`. A profile architecture mismatch is
rejected. The service is an inventory/reporting layer, not a driver loader or
a hardware compatibility guarantee.
