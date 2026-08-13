# Workout schema

Each workout is a JSON object:

```json
{
  "id": "murph",
  "name": "Murph",
  "category": "hero",
  "format": "for_time",
  "time_cap_minutes": 60,
  "rounds": null,
  "movements": [
    { "movement": "run", "reps": 1, "unit": "mile" },
    { "movement": "pull-up", "reps": 100, "unit": "reps" },
    { "movement": "push-up", "reps": 200, "unit": "reps" },
    { "movement": "air squat", "reps": 300, "unit": "reps" },
    { "movement": "run", "reps": 1, "unit": "mile" }
  ]
}
```

## Field notes

- `category`: one of `girl`, `hero`, `open`, `benchmark` — used for filtering/grouping in the browser and dashboard.
- `format`: one of `for_time`, `amrap`, `emom`, `rounds_for_time` — display only, not used in muscle math.
- `time_cap_minutes` / `rounds`: whichever applies to the format; the other is `null`.
- `movements[].movement`: must exactly match a key in `movements.json` (the muscle mapping lookup). This is the join key between workout data and muscle logic.
- `movements[].reps` / `unit`: kept for display and future load-weighting (Phase 2) — not used in the MVP muscle load calculation, which currently treats every listed movement as equally "present" in the workout regardless of rep count.

## Why repeated movement entries stack (design decision)

Muscle load is **not** rep-count weighted — a 5-rep set and a 50-rep set of the same movement still just count as "one entry." But if a movement appears as **multiple separate entries** in the `movements` list (e.g. Open 26.1's wall-ball pyramid: 20-30-40-66-40-30-20, written as 7 entries), each entry's weight stacks. So a workout that repeats a movement across several rounds/blocks will show a proportionally higher load for that muscle group than a workout hitting it once — this is intentional, not a bug.

This gives a rough, cheap proxy for volume without doing real rep-count math (that's still deferred to a later phase). The practical rule when curating new workouts: **if the source lists a movement as N separate rounds/steps, write it as N separate entries** in `movements`, not one entry with a combined rep count. Keep entries at whatever granularity the workout itself uses (e.g. DT's 5 rounds are folded into one entry per movement since it's a flat 5x repeat, not an escalating structure — but a pyramid or ladder should be broken out, since the whole point is that some steps repeat more than others).
