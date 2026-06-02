# Timer Plugin
Set a Timer (in minutes or seconds) and display a visual status indicator of the remaining time, initiated via a POST from an external source.

<img width="550" height="222" alt="Timer - In Progress" src="./docs/Timer - In Progress.png" />

## Overview
The Timer plugin exposes a local HTTP endpoint at /api/plugins/timer/receive. Any system can POST a JSON payload to set the Timer which will immediately start running. Optionally verify requests with an HMAC secret.

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

## Configuration

| Setting | Name | Description | Required |
|---|---|---|---|
| `secret` | HMAC Secret | Optional secret to verify incoming webhooks (leave blank to disable). | No |
| `status_color` | Flap Color | Flap color for 'status_display' variable. Used to display what % of time remains on the timer | Yes |
| `status_color_completed` | Flap Color (Completed) | Flap color for 'status_display_padded' variable. Used to display what % of time has surpassed on the timer so the status bar remains the same length | Yes |
| `max_status_flaps` | Max Status Flaps | The maximum number of flaps used to display the timer status. Used to make sure the status bar fits on the Vestaboard page without overflowing a row | Yes |
| `default_measure` | Default Timer Value Qualifier | Expected qualifier for the 'duration' value received via API ("minutes" or "seconds") | No |

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
