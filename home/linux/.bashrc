#!/bin/bash
#
# github.com/tmck-code/dotfiles
#
# - use DEBUG=true before sourcing to enable debug print statements
# - use HIDE=true before sourcing to _not_ print the PS1

# DEBUG=1
# NOTE: Enter tmux in your .bash_profile, before entering .bashrc
if [ -n "${DEBUG:-}" ]; then
  echo '{"sourcing": ".bashrc", "DEBUG": "'${DEBUG:-}'"}'
  echo -n '{"$PS1": '
  [ -z "$PS1" ] && echo 'false}' || echo 'true}'
  echo -n '{".bash_profile sourced": '
  [ -z "${BASH_PROFILE_SOURCED:-}" ] && echo 'false}' || echo 'true}'
fi

export HISTFILESIZE=                    # largest history written to file at one time
export HISTSIZE=                        # large history file
export HISTCONTROL=ignoreboth:erasedups # don't put lines in the history that start with space, or are duplicates
shopt -s histappend                     # append to the history file, don't overwrite

# Change the file location because certain bash sessions truncate .bash_history file upon close.
# - http://superuser.com/questions/575479/bash-history-truncated-to-500-lines-on-each-login
export HISTFILE="$HOME/.bash_eternal_history"

# Per-pane shell-local setup --------------------

# For every interactive shell, resource aliases, functions, and completions
[ -f "$HOME/.bash_aliases" ] && source "$HOME/.bash_aliases"
[ -f "$HOME/dev/z/z.sh" ] && source "$HOME/dev/z/z.sh"
[ -f /usr/share/bash-completion/bash_completion ] && source /usr/share/bash-completion/bash_completion

# NVM lazy-load shim: stub functions source nvm.sh on first use.
# This allows each pane to start up in <1ms, avoiding the ~500 ms cost to load nvm.sh
for cmd in nvm node npm npx; do
  eval "$cmd() {
    unset -f nvm node npm npx
    [ -s \"\$NVM_DIR/nvm.sh\" ] && . \"\$NVM_DIR/nvm.sh\"
    $cmd \"\$@\"
  }"
done

# Function to shorten the current directory
short_pwd() {
  sed 's:\([^/]\)[^/]*/:\1/:g' <<<"${PWD/#${HOME}/\~}"
}

if [[ "$USER" == "root" ]]; then
  export PS1="\[\e[1;31m\]\u\[\e[0m\] \[\e[1;33m\]\w\[\e[0m\] "
else
  export PS1="\[\e[1;33m\]\$(short_pwd)\[\e[0m\] "
fi

export _GIT_LAST_REPO=""

# 100% pure Bash (no forking) function to determine the name of the current git branch
#
# The best speed to fetch all the git info is achieved by reading .git files rather
# than running any git commands.
# The function searches recursively up the directory tree until it find a .git dir.
# - If this is found, then that dir path is cached in _GIT_REPO.
# - If root is reached without finding a .git dir, then _GIT_REPO is unset.
# If the user moves to a dir that is under _GIT_REPO, then git infor is reused
# (only the branch name is re-read)
gitbranch() {
  export GIT_BRANCH=""

  local repo="${_GIT_REPO-}"
  local gitdir=""

  # If repo is set, and we are in that repo
  if [[ -n "${repo:-}" && "$PWD" == "${repo}/*" ]]; then
    gitdir="$repo/.git"
  else
    local curr="$PWD"
    while [[ -n "$curr" ]]; do       # while we are in a dir
      if [[ -e "$curr/.git" ]]; then # check if .git exists
        repo="$curr"                 # if it does, set our vars and break
        gitdir="$curr/.git"
        break
      fi
      curr="${curr%/*}" # else, go up one dir, i.e. "../"
    done
  fi

  if [[ -z "${gitdir:-}" ]]; then # if we aren't in a git repo, just return
    unset _GIT_REPO
    return 0
  fi

  export _GIT_REPO="${repo}"

  # Read and export git branch from the HEAD file
  local head
  read -r head <"${gitdir}/HEAD"

  case "${head}" in
  ref:*) export GIT_BRANCH="${head##*/}" ;;
  "") return 0 ;;
  *) export GIT_BRANCH="d:${head:0:7}" ;;
  esac

  local commit
  if [ -f "${gitdir}/refs/heads/${GIT_BRANCH}" ]; then
    read -r commit <"${gitdir}/refs/heads/${GIT_BRANCH}"
  elif [ -f "${gitdir}/ORIG_HEAD" ]; then
    read -r commit <"${gitdir}/ORIG_HEAD"
  fi
  export GITCOMMIT="${commit:0:9}"
}

PS1_green='\[\e[1;32m\]'
PS1_purple='\[\e[3;35m\]'
PS1_reset='\[\e[0m\]'
PS1_yellow_bg='\[\e[1;33m\]'
PS1_dim='\[\e[2;37m\]'

# Capture command start time before execution to use for duration calc later.
# \r\e[K erases the printed integer so it doesn't appear above the command output.
PS0=$'${_PS0_TIME:=${EPOCHREALTIME/./}}\r\e[K'

# Format integer microseconds as fixed-width auto-scaled duration.
_fmt_duration() {
  local us=$1 out
  if   (( us < 1000 ));     then printf -v out '%d µs' "$us"
  elif (( us < 1000000 ));  then printf -v out '%d.%02d ms' $((us/1000))    $((us%1000/10))
  elif (( us < 60000000 )); then printf -v out '%d.%02d s'  $((us/1000000)) $((us%1000000/10000))
  else
    local s=$((us/1000000))
    printf -v out '%dm %02ds' $((s/60)) $((s%60))
  fi
  # Pad to 8 display columns. µ is 2 bytes / 1 column, so add a byte when µs.
  [[ $out == *µs ]] && printf '%-9s' "$out" || printf '%-8s' "$out"
}

_mk_prompt() {
  # Capture exit status of last command^. MUST be done first.
  local last_exit=$?

  # Update the ~/.bash_eternal_history every time
  history -a

  # Change the window title of X terminals
  if [[ "$TERM" =~ xterm* ]]; then
    echo -ne "\033]0;${USER}@${HOSTNAME%%.*}:${PWD/$HOME/~}\007"
  fi

  # get the current git branch
  gitbranch

  local dur_str='        ' # 8-space placeholder when no command was run
  if [[ -n "${_PS0_TIME:-}" ]]; then
    dur_str=$(_fmt_duration $(( ${EPOCHREALTIME/./} - _PS0_TIME )))
  fi
  unset _PS0_TIME

  sep="∈"
  local exit_colour="${PS1_green}"
  [ "$last_exit" -ne 0 ] && exit_colour='\[\e[1;31m\]'
  local prefix=("${exit_colour}${last_exit}${PS1_reset} ${PS1_dim}[${dur_str}]${PS1_reset} > \D{%T}")
  # local prefix=("")
  if [ -n "${GIT_BRANCH:-}" ]; then
    prefix+=("${PS1_yellow_bg}${sep}${PS1_reset} ${PS1_green}${GIT_BRANCH}${PS1_reset} / ${PS1_purple}${GITCOMMIT}${PS1_reset}")

    # Modified files
    if [ -n "$(git ls-files -m)" ]; then
      prefix+=("✹")
    fi
    # New, untracked files
    if [ -n "$(git ls-files --others --exclude-standard --directory --no-empty-directory --error-unmatch -- ':/*' 2>/dev/null)" ]; then
      prefix+=("✭")
    fi
  fi

  unset _PS0_TIME

  if test -v HIDE; then
    export PS1=""
  else
    export PS1=" ${prefix[@]}\n ☯ $_MK_PROMPT_ORIG_PS1"
  fi
}

export _MK_PROMPT_ORIG_PS1="$PS1" # Keep a static copy of PS1
export PROMPT_COMMAND=_mk_prompt  # Create PS1 prompt (history -a is called inside)

# Detect if in SSH/SCP session, as printing the pokesay message causes scp to fail
# Only print the pokemon fortune if:
# - there isn't an SSH session detected (scp/ssh etc)
if [ -z "${SSH_CONNECTION:-}" ]; then
  # Present a pretty message
  if test $((RANDOM % 10)) -eq 1; then
    display-message -p "$(date)" -f 'AMC AAA01' | pokesay -uWbCjFI -w 150
  else
    # fortune | pokesay -jCubFI -w 40
    fortune | pokesay -jCubFI -w 40
  fi
fi
