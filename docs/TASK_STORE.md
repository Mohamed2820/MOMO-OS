# Persistent task store

The runtime now has an optional SQLite-backed task journal in
`intelligence/runtime/task_store.py`.

- Task state and transition reasons survive process restarts.
- State changes are serialized with SQLite `BEGIN IMMEDIATE` transactions.
- Transition events are append-only; invalid state changes are rejected before
  a database update is committed.
- The store does not execute tools or confer OS permissions.
- High-risk tasks still cannot move directly from planned to executing. The
  platform permission broker and explicit approval UI remain separate gates.

The default target database path is `/var/lib/momo/tasks.sqlite3`; callers may
supply a different path for tests and development.
