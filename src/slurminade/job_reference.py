import abc
from typing import Any, Dict, Optional

class JobReference(abc.ABC):
    @abc.abstractmethod
    def get_job_id(self) -> Optional[int]:
        pass

    @abc.abstractmethod
    def get_exit_code(self) -> Optional[int]:
        pass

    @abc.abstractmethod
    def get_info(self) -> Dict[str, Any]:
        pass