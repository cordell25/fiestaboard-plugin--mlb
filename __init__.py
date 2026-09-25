# MLB - Track Team Games / Scores

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

        # Schedule tracking cache states
        self._last_schedule_fetch: Optional[datetime] = None
        self._cached_schedule_payload: Optional[Dict[str, Any]] = None

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
        if not teams or not isinstance(teams, list):
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

            new_teams_map = {}
            for team in team_payload.get("teams", []):
                t_id = team.get("id")
                name = team.get("name") or ""

                if t_id:
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
                        "color": team_color,
                    }

            self._teams = new_teams_map
            logger.info("Successfully cached %d MLB teams by ID with colors.", len(self._teams))

            self._last_schedule_fetch = None
            self._cached_schedule_payload = None

        except Exception as e:
            logger.error("Failed to populate league team map: %s", e)

    # ------------------------------------------------------------------
    # Data fetching
    # ------------------------------------------------------------------

    def fetch_data(self) -> PluginResult:
        """Fetch team scores for all configured teams in configured order."""
        user_timezone = self.config.get("timezone", "America/Los_Angeles")
        tz = pytz.timezone(user_timezone)
        now = datetime.now(tz)

        teams = self.config.get("teams", [])
        if not teams:
            return PluginResult(available=False, error="No teams selected")

        if not self._teams:
            logger.warning("League map empty. Fetching now.")
            self.on_config_change({}, self.config)

        configured_team_ids = []
        for team_name in teams:
            team_meta = self.get_configured_team_id_and_color(team_name)
            if team_meta and team_meta.get("id"):
                configured_team_ids.append(team_meta["id"])

        if not configured_team_ids:
            return PluginResult(available=False, error="None of the selected teams could be identified.")

        team_ids_param = ",".join(str(tid) for tid in configured_team_ids)

        # --------------------------------------------------------------
        # SMART CACHING GATE FOR SCHEDULE API
        # --------------------------------------------------------------
        skip_schedule_api_call = False

        if self._cached_schedule_payload and self._last_schedule_fetch:
            time_since_last_fetch = now - self._last_schedule_fetch
            minutes_since_fetch = time_since_last_fetch.total_seconds() / 60

            cached_dates = self._cached_schedule_payload.get("dates", [])
            cached_games = cached_dates[0].get("games", []) if cached_dates else []

            if not cached_games:
                if minutes_since_fetch < 10:
                    skip_schedule_api_call = True
            else:
                has_imminent_or_live_game = False
                for g in cached_games:
                    g_status = g.get("status", {}).get("statusCode")
                    g_utc = datetime.strptime(g["gameDate"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                    g_local = g_utc.astimezone(tz)
                    mins_until = (g_local - now).total_seconds() / 60

                    if mins_until <= 15 and g_status not in ("F", "O", "D"):
                        has_imminent_or_live_game = True
                        break

                if not has_imminent_or_live_game and minutes_since_fetch < 10:
                    skip_schedule_api_call = True

        if skip_schedule_api_call:
            logger.info("Reusing cached schedule payload to preserve API overhead.")
            schedule_payload = self._cached_schedule_payload
        else:
            logger.info("Fetching fresh schedule payload for teams: %s", team_ids_param)
            try:
                response = requests.get(
                    f"{API_SCHEDULE_URL}{team_ids_param}",
                    timeout=15,
                )
                response.raise_for_status()
                schedule_payload = response.json()

                self._cached_schedule_payload = schedule_payload
                self._last_schedule_fetch = now
            except Exception as e:
                logger.warning("Schedule fetch failed: %s. Falling back to cache.", e)
                if self._cached_schedule_payload:
                    schedule_payload = self._cached_schedule_payload
                else:
                    return PluginResult(available=True, data={"games": []})

        raw_games = []
        for date_entry in schedule_payload.get("dates", []):
            raw_games.extend(date_entry.get("games", []))

        # --------------------------------------------------------------
        # DETERMINISTIC ARRAY BUILDING (1:1 with configured teams)
        # --------------------------------------------------------------
        games_list = []
        linescore_cache = {}

        for team_name in teams:
            team_meta = self.get_configured_team_id_and_color(team_name)
            if not team_meta:
                continue
            target_id = team_meta["id"]

            # Collect all games scheduled today for this specific team
            team_games = []
            for g in raw_games:
                home_id = g.get("teams", {}).get("home", {}).get("team", {}).get("id")
                away_id = g.get("teams", {}).get("away", {}).get("team", {}).get("id")
                if home_id == target_id or away_id == target_id:
                    team_games.append(g)

            # Case 1: Off Day
            if not team_games:
                abbr = team_meta.get("abbreviation") or team_name[:3].upper()
                games_list.append(
                    {
                        "formatted": f"{abbr} - OFF",
                        "team_tracked": team_name,
                        "game_today": False,
                        "game_scheduled_start": "",
                        "minutes_until_game": 0,
                        "game_status_code": "OFF",
                        "stadium": "",
                        "current_inning": 0,
                        "current_inning_state": "",
                        "home_team_name": "",
                        "home_team_abbr": "",
                        "home_team_club_name": "",
                        "home_team_color": "white",
                        "away_team_name": "",
                        "away_team_abbr": "",
                        "away_team_club_name": "",
                        "away_team_color": "white",
                        "current_home_score": 0,
                        "current_home_hits": 0,
                        "current_home_errors": 0,
                        "current_away_score": 0,
                        "current_away_hits": 0,
                        "current_away_errors": 0,
                    }
                )
                continue

            # Sort games chronologically
            team_games.sort(key=lambda x: x.get("gameDate", ""))

            # Case 2: Doubleheader Evaluation
            matching_game = team_games[0]
            if len(team_games) > 1:
                g1 = team_games[0]
                g2 = team_games[1]
                g1_status = g1.get("status", {}).get("statusCode", "")
                g2_status = g2.get("status", {}).get("statusCode", "")

                g1_complete = g1_status in ("F", "O", "FR")
                # Game 2 has started if it's not preview/scheduled
                g2_started = g2_status not in ("P", "S", "PR")

                # Only swap to game 2 if game 1 is complete AND game 2 has actually started
                if g1_complete and g2_started:
                    matching_game = g2
                else:
                    matching_game = g1

            # Case 3: Parse and Populate Game Data
            try:
                utc_start = datetime.strptime(matching_game["gameDate"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                local_start = utc_start.astimezone(tz)
                scheduled_game_start = local_start.strftime("%I:%M %p").lstrip("0")
                minutes_until_game = int((local_start - now).total_seconds() / 60)

                away_id = matching_game["teams"]["away"]["team"]["id"]
                home_id = matching_game["teams"]["home"]["team"]["id"]

                away_cached = self._teams.get(away_id, {})
                home_cached = self._teams.get(home_id, {})

                away_abbr = away_cached.get("abbreviation") or matching_game["teams"]["away"]["team"].get("abbreviation", "AWY")
                home_abbr = home_cached.get("abbreviation") or matching_game["teams"]["home"]["team"].get("abbreviation", "HOM")

                game_status_code = matching_game.get("status", {}).get("statusCode", "0")
                should_fetch_live_data = (minutes_until_game <= 15) and (game_status_code not in ("F", "O", "D"))

                away_stats = {}
                home_stats = {}
                current_inning = None
                current_inning_state = None

                game_pk = matching_game.get("gamePk")
                if game_pk and should_fetch_live_data:
                    if game_pk in linescore_cache:
                        linescore_payload = linescore_cache[game_pk]
                    else:
                        try:
                            linescore_resp = requests.get(
                                f"{API_GAME_URL}{game_pk}{API_GAME_URL_APPEND}",
                                timeout=10,
                            )
                            linescore_resp.raise_for_status()
                            linescore_payload = linescore_resp.json()
                            linescore_cache[game_pk] = linescore_payload
                        except Exception as e:
                            logger.warning("Linescore fetch failed for game %s: %s", game_pk, e)
                            linescore_payload = None

                    if linescore_payload:
                        linescore_teams = linescore_payload.get("teams", {})
                        away_stats = linescore_teams.get("away", {})
                        home_stats = linescore_teams.get("home", {})
                        current_inning = linescore_payload.get("currentInning")
                        current_inning_state = linescore_payload.get("inningState")
                    else:
                        away_stats = {"runs": matching_game["teams"]["away"].get("score", 0)}
                        home_stats = {"runs": matching_game["teams"]["home"].get("score", 0)}
                elif game_status_code in ("F", "O", "D"):
                    away_stats = {"runs": matching_game["teams"]["away"].get("score", 0)}
                    home_stats = {"runs": matching_game["teams"]["home"].get("score", 0)}

                game_item = {
                    "formatted": f"{away_abbr} @ {home_abbr}",
                    "team_tracked": team_name,
                    "game_today": True,
                    "game_scheduled_start": scheduled_game_start,
                    "minutes_until_game": max(0, minutes_until_game),
                    "game_status_code": game_status_code,
                    "stadium": matching_game.get("venue", {}).get("name", "Unknown Field"),
                    "current_inning": current_inning or 0,
                    "current_inning_state": current_inning_state or "",

                    "home_team_name": matching_game["teams"]["home"]["team"].get("name", ""),
                    "home_team_abbr": home_abbr,
                    "home_team_club_name": home_cached.get("club_name") or matching_game["teams"]["home"]["team"].get("clubName", "Home"),
                    "home_team_color": home_cached.get("color", "white"),

                    "away_team_name": matching_game["teams"]["away"]["team"].get("name", ""),
                    "away_team_abbr": away_abbr,
                    "away_team_club_name": away_cached.get("club_name") or matching_game["teams"]["away"]["team"].get("clubName", "Away"),
                    "away_team_color": away_cached.get("color", "white"),

                    "current_home_score": home_stats.get("runs", 0),
                    "current_home_hits": home_stats.get("hits", 0),
                    "current_home_errors": home_stats.get("errors", 0),

                    "current_away_score": away_stats.get("runs", 0),
                    "current_away_hits": away_stats.get("hits", 0),
                    "current_away_errors": away_stats.get("errors", 0),
                }
                games_list.append(game_item)

            except KeyError as e:
                logger.error("Skipping malformed game entry %s: %s", matching_game.get("gamePk"), e)

        return PluginResult(
            available=True,
            data={"games": games_list},
        )

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
            "Washington Nationals": {"id": 120, "color": "red"},
        }
        return team_map.get(team_name)

    def cleanup(self) -> None:
        pass
