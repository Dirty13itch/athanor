from .system import check_services, get_gpu_metrics, get_vllm_models, get_storage_info
from .execution import delegate_to_agent, check_task_status

ALL_TOOLS = [
    check_services, get_gpu_metrics, get_vllm_models, get_storage_info,
    delegate_to_agent, check_task_status,
]
