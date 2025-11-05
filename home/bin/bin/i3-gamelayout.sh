#!/bin/bash

set -euxo pipefail

# focus on the container that momentum mod is running in

i3-msg -t get_tree \
  | jq '
    .nodes[].nodes[].nodes[].floating_nodes[]
    | select(.nodes[].window_properties.class == "momentum")
    | .rect'

# screen resolution: 3440 x 1440
# game window size:  2560 x 1440

SCREEN_WIDTH=3440
SCREEN_HEIGHT=1440

GAME_WIDTH=2560
GAME_HEIGHT=1440

GAME_X=$(( SCREEN_WIDTH - GAME_WIDTH ))
GAME_Y=-26 # adjust for height of window title

# move the game window to the right side of the screen
i3-msg [class="momentum"] move position -- "$GAME_X" "$GAME_Y"

OBS_HEIGHT=700
CHROME_HEIGHT=$(( SCREEN_HEIGHT - OBS_HEIGHT ))

# add chrome in the bottom left corner
i3-msg 'exec /usr/bin/google-chrome-stable'
sleep 1
i3-msg [class="Google-chrome"] focus
i3-msg [class="Google-chrome"] floating enable
i3-msg [class="Google-chrome"] resize set $GAME_X $CHROME_HEIGHT
i3-msg [class="Google-chrome"] move position -- '0' '0'

# start obs to the left of momentum
i3-msg 'exec /usr/bin/obs'
sleep 2
# make obs floating
i3-msg [class="obs"] focus
i3-msg [class="obs"] floating enable
i3-msg [class="obs"] resize set $GAME_X $CHROME_HEIGHT
i3-msg [class="obs"] move position -- '0' $OBS_HEIGHT


