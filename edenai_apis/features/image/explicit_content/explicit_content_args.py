import os
from typing import Dict

feature_path = os.path.dirname(os.path.dirname(__file__))

data_path = os.path.join(feature_path, "data")


def explicit_content_arguments() -> Dict:
    return {"file": open(f"{data_path}/explicit_content.jpeg", "rb")}
