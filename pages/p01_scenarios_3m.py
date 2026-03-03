"""3-Month Horizon Scenario Page — for Streamlit multipage navigation."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from components.scenario_page import render_scenario_page

render_scenario_page("3m")
