#!/bin/bash

set -euxo pipefail

# focus on the container that momentum mod is running in

i3-msg -t get_tree \
  | jq '
    .nodes[].nodes[].nodes[].floating_nodes[]
    | select(.nodes[].window_properties.class == "momentum")
    | .rect'

i3-msg [class="momentum"] move position -- '880' '-26'
