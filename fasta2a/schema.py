"""This module contains the schema for the agent card."""

from __future__ import annotations as _annotations

from typing import Annotated, Any, Generic, Literal, TypeVar, Union

import pydantic
from pydantic import Discriminator, TypeAdapter
from pydantic.alias_generators import to_camel
from typing_extensions import NotRequired, TypeAlias, TypedDict


@pydantic.with_config({'alias_generator': to_camel})
class AgentCard(TypedDict):
    """The card that describes an agent."""

    name: str
    """Human readable name of the agent e.g. "Recipe Agent"."""

    description: str
    """A human-readable description of the agent.

    Used to assist users and other agents in understanding what the agent can do.
    (e.g. "Agent that helps users with recipes and cooking.")
    """

    version: str
    """The version of the agent - format is up to the provider. (e.g. "1.0.0")"""

    provider: NotRequired[AgentProvider]
    """The service provider of the agent."""

    documentation_url: NotRequired[str]
    """A URL to documentation for the agent."""

    icon_url: NotRequired[str]
    """A URL to an icon for the agent."""

    supported_interfaces: NotRequired[list[AgentInterface]]
    """Ordered list of supported interfaces. The first entry is preferred."""

    capabilities: AgentCapabilities
    """The capabilities of the agent."""

    security_requirements: NotRequired[list[SecurityRequirement]]
    """Security requirements for contacting the agent."""

    security_schemes: NotRequired[dict[str, SecurityScheme]]
    """Security scheme definitions."""

    default_input_modes: list[str]
    """Supported mime types for input data."""

    default_output_modes: list[str]
    """Supported mime types for output data."""

    skills: list[Skill]
    """The set of skills, or distinct capabilities, that the agent can perform."""

    signatures: NotRequired[list[AgentCardSignature]]
    """JSON Web Signatures computed for this AgentCard."""


agent_card_ta = pydantic.TypeAdapter(AgentCard)


class AgentProvider(TypedDict):
    """The service provider of the agent."""

    organization: str
    """The name of the agent provider's organization."""

    url: str
    """A URL for the agent provider's website or relevant documentation."""


@pydantic.with_config({'alias_generator': to_camel})
class AgentCapabilities(TypedDict):
    """The capabilities of the agent."""

    streaming: NotRequired[bool]
    """Whether the agent supports streaming."""

    push_notifications: NotRequired[bool]
    """Whether the agent can notify updates to client."""

    extended_agent_card: NotRequired[bool]
    """Whether the agent supports providing an extended agent card when authenticated."""

    extensions: NotRequired[list[AgentExtension]]
    """A list of protocol extensions supported by the agent."""


@pydantic.with_config({'alias_generator': to_camel})
class HttpSecurityScheme(TypedDict):
    """HTTP security scheme."""

    scheme: str
    """The name of the HTTP Authorization scheme (e.g., 'Bearer')."""

    bearer_format: NotRequired[str]
    """A hint to the client to identify how the bearer token is formatted."""

    description: NotRequired[str]
    """Description of this security scheme."""


@pydantic.with_config({'alias_generator': to_camel})
class ApiKeySecurityScheme(TypedDict):
    """API Key security scheme."""

    name: str
    """The name of the header, query or cookie parameter to be used."""

    location: str
    """The location of the API key. Valid values are 'query', 'header', or 'cookie'."""

    description: NotRequired[str]
    """Description of this security scheme."""


@pydantic.with_config({'alias_generator': to_camel})
class AuthorizationCodeOAuthFlow(TypedDict):
    """Configuration for the OAuth 2.0 Authorization Code flow."""

    authorization_url: str
    """The authorization URL to be used for this flow."""

    token_url: str
    """The token URL to be used for this flow."""

    refresh_url: NotRequired[str]
    """The URL to be used for obtaining refresh tokens."""

    scopes: NotRequired[dict[str, str]]
    """The available scopes for the OAuth2 security scheme."""

    pkce_required: NotRequired[bool]
    """Whether PKCE (RFC 7636) is required for this flow."""


@pydantic.with_config({'alias_generator': to_camel})
class ClientCredentialsOAuthFlow(TypedDict):
    """Configuration for the OAuth 2.0 Client Credentials flow."""

    token_url: str
    """The token URL to be used for this flow."""

    refresh_url: NotRequired[str]
    """The URL to be used for obtaining refresh tokens."""

    scopes: NotRequired[dict[str, str]]
    """The available scopes for the OAuth2 security scheme."""


@pydantic.with_config({'alias_generator': to_camel})
class DeviceCodeOAuthFlow(TypedDict):
    """Configuration for the OAuth 2.0 Device Code flow (RFC 8628)."""

    device_authorization_url: str
    """The device authorization endpoint URL."""

    token_url: str
    """The token URL to be used for this flow."""

    refresh_url: NotRequired[str]
    """The URL to be used for obtaining refresh tokens."""

    scopes: NotRequired[dict[str, str]]
    """The available scopes for the OAuth2 security scheme."""


@pydantic.with_config({'alias_generator': to_camel})
class ImplicitOAuthFlow(TypedDict):
    """Deprecated: Use Authorization Code + PKCE instead."""

    authorization_url: str
    """The authorization URL to be used for this flow."""

    refresh_url: NotRequired[str]
    """The URL to be used for obtaining refresh tokens."""

    scopes: NotRequired[dict[str, str]]
    """The available scopes for the OAuth2 security scheme."""


@pydantic.with_config({'alias_generator': to_camel})
class PasswordOAuthFlow(TypedDict):
    """Deprecated: Use Authorization Code + PKCE or Device Code."""

    token_url: str
    """The token URL to be used for this flow."""

    refresh_url: NotRequired[str]
    """The URL to be used for obtaining refresh tokens."""

    scopes: NotRequired[dict[str, str]]
    """The available scopes for the OAuth2 security scheme."""


@pydantic.with_config({'alias_generator': to_camel})
class OAuthFlows(TypedDict):
    """Configuration for the supported OAuth 2.0 flows."""

    authorization_code: NotRequired[AuthorizationCodeOAuthFlow]
    """Configuration for the OAuth Authorization Code flow."""

    client_credentials: NotRequired[ClientCredentialsOAuthFlow]
    """Configuration for the OAuth Client Credentials flow."""

    device_code: NotRequired[DeviceCodeOAuthFlow]
    """Configuration for the OAuth Device Code flow."""

    implicit: NotRequired[ImplicitOAuthFlow]
    """Deprecated: Use Authorization Code + PKCE instead."""

    password: NotRequired[PasswordOAuthFlow]
    """Deprecated: Use Authorization Code + PKCE or Device Code."""


@pydantic.with_config({'alias_generator': to_camel})
class OAuth2SecurityScheme(TypedDict):
    """OAuth2 security scheme."""

    flows: NotRequired[OAuthFlows]
    """An object containing configuration information for the supported OAuth 2.0 flows."""

    oauth2_metadata_url: NotRequired[str]
    """URL to the OAuth2 authorization server metadata (RFC 8414)."""

    description: NotRequired[str]
    """Description of this security scheme."""


@pydantic.with_config({'alias_generator': to_camel})
class OpenIdConnectSecurityScheme(TypedDict):
    """OpenID Connect security scheme."""

    open_id_connect_url: str
    """OpenId Connect URL to discover OAuth2 configuration values."""

    description: NotRequired[str]
    """Description of this security scheme."""


class MutualTlsSecurityScheme(TypedDict):
    """Mutual TLS security scheme."""

    description: NotRequired[str]
    """Description of this security scheme."""


@pydantic.with_config({'alias_generator': to_camel})
class SecurityScheme(TypedDict):
    """A security scheme for authentication.

    This is a wrapper type with mutually exclusive optional fields.
    """

    http_auth_security_scheme: NotRequired[HttpSecurityScheme]
    """HTTP authentication (Basic, Bearer, etc.)."""

    api_key_security_scheme: NotRequired[ApiKeySecurityScheme]
    """API key-based authentication."""

    oauth2_security_scheme: NotRequired[OAuth2SecurityScheme]
    """OAuth 2.0 authentication."""

    open_id_connect_security_scheme: NotRequired[OpenIdConnectSecurityScheme]
    """OpenID Connect authentication."""

    mtls_security_scheme: NotRequired[MutualTlsSecurityScheme]
    """Mutual TLS authentication."""


@pydantic.with_config({'alias_generator': to_camel})
class SecurityRequirement(TypedDict):
    """Defines the security requirements for an agent or skill."""

    schemes: dict[str, list[str]]
    """A map of security scheme names to the required scopes."""


@pydantic.with_config({'alias_generator': to_camel})
class AgentInterface(TypedDict):
    """An interface that the agent supports."""

    protocol_binding: Literal['JSONRPC', 'GRPC', 'HTTP+JSON'] | str
    """The protocol binding (e.g., 'JSONRPC', 'GRPC', 'HTTP+JSON')."""

    url: str
    """The URL endpoint for this interface."""

    protocol_version: NotRequired[str]
    """The version of the A2A protocol this interface exposes."""

    tenant: NotRequired[str]
    """Tenant ID to be used in the request when calling the agent."""


@pydantic.with_config({'alias_generator': to_camel})
class AgentExtension(TypedDict):
    """A declaration of an extension supported by an Agent."""

    uri: str
    """The URI of the extension."""

    description: NotRequired[str]
    """A description of how this agent uses this extension."""

    required: NotRequired[bool]
    """Whether the client must follow specific requirements of the extension."""

    params: NotRequired[dict[str, Any]]
    """Optional configuration for the extension."""


class AgentCardSignature(TypedDict):
    """Represents a JWS signature of an AgentCard (RFC 7515)."""

    protected: str
    """The protected JWS header, base64url-encoded JSON object."""

    signature: str
    """The computed signature, base64url-encoded."""

    header: NotRequired[dict[str, Any]]
    """The unprotected JWS header values."""


@pydantic.with_config({'alias_generator': to_camel})
class Skill(TypedDict):
    """Skills are a unit of capability that an agent can perform."""

    id: str
    """A unique identifier for the skill."""

    name: str
    """Human readable name of the skill."""

    description: str
    """A human-readable description of the skill.

    It will be used by the client or a human as a hint to understand the skill.
    """

    tags: list[str]
    """Set of tag-words describing classes of capabilities for this specific skill.

    Examples: "cooking", "customer support", "billing".
    """

    examples: NotRequired[list[str]]
    """The set of example scenarios that the skill can perform.

    Will be used by the client as a hint to understand how the skill can be used. (e.g. "I need a recipe for bread")
    """

    input_modes: list[str]
    """Supported mime types for input data."""

    output_modes: list[str]
    """Supported mime types for output data."""

    security_requirements: NotRequired[list[SecurityRequirement]]
    """Security schemes necessary for this skill."""


@pydantic.with_config({'alias_generator': to_camel})
class Artifact(TypedDict):
    """Agents generate Artifacts as an end result of a Task.

    Artifacts are immutable, can be named, and can have multiple parts. A streaming response can append parts to
    existing Artifacts.

    A single Task can generate many Artifacts. For example, "create a webpage" could create separate HTML and image
    Artifacts.
    """

    artifact_id: str
    """Unique identifier for the artifact."""

    name: NotRequired[str]
    """The name of the artifact."""

    description: NotRequired[str]
    """A description of the artifact."""

    parts: list[Part]
    """The parts that make up the artifact."""

    metadata: NotRequired[dict[str, Any]]
    """Metadata about the artifact."""

    extensions: NotRequired[list[str]]
    """Array of extensions."""


class AuthenticationInfo(TypedDict):
    """Defines authentication details, used for push notifications."""

    scheme: str
    """HTTP Authentication Scheme (e.g., 'Bearer', 'Basic', 'Digest')."""

    credentials: NotRequired[str]
    """Push notification credentials. Format depends on the scheme (e.g., token for Bearer)."""


@pydantic.with_config({'alias_generator': to_camel})
class TaskPushNotificationConfig(TypedDict):
    """A container associating a push notification configuration with a specific task."""

    id: NotRequired[str]
    """A unique identifier (e.g. UUID) for this push notification configuration."""

    task_id: NotRequired[str]
    """The ID of the task this configuration is associated with."""

    tenant: NotRequired[str]
    """Optional. Tenant ID."""

    url: str
    """The URL where the notification should be sent."""

    token: NotRequired[str]
    """A token unique for this task or session."""

    authentication: NotRequired[AuthenticationInfo]
    """Authentication information required to send the notification."""


@pydantic.with_config({'alias_generator': to_camel})
class Message(TypedDict):
    """A Message contains any content that is not an Artifact.

    This can include things like agent thoughts, user context, instructions, errors, status, or metadata.

    All content from a client comes in the form of a Message. Agents send Messages to communicate status or to provide
    instructions (whereas generated results are sent as Artifacts).

    A Message can have multiple parts to denote different pieces of content. For example, a user request could include
    a textual description from a user and then multiple files used as context from the client.
    """

    role: Literal['user', 'agent']
    """The role of the message."""

    parts: list[Part]
    """The parts of the message."""

    metadata: NotRequired[dict[str, Any]]
    """Metadata about the message."""

    message_id: str
    """Identifier created by the message creator."""

    context_id: NotRequired[str]
    """The context the message is associated with."""

    task_id: NotRequired[str]
    """Identifier of task the message is related to."""

    reference_task_ids: NotRequired[list[str]]
    """Array of task IDs this message references."""

    extensions: NotRequired[list[str]]
    """Array of extensions."""


@pydantic.with_config({'alias_generator': to_camel})
class Part(TypedDict):
    """A container for a section of communication content.

    Parts can be textual, a file (image, video, etc), or structured data.
    Fields are mutually exclusive: use `text` for text content, `raw`/`url` for file content,
    or `data` for structured JSON data.
    """

    text: NotRequired[str]
    """The string content of the text part."""

    raw: NotRequired[str]
    """The raw byte content of a file, base64-encoded."""

    url: NotRequired[str]
    """A URL pointing to the file's content."""

    data: NotRequired[Any]
    """Arbitrary structured data as a JSON value."""

    filename: NotRequired[str]
    """An optional filename for the file (e.g., 'document.pdf')."""

    media_type: NotRequired[str]
    """The MIME type of the part content (e.g., 'text/plain', 'application/json', 'image/png')."""

    metadata: NotRequired[dict[str, Any]]
    """Optional metadata associated with this part."""


TaskState: TypeAlias = Literal[
    'submitted', 'working', 'input-required', 'completed', 'canceled', 'failed', 'rejected', 'auth-required'
]
"""The possible states of a task."""

STREAM_ENDING_STATES: frozenset[str] = frozenset(
    {'completed', 'canceled', 'failed', 'rejected', 'input-required', 'auth-required'}
)
"""The states at which a task's stream ends: the task is over, or it is waiting on the client.

The status update that carries one of these is the last event of a `message/stream`, and
`tasks/resubscribe` on such a task has nothing to wait for.
"""


@pydantic.with_config({'alias_generator': to_camel})
class TaskStatus(TypedDict):
    """Status and accompanying message for a task."""

    state: TaskState
    """The current state of the task."""

    message: NotRequired[Message]
    """Additional status updates for client."""

    timestamp: NotRequired[str]
    """ISO datetime value of when the status was updated."""


@pydantic.with_config({'alias_generator': to_camel})
class Task(TypedDict):
    """A Task is a stateful entity that allows Clients and Remote Agents to achieve a specific outcome.

    Clients and Remote Agents exchange Messages within a Task. Remote Agents generate results as Artifacts.
    A Task is always created by a Client and the status is always determined by the Remote Agent.
    """

    id: str
    """Unique identifier for the task."""

    context_id: str
    """The context the task is associated with."""

    status: TaskStatus
    """Current status of the task."""

    history: NotRequired[list[Message]]
    """Optional history of messages."""

    artifacts: NotRequired[list[Artifact]]
    """Collection of artifacts created by the agent."""

    metadata: NotRequired[dict[str, Any]]
    """Extension metadata."""


@pydantic.with_config({'alias_generator': to_camel})
class TaskStatusUpdateEvent(TypedDict):
    """Sent by server during message/stream requests."""

    task_id: str
    """The id of the task."""

    context_id: str
    """The context the task is associated with."""

    status: TaskStatus
    """The status of the task."""

    metadata: NotRequired[dict[str, Any]]
    """Extension metadata."""


@pydantic.with_config({'alias_generator': to_camel})
class TaskArtifactUpdateEvent(TypedDict):
    """Sent by server during message/stream requests."""

    task_id: str
    """The id of the task."""

    context_id: str
    """The context the task is associated with."""

    artifact: Artifact
    """The artifact that was updated."""

    append: NotRequired[bool]
    """Whether to append to existing artifact (true) or replace (false)."""

    last_chunk: NotRequired[bool]
    """Indicates this is the final chunk of the artifact."""

    metadata: NotRequired[dict[str, Any]]
    """Extension metadata."""


@pydantic.with_config({'alias_generator': to_camel})
class TaskIdParams(TypedDict):
    """Parameters for a task id."""

    id: str
    """The unique identifier for the task."""

    tenant: NotRequired[str]
    """Optional. Tenant ID."""

    metadata: NotRequired[dict[str, Any]]
    """Optional metadata associated with the request."""


@pydantic.with_config({'alias_generator': to_camel})
class TaskQueryParams(TaskIdParams):
    """Query parameters for a task."""

    history_length: NotRequired[int]
    """Number of recent messages to be retrieved."""


@pydantic.with_config({'alias_generator': to_camel})
class ListTasksParams(TypedDict):
    """Parameters for listing tasks with optional filtering criteria."""

    context_id: NotRequired[str]
    """Filter tasks by context ID."""

    status: NotRequired[TaskState]
    """Filter tasks by their current status state."""

    status_timestamp_after: NotRequired[str]
    """Filter tasks with status updated after this ISO 8601 timestamp."""

    history_length: NotRequired[int]
    """The maximum number of messages to include in each task's history."""

    include_artifacts: NotRequired[bool]
    """Whether to include artifacts in the returned tasks. Defaults to false."""

    page_size: NotRequired[int]
    """The maximum number of tasks to return (1-100, default 50)."""

    page_token: NotRequired[str]
    """A page token from a previous `ListTasks` call for pagination."""

    tenant: NotRequired[str]
    """Optional. Tenant ID."""


@pydantic.with_config({'alias_generator': to_camel})
class ListTasksResult(TypedDict):
    """Result for listing tasks with pagination information."""

    tasks: list[Task]
    """Array of tasks matching the specified criteria."""

    next_page_token: NotRequired[str]
    """A token to retrieve the next page of results."""

    page_size: NotRequired[int]
    """The page size used for this response."""

    total_size: NotRequired[int]
    """Total number of tasks available (before pagination)."""


@pydantic.with_config({'alias_generator': to_camel})
class MessageSendConfiguration(TypedDict):
    """Configuration for the send message request."""

    accepted_output_modes: list[str]
    """Accepted output modalities by the client."""

    blocking: NotRequired[bool]
    """If the server should treat the client as a blocking request."""

    history_length: NotRequired[int]
    """Number of recent messages to be retrieved."""

    task_push_notification_config: NotRequired[TaskPushNotificationConfig]
    """Configuration for the agent to send push notifications for task updates."""


@pydantic.with_config({'alias_generator': to_camel})
class MessageSendParams(TypedDict):
    """Parameters for message/send method."""

    configuration: NotRequired[MessageSendConfiguration]
    """Send message configuration."""

    message: Message
    """The message being sent to the server."""

    tenant: NotRequired[str]
    """Optional. Tenant ID."""

    metadata: NotRequired[dict[str, Any]]
    """Extension metadata."""


@pydantic.with_config({'alias_generator': to_camel})
class TaskSendParams(TypedDict):
    """Internal parameters for task execution within the framework.

    Note: This is not part of the A2A protocol - it's used internally
    for broker/worker communication.
    """

    id: str
    """The id of the task."""

    context_id: str
    """The context id for the task."""

    message: Message
    """The message to process."""

    history_length: NotRequired[int]
    """Number of recent messages to be retrieved."""

    accepted_output_modes: NotRequired[list[str]]
    """The media types the client accepts for the answer (`acceptedOutputModes`), when it named any."""

    metadata: NotRequired[dict[str, Any]]
    """Extension metadata."""


@pydantic.with_config({'alias_generator': to_camel})
class GetTaskPushNotificationConfigParams(TypedDict):
    """Parameters for getting a push notification configuration."""

    id: str
    """The resource ID of the configuration to retrieve."""

    task_id: str
    """The parent task resource ID."""

    tenant: NotRequired[str]
    """Optional. Tenant ID."""


@pydantic.with_config({'alias_generator': to_camel})
class ListTaskPushNotificationConfigParams(TypedDict):
    """Parameters for listing push notification configurations associated with a task."""

    task_id: str
    """The parent task resource ID."""

    page_size: NotRequired[int]
    """The maximum number of configurations to return."""

    page_token: NotRequired[str]
    """A page token received from a previous request."""

    tenant: NotRequired[str]
    """Optional. Tenant ID."""


@pydantic.with_config({'alias_generator': to_camel})
class ListTaskPushNotificationConfigResult(TypedDict):
    """Result for listing push notification configurations."""

    configs: list[TaskPushNotificationConfig]
    """The list of push notification configurations."""

    next_page_token: NotRequired[str]
    """A token to retrieve the next page of results."""


@pydantic.with_config({'alias_generator': to_camel})
class DeleteTaskPushNotificationConfigParams(TypedDict):
    """Parameters for removing a push notification configuration associated with a task."""

    id: str
    """The resource ID of the configuration to delete."""

    task_id: str
    """The parent task resource ID."""

    tenant: NotRequired[str]
    """Optional. Tenant ID."""


class JSONRPCMessage(TypedDict):
    """A JSON RPC message."""

    jsonrpc: Literal['2.0']
    """The JSON RPC version."""

    id: int | str | None
    """The request id."""


Method = TypeVar('Method')
Params = TypeVar('Params')


class JSONRPCRequest(JSONRPCMessage, Generic[Method, Params]):
    """A JSON RPC request."""

    method: Method
    """The method to call."""

    params: Params
    """The parameters to pass to the method."""


###############################################################################################
#######################################   Error codes   #######################################
###############################################################################################

CodeT = TypeVar('CodeT', bound=int)
MessageT = TypeVar('MessageT', bound=str)


class JSONRPCError(TypedDict, Generic[CodeT, MessageT]):
    """A JSON RPC error."""

    code: CodeT
    """A number that indicates the error type that occurred."""

    message: MessageT
    """A string providing a short description of the error."""

    data: NotRequired[Any]
    """A primitive or structured value containing additional information about the error."""


ResultT = TypeVar('ResultT')
ErrorT = TypeVar('ErrorT', bound=JSONRPCError[Any, Any])


class JSONRPCResponse(JSONRPCMessage, Generic[ResultT, ErrorT]):
    """A JSON RPC response."""

    result: NotRequired[ResultT]
    error: NotRequired[ErrorT]


JSONParseError = JSONRPCError[Literal[-32700], Literal['Invalid JSON payload']]
"""A JSON RPC error for a parse error."""

InvalidRequestError = JSONRPCError[Literal[-32600], Literal['Request payload validation error']]
"""A JSON RPC error for an invalid request."""

MethodNotFoundError = JSONRPCError[Literal[-32601], Literal['Method not found']]
"""A JSON RPC error for a method not found."""

InvalidParamsError = JSONRPCError[Literal[-32602], Literal['Invalid parameters']]
"""A JSON RPC error for invalid parameters."""

InternalError = JSONRPCError[Literal[-32603], Literal['Internal error']]
"""A JSON RPC error for an internal error."""

TaskNotFoundError = JSONRPCError[Literal[-32001], Literal['Task not found']]
"""A JSON RPC error for a task not found."""

TaskNotCancelableError = JSONRPCError[Literal[-32002], Literal['Task not cancelable']]
"""A JSON RPC error for a task not cancelable."""

PushNotificationNotSupportedError = JSONRPCError[Literal[-32003], Literal['Push notification not supported']]
"""A JSON RPC error for a push notification not supported."""

UnsupportedOperationError = JSONRPCError[Literal[-32004], Literal['This operation is not supported']]
"""A JSON RPC error for an unsupported operation."""

ContentTypeNotSupportedError = JSONRPCError[Literal[-32005], Literal['Incompatible content types']]
"""A JSON RPC error for incompatible content types."""

InvalidAgentResponseError = JSONRPCError[Literal[-32006], Literal['Invalid agent response']]
"""A JSON RPC error for invalid agent response."""

###############################################################################################
#######################################   Requests and responses   ############################
###############################################################################################

SendMessageRequest = JSONRPCRequest[Literal['message/send'], MessageSendParams]
"""A JSON RPC request to send a message."""


@pydantic.with_config({'alias_generator': to_camel})
class SendMessageResult(TypedDict):
    """The result of a SendMessage request."""

    message: NotRequired[Message]
    """A message from the agent."""

    task: NotRequired[Task]
    """The task created or updated by the message."""


SendMessageResponse = JSONRPCResponse[SendMessageResult, JSONRPCError[Any, Any]]
"""A JSON RPC response to send a message."""

StreamMessageRequest = JSONRPCRequest[Literal['message/stream'], MessageSendParams]
"""A JSON RPC request to stream a message."""


@pydantic.with_config({'alias_generator': to_camel})
class StreamResponse(TypedDict):
    """A wrapper object used in streaming operations to encapsulate different types of response data."""

    message: NotRequired[Message]
    """A Message object containing a message from the agent."""

    task: NotRequired[Task]
    """A Task object containing the current state of the task."""

    status_update: NotRequired[TaskStatusUpdateEvent]
    """An event indicating a task status update."""

    artifact_update: NotRequired[TaskArtifactUpdateEvent]
    """An event indicating a task artifact update."""


StreamMessageResponse = JSONRPCResponse[StreamResponse, JSONRPCError[Any, Any]]
"""A JSON RPC response to a StreamMessageRequest."""

GetTaskRequest = JSONRPCRequest[Literal['tasks/get'], TaskQueryParams]
"""A JSON RPC request to get a task."""

GetTaskResponse = JSONRPCResponse[Task, TaskNotFoundError]
"""A JSON RPC response to get a task."""

CancelTaskRequest = JSONRPCRequest[Literal['tasks/cancel'], TaskIdParams]
"""A JSON RPC request to cancel a task."""

CancelTaskResponse = JSONRPCResponse[Task, Union[TaskNotCancelableError, TaskNotFoundError]]
"""A JSON RPC response to cancel a task."""

SetTaskPushNotificationRequest = JSONRPCRequest[Literal['tasks/pushNotification/set'], TaskPushNotificationConfig]
"""A JSON RPC request to set a task push notification."""

SetTaskPushNotificationResponse = JSONRPCResponse[TaskPushNotificationConfig, PushNotificationNotSupportedError]
"""A JSON RPC response to set a task push notification."""

GetTaskPushNotificationRequest = JSONRPCRequest[
    Literal['tasks/pushNotification/get'], GetTaskPushNotificationConfigParams
]
"""A JSON RPC request to get a task push notification."""

GetTaskPushNotificationResponse = JSONRPCResponse[TaskPushNotificationConfig, PushNotificationNotSupportedError]
"""A JSON RPC response to get a task push notification."""

ResubscribeTaskRequest = JSONRPCRequest[Literal['tasks/resubscribe'], TaskIdParams]
"""A JSON RPC request to resubscribe to a task."""

ListTaskPushNotificationConfigRequest = JSONRPCRequest[
    Literal['tasks/pushNotificationConfig/list'], ListTaskPushNotificationConfigParams
]
"""A JSON RPC request to list task push notification configs."""

ListTaskPushNotificationConfigResponse = JSONRPCResponse[
    ListTaskPushNotificationConfigResult, PushNotificationNotSupportedError
]
"""A JSON RPC response to list task push notification configs."""

DeleteTaskPushNotificationConfigRequest = JSONRPCRequest[
    Literal['tasks/pushNotificationConfig/delete'], DeleteTaskPushNotificationConfigParams
]
"""A JSON RPC request to delete a task push notification config."""

DeleteTaskPushNotificationConfigResponse = JSONRPCResponse[None, PushNotificationNotSupportedError]
"""A JSON RPC response to delete a task push notification config."""

ListTasksRequest = JSONRPCRequest[Literal['tasks/list'], ListTasksParams]
"""A JSON RPC request to list tasks."""

ListTasksResponse = JSONRPCResponse[ListTasksResult, JSONRPCError[Any, Any]]
"""A JSON RPC response to list tasks."""

A2ARequest = Annotated[
    Union[
        SendMessageRequest,
        StreamMessageRequest,
        GetTaskRequest,
        CancelTaskRequest,
        SetTaskPushNotificationRequest,
        GetTaskPushNotificationRequest,
        ResubscribeTaskRequest,
        ListTaskPushNotificationConfigRequest,
        DeleteTaskPushNotificationConfigRequest,
        ListTasksRequest,
    ],
    Discriminator('method'),
]
"""A JSON RPC request to the A2A server."""

A2AResponse: TypeAlias = Union[
    SendMessageResponse,
    StreamMessageResponse,
    GetTaskResponse,
    CancelTaskResponse,
    SetTaskPushNotificationResponse,
    GetTaskPushNotificationResponse,
    ListTaskPushNotificationConfigResponse,
    DeleteTaskPushNotificationConfigResponse,
    ListTasksResponse,
]
"""A JSON RPC response from the A2A server."""


a2a_request_ta: TypeAdapter[A2ARequest] = TypeAdapter(A2ARequest)
a2a_response_ta: TypeAdapter[A2AResponse] = TypeAdapter(A2AResponse)
send_message_request_ta: TypeAdapter[SendMessageRequest] = TypeAdapter(SendMessageRequest)
send_message_response_ta: TypeAdapter[SendMessageResponse] = TypeAdapter(SendMessageResponse)
stream_message_request_ta: TypeAdapter[StreamMessageRequest] = TypeAdapter(StreamMessageRequest)
stream_message_response_ta: TypeAdapter[StreamMessageResponse] = TypeAdapter(StreamMessageResponse)
