#!/bin/bash
# ============================================================================
# Scribe API Test Script
# ============================================================================
# This script tests the AI-powered medical scribe functionality.
#
# Prerequisites:
# 1. Set OPENAI_API_KEY in your environment or .env file
# 2. Have an audio file ready (scribe_sample_audio.mp3)
# 3. Server running at http://127.0.0.1:9000
#
# Usage:
#   chmod +x test_scribe.sh
#   ./test_scribe.sh
# ============================================================================

BASE_URL="http://127.0.0.1:9000/api/v1"
AUTH_HEADER="authorization: Basic YWRtaW46YWRtaW4="

# Audio file path - Update this to your audio file
AUDIO_FILE="./scribe_sample_audio.mp3"

# Output directory for results
OUTPUT_DIR="./scribe_test_results"
mkdir -p "$OUTPUT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Function to print section header
print_header() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

# Function to print sub-section
print_subsection() {
    echo ""
    echo -e "${CYAN}▶ $1${NC}"
    echo -e "${CYAN}─────────────────────────────────────────────────────────────────────────${NC}"
}

print_header "🎙️  SCRIBE API TEST SUITE"

echo -e "${YELLOW}Configuration:${NC}"
echo -e "  Base URL:    ${BASE_URL}"
echo -e "  Audio File:  ${AUDIO_FILE}"
echo -e "  Output Dir:  ${OUTPUT_DIR}"
echo ""

# ============================================================================
# Test 1: List Scribe Capabilities
# ============================================================================
print_header "Test 1: Scribe Capabilities"

echo -e "${YELLOW}Fetching supported providers, formats, and resource types...${NC}"
echo ""

RESULT=$(curl -s -X GET "${BASE_URL}/scribe/" \
  -H "${AUTH_HEADER}" \
  -H "Content-Type: application/json")

echo "$RESULT" | python3 -m json.tool > "${OUTPUT_DIR}/1_capabilities.json" 2>/dev/null

echo "$RESULT" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print('  \033[1mSupported Providers:\033[0m')
    for p in data.get('providers', []):
        print(f'    • {p}')
    print()
    print('  \033[1mSupported Audio Formats:\033[0m')
    formats = data.get('audio_formats', [])
    print(f'    {', '.join(formats)}')
    print()
    print('  \033[1mSupported Languages:\033[0m')
    langs = data.get('languages', {})
    lang_list = [f'{k} ({v})' for k, v in list(langs.items())[:10]]
    print(f'    {', '.join(lang_list)}...')
    print()
    print('  \033[1mFHIR Resource Types:\033[0m')
    types = data.get('fhir_resource_types', [])
    print(f'    {', '.join(types)}')
except Exception as e:
    print(f'Error: {e}')
"

echo ""
echo -e "${GREEN}✓ Saved to: ${OUTPUT_DIR}/1_capabilities.json${NC}"

# ============================================================================
# Test 2: Process Audio File (Full Pipeline)
# ============================================================================
print_header "Test 2: Process Audio File (Full Pipeline)"

if [ ! -f "$AUDIO_FILE" ]; then
    echo -e "${RED}✗ Audio file not found: $AUDIO_FILE${NC}"
    echo -e "${RED}  Please update AUDIO_FILE variable with your audio file path${NC}"
    echo ""
else
    FILE_SIZE=$(ls -lh "$AUDIO_FILE" | awk '{print $5}')
    echo -e "${YELLOW}📁 Audio file: ${AUDIO_FILE} (${FILE_SIZE})${NC}"
    echo -e "${YELLOW}⏳ Processing... (this may take 30-60 seconds)${NC}"
    echo ""

    RESULT=$(curl -s --max-time 300 -X POST "${BASE_URL}/scribe/process/" \
      -H "${AUTH_HEADER}" \
      -F "audio=@${AUDIO_FILE}" \
      -F 'metadata={"patient_context": "Patient presenting for consultation", "specialty": "general-medicine", "encounter_type": "outpatient"}' \
      -F 'generation_model={"provider": "openai", "model": "gpt-4o", "parameters": {"temperature": 0.3}}' \
      -F 'transcription_model={"provider": "openai", "model": "whisper-1"}' \
      -F "validate_bundle=true" \
      -F "include_transcript=true")

    # Save full result
    echo "$RESULT" | python3 -m json.tool > "${OUTPUT_DIR}/2_audio_processing_full.json" 2>/dev/null

    # Display results
    print_subsection "Status"
    echo "$RESULT" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    success = data.get('success', False)
    if success:
        print('  \033[0;32m✓ SUCCESS\033[0m')
    else:
        print('  \033[0;31m✗ FAILED\033[0m')
        if data.get('error'):
            print(f'  Error: {data[\"error\"]}')
except Exception as e:
    print(f'  Parse error: {e}')
"

    print_subsection "📝 Transcript"
    echo "$RESULT" | python3 -c "
import json, sys, textwrap
try:
    data = json.load(sys.stdin)
    transcript = data.get('transcript', '')
    language = data.get('transcript_language', 'N/A')
    duration = data.get('transcript_duration', 'N/A')

    print(f'  Language: \033[1m{language}\033[0m')
    if duration and duration != 'N/A':
        mins = int(float(duration) // 60)
        secs = float(duration) % 60
        print(f'  Duration: \033[1m{mins}m {secs:.1f}s\033[0m ({duration}s)')
    print()

    if transcript:
        print('  \033[1m--- Transcribed Text ---\033[0m')
        print()
        # Word wrap the transcript
        wrapped = textwrap.fill(transcript, width=75, initial_indent='  ', subsequent_indent='  ')
        print(wrapped)
    else:
        print('  (No transcript available)')
except Exception as e:
    print(f'  Parse error: {e}')
"

    # Save transcript separately
    echo "$RESULT" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('transcript', ''))
except:
    pass
" > "${OUTPUT_DIR}/2_transcript.txt"

    print_subsection "🏥 Generated FHIR Bundle"
    echo "$RESULT" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    bundle = data.get('bundle')
    if bundle:
        entries = bundle.get('entry', [])
        print(f'  Bundle Type: \033[1m{bundle.get(\"type\", \"N/A\")}\033[0m')
        print(f'  Total Resources: \033[1m{len(entries)}\033[0m')
        print()

        # Group resources by type
        by_type = {}
        for entry in entries:
            resource = entry.get('resource', {})
            rtype = resource.get('resourceType', 'Unknown')
            if rtype not in by_type:
                by_type[rtype] = []
            by_type[rtype].append(resource)

        for rtype, resources in by_type.items():
            print(f'  \033[1m{rtype}\033[0m ({len(resources)}):')
            for resource in resources:
                # Get a meaningful identifier/name for the resource
                identifier = ''
                if rtype == 'Condition':
                    code = resource.get('code', {}).get('coding', [{}])[0]
                    identifier = code.get('display', code.get('code', ''))
                    status = resource.get('clinicalStatus', {}).get('coding', [{}])[0].get('code', '')
                    if status:
                        identifier += f' [{status}]'
                elif rtype == 'Observation':
                    code = resource.get('code', {}).get('coding', [{}])[0]
                    identifier = code.get('display', code.get('code', ''))
                    value = resource.get('valueQuantity', {})
                    valueStr = resource.get('valueString', '')
                    if value:
                        identifier += f' = {value.get(\"value\", \"\")} {value.get(\"unit\", \"\")}'
                    elif valueStr:
                        identifier += f' = {valueStr[:30]}'
                elif rtype == 'MedicationRequest':
                    med = resource.get('medicationCodeableConcept', {}).get('coding', [{}])[0]
                    identifier = med.get('display', med.get('code', ''))
                    dosage = resource.get('dosageInstruction', [{}])
                    if dosage and dosage[0].get('text'):
                        identifier += f' - {dosage[0][\"text\"]}'
                elif rtype == 'AllergyIntolerance':
                    code = resource.get('code', {}).get('coding', [{}])[0]
                    identifier = code.get('display', code.get('code', ''))
                elif rtype == 'ServiceRequest':
                    code = resource.get('code', {}).get('coding', [{}])[0]
                    identifier = code.get('display', code.get('code', ''))
                elif rtype == 'Procedure':
                    code = resource.get('code', {}).get('coding', [{}])[0]
                    identifier = code.get('display', code.get('code', ''))
                elif rtype == 'MedicationStatement':
                    med = resource.get('medicationCodeableConcept', {}).get('coding', [{}])[0]
                    identifier = med.get('display', med.get('code', ''))
                elif rtype == 'FamilyMemberHistory':
                    rel = resource.get('relationship', {}).get('coding', [{}])[0]
                    identifier = rel.get('display', rel.get('code', ''))

                if identifier:
                    print(f'    • {identifier}')
                else:
                    print(f'    • (details in JSON)')
            print()
    else:
        print('  \033[0;31mNo bundle generated\033[0m')
        if data.get('error'):
            print(f'  Error: {data[\"error\"]}')
except Exception as e:
    print(f'  Parse error: {e}')
    import traceback
    traceback.print_exc()
"

    # Save bundle separately
    echo "$RESULT" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    bundle = data.get('bundle')
    if bundle:
        print(json.dumps(bundle, indent=2))
except:
    pass
" > "${OUTPUT_DIR}/2_fhir_bundle.json"

    print_subsection "✅ Validation Results"
    echo "$RESULT" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    validation = data.get('validation', {})
    if validation:
        is_valid = validation.get('is_valid', False)
        resource_count = validation.get('resource_count', 0)
        resource_types = validation.get('resource_types', [])
        errors = validation.get('errors', [])
        warnings = validation.get('warnings', [])

        if is_valid:
            print('  Status: \033[0;32m✓ VALID\033[0m')
        else:
            print('  Status: \033[0;31m✗ INVALID\033[0m')

        print(f'  Resource Count: {resource_count}')
        print(f'  Resource Types: {', '.join(resource_types)}')

        if errors:
            print()
            print('  \033[0;31mErrors:\033[0m')
            for err in errors[:5]:
                print(f'    ✗ [{err.get(\"path\", \"\")}] {err.get(\"message\", \"\")}')
            if len(errors) > 5:
                print(f'    ... and {len(errors) - 5} more errors')

        if warnings:
            print()
            print('  \033[0;33mWarnings:\033[0m')
            for warn in warnings[:5]:
                print(f'    ⚠ [{warn.get(\"path\", \"\")}] {warn.get(\"message\", \"\")}')
    else:
        print('  No validation results')
except Exception as e:
    print(f'  Parse error: {e}')
"

    print_subsection "📊 Token Usage"
    echo "$RESULT" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    usage = data.get('usage', {})
    if usage:
        prompt = usage.get('prompt_tokens', 0)
        completion = usage.get('completion_tokens', 0)
        total = usage.get('total_tokens', 0)

        # Estimate cost (GPT-4o pricing as of late 2024)
        cost_prompt = (prompt / 1000) * 0.0025
        cost_completion = (completion / 1000) * 0.01
        total_cost = cost_prompt + cost_completion

        print(f'  Prompt Tokens:     {prompt:,}')
        print(f'  Completion Tokens: {completion:,}')
        print(f'  Total Tokens:      {total:,}')
        print(f'  Estimated Cost:    ~\${total_cost:.4f}')
    else:
        print('  No usage data available')
except Exception as e:
    print(f'  Parse error: {e}')
"

    echo ""
    echo -e "${GREEN}📁 Results saved:${NC}"
    echo -e "   • Full response: ${OUTPUT_DIR}/2_audio_processing_full.json"
    echo -e "   • Transcript:    ${OUTPUT_DIR}/2_transcript.txt"
    echo -e "   • FHIR Bundle:   ${OUTPUT_DIR}/2_fhir_bundle.json"
fi

# ============================================================================
# Summary
# ============================================================================
print_header "🎉 Test Complete!"

echo -e "Output files are in: ${CYAN}${OUTPUT_DIR}/${NC}"
echo ""
echo -e "To view the full FHIR bundle:"
echo -e "  ${YELLOW}cat ${OUTPUT_DIR}/2_fhir_bundle.json | python3 -m json.tool${NC}"
echo ""
echo -e "To view the transcript:"
echo -e "  ${YELLOW}cat ${OUTPUT_DIR}/2_transcript.txt${NC}"
echo ""
