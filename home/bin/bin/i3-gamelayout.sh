#!/bin/bash

set -euo pipefail

. ~/.uvenv/bin/activate

# focus on the container that momentum mod is running in

i3-msg -t get_tree \
  | jq '
    .nodes[].nodes[].nodes[].floating_nodes[]
    | select(.nodes[].window_properties.class == "momentum")
    | .rect'

# screen resolution: 3440 x 1440
# game window size:  2560 x 1440

function wait_for_window() {
  local class_name="$1"
  until i3-client --grab --exists "$class_name"; do
    echo "Waiting for $class_name window to appear..."
    sleep 1
  done
}

SCREEN_WIDTH=3440
SCREEN_HEIGHT=1440

GAME_WIDTH=2560
GAME_HEIGHT=1440

GAME_X=$(( SCREEN_WIDTH - GAME_WIDTH ))
GAME_Y=-26 # adjust for height of window title

if ! i3-client --grab --exists "momentum"; then
  echo "Could not find momentum window"
  i3-msg 'exec steam-native steam://rungameid/1802710'
  wait_for_window "momentum"
fi

# close the "steamwebhelper" window if it exists
if i3-client --grab --exists "steamwebhelper"; then
  i3-msg [class="steam"] kill
fi

# move the game window to the right side of the screen
i3-msg [class="momentum"] move position -- "$GAME_X" "$GAME_Y"

I3STATUS_HEIGHT=25
TL_HEIGHT=700
BL_HEIGHT=$(( SCREEN_HEIGHT - TL_HEIGHT - I3STATUS_HEIGHT ))

# add terminal in the top left corner
if ! i3-client --grab --exists "ghostty"; then
  echo "Could not find ghostty window"
  i3-msg 'exec ghostty'
  wait_for_window "ghostty"
fi
# make terminal floating
i3-msg [class="ghostty"] floating enable
i3-msg [class="ghostty"] resize set $GAME_X $TL_HEIGHT
i3-msg [class="ghostty"] move position -- '0' '0'

# add obs in the bottom left corner
if ! i3-client --grab --exists "obs"; then
  echo "Could not find obs window"
  i3-msg 'exec /usr/bin/obs --profile surf --scene surf'
  wait_for_window "obs"
fi
# make obs floating
i3-msg [class="obs"] floating enable
i3-msg [class="obs"] resize set $GAME_X $TL_HEIGHT
i3-msg [class="obs"] move position -- '0' $BL_HEIGHT

