# Timer Setup Guide

## Overview

The Timer plugin exposes a local HTTP endpoint at `fiestapi.local:4420/api/plugins/timer/receive`. Any system can POST a JSON payload to set and start the Timer.

## Quick Setup

1. **Enable** — Go to **Integrations** in your FiestaBoard settings and enable **Webhook Display**.
2. **Configure** — Fill in the plugin settings (see Configuration Reference below).
3. **Template** — Add a page using the `timer` plugin variables:
   ```
   {center}{{timer.duration}} {{timer.measure}}
   {{red}}{{timer.status_display_padded}}{{green}}
   {center}{{= IF(timer.seconds_remaining = 0,"TIME'S UP") }}
   ```
4. **View** — Navigate to your board page to see the live display.

## API (To Start Timer)
URL: fiestapi.local:4420/api/plugins/timer/receive

Body:
- **duration** (int, required): How long to set the Timer for
- _**measure**_ (str, optional): What does the 'duration' represent: "minutes" | "seconds" (default is set in plugin config)

```
{
    "duration": 4,
    "measure": "minutes"
}
```
## Example Timer Page Display for a 4 Minute Timer
### Timer Start
<img width="550" height="222" alt="Timer - Start" src="./Timer - Start.png" />

### Timer In Progress
<img width="550" height="222" alt="Timer - In Progress" src="./Timer - In Progress.png" />

### Timer Completed
<img width="550" height="222" alt="Timer - Completed" src="./Timer - Completed.png" />

## Template Variables

| Variable | Description | Example |
|---|---|---|
| `timer.start_time` | Date & Time of when the Timer begins (ISO format) | `2025-06-15T00:00:00` |
| `timer.end_time` | Date & Time of when the Timer ends (ISO format) | `2025-06-15T00:00:00` |
| `timer.duration` | Integer value of how long the Timer is set for | `5` |
| `timer.measure` | Unit of time measure for the timer | `minutes` |
| `timer.status_max_length` | How many status blocks represent the full amount of time | `13` |
| `timer.status_current_length` | Current status blocks representing the time remaining | `10` |
| `timer.status_display` | Visual display of what % of time remains on the timer | `🟨🟨🟨🟨🟨🟨🟨🟨🟨🟨` |
| `timer.status_display_padded` | Visual display of time remaining with padding to maintain bar length | `🟨🟨🟨🟨🟨🟨🟨🟨🟨🟨🟪🟪🟪` |
| `timer.minutes_remaining` | Minutes remaining | `4` |
| `timer.seconds_remaining` | Seconds remaining | `180` |
| `timer.status_block_duration` | How much time elapses (in seconds) before another status block is removed | `15` |
| `timer.last_updated` | When the last timer API call was received | `2026-05-01 12:00` |
| `timer.timer_in_flight` | Is the timer currently counting down? | `Yes` |


## Configuration Reference

## Configuration

| Setting | Name | Description | Required |
|---|---|---|---|
| `secret` | HMAC Secret | Optional secret to verify incoming webhooks (leave blank to disable). | No |
| `status_color` | Flap Color | Flap color for 'status_display' variable. Used to display what % of time remains on the timer | Yes |
| `status_color_completed` | Flap Color (Completed) | Flap color for 'status_display_padded' variable. Used to display what % of time has surpassed on the timer so the status bar remains the same length | Yes |
| `max_status_flaps` | Max Status Flaps | The maximum number of flaps used to display the timer status. Used to make sure the status bar fits on the Vestaboard page without overflowing a row | Yes |
| `default_measure` | Default Timer Value Qualifier | Expected qualifier for the 'duration' value received via API ("minutes" or "seconds") | No |

## Troubleshooting

- **Timer not updating** — verify the POST hits `fiestapi.local:4420/api/plugins/timer/receive` with valid JSON body.
