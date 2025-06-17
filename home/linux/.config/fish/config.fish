if status is-interactive
  # Commands to run in interactive sessions can go here
  if test -z $TMUX
    tmux
  end
end

# Added by LM Studio CLI (lms)
set -gx PATH $PATH /home/freman/.lmstudio/bin
