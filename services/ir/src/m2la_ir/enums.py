"""IR-specific enumerations for MuleSoft construct types."""

from enum import StrEnum


class TriggerType(StrEnum):
    """Types of flow triggers in MuleSoft."""

    HTTP_LISTENER = "http_listener"
    SCHEDULER = "scheduler"
    FLOW_REF = "flow_ref"
    VM_LISTENER = "vm_listener"
    FILE_LISTENER = "file_listener"
    UNKNOWN = "unknown"


class ProcessorType(StrEnum):
    """Types of message processors."""

    LOGGER = "logger"
    SET_VARIABLE = "set_variable"
    REMOVE_VARIABLE = "remove_variable"
    SET_PAYLOAD = "set_payload"
    FLOW_REF = "flow_ref"
    RAISE_ERROR = "raise_error"
    GENERIC = "generic"


class RouterType(StrEnum):
    """Types of message routers."""

    CHOICE = "choice"
    SCATTER_GATHER = "scatter_gather"
    FIRST_SUCCESSFUL = "first_successful"
    ROUND_ROBIN = "round_robin"


class ScopeType(StrEnum):
    """Types of processing scopes."""

    FOREACH = "foreach"
    UNTIL_SUCCESSFUL = "until_successful"
    TRY_SCOPE = "try_scope"
    ASYNC_SCOPE = "async_scope"
    PARALLEL_FOREACH = "parallel_foreach"


class TransformType(StrEnum):
    """Types of data transformations."""

    DATAWEAVE = "dataweave"
    SET_PAYLOAD = "set_payload"
    EXPRESSION = "expression"


class ConnectorType(StrEnum):
    """Types of connector operations."""

    HTTP_REQUEST = "http_request"
    DB = "db"
    MQ = "mq"
    FTP = "ftp"
    SFTP = "sftp"
    EMAIL = "email"
    VM = "vm"
    FILE = "file"
    GENERIC = "generic"


class ErrorHandlerType(StrEnum):
    """Types of error handlers."""

    ON_ERROR_PROPAGATE = "on_error_propagate"
    ON_ERROR_CONTINUE = "on_error_continue"


class FlowKind(StrEnum):
    """Discriminator for flow vs sub-flow."""

    FLOW = "flow"
    SUB_FLOW = "sub_flow"
