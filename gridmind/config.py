"""
GridMind configuration — Ghana national grid constants.

All identifiers, capacities, and thresholds are grounded in
ECG / GRIDCo operational data for the five modelled districts.
"""

# ── XMPP server ──────────────────────────────────────────────

XMPP_SERVER: str = 'localhost'
AGENT_PASSWORD: str = 'gridmind_secret'

# ── Agent JIDs ───────────────────────────────────────────────

ECG_DISPATCH_JID: str = f'ecg_central_dispatch@{XMPP_SERVER}'
GRIDCO_FAULT_JID: str = f'gridco_fault_watch@{XMPP_SERVER}'
ECG_FORECAST_JID: str = f'ecg_forecast_unit@{XMPP_SERVER}'
ACCRA_DR_JID: str = f'accra_industrial_dr@{XMPP_SERVER}'

KALEO_SOLAR_JID: str = f'kaleo_solar@{XMPP_SERVER}'
NZEMA_SOLAR_JID: str = f'nzema_solar@{XMPP_SERVER}'
KETA_WIND_JID: str = f'keta_wind@{XMPP_SERVER}'

TEMA_INDUSTRIAL_JID: str = f'tema_industrial@{XMPP_SERVER}'
ACCRA_CENTRAL_JID: str = f'accra_central@{XMPP_SERVER}'
KUMASI_SUAME_JID: str = f'kumasi_suame@{XMPP_SERVER}'
KASOA_CORRIDOR_JID: str = f'kasoa_corridor@{XMPP_SERVER}'
TAKORADI_HARBOUR_JID: str = f'takoradi_harbour@{XMPP_SERVER}'

DISTRICT_JIDS: list[str] = [
    TEMA_INDUSTRIAL_JID,
    ACCRA_CENTRAL_JID,
    KUMASI_SUAME_JID,
    KASOA_CORRIDOR_JID,
    TAKORADI_HARBOUR_JID,
]

RENEWABLE_JIDS: list[str] = [
    KALEO_SOLAR_JID,
    NZEMA_SOLAR_JID,
    KETA_WIND_JID,
]

# ── District capacities (MW) ────────────────────────────────

DISTRICT_CONFIG: dict[str, dict] = {
    'tema_industrial': {
        'ceiling_mw': 400.0,
        'base_demand_mw': 290.0,
        'sensor_noise_factor': 0.03,
        'jid': TEMA_INDUSTRIAL_JID,
    },
    'accra_central': {
        'ceiling_mw': 190.0,
        'base_demand_mw': 140.0,
        'sensor_noise_factor': 0.02,
        'jid': ACCRA_CENTRAL_JID,
    },
    'kumasi_suame': {
        'ceiling_mw': 150.0,
        'base_demand_mw': 110.0,
        'sensor_noise_factor': 0.025,
        'jid': KUMASI_SUAME_JID,
    },
    'kasoa_corridor': {
        'ceiling_mw': 100.0,
        'base_demand_mw': 65.0,
        'sensor_noise_factor': 0.04,
        'jid': KASOA_CORRIDOR_JID,
    },
    'takoradi_harbour': {
        'ceiling_mw': 175.0,
        'base_demand_mw': 125.0,
        'sensor_noise_factor': 0.02,
        'jid': TAKORADI_HARBOUR_JID,
    },
}

TOTAL_MANAGED_CAPACITY_MW: float = 1015.0

DISTRICT_CAPACITY: dict[str, float] = {
    name: cfg['ceiling_mw'] for name, cfg in DISTRICT_CONFIG.items()
}

DISTRICT_BASE_DEMAND: dict[str, float] = {
    name: cfg['base_demand_mw'] for name, cfg in DISTRICT_CONFIG.items()
}

DISTRICT_DISPLAY_NAMES: dict[str, str] = {
    'tema_industrial': 'Tema Industrial Enclave',
    'accra_central': 'Accra Central (Ministries)',
    'kumasi_suame': 'Kumasi Suame Magazine',
    'kasoa_corridor': 'Kasoa Corridor',
    'takoradi_harbour': 'Takoradi Harbour',
}

# ── Shedding priority (immutable: Kasoa first, Tema last) ───

SHEDDING_ORDER: list[str] = [
    'kasoa_corridor',
    'accra_central',
    'kumasi_suame',
    'takoradi_harbour',
    'tema_industrial',
]

# ── Renewable source configuration ──────────────────────────

RENEWABLE_CONFIG: dict[str, dict] = {
    'kaleo_solar': {
        'max_capacity_mw': 155.0,
        'cost_coeff': 0.28,
        'jid': KALEO_SOLAR_JID,
    },
    'nzema_solar': {
        'max_capacity_mw': 20.0,
        'cost_coeff': 0.31,
        'jid': NZEMA_SOLAR_JID,
    },
    'keta_wind': {
        'max_capacity_mw': 50.0,
        'cost_coeff': 0.19,
        'jid': KETA_WIND_JID,
    },
}

# ── Demand Response consumer roster ─────────────────────────

DR_CONSUMER_ROSTER: dict[str, dict] = {
    'VALCO': {
        'contracted_dr_mw': 80.0,
        'compliance_rate': 0.95,
    },
    'tema_oil_refinery': {
        'contracted_dr_mw': 35.0,
        'compliance_rate': 0.88,
    },
    'meridian_port': {
        'contracted_dr_mw': 20.0,
        'compliance_rate': 0.80,
    },
    'GHACEM_takoradi': {
        'contracted_dr_mw': 25.0,
        'compliance_rate': 0.82,
    },
    'accra_brewery': {
        'contracted_dr_mw': 15.0,
        'compliance_rate': 0.75,
    },
}

TOTAL_DR_CONTRACTED_MW: float = 175.0

# ── BDI thresholds ───────────────────────────────────────────

EMERGENCY_THRESHOLD_PCT: float = 0.98
PREEMPTIVE_THRESHOLD_PCT: float = 0.85
OPTIMISE_THRESHOLD_PCT: float = 0.70

# ── Simulation parameters ───────────────────────────────────

DAY_CYCLE_TICKS: int = 20 
TICK_INTERVAL: float = 0.5
DEMO_TICK_INTERVAL: float = 1.5
SIMULATION_TICKS: int = 30
CNP_DEADLINE_TICKS: int = 3
FORECAST_HORIZON: int = 5
FORECAST_HISTORY_LEN: int = 20
FAULT_WINDOW: int = 5
FAULT_SIGMA_THRESHOLD: float = 2.0
BROADCAST_INTERVAL: int = 5

SENSOR_NOISE_FACTOR: dict[str, float] = {
    'tema_industrial': 0.03,
    'accra_central': 0.02,
    'kumasi_suame': 0.025,
    'kasoa_corridor': 0.04,
    'takoradi_harbour': 0.02,
}
