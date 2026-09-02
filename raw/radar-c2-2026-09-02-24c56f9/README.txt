Radar at main after Auditware/radar#35, measured 2026-09-02 on the VPS host through
tools/scanner_spec.py (adapters/radar.json unchanged, mappings/radar.json unchanged, pre-registered).
radar checkout: 24c56f9747b97f15a1707c8afa755be08d501f5e (merge of #35)
api image:      ghcr.io/auditware/radar-api@sha256:f205bf7a9af877e1f5426322d1445723362ae72c9ed23f53432fd698e997af7e (label org.opencontainers.image.revision = 24c56f9747b97f15a1707c8afa755be08d501f5e, created 2026-09-01T19:45:26Z)
controller:     ghcr.io/auditware/radar-controller@sha256:82351f3cd164148787f2a158e4619da04afbaf2831aaf2879b16aa3fbf72ad3a
The 2026-08-31 measurement used ghcr.io/auditware/radar-api@sha256:b9cc652ac1e2959cae95b6502ada31473f9852509984cb6f2ae6684ede8b2911
(kept locally as auditware-radar-api:measured-2026-08-31). Rules live inside the api image
(api/builtin_templates), not in a bind mount, so the image digest is the version that matters.
This is a NEW ROW beside the old one, never a replacement.
