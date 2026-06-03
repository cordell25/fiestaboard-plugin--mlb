#MLB - Track Team Games / Scores

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import logging
import requests

from src.plugins.base import PluginBase, PluginResult

logger = logging.getLogger(__name__)

# MLB API base URLs
API_SCHEDULE_URL = "https://statsapi.mlb.com/api/v1/schedule?sportId=1&teamId="
API_GAME_URL = "https://statsapi.mlb.com/api/v1/game/"
API_GAME_URL_APPEND = "/linescore"

class mlb(PluginBase):
    def __init__(self, manifest: Dict[str, Any]):
        """Initialize the sports scores plugin."""
        super().__init__(manifest)
    
    @property
    def plugin_id(self) -> str:
        return "mlb"

    # ------------------------------------------------------------------
    # Config validation
    # ------------------------------------------------------------------
    
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate MLB configuration."""
        errors = []
        teams = config.get("teams", [])
        if not teams:
            errors.append("At least one team must be selected")    
        return errors

    # ------------------------------------------------------------------
    # Data fetching
    # ------------------------------------------------------------------
    
    def fetch_data(self) -> PluginResult:
        """Fetch team scores for all configured teams."""
      
        teams = self.config.get("teams", [])
        if not teams:
            return PluginResult(
                available=False,
                error="No teams selected"
            )
        
        logger.info("LOOK HERE")
        logger.info(self.get_team_id(teams[0]))
        team_id = self.get_team_id(teams[0])

        if not team_id:
            return PluginResult(available=False, error=f"Invalid team name: {teams[0]}")

        # Initialize variables for safe scoping
        game_pk = None
        schedule_payload = None
        game_payload = None

        # GET Schedule Information
        try:
            response = requests.get(
                f"{API_SCHEDULE_URL}{team_id}",
                timeout=15,
            )
            response.raise_for_status()
            schedule_payload = response.json()
            
            # Verify a game exists for today in the payload
            if schedule_payload.get("dates") and schedule_payload["dates"][0].get("games"):
                game_pk = schedule_payload["dates"][0]["games"][0]["gamePk"]
            else:
                return PluginResult(available=False, error="No games scheduled for this team today.")
                
        except Exception as e:
            logger.warning("Team Schedule fetch failed for team %s: %s", team_id, e)
            return PluginResult(available=False, error=f"Schedule fetch failed: {e}")

        # GET Game Information
        if game_pk:
            try:
                response = requests.get(
                    f"{API_GAME_URL}{game_pk}{API_GAME_URL_APPEND}",
                    timeout=15,
                )
                response.raise_for_status()
                game_payload = response.json()
            except Exception as e:
                logger.warning("Game fetch failed for game %s: %s", game_pk, e)
                return PluginResult(available=False, error=f"Game fetch failed: {e}")

        # Final check to ensure we have all required data before parsing
        if not schedule_payload or not game_payload:
            return PluginResult(available=False, error="Incomplete game data received from API.")

        try:
            game_info = schedule_payload["dates"][0]["games"][0]
            
            return PluginResult(
                available=True,
                data={
                    "away_team": game_info["teams"]["away"]["team"]["name"],
                    "home_team": game_info["teams"]["home"]["team"]["name"],
                    "stadium": game_info["venue"]["name"],
                    "current_inning": game_payload.get("currentInning"),
                    "current_inning_state": game_payload.get("inningState"),
                    "current_away_score": game_payload["teams"]["away"].get("runs", 0),
                    "current_home_score": game_payload["teams"]["home"].get("runs", 0)
                },
            )
        except KeyError as e:
            logger.error("Failed to parse API structure: %s", e)
            return PluginResult(available=False, error="Data parsing error.")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
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
        
        return team_map.get(team_name)
        
    def cleanup(self) -> None:
        pass