# Simulated Conversations — Local Testing of the Nursery Outreach Script

**Status: simulated only. No real call was placed to produce any transcript below.** These are
hand-written fixtures exercising the script/branch logic in `nursery-outreach-script.md`, scored
against `qualification-rubric.md`, and logged in `simulated-outcomes-log.csv` using the schema in
`call-outcomes-schema.md`. Once Retell's dashboard offers an in-browser prompt-test mode (see
`docs/pilot-economics-2026-09-10.md` Section 5), these same fixtures should be re-run against the
actual LLM to check for prompt-drift before any real call.

---

### SIM-001 — Qualified, fully captured (happy path)

> **Bot:** Namaste! Mujhe kuch dino ke liye apne plants ko paani dene ke liye kisi ki zarurat hai —
> aapke area mein. Kya aapke paas koi mali ya gardener hai jo yeh kar sakta hai?
>
> **Nursery:** Haan haan, hamare paas ek ladka hai, Ramesh, woh yeh kaam karta hai.
>
> **Bot:** Bahut achha! Unka number mil sakta hai, taaki hum unse directly baat kar sakein?
>
> **Nursery:** Haan, 98765 43210 hai unka.
>
> **Bot:** Aur roughly kitna charge karte hain, per din ke hisaab se?
>
> **Nursery:** Around 150-200 rupees per visit lete hain.
>
> **Bot:** Theek hai, confirm kar loon — Ramesh, number 98765 43210, roughly ₹150-200 per visit. Sahi
> hai?
>
> **Nursery:** Haan sahi hai.
>
> **Bot:** Bahut dhanyavaad! Hum jaldi hi unse contact karenge. Aapka din shubh ho!

**Expected outcome:** `QUALIFIED_COMPLETE`, L4. All four capture-accuracy items present, confirm-back
performed and explicitly agreed.

---

### SIM-002 — Not qualified, clean decline

> **Bot:** Namaste! Mujhe kuch dino ke liye apne plants ko paani dene ke liye kisi ki zarurat hai —
> aapke area mein. Kya aapke paas koi mali hai jo yeh kar sakta hai?
>
> **Nursery:** Nahi ji, humare paas aisa koi nahi hai, sorry.
>
> **Bot:** Koi baat nahi, dhanyavaad aapke time ke liye. Aapka din shubh ho!

**Expected outcome:** `NOT_QUALIFIED`, L1. Bot must NOT re-ask or push further — verifies the
"no re-push after decline" rule.

---

### SIM-003 — Clarifying questions before qualification

> **Bot:** Namaste! Mujhe kuch dino ke liye apne plants ko paani dene ke liye kisi ki zarurat hai...
>
> **Nursery:** Kitne din ke liye chahiye?
>
> **Bot:** Abhi ke liye typically 3-7 din ka trip hota hai, exact dates customer se confirm karke
> batayenge.
>
> **Nursery:** Aur aap kaunsi company se ho?
>
> **Bot:** Main watermyplant.in ki taraf se baat kar rahi hoon — hum plant-watering service provide
> karte hain aur local gardeners ko customers se connect karte hain.
>
> **Nursery:** Theek hai, humare paas Suresh hai jo yeh kaam karta hai, par uska number abhi mere paas
> nahi hai, thodi der mein bata sakta hoon.

**Expected outcome:** `DEFERRED`, L2. Tests the Q&A bank being used correctly (honest identification,
no hallucinated address) AND the deferred-outcome path (do not auto-retry; goes to the callback
queue).

---

### SIM-004 — Price negotiation, bot must not commit

> **Nursery:** Haan hai gardener, par uska rate thoda high hai — 500 rupaye per visit legi.
>
> **Bot:** Note kar liya, hum confirm karke aapko wapas batayenge.

**Expected outcome:** Continues to capture (name/number still requested), but bot explicitly avoids
agreeing to the ₹500 rate on its own authority — a disqualification trigger from the rubric if
violated. If name/number are still captured and confirmed, outcome is `QUALIFIED_COMPLETE`; if the
nursery hangs up after the bot doesn't commit, outcome is `QUALIFIED_INCOMPLETE`.

---

### SIM-005 — Hostile / wants to hang up immediately

> **Bot:** Namaste! Mujhe kuch dino ke liye apne plants ko paani dene ke liye...
>
> **Nursery:** Yeh kya hai, mujhe interest nahi hai, please mत call karo. *(hangs up)*

**Expected outcome:** `DECLINED_HOSTILE`, L1. Row must be flagged `do_not_call: true` in the prospects
CSV going forward — tests the disqualification/do-not-call routing in `call-outcomes-schema.md`.

---

### SIM-006 — Voicemail reached, no live person

> *(automated voicemail greeting plays)*
>
> **Bot:** *(does not leave a rambling pitch; ends call)*

**Expected outcome:** `VOICEMAIL`, L0. Tests failure mode #9 from the original QA fixture list in
`docs/pilot-economics-2026-09-10.md` — "agent talks into an answering machine as if to a person" would
be a fail.

---

## Scoring summary (this batch)

| Sim ID | Expected outcome | Qualification level | Tests |
|---|---|---|---|
| SIM-001 | QUALIFIED_COMPLETE | L4 | Happy path, full capture, confirm-back |
| SIM-002 | NOT_QUALIFIED | L1 | Clean decline, no re-push |
| SIM-003 | DEFERRED | L2 | Q&A bank accuracy, honest identification, deferred routing |
| SIM-004 | QUALIFIED_COMPLETE or QUALIFIED_INCOMPLETE | L4 or L3 | Price-commitment guardrail |
| SIM-005 | DECLINED_HOSTILE | L1 | Immediate stop, do-not-call flagging |
| SIM-006 | VOICEMAIL | L0 | No voicemail pitch |

6/6 fixtures currently pass against the *script design* (this is a design-level check, not a live LLM
run — the LLM itself has not been exercised against these fixtures yet since that requires either
Retell's test mode or a real call, both pending the blockers in
`docs/founder-review-blockers-2026-09-17.md`).
