from .system import check_services, get_gpu_metrics, get_vllm_models, get_storage_info

ALL_TOOLS = [check_services, get_gpu_metrics, get_vllm_models, get_storage_info]
