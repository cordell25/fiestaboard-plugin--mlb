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
        teams = self.config.get("teams", [])
        if not teams:
            return PluginResult(
                available=False,
                error="No teams selected"
            )
            
#        for team in teams:
            
        return PluginResult(
            available=True,
            data={
                "home_team": teams[0],
                "away_team": "", 
                "current_inning": "",
                "current_inning_state": "",
                "current_home_score": 3,
                "current_away_score": 4
            },
        )
        except Exception as e:
            logger.exception("Error reading timer payload")
            return PluginResult(available=False, error=str(e))

    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        return []

    def cleanup(self) -> None:
        pass
