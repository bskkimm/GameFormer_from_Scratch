# Notebook illustration redesign

**Goal:** Replace the generic text-card figures with 18 detailed graphical lessons,
retaining an executable, self-contained architecture notebook.

**Design:** Keep the existing figure coverage and stable cell anchors. Use distinct
road scenes, tensor grids, attention maps, trajectory plots and state diagrams,
with shared editable SVG/Pillow drawing primitives and bundled fonts. Expand the
adjacent explanations with worked examples and release-specific caveats.
Simply decorating the existing three-card layout would not explain computation;
generative bitmap figures would not meet editable/reproducible-asset requirements.

**Constraints:** No model/recipe changes or new dependencies. Keep offline image
attachments, empty outputs, the 1 MiB notebook limit, deterministic regeneration,
full local definitions, and package output/loss/gradient parity. All toy values
must be distinguished from measured results and full released dimensions.

- [x] Implement 18 distinct graphical compositions and shared rendering primitives.
- [x] Add explanations and ensure generated Markdown is checked for source drift.
- [x] Check every rendered figure individually, including labels and arrow meaning.
- [x] Rebuild assets/notebook; refresh bounded CPU evidence because the source
      provenance includes the teaching modules; preserve scientific limitations.
- [x] Run all required local stages and independent review. Hosted checks and
      current-head review are recorded in the delivery PR.
- [ ] Sign, push, open PR, obtain current-head pra review, fix valid findings,
      and merge after the required gates pass (user authorized merging).

Review focus: post-mixing own-future masks; detached kinematics versus live
query/score paths; released weighted-mean scaling; common coordinate frame versus
per-target map selection; shared joint mode versus planning per-agent decoding.
