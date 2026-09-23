#!/usr/bin/env python3
"""Create or update the two Retell agents used by the enquiry pipeline.

  customer -- calls the person who enquired and confirms dates, area, plants, visits, access, budget
  gardener -- calls nearby gardeners/nurseries and asks about availability, rate, and contact

Prompts live in prompts/*.md. Re-running this script pushes prompt/config edits to the existing
agents (IDs are kept in agents.json), so it's safe to run repeatedly.
"""
import json

import retell
from retell import AGENTS_FILE, ROOT

END_CALL = [{"type": "end_call", "name": "end_call",
             "description": "End the call once the closing line is said, or the person asks to stop."}]

AGENTS = {
    "customer": {
        "agent_name": "WaterMyPlants - Customer Enquiry Call",
        "voice_id": "11labs-Monika",  # Indian-accent female (en-IN)
        "language": "en-IN",
        "begin_message": "Hi, am I speaking with {{customer_name}}? This is Priya from Water My Plant, "
                         "calling about your plant-watering enquiry. Is this a good time for two minutes?",
        "analysis": [
            {"type": "boolean", "name": "still_needs_service",
             "description": "Customer confirmed they still want someone to water their plants."},
            {"type": "string", "name": "start_date", "description": "Confirmed start date (YYYY-MM-DD if possible)."},
            {"type": "string", "name": "end_date", "description": "Confirmed end date (YYYY-MM-DD if possible)."},
            {"type": "string", "name": "area", "description": "Confirmed locality/area, e.g. 'Jagajyothi Layout'."},
            {"type": "string", "name": "landmark", "description": "Nearby landmark the customer gave."},
            {"type": "string", "name": "plant_count", "description": "Approx number of plants/pots and where (indoor/balcony/garden)."},
            {"type": "enum", "name": "visit_frequency", "choices": ["daily", "alternate_days", "twice_weekly", "other", "unknown"],
             "description": "How often the gardener should visit."},
            {"type": "string", "name": "access_arrangement", "description": "How the gardener gets in (key with security, neighbour, etc.)."},
            {"type": "number", "name": "budget_per_visit_inr", "description": "Customer's stated budget per visit in INR, if given."},
            {"type": "string", "name": "callback_time", "description": "If it was a bad time: when to call back."},
            {"type": "boolean", "name": "do_not_call", "description": "Customer asked not to be called again, or is not interested."},
            {"type": "boolean", "name": "needs_kannada_callback", "description": "Customer could only speak Kannada."},
        ],
    },
    "gardener": {
        "agent_name": "WaterMyPlants - Gardener Availability Call",
        "voice_id": "11labs-Monika",
        "language": "multi",  # Hindi/English code-switching
        "begin_message": "Namaste ji! Main Water My Plant se bol rahi hoon. {{customer_area}} mein "
                         "kuch dino ke liye plants ko paani dene ka kaam hai. Kya aap do minute baat kar sakte hain?",
        "analysis": [
            {"type": "boolean", "name": "available", "description": "They (or their staff) can do the watering job."},
            {"type": "boolean", "name": "can_start_on_date", "description": "They can start on the requested start date."},
            {"type": "number", "name": "price_per_visit_inr", "description": "Quoted charge per visit in INR."},
            {"type": "string", "name": "contact_name", "description": "Name of the person who would do the job."},
            {"type": "string", "name": "contact_number", "description": "Phone/WhatsApp number to share with the customer."},
            {"type": "string", "name": "referral", "description": "Name and number of another gardener/nursery they recommended."},
            {"type": "boolean", "name": "do_not_call", "description": "They asked not to be called again."},
            {"type": "boolean", "name": "needs_kannada_callback", "description": "They could only speak Kannada."},
        ],
    },
}


def main():
    ids = json.loads(AGENTS_FILE.read_text()) if AGENTS_FILE.exists() else {}
    for role, cfg in AGENTS.items():
        llm_body = {
            "model": "gpt-4.1",
            "model_temperature": 0.3,
            "general_prompt": (ROOT / "prompts" / f"{role}.md").read_text(),
            "begin_message": cfg["begin_message"],
            "start_speaker": "agent",
            "general_tools": END_CALL,
        }
        agent_body = {
            "agent_name": cfg["agent_name"],
            "voice_id": cfg["voice_id"],
            "language": cfg["language"],
            "post_call_analysis_data": cfg["analysis"],
            "voicemail_option": {"action": {"type": "static_text",
                                            "text": "Hi, this is Water My Plant calling about plants. "
                                                    "We'll message you on WhatsApp. Thank you!"}},
            "end_call_after_silence_ms": 20000,
            "max_call_duration_ms": 300000,
        }
        entry = ids.get(role)
        if entry:
            retell.request("PATCH", f"/update-retell-llm/{entry['llm_id']}", llm_body)
            retell.request("PATCH", f"/update-agent/{entry['agent_id']}", agent_body)
            print(f"updated {role}: {entry['agent_id']}")
        else:
            llm = retell.request("POST", "/create-retell-llm", llm_body)
            agent = retell.request("POST", "/create-agent", {
                **agent_body, "response_engine": {"type": "retell-llm", "llm_id": llm["llm_id"]}})
            ids[role] = {"llm_id": llm["llm_id"], "agent_id": agent["agent_id"]}
            print(f"created {role}: {agent['agent_id']}")
        AGENTS_FILE.write_text(json.dumps(ids, indent=2) + "\n")


if __name__ == "__main__":
    main()
