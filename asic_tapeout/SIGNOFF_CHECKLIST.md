# Evidence and resume claim checklist (ALL PENDING)

- [ ] Reviewed/frozen specification, interface, clock and target shuttle
- [ ] Self-checking verification PASS, functional coverage and assertions reviewed
- [ ] RTL lint warnings resolved/waived with justification
- [ ] Synthesis netlist and technology mapping captured
- [ ] SDC constraints checked and pre-route STA reviewed
- [ ] Core area, utilization, placement, clock tree and routing reviewed
- [ ] Post-route STA across applicable corners; violations documented
- [ ] DRC, LVS and antenna/density checks as supported by correct PDK/shuttle deck
- [ ] IR-drop, EM and other applicable integrity risks addressed or stated as out-of-scope/shuttle-managed
- [ ] GDS/OASIS and reproducible build reports, hashes and version data archived
- [ ] Official shuttle template, pin map and automated jobs pass
- [ ] Actual shuttle submission acknowledged/accepted
- [ ] Later: chip delivered and independently silicon-tested

Resume-safe milestones:
- **After complete evidenced layout flow:** 'Independently implemented and verified a small digital ASIC RTL-to-GDSII flow using open-source EDA tools and AI assistance.'
- **After submission is actually accepted:** 'Taped out [design] through [shuttle], [date].'
- **Only after testing hardware:** 'Performed post-silicon bring-up and validation.'

Never equate a generic hardened macro, a simple DRC pass or a submitted pull request with a manufactured/signoff-complete production ASIC.