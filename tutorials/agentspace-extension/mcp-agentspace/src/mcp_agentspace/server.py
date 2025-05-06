# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import requests
import json

from mcp.server.fastmcp import FastMCP
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, INTERNAL_ERROR, INVALID_PARAMS

import google.auth
import google.auth.transport.requests
from google.api_core.client_options import ClientOptions
from google.cloud import discoveryengine_v1 as discoveryengine
from google.protobuf.json_format import MessageToDict

mcp = FastMCP("agentspace")

def get_auth_header():
  creds, _ = google.auth.default()
  creds.refresh(google.auth.transport.requests.Request())

  headers = {
      'Authorization': f'Bearer {creds.token}',
      'Content-Type': 'application/json; charset=UTF-8'
  }
  return headers

@mcp.tool()
def get_search_response(
    # project_id: str,
    # location: str,
    # engine_id: str,
    search_query: str,
    # prompt_preamble: str | None = None,
) -> str:
    """Retrieves search results from using the Discovery Engine Python SDK.

    Args:
        search_query: The search query string.

    Returns:
        A list of JSON objects containing the search results.
        This list may be empty if no results are found.
    """
    try:

        # Args:
        #     project_id: The Google Cloud project ID.
        #     location: The location of the Discovery Engine (e.g., "global", "us-central1").
        #     engine_id: The ID of the Discovery Engine.
        #     prompt_preamble: The preamble to use for search summaries.
        project_id = "the-foo-bar"
        location = "global"
        engine_id = "cymbal-bank_1746202630648"
        prompt_preamble = None

        #  For more information, refer to:
        # https://cloud.google.com/generative-ai-app-builder/docs/locations#specify_a_multi-region_for_your_data_store
        client_options = (
            ClientOptions(api_endpoint=f"{location}-discoveryengine.googleapis.com")
            if location != "global"
            else None
        )

        # Create a client
        client = discoveryengine.SearchServiceClient(client_options=client_options)

        # The full resource name of the search app serving config
        serving_config = f"projects/{project_id}/locations/{location}/collections/default_collection/engines/{engine_id}/servingConfigs/default_config"

        # Optional - only supported for unstructured data: Configuration options for search.
        # Refer to the `ContentSearchSpec` reference for all supported fields:
        # https://cloud.google.com/python/docs/reference/discoveryengine/latest/google.cloud.discoveryengine_v1.types.SearchRequest.ContentSearchSpec
        content_search_spec = discoveryengine.SearchRequest.ContentSearchSpec(
            # For information about snippets, refer to:
            # https://cloud.google.com/generative-ai-app-builder/docs/snippets
            snippet_spec=discoveryengine.SearchRequest.ContentSearchSpec.SnippetSpec(
                return_snippet=True
            ),
            # For information about search summaries, refer to:
            # https://cloud.google.com/generative-ai-app-builder/docs/get-search-summaries
            summary_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec(
                summary_result_count=5,
                include_citations=True,
                ignore_adversarial_query=True,
                ignore_non_summary_seeking_query=True,
                model_prompt_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec.ModelPromptSpec(
                    preamble=prompt_preamble
                ),
                model_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec.ModelSpec(
                    version="stable",
                    # version="preview",
                ),
            ),
            # -------extractive content-----
            extractive_content_spec=discoveryengine.SearchRequest.ContentSearchSpec.ExtractiveContentSpec(
                max_extractive_segment_count=2,
                max_extractive_answer_count=2,
                return_extractive_segment_score=True,
            ),
        )

        # Refer to the `SearchRequest` reference for all supported fields:
        # https://cloud.google.com/python/docs/reference/discoveryengine/latest/google.cloud.discoveryengine_v1.types.SearchRequest
        request = discoveryengine.SearchRequest(
            serving_config=serving_config,
            query=search_query,
            page_size=10,
            content_search_spec=content_search_spec,
            query_expansion_spec=discoveryengine.SearchRequest.QueryExpansionSpec(
                condition=discoveryengine.SearchRequest.QueryExpansionSpec.Condition.AUTO,
            ),
            spell_correction_spec=discoveryengine.SearchRequest.SpellCorrectionSpec(
                mode=discoveryengine.SearchRequest.SpellCorrectionSpec.Mode.AUTO
            ),
        )

        response = client.search(request)

        document_dict = MessageToDict(
        response.results[0].document._pb, preserving_proto_field_name=True
        )

        # return response
        return document_dict["derived_struct_data"]["extractive_answers"][0]["content"]
        # return response.results
    
    except ValueError as e:
        raise McpError(ErrorData(INVALID_PARAMS, str(e))) from e
    except Exception as e:
        raise McpError(ErrorData(INTERNAL_ERROR, f"Unexpected error: {str(e)}")) from e

def process_deep_research_response(response):
    """Process the response from the Deep Research API.

    Args:
        response: The response object from the Deep Research API.

    Returns:
        A string containing the processed response.
    """

    text_json = json.loads(response.text)
    raw_text = ''
    raw_text = "# Reserach Plan\n"
    for row in text_json:
        try:
            replies = row['answer']['replies']
            for reply in replies:
                model_text = reply['groundedContent']['content']['text']
                raw_text += model_text + '\n'
        except:
            # print(row)
            continue
    return raw_text

# Get reports with Deep Research
@mcp.tool()
def get_deep_research_response(
    # project_id: str,
    # location: str,
    # engine_id: str,
    query: str,
    start_new_session: bool = False,
) -> str:
    """Deep Research is a Premade by Google agent for users who need to gather, analyze, and understand internal and external information.

    Args:
        query: The query string users can chat with the research agent.
        start_new_session: Whether to start a new session or continue an existing one.

    Returns:
        Text report with citations with markdown formatting.
    """

    try:
        project_id = "the-foo-bar"
        location = "global"
        engine_id = "cymbal-bank_1746202630648"
        assistant_id  = 'default_assistant' 

        headers = get_auth_header()
        headers["X-Goog-User-Project"] = project_id

        # https://cloud.google.com/agentspace/agentspace-enterprise/docs/research-assistant#rest
        # https://cloud.google.com/generative-ai-app-builder/docs/reference/rest/v1alpha/projects.locations.collections.engines.assistants/streamAssist
        stream_assist_request= {
            "query": {
                "text": query
            },
            "answerGenerationMode": "research",
            # "fileIds": [],
            # "filter": "",
            # "userMetadata": {
            #     "timeZone": "America/New_York"
            # },
        }

        if start_new_session == False:
            session = os.environ.get("SESSION")
            if session:
                stream_assist_request["session"] = os.environ.get("SESSION")

        url =  f"https://discoveryengine.googleapis.com/v1alpha/projects/{project_id}/locations/{location}/collections/default_collection/engines/{engine_id}/assistants/{assistant_id}:streamAssist"
        result = requests.post(
            url = url,
            data=json.dumps(stream_assist_request),
            headers=headers,
            )
            #stream=True)

        result_json = json.loads(result.text)    
        if start_new_session == True:
            session = result_json[0]['sessionInfo']['session']
            # Set an environment variable
            os.environ['SESSION'] = session

        markdown_text = process_deep_research_response(result)

        return markdown_text
    
    except ValueError as e:
        raise McpError(ErrorData(INVALID_PARAMS, str(e))) from e
    except Exception as e:
        raise McpError(ErrorData(INTERNAL_ERROR, f"Unexpected error: {str(e)}")) from e

def get_answer_response(
    # project_id: str,
    # location: str,
    # engine_id: str,
    query: str,
) -> str:
    """Retrieves an answer from the Discovery Engine using the AnswerQuery API.

    This function queries the specified Discovery Engine with the provided query
    and configuration options using the `AnswerQuery` API. It supports
    specifying a location-specific endpoint for the API.

    Args:
        project_id: The Google Cloud project ID.
        location: The location of the Discovery Engine (e.g., "global", "us-central1").
        engine_id: The ID of the Discovery Engine.
        query: The query string.

    Returns:
        A `discoveryengine.AnswerQueryResponse` object containing the answer,
        citations, and other related information.
    """
    client_options = (
        ClientOptions(api_endpoint=f"{location}-discoveryengine.googleapis.com")
        if location != "global"
        else None
    )

    # Create a client
    client = discoveryengine.ConversationalSearchServiceClient(
        client_options=client_options
    )

    # The full resource name of the Search serving config
    serving_config = f"projects/{project_id}/locations/{location}/collections/default_collection/engines/{engine_id}/servingConfigs/default_serving_config"

    # Optional: Options for query phase
    # The `query_understanding_spec` below includes all available query phase options.
    # For more details, refer to https://cloud.google.com/generative-ai-app-builder/docs/reference/rest/v1/QueryUnderstandingSpec
    query_understanding_spec = discoveryengine.AnswerQueryRequest.QueryUnderstandingSpec(
        query_rephraser_spec=discoveryengine.AnswerQueryRequest.QueryUnderstandingSpec.QueryRephraserSpec(
            disable=False,  # Optional: Disable query rephraser
            max_rephrase_steps=1,  # Optional: Number of rephrase steps
        ),
        # Optional: Classify query types
        query_classification_spec=discoveryengine.AnswerQueryRequest.QueryUnderstandingSpec.QueryClassificationSpec(
            types=[
                discoveryengine.AnswerQueryRequest.QueryUnderstandingSpec.QueryClassificationSpec.Type.ADVERSARIAL_QUERY,
                discoveryengine.AnswerQueryRequest.QueryUnderstandingSpec.QueryClassificationSpec.Type.NON_ANSWER_SEEKING_QUERY,
            ]  # Options: ADVERSARIAL_QUERY, NON_ANSWER_SEEKING_QUERY or both
        ),
    )

    # Optional: Options for answer phase
    # The `answer_generation_spec` below includes all available query phase options.
    # For more details, refer to https://cloud.google.com/generative-ai-app-builder/docs/reference/rest/v1/AnswerGenerationSpec
    answer_generation_spec = discoveryengine.AnswerQueryRequest.AnswerGenerationSpec(
        ignore_adversarial_query=False,  # Optional: Ignore adversarial query
        ignore_non_answer_seeking_query=False,  # Optional: Ignore non-answer seeking query
        ignore_low_relevant_content=False,  # Optional: Return fallback answer when content is not relevant
        model_spec=discoveryengine.AnswerQueryRequest.AnswerGenerationSpec.ModelSpec(
            model_version="gemini-2.0-flash-001/answer_gen/v1",  # Optional: Model to use for answer generation
            # model_version="gemini-2.0-flash/answer_gen/v2",  # Optional: Model to use for answer generation
        ),
        prompt_spec=discoveryengine.AnswerQueryRequest.AnswerGenerationSpec.PromptSpec(
            preamble="Give a detailed answer.",  # Optional: Natural language instructions for customizing the answer.
        ),
        include_citations=True,  # Optional: Include citations in the response
        answer_language_code="en",  # Optional: Language code of the answer
    )

    # Initialize request argument(s)
    request = discoveryengine.AnswerQueryRequest(
        serving_config=serving_config,
        query=discoveryengine.Query(text=query),
        session=None,  # Optional: include previous session ID to continue a conversation
        query_understanding_spec=query_understanding_spec,
        answer_generation_spec=answer_generation_spec,
    )

    # Make the request
    response = client.answer_query(request)

    # return response
    return response.answer.answer_text