# MLB Scores Plugin
Track live Major League Baseball game scores, team metrics, schedules, and custom board colors for your configured teams.

## Example Page Displays
Upcoming Game

Scoreboard

Current Inning Display

## Overview
The MLB Scores plugin automatically polls the official MLB backend to pull real-time game schedule and linescore data (runs, hits, errors, current inning, and status) for your selected team.
To optimize network usage, the plugin caches league-wide team profiles on configuration. It throttles the schedule API to check at most once every 10 minutes, lifting the restriction to real-time updates only when a game is within 15 minutes of first pitch or actively in progress (based on the configured Refresh Interval, min 60 seconds). The live linescore endpoint is skipped entirely once a game goes final.

## Configuration

| Setting | Name | Description | Required |
|---|---|---|---|
| `enabled` | Enabled | Toggle whether to activate game tracking. | No |
| `teams` | Teams to track | Selected MLB team(s) to monitor game data and match progress for. | Yes |
| `timezone` | Timezone | IANA timezone database string used for interpreting start times and localization. | No |
| `trigger_page_id` | Trigger Page | Custom template page using layout variables to display when a game trigger fires. | No |
| `refresh_seconds` | Refresh Interval (seconds) | Frequency of fetching live game updates (minimum 60 seconds). | No |

## Template Variables

### Game Information
| Variable | Description | Example |
|---|---|---|
| `mlb.game_scheduled_start` | Localized game start time formatted to the configured timezone | `7:10 PM` |
| `mlb.minutes_until_game` | Integer minutes remaining until the scheduled first pitch | `45` |
| `mlb.game_status_code` | Raw official status code tracking play state (`F` = Final, `P` = Pre-Game, `I` = In-Progress, `0` = No Game) | `I` |
| `mlb.stadium` | Venue name where the scheduled game is taking place | `Wrigley Field` |
| `mlb.current_inning` | The current frame integer value of an active live match | `4` |
| `mlb.current_inning_state` | Current half-inning positioning description | `BOTTOM` |

### Team Details & Custom Colors
| Variable | Description | Example |
|---|---|---|
| `mlb.home_team_name` | Full name of the home franchise | `Colorado Rockies` |
| `mlb.home_team_abbr` | Official 3-letter abbreviation code for the home team | `COL` |
| `mlb.home_team_club_name` | Common club/nickname identifier for the home team | `Rockies` |
| `mlb.home_team_color` | Vestaboard-compatible color block value assigned to the home franchise | `purple` |
| `mlb.away_team_name` | Full name of the visiting franchise | `Chicago Cubs` |
| `mlb.away_team_abbr` | Official 3-letter abbreviation code for the visiting team | `CHC` |
| `mlb.away_team_club_name` | Common club/nickname identifier for the visiting team | `Cubs` |
| `mlb.away_team_color` | Vestaboard-compatible color block value assigned to the visiting franchise | `blue` |

### Boxscore Statistics
| Variable | Description | Example |
|---|---|---|
| `mlb.current_home_score` | Total runs accumulated by the home team | `5` |
| `mlb.current_home_hits` | Total hits recorded by the home team | `9` |
| `mlb.current_home_errors` | Total errors committed by the home team | `1` |
| `mlb.current_away_score` | Total runs accumulated by the away team | `3` |
| `mlb.current_away_hits` | Total hits recorded by the away team | `6` |
| `mlb.current_away_errors` | Total errors committed by the away team | `0` |
