"""IEEE 802.11g (ERP-OFDM) PHY/MAC timing used by the simulator.

All times are in microseconds. Frame durations follow the OFDM PHY rule:
preamble+header (20 us) + ceil((16 service bits + 8*bytes + 6 tail bits) / bits_per_symbol) * 4 us.
"""
from dataclasses import dataclass, field
import math

MAC_HEADER_FCS = 28  # bytes: 24 B MAC header + 4 B FCS
ACK_BYTES = 14
RTS_BYTES = 20
CTS_BYTES = 14


def ofdm_duration(nbytes: int, rate_mbps: float) -> float:
    bits_per_symbol = rate_mbps * 4  # 4 us per OFDM symbol
    nsym = math.ceil((16 + 8 * nbytes + 6) / bits_per_symbol)
    return 20.0 + 4.0 * nsym


@dataclass
class PhyParams:
    slot: float = 9.0          # aSlotTime
    sifs: float = 10.0         # aSIFSTime
    data_rate: float = 54.0    # Mb/s
    basic_rate: float = 24.0   # Mb/s for ACK / RTS / CTS
    payload: int = 1500        # bytes of MSDU payload
    rts_cts: bool = False      # basic access (False) or RTS/CTS handshake (True)
    cw_min: int = 16           # window size W0 (backoff drawn from [0, W-1]) == CWmin+1
    cw_max: int = 1024         # == CWmax+1
    retry_limit: int | None = 7  # None -> infinite retries (Bianchi model assumption)
    # derived (filled in __post_init__)
    difs: float = field(init=False)
    t_data: float = field(init=False)
    t_ack: float = field(init=False)
    ts: float = field(init=False)   # channel time of a successful transmission
    tc: float = field(init=False)   # channel time of a collision

    def __post_init__(self):
        self.difs = self.sifs + 2 * self.slot
        self.t_data = ofdm_duration(self.payload + MAC_HEADER_FCS, self.data_rate)
        self.t_ack = ofdm_duration(ACK_BYTES, self.basic_rate)
        ack_timeout = self.sifs + self.t_ack + self.slot
        if not self.rts_cts:
            self.ts = self.t_data + self.sifs + self.t_ack + self.difs
            self.tc = self.t_data + ack_timeout + self.difs
        else:
            t_rts = ofdm_duration(RTS_BYTES, self.basic_rate)
            t_cts = ofdm_duration(CTS_BYTES, self.basic_rate)
            self.ts = (t_rts + self.sifs + t_cts + self.sifs + self.t_data
                       + self.sifs + self.t_ack + self.difs)
            self.tc = t_rts + self.sifs + t_cts + self.slot + self.difs

    @property
    def tc_slots(self) -> float:
        """Collision duration normalised to slot time (T_c* in Bianchi's notation)."""
        return self.tc / self.slot

    def summary(self) -> dict:
        return {
            "slot_us": self.slot, "SIFS_us": self.sifs, "DIFS_us": self.difs,
            "data_rate_Mbps": self.data_rate, "basic_rate_Mbps": self.basic_rate,
            "payload_B": self.payload, "access": "RTS/CTS" if self.rts_cts else "basic",
            "CWmin": self.cw_min - 1, "CWmax": self.cw_max - 1,
            "retry_limit": self.retry_limit, "T_data_us": self.t_data,
            "T_ack_us": self.t_ack, "Ts_us": self.ts, "Tc_us": self.tc,
        }
