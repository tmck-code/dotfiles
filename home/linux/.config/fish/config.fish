if status is-interactive
  # Commands to run in interactive sessions can go here
  if test -z $TMUX
    tmux
  end
end
