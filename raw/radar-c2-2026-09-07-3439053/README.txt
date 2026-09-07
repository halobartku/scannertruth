Radar at main 3439053 (post-#41 "Print which build is running in the scan header";
the first drift with real detection-rule changes after the window #38-#40: 8 new
builtin templates, 1 removed, 5+ rewritten, AST &mut node-drop fix, test code
excluded by default), measured 2026-09-07 through the engine shim (engine code
unmodified from the checkout at /root/.radar pinned to
3439053d8da6339606ec6aee604cf2e1855e43e0). Same shim, same procedure as the
fa81c25 row of 2026-09-04; corpus 2 at its pinned commit; mapping pre-registered
(mappings/radar.json, confirmed by the vendor in radar#32 comment 5523410629).
36 invocations x2 passes (18 cases incl. the cashio calibration control), all ok,
deterministic. 217 location rows (274 at fa81c25, 228 at 24c56f9).
Rule-level delta vs fa81c25, all attributed to #38-#40:
+80 rows across the 7 new templates (Unvalidated CPI Program Account +36, PDA
Address Not Verified +11, Owner Check After CPI +10, Mint Configuration
Unvalidated +10, CPI Self Recursion +6, Rounding Favours The Caller +5,
Unvalidated Instruction Introspection +2); Account Data Matching 47->5 and
Invoke Signed Unvalidated Seeds 42->8 (rewrites in #38/#39); Unchecked
Arithmetics 45->26; Unused Function Parameters 42->0 (generic-rule FP cut,
f36d1a4 line); Missing Security Documentation absent (template removed in #38).
None of the new templates is mapped to a corpus-2 class, so per the pre-registered
mapping they score as unmapped rows, not verdicts. Scored: detected=1 (wormhole-
sysvar, unchanged) missed=8 no-rule=8 unlocated=0 (was 1/6/8/2 at fa81c25).
The two unlocated->missed flips (metaplex-token-metadata, token-2022-confidential-
approve-mint) are the Account Data Matching rewrite (#38/#39) no longer firing in
those vulnerable files at all. Fires-on-fixed for mapped rules 48->26. 40 of the 80
new-template rows land on secure variants (Unvalidated CPI Program Account 18,
PDA Address Not Verified 6, Owner Check After CPI 5, Mint Configuration
Unvalidated 5, CPI Self Recursion 3, Rounding Favours The Caller 2, Unvalidated
Instruction Introspection 1). Corpus 1 columns NOT re-measured at this revision
(rules changed; last corpus-1 measurement remains 67348ee 2026-09-02). This is a
NEW ROW beside the old ones, never a replacement.
