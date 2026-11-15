# Individual figure inspection

On 2026-11-15 the authoring Codex agent opened **each of the 18 redesigned
PNG files individually** at its native 1200×760 resolution. All three figures
changed in the final correction pass (attention residuals, optimizer flow and
ETA contrast) were reopened afterward. The notebook is 776,066 bytes. An
independent review agent also opened the nine input/encoding/query figures
individually and checked their scientific meaning against the local source.

This inspection replaces the earlier three-card layout review. Checked labels,
contrast, clipping, arrow endpoints, dimensions, numerical assumptions, units,
validity and gradient barriers. No clipping or overlapping text remained.
Road scenes, tensor grids, mode tables, uncertainty contours, residual circuits
and state timelines now show mechanisms rather than repeating text panels.

| Figure ID | Scientific check observed |
| --- | --- |
| overview | Parallel history/map encoders -> scene -> level-0/repeated responses -> separate training and inference branches; solid A versus dashed B paths |
| scene-tensors | World (10,6), origin (10,5), heading 90° -> local (1,0); validity independent of zero |
| agent-history | .8×1 + .5×.4 = 1; .5 tanh(1) ≈ .3808; type addition -> .4808 |
| lane-encoding | Geometry/discrete fields, point position at zero adds (0,1), yielding (.5,1.6) |
| crosswalk-encoding | Selected matrix rows transform (2,-1,0) into (2,1), then ReLU |
| map-segments | Per-channel valid maxima (7,4), excluding padded 99; strict/partial policies labeled |
| scene-attention | Masked softmax (.25,.75,0), read 3.5; self residual and released no-query-residual cross block distinguished |
| initial-query | History + mode + agent vectors -> (1.5,1.5); shared joint mode index |
| gaussian-head | Current (10,2) + offset (3,1) -> (13,3); exp(0,ln2) -> std (1,2) |
| future-encoding | 1 m/.1 s -> 10 m/s; kinematics detached, future MLP remains learnable |
| future-interaction | Weighted scalar features (.5,3); released mean -> 1.75; normalized sum differs |
| reasoning-mask | Own future hidden after future self-attention; mixed other tokens may contain own information |
| full-assembly | C34 plus 80 map tokens -> 114; four released stages with [4,B,2,6,80,4] outputs |
| joint-objective | Constant errors at all80 valid steps yield joint costs20/8; constant-free NLL2 and four-term regression8; planning potential labeled |
| optimizer-update | First AdamW step with zero decay/ignored epsilon: w2 -> 1.9; sample weights precede backward, then accumulation/unscale/clip/step |
| decoding-metrics | Joint score argmax selects index1; distances1/2/3 yield ADE2 and FDE3 m; 2 Hz SDK sampling distinguished |
| checkpoint-resume | Atomic temporary-file replacement; complete optimizer/RNG state; epoch boundary only |
| tracking-eta | New-session rate2/20 -> .1 epoch/s; four remaining ->40 s; active40+20 ->60 s |

The inventory and final asset/source hashes are in
[manifest.json](../notebooks/assets/architecture/manifest.json). The automatic check
regenerates SVG/PNG bytes, validates one attachment/anchor per figure, compares
24 local architecture definitions plus all Markdown and executable-probe cells,
rejects shadowing/stored outputs, and compares
package/notebook behavior in a fresh CPU process. Automatic arithmetic fixtures
cover pooling, Gaussian loss and ETA; executable lesson probes cover additional
worked examples. Manual inspection is distinct from these automatic checks.

The PNGs are schematic worked examples with editable SVG text. The overview is
conceptual; other figures explicitly label toy values. None is a measured training
curve or paper-result figure. Source changes require asset checks and reinspection
of any changed pixels or scientific meaning.

## Review corrections and regression evidence

- The initial overview connected inputs and outputs ambiguously. Its parallel
  encoders and separate training/inference branches were corrected before release.
- The full assembly diagram now treats the shared future MLP as a between-level
  mechanism rather than drawing it into prediction-output boxes.
- A failing pixel-comparison regression exposed PNG dash spacing restarting at
  each curve segment. Continuous path-distance dashes now preserve the SVG's
  solid/dashed agent distinction; the regression passes.
- The self-attention query residual now has an independent incoming query path.
  Sample weighting is shown before backward, matching the actual trainer.
- The loss example explicitly assumes all 80 labels and three horizons are valid.
  Executable probes verify regression8, the shared winning mode's mean gradients,
  and uncertainty gradients at an interior log-standard-deviation value.

Fixed 32-color output preserves semantic colors and readable small text while
keeping the copied-alone notebook below its unchanged 1 MiB limit. SVG and PNG
use the same geometry and bundled DejaVu font. Renderer label extents are checked
on every build. The notebook remains self-contained with offline attachments;
none of these illustrations is a measured driving result.
