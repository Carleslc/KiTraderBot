import re

from requests import get
from json import loads as json

from abc import ABC, abstractmethod 

NON_ALPHA = r'[^a-zA-Z]'

def symbol_id(symbol: str) -> str:
  return re.sub(NON_ALPHA, '', symbol.lower())

def is_authorized(bot_name, from_user, superuser, target):
    return target == from_user or (superuser and target == bot_name)

def __float(s):
  try:
      return True, float(s)
  except ValueError:
      return False, 0

class API(ABC):
  """ Trading API """

  def __init__(self, name: str, base_url: str, min_trade: float, fee: float, requests_limit_per_minute: int):
    """
    Create an instance of this API.
    
    name: API name
    base_url: API base url to make requests
    min_trade: minimum total trade (price * amount)
    fee: fee percentage, e.g. 0.005 for a 0.5%
    requests_limit_per_minute: maximum amount of requests allowed per minute
    """
    self.name = name
  
  def __get(self, url, callback, filter_status=True):
    response = get(self.base_url + url)
    code = response.status_code
    success = code >= 200 and code < 300
    content = json(response.content) if success else None
    if not filter_status:
      return callback(content, code)
    if code >= 200 and code < 300:
      return callback(content)
    return f"{self.name} API: {code}"

  @abstractmethod
  def ping(self) -> str:
    """ Test if API is reachable """
    pass

  @abstractmethod
  def list_symbols(self) -> str:
    """ List available symbol pairs """
    pass

  @abstractmethod
  def __price(symbol: str, callback: function):
    """
    Get the current price of a symbol and call the callback with the result
    symbol: pair symbol
    callback: (str -> float or str)
    returns: callback result
    """
    pass

  def get_price(self, symbol: str) -> float:
    """ Get the current price of a symbol """
    return self.__price(symbol_id(symbol), lambda price: float(price))
    
  @abstractmethod
  def price(self, user: str, symbol: str) -> str:
    pass

  @abstractmethod
  def exists(self, symbol: str) -> bool:
    """ Test if symbol is available in this API """
    pass

  @abstractmethod
  def account(bot_name: str, user: str, superuser: bool, other: str) -> str:
    pass

  @abstractmethod
  def history(bot_name: str, user: str, superuser: bool, other: str) -> str:
    pass

  @abstractmethod
  def existsAccount(self, user: str) -> bool:
    """ Check if a user has an account for this API """
    pass

  def newAccount(self, user: str, args='') -> str:
    """
    Create a user account

    args: [balance] [currency]
    """
    args = args.split(' ', 1)
    balance = args[0] if args[0] else '1000'
    success, balance = __float(balance)
    if not success:
        return "Balance must be in decimal format. For example: 500.25 USD"
    currency = 'USD' if len(args) < 2 else args[1]
    return self.__newAccount(user, balance, currency)

  @abstractmethod
  def __newAccount(self, user: str, balance: float, currency: str) -> str:
    pass

  @abstractmethod
  def deleteAccount(self, user: str) -> str:
    pass

  @abstractmethod
  def trade(self, user: str, order: str) -> str:
    pass

  @abstractmethod
  def tradeAll(self, user: str, order: str) -> str:
    pass

  @abstractmethod
  def load(self):
    """ Load accounts and API resources """
    pass

  @abstractmethod
  def save(self):
    """ Save accounts and API resources """
    pass
