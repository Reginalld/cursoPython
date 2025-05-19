# tests/test_logger.py
import os
from brazil_data_cube.brazil_data_cube.utils.logger import ResultManager

def test_log_error_csv(mocker):
    mock_open = mocker.mock_open()
    mocker.patch("builtins.open", mock_open)

    ResultManager.log_error_csv(tile="21JYM", satelite="S2_L2A-1", erro_msg="Teste")
    assert mock_open.called