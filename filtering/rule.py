from abc import ABC, abstractmethod  # create  abstract  class
from typing import Optional 
from logic_manager import _normalise  # lowercase, removes symbols and extra spaces
from models import Recommendation, RuleResult, UserRequirements  # the shared data classes