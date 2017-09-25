#!/bin/bash
# create a new session. The -d flag signifies that the session is not attached yet
tmux new-session -s asdf -n 'myWindow' -d

# The first pane is referenced using the -t flag, however this is not necessary.
# for the <enter> key, we can use either C-m (linefeed) or C-j (newline)
tmux send-keys -t asdf:myWindow.0 'htop' C-j

# split the window *vertically*
tmux split-window -v

# we now have two panes in myWindow: pane 0 is above pane 1
# again, specifying pane 1 with '-t 1' is optional
tmux send-keys -t 1 'sudo iotop' C-j
tmux split-window -h
tmux send-keys -t 2 'watch df -h' C-j

# uncomment the following command if you want to attach
# explicitly to the window we just created

#tmux select-window -t asdf:mywindow

# finally attach to the session
# If 'cc' is passes as the first argument, then open this iterm-style
if [ $1 == 'cc' ]; then
  tmux -CC attach -t asdf
else
  tmux attach -t asdf
fi
