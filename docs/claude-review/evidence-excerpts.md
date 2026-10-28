# Review evidence excerpts

Exact excerpts for checking the report’s central mechanism. Transcript lines come from the ignored local `downloads/results.zip`; no full transcript or request log is included. CPU-reconstructed frame counts are in `cpu-results.json`, not asserted to be historical raw frames.

## TN36 p0: multicall probe and NO-OP echo

Archive member: `transcripts/tn36-ef4dde99_p0.txt`. Member SHA-256: `acf74ccb83c812027ff4568d6dddf17bda6e6e85d280b0d1ddeaf8196bba0ef4`.

Lines 710–720:

```text
710: probes = [{'action':'MOUSE','row':42,'col':25},
711:           {'action':'MOUSE','row':42,'col':20},
712:           {'action':'MOUSE','row':55,'col':37},
713:           {'action':'MOUSE','row':20,'col':20}]
714: n0 = len(transitions)
715: for p in probes:
716:     res = action([p])
717:     print('PROBE', p['row'], p['col'], 'noop' if res.get('no_op') else 'CHANGED', 'lvl', res.get('level'), res.get('level_completed'), res.get('game_over'))
718:     show_diff(frame_diff(transitions[-1].before_frame, transitions[-1].after_frame))
719:     if res.get('level_completed') or res.get('game_over') or res.get('done'):
720:         break
```

Lines 738–745:

```text
738: [action] MOUSE(row=55, col=37) -> NO-OP (executed, no change inside the board area)
739: PROBE 55 37 noop lvl 1 False False
740:   changed 1
741:    resized {'at_before': [1, 1], 'at_after': [1, 1], 'color': 'b', 'before_pixels': 58, 'after_pixels': 57}
742:    resized {'at_before': [1, 59], 'at_after': [1, 58], 'color': 'G', 'before_pixels': 3, 'after_pixels': 4}
743: [action] MOUSE(row=20, col=20) -> NO-OP (executed, no change inside the board area)
744: PROBE 20 20 noop lvl 1 False False
745:   changed 1
```

Lines 5584–5584:

```text
5584: Hmm... wait a moment. What if the win condition is not a "state" but the ACT of clicking something specific that I haven't found? My probe list covered many cells but not all. I probed ~20 cells. The board has 4096 cells. The clickable spot could be a specific pixel — e.g., the ball's exact center? I clicked (55,37): the ball spans rows 51-59, cols ~34-40 → center ≈ (55,37). That was a no-op.
```

Lines 5616–5617:

```text
5616: The most salient "broken" thing: the two yellow pieces are separated, and they fit together. The goal is probably to bring them together. But nothing moves them...
5617: UNLESS: the yellow pieces DO move but only when a switch is toggled in the right way, and the movement is a TRANSIENT animation that ends back where it started?! No — the harness reports transient pixels for animations; my toggles reported only the segment change (4 cells = 3 segment + 1 timer).
```

## TN36 p3: surviving feedback is inspected

Archive member: `transcripts/tn36-ef4dde99_p3.txt`. Member SHA-256: `0e4013da1f24cb1694d44df1288d1a5e9f4da94a0fea16ff2824b4ead9629f72`.

Lines 1059–1060:

```text
1059: The blue ball click animated with 270 transient pixels spanning rows 13-59, cols 19-43 — that includes the yellow pieces and the ball. That's a big animation. Let me read last_animation_timeline to see what happened. Maybe the ball is a "submit"/"check" button, and the animation showed something (e.g., the top piece dropping into the bottom piece, or sparks indicating wrong).
1060: Let me inspect the timeline.
```

Lines 1066–1070:

```text
1066: t = last_action_call_result['animation']
1067: print(t['frames'], t['transient_pixels'], t['transient_bbox'])
1068: tl = last_animation_timeline
1069: for s in tl['steps']:
1070:     print(s['step'], s.get('bbox'), s.get('changes') if 'changes' in s else s.get('transitions'))
```

## SC25 p3: multicall loss and false absence claim

Archive member: `transcripts/sc25-635fd71a_p3.txt`. Member SHA-256: `314323b62c44779a04d4084bd43d1859f38b5e477dfeb83a2c1cbf2d72cdc948`.

Lines 3826–3832:

```text
3826: for (r,c) in [(55,16),(51,13),(19,14),(19,30)]:
3827:     res = action([{'action':'MOUSE','row':r,'col':c}])
3828:     d = frame_diff()
3829:     print((r,c),'noop',res.get('no_op'),'chg',d['changed_cell_count'],
3830:           [(e['at'],e['before_color'],e['after_color']) for e in d['changed_color']],
3831:           'lvl',res.get('level_completed'),'over',res.get('game_over'))
3832: print('pad',panel(current_frame),'bar',barsz(current_frame)[0])
```

Lines 3840–3846:

```text
3840: [action] MOUSE(row=51, col=13) -> NO-OP (executed, no change inside the board area)
3841: (51, 13) noop True chg 0 [] lvl False over False
3842: [action] MOUSE(row=19, col=14) -> NO-OP (executed, no change inside the board area)
3843: (19, 14) noop True chg 0 [] lvl False over False
3844: [action] MOUSE(row=19, col=30) -> NO-OP (executed, no change inside the board area)
3845: (19, 30) noop True chg 0 [] lvl False over False
3846: pad gWgWgWgWg bar 46
```

Lines 4107–4107:

```text
4107: The whole pad flashed RED twice. Red = error/flash. So clicking the cord at (19,30)... hmm, why would that flash the pad red? Maybe it's a "test/scan" of the pad. Or maybe clicking anywhere that isn't interactive triggers a "pad flash" as a generic response? Hmm, but clicks at (19,14) and (51,13) were no-ops with no animation.
```

## Source provenance

The tracked release notebook is authoritative. `notebook-v3.py` is a local cached text export; its line numbers are export coordinates, not applied-file coordinates. The two applied source caches are SHA-pinned by the existing fixture and checked against the notebook patch. Snapshots below are excerpts, not a substitute for complete source review.

### Animation record overwrite and its guard assumption

Source: `local_output/research_refs/franzen/notebook-v3.py`.

Lines 8737–8742:

```text
8737: +            animation_summary = summarize_animation(chain)
8738: +            # ONE record, replaced by every executed action - animated or not.
8739: +            # A no-op that animated is the case this exists for, and the guards
8740: +            # refuse the NEXT action without executing it, so the record still
8741: +            # describes the animated one when the model reads the opener.
8742: +            self.animation_record = (
```

### Level-gated stale guard

Source: `local_output/research_refs/franzen/notebook-v3.py`.

Lines 8526–8530:

```text
8526: +        stale_after = (
8527: +            arguments.get("stale_after")
8528: +            if STALE_STATE_BLOCK and _guards_active(_level_number(self.game))
8529: +            else None
8530: +        )
```

Lines 10198–10201:

```text
10198:     ########## guards ##########
10199:     'ARC3_GUARDS_FROM_LEVEL': 2,
10200:     'ARC3_BATCH_NOOP_BLOCK': '1',
10201:     'ARC3_STALE_STATE_BLOCK': '1',
```

### Sandbox invalidation and fetch

Source: `local_output/research_refs/franzen/ARC3-Inference/inference/agent/python_tool_sandbox.py`.

Lines 507–512:

```text
507:             action_results.append(action_result)
508:             # Cached animations describe the previous action. Invalidate the
509:             # existing views so aliases also refresh, even if a guard raises.
510:             for view in _animation_views:
511:                 view.invalidate()
512:             _refresh_state(reply.get("state") or {})
```

Lines 566–577:

```text
566:                 if not _stale_state:
567:                     _stale_state.append(str(_name))
568:             return action_result
569: 
570:         def _animation_fetch(kind):
571:             _send({"type": "animation", "request": {"kind": kind}})
572:             reply = _recv()
573:             if reply.get("type") == "animation_error":
574:                 raise RuntimeError(str(reply.get("error", "animation failed")))
575:             if reply.get("type") != "animation_result":
576:                 raise RuntimeError("Invalid animation response from sandbox host.")
577:             payload = reply.get("animation")
```

### Last-action animation summary

Source: `local_output/research_refs/franzen/ARC3-Inference/inference/agent/tool_agent.py`.

Lines 3780–3796:

```text
3780:                 for item in executed_results
3781:                 if item.get("stop_reason") == "no_op_action"
3782:             ],
3783:             # the animation of the last executed action, which is what
3784:             # last_animation_frames / last_animation_timeline will return when asked
3785:             "animation": (executed_results[-1].get("animation") if executed_results else None),
3786:             "animation_action": (
3787:                 executed_results[-1].get("action_display") if executed_results else None
3788:             ),
3789:             "guard_stops": [
3790:                 {
3791:                     "kind": item.get("stop_reason"),
3792:                     "action": item.get("blocked_action"),
3793:                     "detail": item.get("stop_detail"),
3794:                     "skipped": item.get("skipped_actions") or [],
3795:                     "trace": item.get("action_trace") or [],
3796:                 }
```
