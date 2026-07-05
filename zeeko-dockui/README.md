# Zeeko DockedUI VamTimeline Patching Scripts

Python scripts for patching Zeeko (and Coffy) `.var` scene packages to wire up
VamEssentials DockedUI STOP/PREV/PLAY/NEXT buttons correctly with VamTimeline.

All scripts require Python 3 and 7-Zip at `C:\Program Files\7-Zip\7z.exe`.

## Key concepts

- **Leader atom** — the Person atom that UIButtons send `Play Anim N` to. VamTimeline
  peer-syncs all other atoms to it automatically.
- **Follower atom** — any other VT atom in the scene. Never receives explicit play/nav
  triggers; follows the leader via `SyncWithPeers`.

## Apply scripts (run in order if starting fresh)

| Script | What it does |
|---|---|
| `batch_add_playanim_nextprev.py` | Initial batch: adds DockedUI + Play Anim N triggers to NEXT/PREV *(superseded — do not rerun)* |
| `strip_playanim_nextprev.py` | Strips all `Play Anim N` from NEXT/PREV (they fired all animations at once) |
| `fix_follower_atoms.py` | Removes follower atoms from PLAY/NEXT/PREV nav actions (leader only controls) |
| `fix_play_cycle.py` | Sets PLAY button to cycle: `startActions=Play Current Clip` / `endActions=Stop` (leader only) |
| `fix_nextprev_autoplay.py` | Appends `Play Current Clip` (leader) after navigate action on NEXT/PREV |
| `rename_and_refix.py` | Renames current `.var` → `.DISABLED`, re-applies nextprev autoplay fix, verifies output |

## One-off fixes

| Script | What it does |
|---|---|
| `fix_smasher41.py` | Recovers THE_SMASHER_41 from `.2.DISABLED` source |
| `fix_coffy_nextprev.py` | Strips Play Anim N from Coffy NEXT/PREV |
| `fix_coffy_play.py` | Removes female from Coffy PLAY button (female is follower) |
| `fix_coffy_all.py` | Applies follower strip + play cycle to Coffy in one pass |
| `fix_play_autosync.py` | Intermediate attempt: adds `Stop And Reset` on followers to PLAY *(superseded by fix_play_cycle)* |

## Audit scripts

| Script | What it does |
|---|---|
| `audit_zeeko_leaders.py` | Identifies leader/follower atoms and shows current button state per package |
| `audit_deep_play.py` | Recursive scan for all VamTimeline Play triggers and `_Play` name strings |
| `audit_coffy_sxs4.py` | Compares DockedUI button structure between Coffy and sxs4 reference file |
| `audit_play_structure.py` | Dumps full PLAY button entry (all keys) + all VT receiverTargetNames in scene |
| `audit_pose_studio.py` | Scans POSE_STUDIO files for VamTimeline and `_Play` hits |
| `audit_pose_full.py` | Shows full action objects for UIButton atoms in POSE_STUDIO files |

## Final DockedUI button layout (per package)

```
STOP : Stop And Reset  → all VT atoms
PREV : Previous Animation → leader | Play Current Clip → leader
PLAY : [start] Play Current Clip → leader  /  [end] Stop → leader  (cycles)
NEXT : Next Animation → leader | Play Current Clip → leader
```
