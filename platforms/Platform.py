'''
this abstract class will be uesed as a muster to implement that possible classes of trade platform
'''
from abc import ABC, abstractmethod

class Platform(ABC):

    @abstractmethod
    def __init__(self, ws_url=None):
        self.ws_url = ws_url

    # @property
    # def ws_url(self):
    #     pass

    # @ws_url.setter
    # @abstractmethod
    # def ws_url(self, ws_url):
    #     pass

    # @ws_url.getter
    # @abstractmethod  
    # def ws_url(self):
    #     pass

    @abstractmethod
    def fetch_subscription(self):
        pass

    @abstractmethod
    def get_current_bid(self):
        pass

    @abstractmethod
    def get_current_ask(self):
        pass