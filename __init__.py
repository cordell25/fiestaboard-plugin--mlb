#MLB - Track Team Games / Scores

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import logging
import requests

from src.plugins.base import PluginBase, PluginResult

logger = logging.getLogger(__name__)

# MLB API base URLs (Targeting AL and NL explicitly)
API_TEAMS_LIST_URL = "https://statsapi.mlb.com/api/v1/teams?leagueIds=103,104"
API_SCHEDULE_URL = "https://statsapi.mlb.com/api/v1/schedule?sportId=1&teamId="
API_GAME_URL = "https://statsapi.mlb.com/api/v1/game/"
API_GAME_URL_APPEND = "/linescore"

class mlb(PluginBase):
    def __init__(self, manifest: Dict[str, Any]):
        """Initialize the sports scores plugin."""
        super().__init__(manifest)
        # Fast lookup map: { team_id: { "name": "...", "abbreviation": "..." } }
        self._teams: Dict[int, Dict[str, Any]] = {}
    
    @property
    def plugin_id(self) -> str:
        return "mlb"

    # ------------------------------------------------------------------
    # Config validation
    # ------------------------------------------------------------------
    
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate MLB configuration."""
        errors = []
        # Accessing setting schema properties based on manifest structure
        teams = config.get("teams", [])
        if not teams:
            errors.append("At least one team must be selected")    
        return errors

    def on_config_change(self, old_config: dict, new_config: dict):
        logger.warning("on_config_change called - Caching all MLB teams")
        
        try:
            response = requests.get(
                API_TEAMS_LIST_URL,
                timeout=15,
            )
            response.raise_for_status()
            team_payload = response.json()
            
            # Rebuild our global team map using ID as the key
            new_teams_map = {}
            for team in team_payload.get("teams", []):
                t_id = team.get("id")
                if t_id:
                    new_teams_map[t_id] = {
                        "name": team.get("name"),
                        "short_name": team.get("shortName"),
                        "franchise_name": team.get("franchiseName"),
                        "club_name": team.get("clubName"),
                        "abbreviation": team.get("abbreviation"),
                        "location": team.get("locationName")
                    }
            
            self._teams = new_teams_map
            logger.info("Successfully cached %d MLB teams by ID.", len(self._teams))
            
        except Exception as e:
            logger.error("Failed to populate league team map: %s", e)


    # ------------------------------------------------------------------
    # Data fetching
    # ------------------------------------------------------------------
    
    def fetch_data(self) -> PluginResult:
        """Fetch team scores for all configured teams."""
        teams = self.config.get("teams", [])
        if not teams:
            return PluginResult(available=False, error="No teams selected")
        
        # Self-healing if cache didn't populate on startup
        if not self._teams:
            logger.warning("League map empty. Fetching now.")
            self.on_config_change({}, self.config)

        # Get the ID of our configured team using our hardcoded string matcher
        configured_team_id = self.get_configured_team_id(teams[0])
        if not configured_team_id:
            return PluginResult(available=False, error=f"Invalid configured team: {teams[0]}")

        # Initialize variables for safe scoping
        game_pk = None
        schedule_payload = None
        game_payload = None

        # GET Schedule Information
        try:
            response = requests.get(
                f"{API_SCHEDULE_URL}{configured_team_id}",
                timeout=15,
            )
            response.raise_for_status()
            schedule_payload = response.json()
            
            if schedule_payload.get("dates") and schedule_payload["dates"][0].get("games"):
                game_pk = schedule_payload["dates"][0]["games"][0]["gamePk"]
            else:
                return PluginResult(available=False, error="No games scheduled today.")
                
        except Exception as e:
            logger.warning("Schedule fetch failed: %s", e)
            return PluginResult(available=False, error=f"Schedule fetch failed: {e}")

        # GET Game Information (linescore payload containing metrics)
        if game_pk:
            try:
                response = requests.get(
                    f"{API_GAME_URL}{game_pk}{API_GAME_URL_APPEND}",
                    timeout=15,
                )
                response.raise_for_status()
                game_payload = response.json()
            except Exception as e:
                logger.warning("Game linescore fetch failed: %s", e)
                return PluginResult(available=False, error=f"Game fetch failed: {e}")

        if not schedule_payload or not game_payload:
            return PluginResult(available=False, error="Incomplete live game data.")

        try:
            game_info = schedule_payload["dates"][0]["games"][0]
            
            # Extract live team IDs from schedule
            away_id = game_info["teams"]["away"]["team"]["id"]
            home_id = game_info["teams"]["home"]["team"]["id"]

            # Pull cached metadata descriptions
            away_cached = self._teams.get(away_id, {})
            home_cached = self._teams.get(home_id, {})

            # Extract team objects safely from linescore teams structure
            linescore_teams = game_payload.get("teams", {})
            away_stats = linescore_teams.get("away", {})
            home_stats = linescore_teams.get("home", {})

            # Return dynamic values mapping 1:1 to variables in manifest.json
            return PluginResult(
                available=True,
                data={
                    "home_team_name": game_info["teams"]["home"]["team"]["name"],
                    "home_team_abbr": home_cached.get("abbreviation", "HOM"),
                    "home_team_club_name": home_cached.get("club_name", "Home"),
                    
                    "away_team_name": game_info["teams"]["away"]["team"]["name"],
                    "away_team_abbr": away_cached.get("abbreviation", "AWY"),
                    "away_team_club_name": away_cached.get("club_name", "Away"),
                    
                    "stadium": game_info.get("venue", {}).get("name", "Unknown Field"),
                    "current_inning": game_payload.get("currentInning"),
                    "current_inning_state": game_payload.get("inningState"),
                    
                    # Boxscore statistics matching manifest types
                    "current_home_score": home_stats.get("runs", 0),
                    "current_home_hits": home_stats.get("hits", 0),
                    "current_home_errors": home_stats.get("errors", 0),
                    
                    "current_away_score": away_stats.get("runs", 0),
                    "current_away_hits": away_stats.get("hits", 0),
                    "current_away_errors": away_stats.get("errors", 0)
                },
            )
        except KeyError as e:
            logger.error("Failed to parse API structure: %s", e)
            return PluginResult(available=False, error="Data parsing error.")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def get_configured_team_id(team_name: str) -> Optional[int]:
        """Translates your manifest selection string into an initial team ID."""
        team_map = {
            "Arizona Diamondbacks": 109, "Athletics": 133, "Atlanta Braves": 144,
            "Baltimore Orioles": 110, "Boston Red Sox": 111, "Chicago Cubs": 112,
            "Chicago White Sox": 145, "Cincinnati Reds": 113, "Cleveland Guardians": 114,
            "Colorado Rockies": 115, "Detroit Tigers": 116, "Houston Astros": 117,
            "Kansas City Royals": 118, "Los Angeles Angels": 108, "Los Angeles Dodgers": 119,
            "Miami Marlins": 146, "Milwaukee Brewers": 158, "Minnesota Twins": 142,
            "New York Mets": 121, "New York Yankees": 147, "Philadelphia Phillies": 143,
            "Pittsburgh Pirates": 134, "San Diego Padres": 135, "San Francisco Giants": 137,
            "Seattle Mariners": 136, "St. Louis Cardinals": 138, "Tampa Bay Rays": 139,
            "Texas Rangers": 140, "Toronto Blue Jays": 141, "Washington Nationals": 120
        }
        return team_map.get(team_name)
        
    def cleanup(self) -> None:
        pass