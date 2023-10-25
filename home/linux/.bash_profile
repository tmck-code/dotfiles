#!/bin/bash

[ -n "${DEBUG_SHELL:-}" ] && echo "~~ .BASH_PROFILE: sourcing .bash_profile"

# ENV configs -----------------------------------

# Use vim as editor instead of the default 'nano'
alias crontab="VIM_CRONTAB=true crontab"
export EDITOR=vim
export VISUAL=vim

export TERM=xterm-256color

# PATH ------------------------------------------

# Load personal scripts
PATH="$PATH:$HOME/bin:$HOME/.local/bin:/usr/local/bin"
# Language paths
# - golang
export GOPATH="$HOME/go"
export GOROOT="/usr/lib/go-1.19/"
PATH="$PATH:$GOPATH/bin"
# Tool paths
PATH="$PATH:.emacs.d/bin"
export PATH

# Bash completion -------------------------------
sources_dirs=(
  "/usr/share/bash-completion/bash_completion" # bash/shell completions dir
)
sources_files=(
  "/usr/share/doc/git/contrib/completion/git-completion.bash" # git completions
  "$HOME/.cargo/env" # cargo/rust
  "$HOME/dev/z/z.sh" # z - jump around
  "$HOME/.secrets" # my api keys
  "$HOME/.venv/bin/activate" # python virtual env
)

for f in "${sources_dirs[@]}"; do
  for i in "$f"/*; do
    test -f "$i" && source "$i"
  done
done

for f in "${sources_files[@]}"; do
  test -f "$f" && source "$f"
done

# Finish ----------------------------------------

[ -n "${DEBUG_SHELL:-}" ] && echo "loading bashrc!"
export BASHPROFILE_LOADED=true
if ! shopt -q login_shell; then
  [ -n "${DEBUG_SHELL:-}" ] && echo "~~ .BASH_PROFILE: non-login shell, exiting .bash_profile"
  return 0
else
  [ -n "${DEBUG_SHELL:-}" ] && echo "~~ .BASH_PROFILE: login shell, sourcing .bashrc"
  source "$HOME/.bashrc"
fi

