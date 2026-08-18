RAW_TO_CANONICAL = {
    "UDI": "udi",
    "Product ID": "urun_kodu",
    "Type": "urun_tipi",
    "Air temperature [K]": "hava_sicakligi_k",
    "Process temperature [K]": "proses_sicakligi_k",
    "Rotational speed [rpm]": "donus_hizi_rpm",
    "Torque [Nm]": "tork_nm",
    "Tool wear [min]": "takim_asinmasi_dk",
    "Machine failure": "makine_arizasi",
    "TWF": "TWF",
    "HDF": "HDF",
    "PWF": "PWF",
    "OSF": "OSF",
    "RNF": "RNF",
}
RAW_COLUMNS = tuple(RAW_TO_CANONICAL)
CANONICAL_COLUMNS = tuple(RAW_TO_CANONICAL.values())
ID_COLUMNS = ("udi", "urun_kodu")
CATEGORICAL_COLUMNS = ("urun_tipi",)
NUMERIC_SENSOR_COLUMNS = (
    "hava_sicakligi_k",
    "proses_sicakligi_k",
    "donus_hizi_rpm",
    "tork_nm",
    "takim_asinmasi_dk",
)
BINARY_TARGET_COLUMNS = ("makine_arizasi", "TWF", "HDF", "PWF", "OSF", "RNF")
FAILURE_TYPE_COLUMNS = ("TWF", "HDF", "PWF", "OSF", "RNF")
MODELED_FAILURE_TYPE_COLUMNS = ("TWF", "HDF", "PWF", "OSF")
DERIVED_COLUMNS = ("proses_hava_sicaklik_farki_k", "acisal_hiz_rad_s", "mekanik_guc_w")
MODEL_FEATURE_COLUMNS = (
    "urun_tipi",
    *NUMERIC_SENSOR_COLUMNS,
    *DERIVED_COLUMNS,
)
ALLOWED_PRODUCT_TYPES = frozenset({"L", "M", "H"})
UNITS = {
    "hava_sicakligi_k": "K",
    "proses_sicakligi_k": "K",
    "donus_hizi_rpm": "rpm",
    "tork_nm": "N·m",
    "takim_asinmasi_dk": "min",
    "proses_hava_sicaklik_farki_k": "K",
    "acisal_hiz_rad_s": "rad/s",
    "mekanik_guc_w": "W",
}
PIPELINE_VERSION = "1.0.0"


def canonicalize_columns(frame):
    return frame.rename(columns=RAW_TO_CANONICAL, copy=True)
