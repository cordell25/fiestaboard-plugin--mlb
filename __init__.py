#MLB - Track Team Games / Scores

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import pytz
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
        # Fast lookup map: { team_id: { "name": "...", "abbreviation": "...", "color": "..." } }
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
        teams = config.get("teams", [])
        if not teams:
            errors.append("At least one team must be selected")    
        return errors

    def on_config_change(self, old_config: dict, new_config: dict):
        logger.warning("on_config_change called - Caching all MLB teams with colors")
        
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
                name = team.get("name") or ""
                
                if t_id:
                    # Normalize common variations like "Oakland Athletics" vs "Athletics"
                    match_name = name
                    if "Athletics" in name:
                        match_name = "Athletics"
                        
                    blueprint = self.get_configured_team_id_and_color(match_name) or {}
                    team_color = blueprint.get("color", "white")
                    
                    new_teams_map[t_id] = {
                        "name": name,
                        "short_name": team.get("shortName"),
                        "franchise_name": team.get("franchiseName"),
                        "club_name": team.get("clubName"),
                        "abbreviation": team.get("abbreviation"),
                        "location": team.get("locationName"),
                        "color": team_color
                    }
            
            self._teams = new_teams_map
            logger.info("Successfully cached %d MLB teams by ID with colors.", len(self._teams))
            
        except Exception as e:
            logger.error("Failed to populate league team map: %s", e)


    # ------------------------------------------------------------------
    # Data fetching
    # ------------------------------------------------------------------
    
    def fetch_data(self) -> PluginResult:
        """Fetch team scores for all configured teams."""

        # Default values if no game is scheduled today or API drops offline
        fallback_data = {
            "home_team_name": "",
            "home_team_abbr": "",
            "home_team_club_name": "",
            "home_team_color": "black",
            
            "away_team_name": "",
            "away_team_abbr": "",
            "away_team_club_name": "",
            "away_team_color": "black",

            "game_scheduled_start": "",
            "minutes_until_game": 0,
            "game_status_code": "0",
            "stadium": "",
            "current_inning": 0,
            "current_inning_state": "",
            
            "current_home_score": 0,
            "current_home_hits": 0,
            "current_home_errors": 0,
            
            "current_away_score": 0,
            "current_away_hits": 0,
            "current_away_errors": 0
        }

        user_timezone = self.config.get("timezone", "America/Los_Angeles")
        tz = pytz.timezone(user_timezone)
        now = datetime.now(tz)
        
        teams = self.config.get("teams", [])
        if not teams:
            return PluginResult(available=False, error="No teams selected")
        
        # Self-healing if cache didn't populate on startup
        if not self._teams:
            logger.warning("League map empty. Fetching now.")
            self.on_config_change({}, self.config)

        # Get the ID and color blueprint of our configured team
        team_meta = self.get_configured_team_id_and_color(teams[0])
        if not team_meta:
            return PluginResult(available=False, error=f"Invalid configured team: {teams[0]}")
        configured_team_id = team_meta["id"]

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
                game_info = schedule_payload["dates"][0]["games"][0]
                game_pk = game_info["gamePk"]
            else:
                return PluginResult(available=True, data=fallback_data)
                
        except Exception as e:
            logger.warning("Schedule fetch failed: %s. Emitting safe fallback data.", e)
            return PluginResult(available=True, data=fallback_data)

        try:
            # Time conversion and tracking math
            utc_start = datetime.strptime(game_info["gameDate"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            local_start = utc_start.astimezone(tz)
            scheduled_game_start = local_start.strftime("%I:%M %p").lstrip("0")
            
            time_delta = local_start - now
            minutes_until_game = int(time_delta.total_seconds() / 60)
            
            # Extract live IDs from the schedule
            away_id = game_info["teams"]["away"]["team"]["id"]
            home_id = game_info["teams"]["home"]["team"]["id"]

            # Pull clean details out of our global self._teams dictionary
            away_cached = self._teams.get(away_id, {})
            home_cached = self._teams.get(home_id, {})

            game_status_code = game_info["status"]["statusCode"]

            # Gating Rule: Only call game linescore API if within 15 minutes of start AND not finished
            should_fetch_live_data = (minutes_until_game <= 15) and (game_status_code != "F")

            # Initialize safe default structures for linescore parameters
            away_stats = {}
            home_stats = {}
            current_inning = None
            current_inning_state = None

            if game_pk and should_fetch_live_data:
                logger.info("Game active or pre-game window open. Fetching linescore data for game %s", game_pk)
                try:
                    response = requests.get(
                        f"{API_GAME_URL}{game_pk}{API_GAME_URL_APPEND}",
                        timeout=15,
                    )
                    response.raise_for_status()
                    game_payload = response.json()
                    
                    # Safely map objects from active linescore
                    linescore_teams = game_payload.get("teams", {})
                    away_stats = linescore_teams.get("away", {})
                    home_stats = linescore_teams.get("home", {})
                    current_inning = game_payload.get("currentInning")
                    current_inning_state = game_payload.get("inningState")
                    
                except Exception as e:
                    logger.warning("Game linescore fetch failed: %s. Falling back to schedule metrics.", e)
            else:
                logger.info("Outside of active live window (Minutes until: %d, Status: %s). Skipping linescore call.", minutes_until_game, game_status_code)
                # If the game is final ('F'), we parse final scores directly out of the schedule payload instead of linescore
                if game_status_code == "F":
                    away_stats = {"runs": game_info["teams"]["away"].get("score", 0)}
                    home_stats = {"runs": game_info["teams"]["home"].get("score", 0)}

            # Return dynamic values mapping 1:1 to variables in manifest.json
            return PluginResult(
                available=True,
                data={
                    "home_team_name": game_info["teams"]["home"]["team"]["name"],
                    "home_team_abbr": home_cached.get("abbreviation", "HOM"),
                    "home_team_club_name": home_cached.get("club_name", "Home"),
                    "home_team_color": home_cached.get("color", "white"),
                    
                    "away_team_name": game_info["teams"]["away"]["team"]["name"],
                    "away_team_abbr": away_cached.get("abbreviation", "AWY"),
                    "away_team_club_name": away_cached.get("club_name", "Away"),
                    "away_team_color": away_cached.get("color", "white"),

                    "game_scheduled_start": scheduled_game_start,
                    "minutes_until_game": max(0, minutes_until_game),
                    "game_status_code": game_status_code,
                    "stadium": game_info.get("venue", {}).get("name", "Unknown Field"),
                    "current_inning": current_inning,
                    "current_inning_state": current_inning_state,
                    
                    # Boxscore statistics safely resolving to 0 when unfetched or pregame
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
    def get_configured_team_id_and_color(team_name: str) -> Optional[Dict[str, Any]]:
        """Translates your manifest selection string into an initial team ID and Vestaboard color mapping."""
        team_map = {
            "Arizona Diamondbacks": {"id": 109, "color": "red"},
            "Athletics": {"id": 133, "color": "green"},
            "Atlanta Braves": {"id": 144, "color": "blue"},
            "Baltimore Orioles": {"id": 110, "color": "orange"},
            "Boston Red Sox": {"id": 111, "color": "red"},
            "Chicago Cubs": {"id": 112, "color": "blue"},
            "Chicago White Sox": {"id": 145, "color": "white"},
            "Cincinnati Reds": {"id": 113, "color": "red"},
            "Cleveland Guardians": {"id": 114, "color": "blue"},
            "Colorado Rockies": {"id": 115, "color": "purple"},
            "Detroit Tigers": {"id": 116, "color": "orange"},
            "Houston Astros": {"id": 117, "color": "orange"},
            "Kansas City Royals": {"id": 118, "color": "blue"},
            "Los Angeles Angels": {"id": 108, "color": "red"},
            "Los Angeles Dodgers": {"id": 119, "color": "blue"},
            "Miami Marlins": {"id": 146, "color": "blue"},
            "Milwaukee Brewers": {"id": 158, "color": "yellow"},
            "Minnesota Twins": {"id": 142, "color": "red"},
            "New York Mets": {"id": 121, "color": "orange"},
            "New York Yankees": {"id": 147, "color": "white"},
            "Philadelphia Phillies": {"id": 143, "color": "red"},
            "Pittsburgh Pirates": {"id": 134, "color": "yellow"},
            "San Diego Padres": {"id": 135, "color": "yellow"},
            "San Francisco Giants": {"id": 137, "color": "orange"},
            "Seattle Mariners": {"id": 136, "color": "green"},
            "St. Louis Cardinals": {"id": 138, "color": "red"},
            "Tampa Bay Rays": {"id": 139, "color": "blue"},
            "Texas Rangers": {"id": 140, "color": "blue"},
            "Toronto Blue Jays": {"id": 141, "color": "blue"},
            "Washington Nationals": {"id": 120, "color": "red"}
        }
        return team_map.get(team_name)
        
    def cleanup(self) -> None:
        pass
