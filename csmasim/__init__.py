"""csmasim: slot-level IEEE 802.11 DCF simulator for comparing backoff strategies."""
from .phy import PhyParams
from .simulator import SimConfig, SimResult, Simulator, simulate
from .strategies import REGISTRY, ALL
