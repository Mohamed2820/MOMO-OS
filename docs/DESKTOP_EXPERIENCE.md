# MOMO Desktop Experience

Status: product and implementation specification.

## Modes
- **Phone mode:** touch-first launcher, gestures, notifications, voice, and one-app/fullscreen flows.
- **Productivity mode:** resizable windows, taskbar/dock, keyboard shortcuts, pointer support, clipboard, and drag/drop where supported.
- **External display mode:** separate desktop workspace only on devices and adapters that support display output. Do not promise wired video output on hardware without the required display capability.
- **Remote workspace:** optional browser/remote desktop integration, clearly distinguished from native local desktop mode.

## Core UX
- Persistent taskbar with pinned and running apps.
- Window controls: move, resize, minimize, maximize, snap, close.
- Keyboard-first navigation with accessible shortcuts.
- App switcher and virtual workspaces.
- File manager with explicit scoped storage permissions.
- Multi-window clipboard and drag/drop.
- Touch adaptation and safe fallback to phone mode.

## Android integration strategy
Start with launcher/system app prototypes and public Android APIs. Evaluate platform windowing and desktop mode capabilities for the chosen Android baseline. Framework modifications are allowed only when an app-level implementation cannot meet the requirement and the change has tests and a security review.

## Acceptance tests
- Window state survives supported configuration changes.
- Keyboard and pointer navigation is usable.
- Multi-window does not break phone navigation or accessibility.
- External display claims are tested on actual supported hardware.
- AI cannot secretly read or control another app's screen; screen/context capture is user-initiated and visibly indicated.
