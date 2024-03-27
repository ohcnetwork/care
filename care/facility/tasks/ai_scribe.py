import json
import logging

import requests
from celery import shared_task
from django.conf import settings

from care.facility.models.ai import AIFormFill
from care.facility.models.file_upload import FileUpload

logger = logging.getLogger(__name__)

prompt_1 = """
Given a raw transcript, your task is to extract relevant information and structure it according to a predefined schema.
Output the structured data in JSON format.
If a field cannot be filled due to missing information in the transcript, do not include it in the output, skip that JSON key.
For fields that offer options, output the chosen option's ID. Ensure the output strictly adheres to the JSON schema provided.
If the option is not available in the schema, omit the field from the output.
DO NOT Hallucinate or make assumptions about the data. Only include information that is explicitly mentioned in the transcript.
If decimals are requested in the output where the field type is integer, send the default value as per the schema. Do not round off the value.
"""

prompt_2 = """
Below is the JSON schema that defines the structure and type of fields expected in the output.
Use this schema as a guide to ensure your output matches the expected format and types.
Each field in the output must conform to its definition in the schema, including type, options (where applicable), and format.
Schema:
{form_schema}
"""


@shared_task
def process_ai_form_fill(external_id):
    ai_form_fills = AIFormFill.objects.filter(
        external_id=external_id, status=AIFormFill.Status.READY
    )

    for form in ai_form_fills:
        # Skip forms without audio files
        if not form.audio_file_ids:
            logger.warning(f"AI form fill {form.external_id} has no audio files")
            continue

        logger.info(f"Processing AI form fill {form.external_id}")

        audio_file_urls = []
        transcript = ""

        # Get the audio file URLs
        for audio_file_id in form.audio_file_ids:
            audio_file = FileUpload.objects.get(external_id=audio_file_id)
            audio_file_urls.append(audio_file.read_signed_url())
            logger.info(f"Audio file URL: {audio_file_urls[-1]}")

        try:
            # Update status to GENERATING_TRANSCRIPT
            logger.info(f"Generating transcript for AI form fill {form.external_id}")
            form.status = AIFormFill.Status.GENERATING_TRANSCRIPT
            form.save()

            if not form.transcript:
                # Use Ayushma to generate transcript from the audio file
                transcript = ""
                for audio_file_url in audio_file_urls:
                    audio_file_data = requests.request("GET", audio_file_url).content

                    response = requests.request(
                        "POST",
                        f"{settings.AYUSHMA_ENDPOINT}/api/chats/transcribe",
                        headers={"X-Api-Key": settings.AYUSHMA_API_KEY},
                        data={"language": "en", "engine": "whisper"},
                        files={"audio": ("file.mp3", audio_file_data)},
                    )

                    transcript += response.json()["transcript"]

                    logger.info(f"Transcript: {transcript}")

                # Save the transcript to the form
                form.transcript = transcript
            else:
                transcript = form.transcript

            # Update status to GENERATING_AI_RESPONSE
            logger.info(f"Generating AI response for AI form fill {form.external_id}")
            form.status = AIFormFill.Status.GENERATING_AI_RESPONSE
            form.save()

            # Process the transcript with Ayushma
            ai_response = requests.request(
                "POST",
                f"{settings.AYUSHMA_ENDPOINT}/api/chats/completion",
                headers={"X-Api-Key": settings.AYUSHMA_API_KEY},
                json={
                    "task": "ai_form_fill",
                    "messages": [
                        {
                            "role": "system",
                            "content": prompt_1,
                        },
                        {
                            "role": "system",
                            "content": prompt_2.replace(
                                "{form_schema}", json.dumps(form.form_data, indent=2)
                            ),
                        },
                        {
                            "role": "system",
                            "content": "Below is a sample output for reference. Your task is to produce a similar JSON output based on the provided transcript, following the schema and instructions above.\n"
                            + json.dumps(
                                {
                                    field["id"]: field["example"]
                                    for field in form.form_data
                                },
                                indent=2,
                            ),
                        },
                        {
                            "role": "user",
                            "content": "Please process the following transcript and output the structured data in JSON format as per the schema provided above:\nTranscript:\n"
                            + transcript,
                        },
                    ],
                },
            )
            ai_response_json = ai_response.json()["response"]
            logger.info(f"AI response: {ai_response_json}")

            # Save AI response to the form
            form.ai_response = ai_response_json
            form.status = AIFormFill.Status.COMPLETED
            form.save()

        except Exception as e:
            # Log the error or handle it as needed
            form.status = AIFormFill.Status.FAILED
            form.save()
            logger.error(f"AI form fill processing failed: {e}")
