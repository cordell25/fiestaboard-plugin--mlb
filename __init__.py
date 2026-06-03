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

        # GET Schedule Information (Needs to only be run every so often, maybe hourly?)
        try:
            response = requests.get(
                f"{API_SCHEDULE_URL}{team_id}",
                timeout=15,
            )
            response.raise_for_status()
            schedule_payload = response.json()
            gamePk = schedule_payload.dates[0].games[0].gamePk
        except Exception as e:
            logger.warning("Team Schedule fetch failed for team %s: %s", team_id, e)

        # GET Game Information (Needs to only be run every so often, maybe every 5 minutes?)
        if gamePk:
            try:
                response = requests.get(
                    f"{API_GAME_URL}{gamePk}{API_GAME_URL_APPEND}",
                    timeout=15,
                )
                response.raise_for_status()
                game_payload = response.json()
            except Exception as e:
                logger.warning("Game fetch failed for game %s: %s", gamePk, e)

        # Set Variables with values from API calls
        return PluginResult(
            available=True,
            data={
                "home_team": schedule_payload.dates[0].games[0].teams.away.team.name,
                "away_team": schedule_payload.dates[0].games[0].teams.home.team.name,
                "stadium": schedule_payload.dates[0].games[0].venue.name,
                "current_inning": game_payload.currentInning,
                "current_inning_state": game_payload.inningState,
                "current_home_score": game_payload.teams.home.runs,
                "current_away_score": game_payload.teams.away.runs
            },
        )

    # ------------------------------------------------------------------
    # Trigger support
    # ------------------------------------------------------------------

    # def check_triggers(self) -> List[TriggerResult]:
    #     """Fire triggers for events starting within the configured window."""
    #     results: List[TriggerResult] = []

    #     # Use cached events if available to avoid extra HTTP calls
    #     if not self._events_cache:
    #         try:
    #             self._events_cache = self._fetch_events()
    #         except Exception:
    #             logger.warning("Could not fetch events for trigger check", exc_info=True)
    #             return results

    #     # minutes_before = int(self.config.get("minutes_before", 15))
    #     # display_minutes = int(self.config.get("display_duration_minutes", 0))
    #     display_minutes = 5
    #     duration_seconds = (
    #         display_minutes * 60 if display_minutes > 0 else _INDEFINITE_DURATION_SECONDS
    #     )

    #     tz_str = self.config.get("timezone", "America/Los_Angeles")
    #     tz = pytz.timezone(tz_str)
    #     now = datetime.now(tz)

    #     for event in self._events_cache:
    #         start = event["start_dt"]
    #         end = event["end_dt"]

    #         minutes_until = (start - now).total_seconds() / 60
    #         is_now = start <= now <= end

    #         if is_now:
    #             results.append(TriggerResult(
    #                 triggered=True,
    #                 trigger_id=_event_trigger_id(event) + "_now",
    #                 formatted_lines=self._format_trigger_display(event, now, is_now=True),
    #                 priority=5,
    #                 duration_seconds=duration_seconds,
    #                 data=self._build_data(event, self._events_cache),
    #             ))
    #         elif 0 <= minutes_until <= minutes_before:
    #             results.append(TriggerResult(
    #                 triggered=True,
    #                 trigger_id=_event_trigger_id(event),
    #                 formatted_lines=self._format_trigger_display(event, now, is_now=False),
    #                 priority=5,
    #                 duration_seconds=duration_seconds,
    #                 data=self._build_data(event, self._events_cache),
    #             ))

    #     return results

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
        
        # Returns the ID if found, otherwise returns None
        return team_map.get(team_name)
        
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        return []

    def cleanup(self) -> None:
        pass
