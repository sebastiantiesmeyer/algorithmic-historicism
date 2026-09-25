# algorithmic-historicism

`algorithmic-historicism` explores whether a vision-guided modelling agent can learn reusable procedural architectural knowledge from repeated reconstruction attempts.

Core loop:

```text
vision
→ procedural reconstruction
→ render
→ evaluation
→ experience
→ knowledge
→ improved procedural skill
```

Current scope is deliberately restricted to manually selected façade components (for example rustication, pediments, and column capitals), not whole-building segmentation.

Long-term direction:

```text
whole façade image
→ hierarchical decomposition
→ repetition detection
→ component reconstruction
→ procedural assembly
→ iterative rendering/evaluation
→ accumulated architectural knowledge
→ evolving reusable skill corpus
```

Persistent layers are intentionally separated:

- raw trajectories (`runs/`)
- wiki knowledge (`wiki/`)
- candidate skills (`skills/.candidates/`)
- accepted skills (`skills/*`)

## CLI

```bash
algorithmic-historicism model --image examples/rustication/reference.png --type rustication --description "Reproduce routed lower-floor rustication"
algorithmic-historicism consolidate runs/<task-id>
algorithmic-historicism skills list
algorithmic-historicism skills evaluate routed-rustication
algorithmic-historicism evolve routed-rustication
```

## Testing

```bash
python -m pytest
```
