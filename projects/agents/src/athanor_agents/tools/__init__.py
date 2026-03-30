try:
    from .system import check_services, get_gpu_metrics, get_vllm_models, get_storage_info
    SYSTEM_TOOLS = [check_services, get_gpu_metrics, get_vllm_models, get_storage_info]
except ModuleNotFoundError:
    check_services = None
    get_gpu_metrics = None
    get_vllm_models = None
    get_storage_info = None
    SYSTEM_TOOLS = []

from .execution import (
    delegate_to_agent, check_task_status,
    read_file, write_file, list_directory, search_files,
    run_command,
    DELEGATION_TOOLS, FILESYSTEM_TOOLS, SHELL_TOOLS, EXECUTION_TOOLS,
)

ALL_TOOLS = [
    *SYSTEM_TOOLS,
    delegate_to_agent, check_task_status,
    read_file, write_file, list_directory, search_files,
]
