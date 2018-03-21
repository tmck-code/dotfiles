# prompt examples:
#   [3 jobs master virtualenv] ~/code/myproject/foo
#   [1 job my-branch virtualenv] ~/code/bar/
#   [virtualenv] ~/code/
#   ~
# Very, very fast, only requiring a couple of fork()s (and no forking at all to determine the current git branch)

shopt -s histappend    # append to the history file, don't overwrite it
HISTSIZE=1000          # for setting history length
HISTFILESIZE=2000
HISTCONTROL=ignoreboth # don't put duplicate lines or lines starting with space in the history.

export CLICOLOR="exfxcxdxbxegedabagacad" # enable colours
alias grep='grep --color=auto'

if [[ "$USER" == "root" ]]
then
  export PS1="\[\e[1;31m\]\u\[\e[0m\] \[\e[1;33m\]\w\[\e[0m\] ";
else
    export PS1="\[☯ \e[1;33m\]\w\[\e[0m\] ";
fi

# 100% pure Bash (no forking) function to determine the name of the current git branch
gitbranch() {
    export GITBRANCH=""

    local repo="${_GITBRANCH_LAST_REPO-}"
    local gitdir=""
    if [[ ! -z "$repo" && "$PWD" == "$repo"* ]]; then
        gitdir="$repo/.git"
    fi

    # If we don't have a last seen git repo, or we are in a different directory
    if [[ -z "$repo" || "$PWD" != "$repo"* || ! -e "$gitdir" ]]; then
        local curr="$PWD"
        while [[ ! -z "$curr" ]]; do
            if [[ -e "$curr/.git" ]]; then
                repo="$curr"
                gitdir="$curr/.git"
                break
            fi
            curr="${curr%/*}"
        done
    fi

    if [[ -z "$gitdir" ]]; then
        unset _GITBRANCH_LAST_REPO
        return 0
    fi
    export _GITBRANCH_LAST_REPO="${repo}"
    local head=""
    local branch=""
    read head < "$gitdir/HEAD"
    case "$head" in
        ref:*)
            branch="${head##*/}"
            ;;
        "")
            branch=""
            ;;
        *)
            branch="d:${head:0:7}"
            ;;
    esac
    if [[ -z "$branch" ]]; then
        return 0
    fi
    export GITBRANCH="$branch"
}

PS1_green='\[\e[32m\]'
PS1_blue='\[\e[34m\]'
PS1_reset='\[\e[0m\]'

_mk_prompt() {
    # Change the window title of X terminals
    case $TERM in
        xterm*|rxvt*|Eterm)
            echo -ne "\033]0;${USER}@${HOSTNAME%%.*}:${PWD/$HOME/~}\007"
           ;;
        screen)
            echo -ne "\033_${USER}@${HOSTNAME%%.*}:${PWD/$HOME/~}\033\\"
          ;;
    esac

    # Un-screw virtualenv stuff
    if [[ ! -z "${_OLD_VIRTUAL_PS1-}" ]]; then
        export PS1="$_OLD_VIRTUAL_PS1"
        unset _OLD_VIRTUAL_PS1
    fi

    if [[ -z "${_MK_PROMPT_ORIG_PS1-}" ]]; then
        export _MK_PROMPT_ORIG_PS1="$PS1"
    fi

    local prefix=("\D{%T}")
    local jobcount="$(jobs -p | wc -l)"
    if [[ "$jobcount" -gt 0 ]]; then
        local job="${jobcount##* } job"
        [[ "$jobcount" -gt 1 ]] && job="${job}s"
        prefix+=("$job")
    fi

    gitbranch
    if [[ ! -z "$GITBRANCH" ]]; then
        prefix+=("${PS1_green}$GITBRANCH${PS1_reset}")
    fi

    local virtualenv="${VIRTUAL_ENV##*/}"
    if [[ ! -z "$virtualenv" ]]; then
        prefix+=("${PS1_blue}$virtualenv${PS1_reset}")
    fi

    PS1="$_MK_PROMPT_ORIG_PS1"
    if [[ ! -z "$prefix" ]]; then
        PS1="[${prefix[@]}] $PS1"
    fi

    export PS1
}

export PROMPT_COMMAND=_mk_prompt

if [ -f ~/.bash_aliases ]; then
    . ~/.bash_aliases
fi

fortune -a | pokemonsay

cd $HOME

