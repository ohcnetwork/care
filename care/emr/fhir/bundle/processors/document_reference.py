"""
FHIR DocumentReference Resource Processor.

Maps FHIR DocumentReference resources with plain text content to care Notes.
Other DocumentReference types are skipped.
"""

import base64
import logging
from typing import Any

from pydantic import UUID4

from care.emr.fhir.bundle.base import FHIRResourceProcessor
from care.emr.fhir.bundle.registry import register_processor
from care.emr.models.notes import NoteMessage, NoteThread
from care.emr.resources.notes.notes_spec import NoteMessageSpec

logger = logging.getLogger(__name__)


@register_processor
class DocumentReferenceProcessor(FHIRResourceProcessor):
    """
    Processor for FHIR DocumentReference resources.

    Only processes DocumentReference resources with plain text content,
    creating Notes in the care system. Other types are skipped.

    FHIR DocumentReference Reference:
    https://www.hl7.org/fhir/documentreference.html
    """

    resource_type = "DocumentReference"
    pydantic_spec = NoteMessageSpec  # Using NoteMessageSpec as placeholder

    # Content types that are considered plain text
    PLAIN_TEXT_CONTENT_TYPES = [
        "text/plain",
        "text/html",
        "text/markdown",
    ]

    def map_fhir_to_spec(
        self, fhir_resource: dict[str, Any], encounter_id: UUID4
    ) -> dict[str, Any]:
        """
        Map FHIR DocumentReference to note data.

        Args:
            fhir_resource: The FHIR DocumentReference resource
            encounter_id: The encounter UUID

        Returns:
            Dictionary with note data
        """
        # Extract title from type
        title = None
        doc_type = fhir_resource.get("type", {})
        if doc_type.get("text"):
            title = doc_type.get("text")
        elif doc_type.get("coding"):
            codings = doc_type.get("coding", [])
            if codings:
                title = codings[0].get("display") or codings[0].get("code")

        # Extract content
        content_text = self._extract_plain_text_content(fhir_resource)

        # Extract description if available
        description = fhir_resource.get("description")

        return {
            "title": title or "Clinical Note",
            "message": content_text,
            "description": description,
            "encounter_id": encounter_id,
        }

    def _extract_plain_text_content(self, fhir_resource: dict[str, Any]) -> str | None:
        """
        Extract plain text content from DocumentReference.

        Args:
            fhir_resource: The FHIR DocumentReference resource

        Returns:
            Plain text content or None
        """
        contents = fhir_resource.get("content", [])
        for content in contents:
            attachment = content.get("attachment", {})
            content_type = attachment.get("contentType", "")

            # Check if it's a plain text type
            if any(ct in content_type.lower() for ct in self.PLAIN_TEXT_CONTENT_TYPES):
                # Check for inline data
                if attachment.get("data"):
                    # Data is base64 encoded
                    try:
                        decoded = base64.b64decode(attachment.get("data")).decode("utf-8")
                        return decoded
                    except Exception:
                        # If it's not base64, use as-is (some systems send plain text directly)
                        return attachment.get("data")

                # Check for URL (we can't fetch it, but note its presence)
                if attachment.get("url"):
                    return f"[Document URL: {attachment.get('url')}]"

        return None

    def _has_plain_text_content(self, fhir_resource: dict[str, Any]) -> bool:
        """
        Check if the DocumentReference has plain text content.

        Args:
            fhir_resource: The FHIR DocumentReference resource

        Returns:
            True if plain text content is present, False otherwise
        """
        contents = fhir_resource.get("content", [])
        for content in contents:
            attachment = content.get("attachment", {})
            content_type = attachment.get("contentType", "")

            # Check if it's a plain text type with actual content
            if any(ct in content_type.lower() for ct in self.PLAIN_TEXT_CONTENT_TYPES):
                if attachment.get("data") or attachment.get("url"):
                    return True

        return False

    def validate_fhir_resource(self, fhir_resource: dict[str, Any]) -> list[str]:
        """
        Validate the FHIR DocumentReference resource.

        Args:
            fhir_resource: The FHIR DocumentReference resource

        Returns:
            List of validation errors
        """
        errors = super().validate_fhir_resource(fhir_resource)

        # Status is required
        if not fhir_resource.get("status"):
            errors.append("DocumentReference.status is required")

        return errors

    def process(self, fhir_resource: dict[str, Any]) -> dict[str, Any]:
        """
        Process a FHIR DocumentReference and create a Note if it has plain text content.

        DocumentReferences without plain text content are skipped.

        Args:
            fhir_resource: The FHIR DocumentReference resource

        Returns:
            Processing result dictionary
        """
        result = {
            "success": False,
            "resource_type": self.resource_type,
            "fhir_id": fhir_resource.get("id"),
        }

        # Check if it has plain text content - skip if not
        if not self._has_plain_text_content(fhir_resource):
            logger.info(
                f"Skipping DocumentReference without plain text content: {fhir_resource.get('id')}"
            )
            return {
                "success": True,
                "resource_type": self.resource_type,
                "fhir_id": fhir_resource.get("id"),
                "skipped": True,
                "message": "DocumentReference without plain text content is skipped (only text/plain, text/html, text/markdown are processed as notes)",
            }

        # Validate FHIR resource
        validation_errors = self.validate_fhir_resource(fhir_resource)
        if validation_errors:
            result["errors"] = validation_errors
            return result

        try:
            # Map FHIR to note data
            note_data = self.map_fhir_to_spec(
                fhir_resource, self.encounter.external_id
            )

            # Create NoteThread
            thread = NoteThread.objects.create(
                patient=self.encounter.patient,
                encounter=self.encounter,
                title=note_data.get("title"),
                created_by=self.user,
                updated_by=self.user,
            )

            # Create NoteMessage
            message_content = note_data.get("message", "")
            if note_data.get("description"):
                message_content = f"{note_data.get('description')}\n\n{message_content}"

            note_message = NoteMessage.objects.create(
                thread=thread,
                message=message_content,
                message_history={},
                created_by=self.user,
                updated_by=self.user,
            )

            result["success"] = True
            result["care_id"] = str(note_message.external_id)
            result["thread_id"] = str(thread.external_id)
            result["stored_as"] = "note"

        except Exception as e:
            logger.exception(f"Error processing FHIR DocumentReference: {e}")
            result["errors"] = [str(e)]

        return result
