#MLB - Track Team Games / Scores

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import logging
import requests

from src.plugins.base import PluginBase, PluginResult

logger = logging.getLogger(__name__)

# MLB API base URLs
API_BASE_URL_V1 = "https://statsapi.mlb.com/api/v1/schedule?sportId=1&teamId={{teamId}}"
API_BASE_URL_V2 = "https://statsapi.mlb.com/api/v1/game/{{gamePk}}/linescore"

class mlb(PluginBase):
    def __init__(self, manifest: Dict[str, Any]):
        """Initialize the sports scores plugin."""
        super().__init__(manifest)
    
    @property
    def plugin_id(self) -> str:
        return "mlb"
    
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate MLB configuration."""
        errors = []
        teams = config.get("teams", [])
        if not teams:
            errors.append("At least one team must be selected")    
        return errors
    
    def fetch_data(self) -> PluginResult:
        """Fetch team scores for all configured teams."""
        try:
            teams = self.config.get("teams", [])
            if not teams:
                return PluginResult(
                    available=False,
                    error="No teams selected"
                )
                
    #        for team in teams:
            logger.info(self.get_team_id(teams[0]))
            return PluginResult(
                available=True,
                data={
                    "home_team": teams[0],
                    "away_team": self.get_team_id(teams[0]), 
                    "current_inning": "",
                    "current_inning_state": "",
                    "current_home_score": 3,
                    "current_away_score": 4
                },
            )
        except Exception as e:
            logger.exception("Error reading timer payload")
            return PluginResult(available=False, error=str(e))

    def get_team_id(team_name):
        # Mapping based on the JSON response provided
        team_map = {
            "Athletics": 133,
            "Pittsburgh Pirates": 134,
            "San Diego Padres": 135,
            "Seattle Mariners": 136,
            "San Francisco Giants": 137,
            "St. Louis Cardinals": 138,
            "Tampa Bay Rays": 139,
            "Texas Rangers": 140,
            "Toronto Blue Jays": 141,
            "Minnesota Twins": 142,
            "Philadelphia Phillies": 143,
            "Atlanta Braves": 144,
            "Chicago White Sox": 145,
            "Miami Marlins": 146,
            "New York Yankees": 147,
            "Milwaukee Brewers": 158,
            "Los Angeles Angels": 108,
            "Arizona Diamondbacks": 109,
            "Baltimore Orioles": 110,
            "Boston Red Sox": 111,
            "Chicago Cubs": 112,
            "Cincinnati Reds": 113,
            "Cleveland Guardians": 114,
            "Colorado Rockies": 115,
            "Detroit Tigers": 116,
            "Houston Astros": 117,
            "Kansas City Royals": 118,
            "Los Angeles Dodgers": 119,
            "Washington Nationals": 120,
            "New York Mets": 121
        }
        
        # Returns the ID if found, otherwise returns None
        return team_map.get(team_name)
        
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        return []

    def cleanup(self) -> None:
        pass
