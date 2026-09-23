# Nursery Outreach Script (Hindi/English, Hinglish) — Supply-Sourcing Calls

**Purpose:** the bot (`agent_512e0d7cadfc0f99ed1ebeabaa`, LLM `llm_9ec922e7f5ab140a34b73c6ae708`)
calling a nursery to ask if they have or know a gardener/mali available to water a customer's plants
for a few days.
**Status: for local/simulated testing only.** Not to be used on any real call until both blockers in
`docs/founder-review-blockers-2026-09-17.md` clear.
**Language:** Hinglish primary, code-switches to English/Hindi as the nursery staff responds — matches
the existing agent config (voice `11labs-Monika`, `language: multi`).

---

## 1. Opening (verbatim, per the original brief)

> "Namaste! Mujhe kuch dino ke liye apne plants ko paani dene ke liye kisi ki zarurat hai — aapke area
> mein. Kya aapke paas koi mali ya gardener hai jo yeh kar sakta hai, ya aap kisi ko jaante hain?"
>
> ("Hi! I need someone to water my plants for a few days, near your area — do you have a gardener who
> could do this, or do you know someone?")

**Identification (always given if asked, never evaded):** "Main watermyplant.in ki taraf se baat kar
raha/rahi hoon — hum plant-watering service provide karte hain aur local gardeners ko customers se
connect karte hain."

**AI disclosure — action item added 2026-09-17, not yet in the live opening:** per
`docs/trai-dlt-compliance-2026-09-17.md` Section 2, guidance on AI voice calling in India treats
non-disclosure of an AI voice as a potential deceptive-trade-practice issue, separate from the
DLT/TCCCPR question. Before any real call, the opening or identification line should be amended to
state plainly that the caller is an AI voice assistant, e.g.: *"Main watermyplant.in ka AI assistant
hoon"* ("I'm watermyplant.in's AI assistant") in place of, or alongside, the current phrasing. Flagged
here rather than silently edited into the "verbatim" script above, since the exact wording is a founder
call.

## 2. Branch logic

```
Opening
  │
  ├─ "Haan, hamare paas hai" / "Yes we have someone"
  │     → go to Discovery (availability, price, contact)
  │
  ├─ "Nahi, humein pata nahi" / "No, we don't know anyone"
  │     → Polite close (Outcome: NOT_QUALIFIED)
  │
  ├─ Nursery asks a clarifying question (kitne din? kaunsa plant? kahan pe?)
  │     → Answer from brief (see Q&A bank below), then return to Opening flow
  │
  ├─ Nursery is hostile / wants to hang up
  │     → Immediate polite close, no further push (Outcome: DECLINED)
  │
  └─ Voicemail / IVR detected
        → Do not leave a rambling pitch; end call (Outcome: NO_ANSWER — voicemail)
```

## 3. Discovery questions (only if nursery confirms availability)

1. "Unka naam aur number mil sakta hai, taaki hum unse directly baat kar sakein?"
   (Can we get their name and number so we can speak with them directly?)
2. "Roughly kitna charge karte hain, per din ya per visit ke hisaab se?"
   (Roughly what do they charge, per day or per visit?)
3. "Kya woh Jagajyothi Layout / [locality] tak aa sakte hain?"
   (Can they come to [locality]?)

## 4. Confirm-back (mandatory before ending a qualified call)

Bot must read back captured details and get explicit confirmation — this is the #1 failure mode from
the QA fixtures in `docs/pilot-economics-2026-09-10.md` (Section 5, "mishears number/price, doesn't
repeat back"):

> "Toh confirm kar loon — [naam], number [xxx-xxx-xxxx], roughly ₹[price] per [din/visit]. Sahi hai?"
> (So let me confirm — [name], number [xxx-xxx-xxxx], roughly ₹[price] per [day/visit]. Is that right?)

If the nursery corrects any detail, re-read the corrected version back once more before closing.

## 5. Q&A bank (answer only from this list; if not covered, say so and offer a follow-up)

| Question | Answer |
|---|---|
| "Kitne din ke liye?" (How many days?) | "Abhi ke liye typically 3-7 din ka trip hota hai, lekin exact dates customer se confirm karke hum bata denge." |
| "Kaunsa plant, indoor ya outdoor?" | "Dono ho sakte hain — mostly balcony aur indoor plants, kabhi kabhi thoda garden bhi." |
| "Aap kahan se bol rahe hain / kaunsi company?" | See Identification line above — always honest, never evasive. |
| "Aapko humara number kahan se mila?" (Where did you get our number?) | "Humne area mein nurseries ko dhoondha tha online, taaki gardeners se connect ho sakein." (We looked up nurseries in the area online, to connect with gardeners.) |
| "Payment kaise hoga?" | "Yeh detail hum unhe directly connect karke customer ke saath finalize karwa denge — abhi hum sirf availability check kar rahe hain." (Do not commit to a payment term on the nursery's behalf.) |
| Price negotiation above expected range | "Note kar liya, hum confirm karke wapas batayenge" — do not agree to a price on the bot's own authority. |

## 6. Closing lines

- **Qualified, confirmed:** "Bahut dhanyavaad! Hum jaldi hi unse contact karenge. Aapka din shubh ho!"
- **Not qualified / declined:** "Koi baat nahi, dhanyavaad aapke time ke liye. Aapka din shubh ho!"
- Never re-ask after a clear "no" in the same call. Never place a follow-up call in the same session.
