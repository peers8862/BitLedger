# BitLedger Mathematical Model (Formal Specification)

## 1. System definition

BitLedger is a **stateful event-stream accounting system** defined over a sequence of encoded records:

\[
\Sigma = (x_1, x_2, ..., x_n)
\]

Where each \( x_i \) is either:
- a **control byte** (structural instruction), or  
- a **data event** (economic observation)

---

## 2. Event structure

Each data event is defined as:

\[
e = (q, d, c)
\]

Where:
- \( q \in \mathbb{R} \) → magnitude of value
- \( d \in \{-1, +1\} \) → direction (outflow/inflow)
- \( c \in C \) → contextual label space

This defines a **signed value-bearing event embedded in a contextual domain**.

---

## 3. Control byte structure

A control byte is a **state transition operator**:

\[
b \in B
\]

Each control byte updates an internal parser state:

\[
s_{t+1} = \delta(s_t, b_t)
\]

Where:
- \( s_t \) is the current interpretation state
- \( \delta \) is the state transition function

Control bytes define:
- grouping boundaries
- interpretation mode
- continuation rules for subsequent events

---

## 4. Follow-on record rule

A follow-on record is defined as:

> an event whose structural membership is determined by the most recent active control state

Formally:

\[
\text{group}(e_i) = s_t \quad \text{where } s_t \text{ is active at time of } e_i
\]

This induces a partition of the event stream into ordered groups:

\[
\mathcal{G} = \{ G_1, G_2, ..., G_k \}
\]

Where:
- each \( G_j \subset \Sigma \)
- each group is defined by control-state segmentation

---

## 5. Value aggregation function

Within each group:

\[
\mu(G_j) = \sum_{e \in G_j} d_e q_e
\]

This defines the **net signed value of a structured event group**.

---

## 6. System state

The global system state is defined as the collection of all group valuations:

\[
S(\Sigma) = \{\mu(G_1), \mu(G_2), ..., \mu(G_k)\}
\]

Optionally, a global aggregation exists:

\[
\mu(\Sigma) = \sum_{j=1}^{k} \mu(G_j)
\]

---

## 7. Interpretation function

BitLedger defines a separation between:

- raw event stream \( \Sigma \)
- and interpreted structures derived from it

Formally:

\[
\Pi : \Sigma \rightarrow \mathcal{G}
\]

Where \( \Pi \) is a deterministic parsing function governed by control bytes.

---

## 8. Core system characterization

BitLedger is formally:

> A state-driven partitioned signed-event system over a linear record stream, where structure is not intrinsic to events but is induced by control-state transitions that define grouping semantics over which value aggregation is performed.

---

## 9. Essential properties

- Order dependence (sequence matters via state transitions)
- Stateful interpretation (meaning depends on control context)
- Partitioned aggregation (values are computed over induced groups)
- Signed value semantics (directional magnitude representation)
- Separation of storage and interpretation (events vs structure)
