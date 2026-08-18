import pandas as pd
import pytest

from bakim_ml.data_contract import RAW_COLUMNS


@pytest.fixture
def raw_frame():
    rows = [
        [1, "L00001", "L", 298.1, 308.6, 1551, 42.8, 0, 0, 0, 0, 0, 0, 0],
        [2, "M00002", "M", 299.0, 309.2, 1400, 50.0, 20, 1, 1, 0, 0, 0, 0],
    ]
    return pd.DataFrame(rows, columns=RAW_COLUMNS)
