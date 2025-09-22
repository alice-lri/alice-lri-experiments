from abc import ABC, abstractmethod

class Dataset(ABC):
    @property
    @abstractmethod
    def v_offsets(self) -> list[float]:
        pass

    @property
    @abstractmethod
    def v_angles(self) -> list[float]:
        pass

    @property
    @abstractmethod
    def h_offsets(self) -> list[float]:
        pass

    @property
    @abstractmethod
    def h_resolutions(self) -> list[float]:
        pass