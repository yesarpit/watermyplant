#!/usr/bin/env bash
# Places a single outbound test call via the WaterMyPlants nursery-outreach
# Retell AI agent. Test-only: hardcoded to the owner's own number.
#
# Usage: FROM_NUMBER=+1XXXXXXXXXX ./place_test_call.sh
# (FROM_NUMBER is the Retell/Twilio number purchased for this agent — see README.md)
set -euo pipefail

cd "$(dirname "$0")/.."
set -a; source .env; set +a

AGENT_ID="agent_512e0d7cadfc0f99ed1ebeabaa"
TO_NUMBER="+918087404471"

if [ -z "${FROM_NUMBER:-}" ]; then
  echo "Set FROM_NUMBER to the purchased Retell outbound number (E.164), e.g.:" >&2
  echo "  FROM_NUMBER=+14155551234 $0" >&2
  exit 1
fi

curl -s -X POST https://api.retellai.com/v2/create-phone-call \
  -H "Authorization: Bearer $API_KEY_RETELL" \
  -H "Content-Type: application/json" \
  -d "{\"from_number\":\"$FROM_NUMBER\",\"to_number\":\"$TO_NUMBER\",\"override_agent_id\":\"$AGENT_ID\"}"
