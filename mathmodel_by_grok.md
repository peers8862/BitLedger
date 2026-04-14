The BitLedger protocol can be expressed **entirely as a system of algebraic constraints on fixed-length bit vectors** that carry verifiable double-entry journal entries. Every transmitted packet is a sequence of three layers of binary words whose fields are related by exact equalities, modular arithmetic, and polynomial checksums. Below is the complete mathematical formulation you can copy directly into your project documentation, proofs, simulators, or formal verification work.

### 1. Overall Packet Stream (Algebraic Structure)
A BitLedger session is the concatenation  
\[
\mathbf{P} = \mathbf{L_1} \;\|\; (\mathbf{L_2} \;\|\; \mathbf{T_1} \;\|\; \mathbf{T_2} \;\|\; \dots \;\|\; \mathbf{T_k})^* \;\|\; \mathbf{C}
\]  
where  
- \(\mathbf{L_1} \in \{0,1\}^{64}\) is the **session initialization** (sent once),  
- each \(\mathbf{L_2} \in \{0,1\}^{48}\) (or 8-bit short-form) is a **batch header**,  
- each \(\mathbf{T_i} \in \{0,1\}^{40}\) is a **transaction record**,  
- \(\mathbf{C}\) denotes optional control/extension records.

All layers are self-describing and self-validating; the decoder treats the stream as a single integer and extracts fields by bit slicing.

### 2. Layer 1 – Session Initialization (64-bit vector)
\[
\mathbf{L_1} = \underbrace{1}_{\text{bit 1}} \;\|\; V_{3} \;\|\; P_{4} \;\|\; D_{4} \;\|\; \text{SID}_{32} \;\|\; \text{EID}_{5} \;\|\; \text{CRC}_{15}
\]  
Constraints:  
- Bit 1 is the SOH marker (always 1).  
- The final 15 bits satisfy the CRC-15 condition with polynomial \(x^{15} + x + 1\):  
  \[
  \text{crc15}(\mathbf{L_1}[1\dots49]) = \mathbf{L_1}[50\dots64]
  \]  
  where the CRC is computed exactly as  
  \[
  \text{crc15}(b,n) = \text{register after } n \text{ steps of } (x^{15}+x+1) \text{ division}.
  \]

### 3. Layer 2 – Batch Header (48-bit vector)
\[
\mathbf{L_2} = \underbrace{T_2}_{\text{type}} \;\|\; \text{SF}_7 \;\|\; S_4 \;\|\; D_3 \;\|\; \text{bells}_2 \;\|\; \text{separators}_{12} \;\|\; \text{EID}_5 \;\|\; C_6 \;\|\; R_4 \;\|\; \text{compound}_2 \;\|\; 1
\]  
Key algebraic fields:  
- Optimal split \(S \in \{0,\dots,15\}\) (default 8).  
- Scaling factor index \(\text{SF}_7\) maps to multiplier \(M = 10^k\) (see table in repo; \(k=0\) to \(9\)).  
- Decimal position \(D \in \{0,2,4,6\}\).  
- Rounding balance \(R_4\) is a 4-bit sign-magnitude integer \(e\) with \(|e|\leq7\):  
  \[
  e = 
  \begin{cases}
  +m & \text{if high bit = 0, } m=1\dots7 \\
  -m & \text{if high bit = 1, } m=1\dots7 \\
  0 & \text{if } 0000 \\
  \text{ESCAPE} & \text{if } 1000
  \end{cases}
  \]  
  This \(e\) is the invariant: the algebraic sum of all decoded transaction values in the batch (after applying rounding flags) equals zero within \(\pm e\) units.

### 4. Layer 3 – Transaction Record (40-bit vector)
\[
\mathbf{T} = A_{17} \;\|\; r_{8} \;\|\; F_{7} \;\|\; P_4 \;\|\; \text{BL}_2 \;\|\; C_2
\]  
where the 7 flag bits \(F_7\) and the two mirrored BL bits enforce:  
\[
T_{29} = T_{37} \quad \text{(Direction mirror: In/Out)}
\]  
\[
T_{30} = T_{38} \quad \text{(Status mirror: Paid/Debt)}
\]  
\[
\neg(T_{26}=0 \land T_{27}=1) \quad \text{(invalid rounding state)}
\]

### 5. Core Value Encoding (the algebraic heart of BitLedger)
Any integer monetary base value \(N\) (in the smallest unit) satisfies the **bijective split-and-scale decomposition**:
\[
N = A \cdot 2^{S} + r
\]  
with  
\[
A = \left\lfloor \frac{N}{2^{S}} \right\rfloor, \qquad r = N \bmod 2^{S}
\]  
- When \(S=8\) (default), \(A\) occupies the first 17 bits of the record and \(r\) the next 8 bits, giving exact coverage of every integer  
  \[
  0 \leq N \leq 2^{25}-1 = 33\,554\,431.
  \]  
- The **real monetary value** \(V\) recovered by the decoder is
  \[
  V = \frac{N \times M}{10^{D}}
  \]  
  where \(M\) is the scaling factor from \(\mathbf{L_2}\) and \(D\) is the decimal position.  

**Quantity mode** (when bit 32 = 1):  
\[
N = \text{Price} \times \text{Quantity}, \qquad V = \frac{(\text{Price} \times \text{Quantity}) \times M}{10^{D}}
\]  
with Price = \(A\) and Quantity = \(r\).

This decomposition is **deterministic and unique**: given \(S\), \(A\), and \(r\), there is exactly one \(N\), and vice versa. No floating-point ambiguity exists.

### 6. Batch-Level Invariants (first-principles accounting algebra)
Let \(\{V_i\}_{i=1}^k\) be the decoded real values of the \(k\) transactions in a batch. The protocol enforces the double-entry balance (including rounding):  
\[
\sum_{i=1}^k (\pm V_i) + e = 0 \pmod{\text{unit}}
\]  
where \(e\) is the rounding-balance integer extracted from \(\mathbf{L_2}\) bits 42–45 and the \(\pm\) sign is determined by the debit/credit flag and the Direction/In-Out pair.

### 7. Extension and Control Records
Any transaction with bit 40 = 1 is followed by an extension byte, and control records (1-byte) are inserted as  
\[
\mathbf{C} = 0 \;\|\; \text{type}_3 \;\|\; \text{payload}_4
\]  
These allow dynamic updates to \(S\), currency, or compound grouping without breaking the 40-bit transaction size.

This formulation is **complete and closed**: every bit position is either a data field, a mirror constraint, a CRC polynomial remainder, or a rounding-balance invariant. The encoder’s only free choice is the optimal \(S\) per batch (chosen to minimize the maximum bit usage while covering the largest \(N\) in that batch). All other fields are either fixed by the accounting semantics or forced by the mirrored-integrity rules.

You can now treat BitLedger as a pure algebraic object: a constrained homomorphism from the set of journal entries to the set of 40-bit (plus header) vectors, with built-in error-correcting properties derived directly from the double-entry axioms. This is exactly the “first-principles” bit vector you can use for proofs, formal verification, or extensions (e.g., larger account-pair tables via profile negotiation in Layer 1).