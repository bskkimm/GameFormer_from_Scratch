# GameFormer illustration inventory

Exactly **18 distinct instructional figures**, each with an editable SVG, compact
PNG and offline Markdown attachment. There is exactly one opening overview.
All values in mechanism figures are reduced illustrative examples, not learned
weights or measured benchmark results. Full released dimensions are D256, C34,
P2, M6, H11, T80; the default executable probes use the named D32 CPU smoke model.

| ID / notebook anchor | Exact placement | Visual computation | Source |
| --- | --- | --- | --- |
| overview | Introduction before setup | Intersection scene; parallel encoders; decoder outputs branch into training and inference | model.py |
| scene-tensors | Before sample preparation | World/local coordinate axes, rotated point and explicit validity tensor | geometry.py, data.py |
| agent-history | Before AgentEncoder | Two-layer recurrent unroll and an expanded scalar gate circuit | model.py |
| lane-encoding | Before LaneEncoder | Curved lane/boundaries, parallel feature embeddings, concatenation and position wave | model.py |
| crosswalk-encoding | Before CrosswalkEncoder | Polygon/point samples and matrix multiplication through a point MLP | model.py |
| map-segments | Before segment_points | Colored channel winners, masked padding and strict/partial segment decisions | model.py |
| scene-attention | Before AttentionBlock | Masked logits, probability bars, weighted read and actual residual routes | model.py |
| initial-query | Before level-0 query definition | Vector addition and agent-by-mode query grid with distinct output heads | model.py |
| gaussian-head | Before GaussianHead | Offset geometry, Gaussian uncertainty contours and mode scores | model.py |
| future-encoding | Before FutureEncoder | Position differences, eight kinematic channels, gradient barrier and time pooling | model.py |
| future-interaction | Before InteractionDecoder | Probability-weighted mode grid with released 1/M factor and agent mixing | model.py |
| reasoning-mask | Before level-k mask probe | Visible/hidden context paths after future mixing and live own-query route | model.py |
| full-assembly | Before GameFormer | Reused scene-context bus, four decoder levels and stacked output shapes | model.py |
| joint-objective | Before objective | Shared-winner cost table, constant-free Gaussian NLL and all-level score supervision | losses.py |
| optimizer-update | Before backward/update | Loss/backward/accumulation/clip flow and worked first AdamW update | engine.py |
| decoding-metrics | Before inference/metrics | Scored joint paths, target distances, ADE/FDE and official resampling | evaluation.py |
| checkpoint-resume | Beside opt-in recovery | State bundle, atomic file publication and next-epoch recovery | engine.py |
| tracking-eta | Beside tracking | Wall/active timeline, completed-epoch blocks and remaining-time arithmetic | tracking.py |

Scene preparation merges coordinate transforms, validity and targets into one
worked example. Lane attribute and position mechanisms are merged; future mode
pooling and self-attention share a figure. Repeated decoder levels use one worked
mechanism plus the full stack figure. No sensor/backbone or marginal-EM workflow
exists in this target, so those are not pictured.

Generate with `python -m gameformer.teaching build`. Check inventory, exact
placement, source freshness, attachment hashes, arithmetic, deterministic rendering
and package output/gradient parity with `python -m gameformer.teaching check`.
`manifest.json` records source hashes, render versions, captions and alt text.
All diagrams are authored programmatically; no generative image tool is used.

## Reading the redesigned figures

Every figure has a dedicated composition rather than repeated text cards. Roads,
vehicles, trajectory alternatives, tensor grids, probability bars and explicit
operator connections show how values move. Color is reinforced by labels, line
styles and mask annotations. A mode is one joint alternative across both agents;
training supervision and inference selection have separate branches.

The 1200×760 previews use a fixed 32-color palette, bundled fonts and shared
SVG/PNG geometry. Captions and the adjacent notebook guides explain symbols,
units, full-versus-toy dimensions, worked arithmetic and release caveats. Text
extents are checked while rendering. Markdown and executable probes are compared
against their source builder, in addition to architecture-definition parity.
The main notebook remains below 1 MiB, with no stored code outputs.
