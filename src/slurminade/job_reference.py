import abc
from typing import Any, Dict, Optional


class JobReference(abc.ABC):
    """
    The reference to a job that has been dispatched using any dispatcher.
    While the primary purpose of slurminde is to dispatch jobs to slurm,
    return a reference to a slurm job, there are other dispatchers for
    local testing. The dispatchers can create their own job reference
    classes, such that they can add additional information to the job
    as needed.
    """

    @abc.abstractmethod
    def get_job_id(self) -> Optional[int]:
        pass

    @abc.abstractmethod
    def get_exit_code(self) -> Optional[int]:
        pass

    @abc.abstractmethod
    def get_info(self) -> Dict[str, Any]:
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(job_id={self.get_job_id()}, exit_code={self.get_exit_code()}, info={self.get_info()})"
