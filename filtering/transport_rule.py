from logic_manager import _normalise  # cleans text: lowercase, removes symbols and extra spaces
from models import Recommendation, RuleResult, UserRequirements  # the shared data classes
from .rule import Rule  # the parent class this rule is based on