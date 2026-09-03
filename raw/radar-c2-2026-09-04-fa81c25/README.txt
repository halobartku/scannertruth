Radar at main fa81c25 (post-#36, post-skill/docs commits, punctuation-only drift ruled
non-semantic in the 2026-09-04 drift check), measured 2026-09-04 through the engine shim
(radar-engine-shim, engine code unmodified from the checkout at /root/.radar pinned to
fa81c2539fdd4e12841400045adc46d7161a5ab1). Same shim, same procedure as the 67348ee row
of 2026-09-02; corpus 2 at its pinned commit; mapping pre-registered (mappings/radar.json,
confirmed by the vendor in radar#32 comment 5523410629).
34 invocations x2 passes, all ok, deterministic. 274 location rows (228 at 24c56f9).
Deltas vs the 24c56f9 docker reference, attributed to commits between the two revisions:
+2 Unvalidated Sysvar Account at verify_signature.rs:92 and :101 (wormhole-sysvar/insecure,
commit 3cd4ae4 "Detect native Solana sysvar substitution") - silent on the secure variant;
+1 Unused Function Parameters at state.rs:85 (solido-anker, both variants, f36d1a4);
line-offset moves only on solido-deposit-reserve-account (322->378 vs old docker ref) and
spl-stake-pool-fee-rounding (481/482), same known offsets as in the 2026-09-02 shim run;
+21 rows on spl-stake-pool-mint-decimals (20x Unused Function Parameters, 1x Incorrect
Ceiling Division, f36d1a4). Scored: detected=1 (wormhole-sysvar) missed=6 no-rule=8
unlocated=2 (was 0/7/8/2 at 24c56f9). This is a NEW ROW beside the old one, never a
replacement.
