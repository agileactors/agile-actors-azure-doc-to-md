from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import DocumentContentFormat
from azure.core.credentials import AzureKeyCredential
import os
from pathlib import Path


def extract_text(source_path: str | Path) -> str:
    """
    Call Azure AI Document Intelligence (prebuilt-layout) on a real file.

    Args:
        source_path (str | Path): The path to the source document.
    Returns:
        str: The extracted text in Markdown format.
    """

    endpoint = os.environ["AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"]
    key = os.environ["AZURE_DOCUMENT_INTELLIGENCE_KEY"]
    client = DocumentIntelligenceClient(
        endpoint=endpoint, credential=AzureKeyCredential(key)
    )

    with open(source_path, "rb") as source_file:
        poller = client.begin_analyze_document(
            "prebuilt-layout",  # prebuilt-layout is the model for general document layout analysis
            body=source_file,
            # the output format is Markdown,
            # which preserves headings and tables in the text
            output_content_format=DocumentContentFormat.MARKDOWN,
        )
    result = poller.result()  # Wait for the operation to complete and get the result
    return result.content
