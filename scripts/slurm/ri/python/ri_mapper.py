from abc import ABC, abstractmethod


class RangeImageMapper(ABC):
    def __init__(self, w, h):
        self.w = w
        self.h = h

    @abstractmethod
    def map(self, points):
        pass

    @abstractmethod
    def unmap(self):
        pass
