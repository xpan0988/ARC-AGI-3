# Execution limits only; never part of the competition notebook.
assert not TRUE_SUBMISSION, "Smoke notebook must never run as a competition submission"
bm.n_passes = 1
bm.solver.concurrency = 1
bm.solver.max_actions_per_game = 4
bm.solver.max_runtime_s_per_game = 8 * 60
bm.solver.save_request_logs = True
print("SMOKE ONLY: ls20, one pass, <=4 actions, eight-minute gameplay deadline")
