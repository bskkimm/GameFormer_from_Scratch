"""Pedagogical reading guides for the notebook's eighteen architecture figures.

These passages describe the local released-compatible operators. Worked numbers
are illustrative arithmetic, never trained predictions or benchmark evidence.
"""

LESSON_NOTES = {
    "overview": r"""
### A reading route through the model

Follow one scene through three questions: **What is present now? What might each
agent do? How should those futures respond to one another?** Histories and map
points become fixed-width vectors called *tokens*. Attention lets a token read
other tokens. Level 0 predicts directly from observed context; each later level
reads features of the preceding predictions. A level is a learned response stage,
not a new observed timestep or a proof that game-theoretic equilibrium was found.

Keep this axis legend beside the diagrams:

| Symbol | Axis meaning | Released joint recipe |
| --- | --- | --- |
| B | independent scenes in a batch | chosen batch size |
| C / P | observed actors / predicted actors | 34 / 2 |
| H / T | history samples / future samples | 11 / 80 |
| M / D | joint alternatives / token channels | 6 / 256 |
| E / K | scene encoder layers / interaction stages | 6 / 3 |

Thus `[B,P,M,T,4]` means a four-number Gaussian at every future time for every
agent and joint alternative. Both agents' mode 2 belongs to the **same scene
alternative**. The released model stores K+1=4 prediction levels; the paper's K6
recipe stores seven. Scalar and two-channel drawings expose arithmetic; the CPU
probe instead uses D32, C4, E1, K1 while retaining P2, M6, H11, T80. The following
cells build that model locally, run an actual update and report synthetic
diagnostics. Read these as execution checks, with no learned-driving claim.
""",
    "scene-tensors": r"""
### Read the scene before reading its tensors

Choose the first target's current position and heading as the coordinate frame.
Translate every position by that origin, then rotate so local +x points forward
and +y points left. In the worked scene, the origin is `(10,5)` m and its heading
is 90 degrees. A world point `(10,6)` has displacement `(0,1)`; rotating by -90
degrees gives local `(1,0)` m. The same physical point now has a convenient
forward-distance interpretation. All agents and both targets' map selections
use this common frame; *agent-local map context* means a selection around each
agent, not a separate rotation of its coordinates.

Each history row contains `x,y,heading,vx,vy,length,width,height,type_id`.
H=11 includes the current sample; the T=80 labels cover 0.1 through 8 seconds
ahead. The target axis P is distinct from the larger observed-actor axis C.
Validity is an independent Boolean axis: `(0,0)` can be a real current position,
whereas an invalid row is excluded even if its stored numbers look plausible.
The probe deliberately keeps the focal actor at the valid origin and prints all
batch shapes. This checks the input contract; synthetic geometry does not
establish parity with real-data preprocessing.
""",
    "agent-history": r"""
### A token carries motion history, not one raw observation

Trace the history sequence into one actor token. An LSTM is a recurrent network
with a *cell state*, its running memory. Its gates are learned numbers that
control how much old memory to retain, how much candidate memory to add and how
much to expose. For one illustrative channel, old memory 1.0, forget gate 0.8,
input gate 0.5 and candidate 0.4 produce
$c_{new}=0.8\cdot1+0.5\cdot0.4=1$. With output gate 0.5,
$h_{new}=0.5\tanh(1)\approx0.3808$. Adding a toy type embedding 0.1 gives 0.4808.
The actual gates operate on D channels with learned matrices.

The numeric path is `[B,H,8] -> [B,H,D] -> [B,D]`; the ninth field selects a
categorical type embedding added to the last output. Two stacked recurrent
layers learn progressively transformed history. Focal and other actors have
separate encoders, while all non-focal actors share one encoder's weights.
Invalid history rows are zeroed by `GameFormer` before this component runs;
zero rows still pass through the recurrence rather than being skipped. Current
validity later controls visibility in attention. The probe checks the final
token width; its random initialization does not reproduce the hand-set gates.
""",
    "lane-encoding": r"""
### Geometry and road rules enter through different paths

Read a lane point as several kinds of information. Centerline, left boundary
and right boundary each supply `(x,y,heading)` to a separate linear projection.
Speed is a continuous number with its own projection. Lane type, boundary type,
signal and binary attributes instead select learned vectors from embedding
tables: an ID names a category, so category 2 need not mean twice category 1.
The six semantic vectors are **summed**, giving 64 channels together. They are
then concatenated with `3*128` geometry channels and 64 speed channels:
$384+64+64=512$. The point network maps 512 to 384 to D.

The point index also matters. Adding sinusoidal position features lets two
otherwise similar points carry different positions along the lane. At point
index zero, a toy sine/cosine pair is `(0,1)`, so a learned feature `(0.5,0.6)`
becomes `(0.5,1.6)` before dropout. This is an example slice, not a measured
lane embedding. The full tensor retains `[B,P,6,100,D]` until segment pooling.
Compatibility intentionally reads semantic columns 14/15 where preprocessing
describes different fields; corrected 15/16 columns are a named configuration
choice. The probe verifies D channels without claiming those two recipes agree.
""",
    "crosswalk-encoding": r"""
### Keep every point until the reduction step

The crosswalk branch starts from `(x,y,heading)` and applies the same small
feature network independently to every point. A *linear layer* computes a
weighted sum plus a bias; ReLU keeps positive values and replaces negative
values by zero. In the illustrative first layer, rows `(1,0,0)` and `(0,-1,0)`
with zero biases transform point `(2,-1,0)` to `(2,1)`. ReLU leaves `(2,1)`
unchanged. The real network uses widths `3 -> 64 -> 128 -> D`, with ReLU after
the first two projections, rather than the two-channel toy output.

Nothing has yet averaged all crosswalk geometry into one number. The full
released tensor is `[B,P,4,50,D]`: four selected crosswalks, fifty points each,
for each predicted actor's map selection. Unlike lanes, this branch adds no
sinusoidal point-position features. Nevertheless, downstream groups still use
the point order supplied by preprocessing. Padding coordinates are zeroed
before encoding, but biased layers can give zero inputs nonzero features;
therefore the separate validity mask remains essential at pooling. The probe
checks that the final channel width is D. The next section explains exactly
which point values survive into scene attention.
""",
    "map-segments": r"""
### A pooled token can borrow channels from different points

Max pooling reduces the map's point count while preserving a strong response
in each feature channel. First group consecutive points, then replace invalid
features by negative infinity, then take a maximum **separately per channel**.
For valid features `(1,4)` and `(7,2)`, the result is `(7,4)`: its first channel
comes from the second point and its second channel from the first. A padded
`(99,99)` must contribute neither value. The result is a learned feature vector,
not a new physical point at coordinate `(7,4)`.

Released lane grouping makes `6*(100/10)=60` tokens per target; crosswalk
grouping makes `4*(50/10)=20`. With C=34 actor tokens this gives S=114 scene
tokens. Here S names the scene-token axis, not a time axis.

The two policies separate numeric reduction from token visibility. Compatibility
requires every point in a group valid; the practical partial policy requires
at least one. An entirely empty group receives a finite zero vector and stays
hidden in either policy. The upcoming probe explicitly enables the partial
policy and verifies `(7,4)` despite the invalid large values. It does not assert
that the same partly valid group is visible under the default strict policy.
""",
    "scene-attention": r"""
### Attention is a weighted read of visible tokens

Treat a query as a request and each key as a description of available content;
the corresponding value supplies the content to read. Dot products measure
query-key compatibility. Division by $\sqrt d$ controls score scale, and
softmax converts visible scores into nonnegative weights summing to one.
A padding mask hides a key before softmax. In the scalar example, values
`(2,4,99)` with weights `(.25,.75,0)` yield `0.25*2+0.75*4=3.5`; the masked
99 cannot contaminate the read. Learned attention usually has several heads,
each making a separate read of projected channels.

Each predicted agent receives all C actor tokens and its selected map tokens.
The implementation folds B and P into one batch axis, so scene input is
`[B*P,S,D]`. The Transformer preserves these axes while enriching each token
with context. Residual addition carries an input around a sublayer; layer
normalization rescales its channels. Scene and future self-attention use
residuals, but the released decoder cross-attention omits the query residual
around its attention read. Its feature-network residual remains. The probe
checks self-attention shape preservation; the illustrated weights are fixed
teaching values, not attention weights recovered from that random module.
""",
    "initial-query": r"""
### Ask several different questions of the same observed scene

After scene encoding, choose each predicted actor's contextualized actor token.
Add one learned vector identifying the actor and another identifying the mode.
An *embedding* is simply a trainable vector indexed by an ID. Element-wise
addition preserves D channels: toy vectors `(1,2)`, `(.5,0)` and `(0,-.5)`
produce query `(1.5,1.5)`. The model broadcasts these ingredients over
`[B,P,M,D]`, forming twelve queries per scene in the released P2, M6 case.
Each query then reads its target's observed context through cross-attention.

Mode IDs provide consistent slots for alternative joint futures, without
hard-coding meanings such as “turn left” or “yield.” Both agents' mode m forms
one joint alternative; independently pairing agent A's mode 0 with agent B's
mode 4 would break that interpretation. At this initial level, no predicted
future is available to condition the read. There is also no self-attention
between the M query slots in this block: diversity comes from their distinct
embeddings and learned predictions, with interaction introduced later.
The following probe verifies the addition arithmetic only. The complete
assembly probe will exercise the learned embeddings and scene read together.
""",
    "gaussian-head": r"""
### Separate where a future goes, its spread and its score

For every agent-mode query, one head emits T sets of four numbers and another
emits one scalar score. Read a row as
`mu_x,mu_y,log_sigma_x,log_sigma_y`. The mean is a position; the standard
deviation sigma describes spread around it along an axis. A log standard
deviation of zero means sigma=1, while $\log 2$ means sigma=2. These are not
variances: the corresponding variances would be 1 and 4. The diagonal model
has no learned x-y covariance term and no explicit cross-time covariance.

Suppose the current position is `(10,2)` m and one predicted offset is `(3,1)`
m. The mean is `(13,3)` m. Every timestep is anchored directly to the **same
current position**; the head does not integrate a chain of incremental moves.
This matters when comparing its outputs to the later finite-difference
velocity calculation. The scalar score belongs to the entire mode trajectory,
not each future step; softmax turns the M scores into relative mode weights.

The probe checks `[2,2,6,80,4]` Gaussian parameters and `[2,2,6]` scores.
Despite its variable name `means`, that first returned tensor includes all
four Gaussian fields. Uncertainty is decoded here and clamped for the loss later.
""",
    "future-encoding": r"""
### Convert positions to motion features, then stop one gradient route

Follow a predicted xy trajectory into the next reasoning level. Prepend the
observed current position before taking differences, so the first velocity
has the same physical meaning as later ones. Moving from `(0,0)` to `(1,0)`
m over 0.1 seconds gives `(10,0)` m/s and heading zero. Concatenate position
(2 channels), heading (1), velocity (2) and observed length/width/height (3):
eight channels per step. A shared `8 -> 64 -> D` network encodes them; a
maximum over T removes time, producing `[B,P,M,D]`, then type is added.

The *gradient barrier* is `states.detach()`: later loss cannot change earlier
xy **through this kinematic-feature route**. The MLP still gets parameter
gradients, and earlier content and mode scores have other routes into later
levels. Earlier predictions also have their own direct supervision. Detach
does not freeze the entire earlier decoder.

Compatibility clamps delta-x to at least .001 for heading only. For a backward
move, that differs from geometric `atan2(dy,dx)`; velocity still uses the
original difference. The probe isolates this feature route: `xy.grad` stays
absent while the future MLP's weight gradient exists. It does not test all
possible gradient routes in the assembled network.
""",
    "future-interaction": r"""
### Compress alternatives before agents read one another

Keep two future representations distinct. The multi-future tensor
`e[B,P,M,D]` retains every candidate mode. A second tensor pools those modes
into one token per agent, so future self-attention can compare agents on
`[B,P,D]`. With toy scalar features `(2,4)` and probabilities `(.25,.75)`,
weighted features are `(.5,3)`. The released operator takes their **mean**,
giving 1.75. A normalized probability-weighted sum would give 3.5. In the full
M6 model, this extra factor is 1/6; it is a compatibility choice, not evidence
that the probabilities fail to sum to one.

Self-attention then allows each agent's pooled token to read other agents'
pooled tokens. Its outputs can contain information about several agents, so
they are mixed interaction features rather than isolated future descriptions.
The unpooled multi-future features remain available to modify each mode's next
query. One future MLP is shared across reasoning levels; each level has its
own interaction attention, cross-attention and prediction head. Shared weights
therefore do not imply identical behavior at every level.

The probe verifies the unusual 1.75 arithmetic and constructs an interaction
block. The later full-model call exercises attention across agents and checks
that all prediction stages are retained.
""",
    "reasoning-mask": r"""
### Identify which connections the mask actually removes

At level k, each mode's next query is previous decoder content plus its own
unpooled future embedding. Its context includes mixed future-agent tokens and
the original encoded scene. For two predicted agents, the future-key mask is
`[[True,False],[False,True]]`: row A hides future token A and can read future
token B; row B does the reverse. True means **hidden**, the opposite of the
input validity masks where True means present. Absent actors and scene padding
also remain hidden.

This is not a rule saying an agent cannot use information about itself. Its
own multi-future embedding explicitly enters the query, and its observed actor
token remains in the scene. More subtly, future self-attention happened before
this mask: token B may already contain information read from A. Hiding the
token labelled A therefore removes a direct key-value read, without proving
that every indirect A-to-A information path is absent. Read the diagram's
arrows in that sequence before interpreting the crossed-out connection.

The next probe constructs the diagonal mask and verifies its Boolean values.
It demonstrates the intended direct visibility pattern; it does not measure
information isolation or establish a causal guarantee about learned features.
""",
    "full-assembly": r"""
### Count stages and distinguish context from predictions

The assembly connects earlier components without replacing the observed scene
at every level. Encode histories and map segments once, then create one
context per predicted agent. All C actors appear in each context, while the
map selection differs by target. In the full recipe, `34+60+20=114` tokens
give scene shape `[B,2,114,256]`. Only the first P=2 actors are decoded; the
other 32 still provide useful observed traffic context.

Level 0 reads that scene. Each of the K interaction stages takes previous xy,
scores and decoder content, constructs future interaction features, and
predicts a replacement set of futures anchored to the observed current state.
The stage axis is distinct from physical future time: K3 yields four stages,
each containing all eighty future timesteps. Stacking produces trajectories
`[4,B,2,6,80,4]` and scores `[4,B,2,6]`. Keeping intermediate predictions allows
loss at every level rather than only the final one.

The executable smoke model instead has K1 and D32, so its two-scene probe
expects `[2,2,2,6,80,4]`; those first three twos mean stage, batch and agent.
Vectorization changes batching, not this dependency graph. Evaluation parity
does not imply identical dropout random-number order during training.
""",
    "joint-objective": r"""
### Choose a whole scene alternative, then teach its coordinates and score

Training first selects one *joint winner*, using both agents' valid trajectory
errors. In the toy comparison, errors `(0,10)` average to 5 for mode 0, whereas
`(2,2)` average to 2 for mode 1. Assume all 80 labels are valid and each error
is constant across time, including horizon indices 29, 49 and 79. Then
adding the three horizon errors makes joint costs 20 and 8, preserving mode 1
for both agents. Independently choosing each agent's nearest path would create
a different objective. The full selector combines temporal mean displacement
with 3-, 5- and 8-second errors (indices 29,49,79), then averages available
agents. This discrete choice does not differentiate through the winning index.

For the chosen Gaussian, residual `(2,0)` with both sigmas 1 gives NLL=2,
omitting the constant Gaussian term as the code does. If every valid timestep
has those values, temporal mean 2 plus three horizon terms gives regression
8. This assumption is needed for the displayed arithmetic. Joint log-sigmas
are clamped to `[0,5]`; scores receive twice the summed-agent cross-entropy
with label smoothing .2. Validity controls reductions, and every level adds
its own loss.

Planning changes reductions and adds .1 potential after level 0. At distance
1 m its potential is .5; at 3 m the strict threshold gives zero. It finds the
nearest previous neighbor across modes, uses the released directional pairs,
and does not detach previous predictions in this loss. The probe checks finite
joint components; the additional analytical probe checks regression 8 and the
winning mode's gradient path. These checks establish no official score or
planning safety guarantee.
""",
    "optimizer-update": r"""
### Trace one update all the way to changed parameters

Forward computes predictions and loss; backward applies the chain rule to
compute parameter gradients; the optimizer uses those gradients to change
weights. A gradient is a local sensitivity, not a prediction error with the
same units. In the toy scalar loss $L=\frac12w^2$ at w=2, the gradient is 2.
For the first AdamW step with learning rate .1, zero weight decay and epsilon
ignored, bias-corrected moments are 2 and 4. The update is
$.1\cdot2/\sqrt4=.1$, giving w=1.9. Those assumptions explain why the drawing
is simple; the actual notebook optimizer has different hyperparameters.

The real probe clears gradients, rebuilds a forward graph, backpropagates the
actual joint objective, clips the total gradient norm at 5, and steps AdamW.
The returned norm is measured before clipping, so it may exceed 5. With
mixed precision, unscale gradients before clipping; Gaussian loss arithmetic
is converted to FP32. The trainer also weights accumulated microbatches by
their actual sample counts: sizes 2 and 1 contribute 2/3 and 1/3, rather than
equal halves. This preserves its sample-weighted update convention for a
partial final group. One finite synthetic update establishes execution, not
convergence or reproduction of the paper's training recipe.
""",
    "decoding-metrics": r"""
### Let scores select first; consult labels only to measure afterward

Inference uses the final level. Sum both agents' scores for each joint mode,
softmax across modes and choose a common winner. For summed logits
`(0,log(8),0)`, probabilities are `(.1,.8,.1)` and mode 1 supplies both
agents' paths. Selection never sees future labels. A nearest-to-label choice
would instead be an oracle comparison and answer a different question.
The planning diagnostic follows the released helper's per-agent argmax, so
its selection rule is deliberately different.

ADE is mean displacement over valid steps; FDE is displacement at each
agent's last valid step. For valid errors `(1,2,3)` m, ADE is 2 m and FDE is
3 m. An additional padded error 99 m changes neither. Aggregate sums and valid counts across
batches before dividing; padding must contribute neither error nor count.

The official joint adapter keeps all six hypotheses and subsamples future
indices `4,9,...,79`, corresponding to 0.5-second intervals, to form
`[B,1,6,2,16,2]`. Its singleton axis groups both agents as one joint prediction.
The probe checks this layout and plots selected synthetic paths. Official
WOMD metrics additionally require genuine state labels, compatible SDK and
the prescribed split; a shape-correct adapter and random-model plot establish
none of those results.
""",
    "checkpoint-resume": r"""
### Recovery needs the training state and the data identity

Weights alone cannot reproduce the next training update. AdamW retains
gradient moments, the scheduler retains learning-rate progress, mixed
precision may retain scaler state, and random generators determine dropout
and sample order. Save them with the completed epoch, timing state and run
identity. A temporary file is flushed and synced before atomic replacement,
so an interrupted write does not expose a half-written latest checkpoint.

At an epoch boundary, completing epoch 6 means the next run continues with
epoch 7; it does not replay an arbitrary fraction of epoch 6. The independent
sampler generator matters because worker startup consumes randomness too:
restarting workers must not advance the future shuffle order. Schema 2 also
checks cache manifests before restoring state and preserves original records
alongside restart-specific sessions.

These guarantees cover deterministic datasets without random worker
augmentation; they do not promise mid-epoch recovery. The following opt-in
cell stays disabled by default and requires genuine prepared caches when
enabled. It is an entry point for a separately budgeted run, not a notebook
recovery experiment. The default local architecture still runs offline without
importing the training infrastructure.
""",
    "tracking-eta": r"""
### A remaining-time estimate is a measurement of the current session

After a restart, distinguish work already completed from speed observed now.
Suppose 6 of 10 epochs are complete, and this session completed 2 in 20
seconds. Its rate is .1 epoch/second, so four remaining epochs suggest
$4/.1=40$ seconds. If prior sessions accumulated 40 active seconds, total
active time is 60 seconds. A wall clock spanning 100 seconds also includes
40 seconds when training was inactive. Folding that downtime into throughput
would misdescribe the current session's speed.

An epoch's measured duration includes observed validation and checkpoint
overhead, so the estimate describes the actual loop rather than only model
steps. It still assumes future epochs resemble the measured ones; hardware
load or evaluation changes can break that assumption. Before two completed
session epochs, the displayed estimate is marked provisional. With no usable
rate yet, remaining time is unknown rather than an invented number.

The probe verifies the toy 40-second arithmetic. The trainer writes
`progress.json` even without MLflow; optional tracking displays active time,
wall time, progress and timezone-aware expected finish. Such metadata makes
compute use inspectable, while providing no evidence that prediction quality
has improved.
""",
}
