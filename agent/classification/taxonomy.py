"""The single shared declaration of supported document types.

Every layer (agent, API schemas, persistence) imports `DocumentType` /
`ALLOWED_DOCUMENT_TYPES` from here so taxonomy expansion stays a one-place,
deliberate change.
"""

from typing import Final, Literal, get_args

DocumentType = Literal["contract", "technical_specification", "generic"]

ALLOWED_DOCUMENT_TYPES: Final[tuple[DocumentType, ...]] = get_args(DocumentType)
