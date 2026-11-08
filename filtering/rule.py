from abc import ABC, abstractmethod  # create  abstract  class
from typing import Optional 
from logic_manager import _normalise  # lowercase, removes symbols and extra spaces
from models import Recommendation, RuleResult, UserRequirements  # the shared data classes

# answers if user did not pick anything
NO_REQUIREMENT = {"", "any", "none"}

class Rule(ABC):
    """A parent class for all recommendation rules."""
    label = "Rule"  