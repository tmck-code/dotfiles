#!/bin/bash

alias g="git"
alias v="vim"

alias pip="python3 -m pip"
alias python="python3"

# LS_COLORS_MISC="rs=0:di=02;93:ln=01;36:mh=00:pi=40;33:so=01;35:do=01;35:bd=40;33;01:cd=40;33;01:or=40;31;01:mi=00:su=37;41:sg=30;43:ca=30;41:tw=30;42:ow=34;42:st=37;44:ex=01;32"
# LS_COLORS_ARCHIVES="*.tar=01;31:*.tgz=01;31:*.arc=01;31:*.arj=01;31:*.taz=01;31:*.lha=01;31:*.lz4=01;31:*.lzh=01;31:*.lzma=01;31:*.tlz=01;31:*.txz=01;31:*.tzo=01;31:*.t7z=01;31:*.zip=01;31:*.z=01;31:*.dz=01;31:*.gz=01;31:*.lrz=01;31:*.lz=01;31:*.lzo=01;31:*.xz=01;31:*.zst=01;31:*.tzst=01;31:*.bz2=01;31:*.bz=01;31:*.tbz=01;31:*.tbz2=01;31:*.tz=01;31:*.deb=01;31:*.rpm=01;31:*.jar=01;31:*.war=01;31:*.ear=01;31:*.sar=01;31:*.rar=01;31:*.alz=01;31:*.ace=01;31:*.zoo=01;31:*.cpio=01;31:*.7z=01;31:*.rz=01;31:*.cab=01;31:*.wim=01;31:*.swm=01;31:*.dwm=01;31:*.esd=01;31"
# LS_COLORS_IMAGES="*.jpg=01;95:*.jpeg=01;95:*.mjpg=01;95:*.mjpeg=01;95:*.gif=01;95:*.bmp=01;95:*.pbm=01;95:*.pgm=01;95:*.ppm=01;95:*.tga=01;95:*.xbm=01;95:*.xpm=01;95:*.tif=01;95:*.tiff=01;95:*.png=01;95:*.svg=01;95:*.svgz=01;95:*.mng=01;95:*.pcx=01;95"
# LS_COLORS_VIDEOS="*.mov=01;95:*.mpg=01;95:*.mpeg=01;95:*.m2v=01;95:*.mkv=01;95:*.webm=01;95:*.ogm=01;95:*.mp4=01;95:*.m4v=01;95:*.mp4v=01;95:*.vob=01;95:*.qt=01;95:*.nuv=01;95:*.wmv=01;95:*.asf=01;95:*.rm=01;95:*.rmvb=01;95:*.flc=01;95:*.avi=01;95:*.fli=01;95:*.flv=01;95:*.gl=01;95:*.dl=01;95:*.xcf=01;95:*.xwd=01;95:*.yuv=01;95:*.cgm=01;95:*.emf=01;95:*.ogv=01;35:*.ogx=01;35"
# LS_COLORS_AUDIO="*.aac=00;36:*.au=00;36:*.flac=00;36:*.m4a=00;36:*.mid=00;36:*.midi=00;36:*.mka=00;36:*.mp3=00;36:*.mpc=00;36:*.ogg=00;36:*.ra=00;36:*.wav=00;36:*.oga=00;36:*.opus=00;36:*.spx=00;36:*.xspf=00;36"
# export LS_COLORS="${LS_COLORS_MISC}:${LS_COLORS_ARCHIVES}:${LS_COLORS_IMAGES}:${LS_COLORS_VIDEOS}:${LS_COLORS_AUDIO}"

export LESS_TERMCAP_mb=$(
  tput bold
  tput setaf 2
) # green
export LESS_TERMCAP_md=$(
  tput bold
  tput setaf 6
) # cyan
export LESS_TERMCAP_me=$(tput sgr0)
export LESS_TERMCAP_so=$(
  tput bold
  tput setaf 3
  tput setab 4
) # yellow on blue
export LESS_TERMCAP_se=$(
  tput rmso
  tput sgr0
)
export LESS_TERMCAP_us=$(
  tput smul
  tput bold
  tput setaf 7
) # white
export LESS_TERMCAP_ue=$(
  tput rmul
  tput sgr0
)
export LESS_TERMCAP_mr=$(tput rev)
export LESS_TERMCAP_mh=$(tput dim)
export LESS_TERMCAP_ZN=$(tput ssubm)
export LESS_TERMCAP_ZV=$(tput rsubm)
export LESS_TERMCAP_ZO=$(tput ssupm)
export LESS_TERMCAP_ZW=$(tput rsupm)
export GROFF_NO_SGR=1             # For Konsole and Gnome-terminal
export LESS="--RAW-CONTROL-CHARS" # Allow ANSI colours in less

alias sort="LC_ALL=C sort" # Makes GNU sort _much_ faster
alias grep="grep --color"  # Enable grep colours
alias gpurge="git fetch origin --prune && git branch --merged | grep -v 'master\|main' | xargs git branch -d &> /dev/null || echo nothing to remove!"

alias dush="du -sh * | sort -h"
alias emacs="emacs -nw"

alias code="/usr/share/code/bin/code"

function ppj-clipboard() {
  echo "$(xclip -o -selection clipboard)" | jq | xclip -i -selection clipboard
}

_JQ_REGULAR=0
_JQ_BRIGHT=1
_JQ_DIM=2
_JQ_UNDERSCORE=4
_JQ_BLINK=5
_JQ_REVERSE=7
_JQ_HIDDEN=8

_JQ_BLACK=30
_JQ_RED=31
_JQ_GREEN=32
_JQ_YELLOW=33
_JQ_BLUE=34
_JQ_MAGENTA=35
_JQ_CYAN=36
_JQ_WHITE=37

JQ_NULL="$_JQ_UNDERSCORE;$_JQ_WHITE"
JQ_TRUE="$_JQ_BRIGHT;$_JQ_YELLOW"
JQ_FALSE="$_JQ_BRIGHT;$_JQ_RED"
JQ_NUMBERS="$_JQ_REGULAR;$_JQ_CYAN"
JQ_STRINGS="$_JQ_REGULAR;$_JQ_YELLOW"
JQ_ARRAYS="$_JQ_REGULAR;$_JQ_BLUE"
JQ_OBJECTS="$_JQ_BRIGHT;$_JQ_MAGENTA"
JQ_OBJECT_KEYS="$_JQ_REGULAR;$_JQ_GREEN"

export JQ_COLORS="${JQ_NULL}:${JQ_FALSE}:${JQ_TRUE}:${JQ_NUMBERS}:${JQ_STRINGS}:${JQ_ARRAYS}:${JQ_OBJECTS}:${JQ_OBJECT_KEYS}"

# Color and attribute definitions
RESET="0"
BOLD="01"
DIM="02"
BG_BLACK="40"

# Foreground colors
FG_BLACK="30"
FG_RED="31"
FG_GREEN="32"
FG_YELLOW="33"
FG_BLUE="34"
FG_MAGENTA="35"
FG_CYAN="36"
FG_WHITE="37"
FG_BRIGHT_YELLOW="93"
FG_BRIGHT_MAGENTA="95"

# Background colors
BG_RED="41"
BG_GREEN="42"
BG_YELLOW="43"
BG_BRIGHT_YELLOW="103"
BG_BLUE="44"

# Composite styles (using semicolon separator)
BOLD_RED="${BOLD};${FG_RED}"
BOLD_GREEN="${BOLD};${FG_GREEN}"
BOLD_CYAN="${BOLD};${FG_CYAN}"
BOLD_MAGENTA="${BOLD};${FG_MAGENTA}"
BOLD_BRIGHT_MAGENTA="${BOLD};${FG_BRIGHT_MAGENTA}"
BOLD_BRIGHT_YELLOW="${BOLD};${FG_BRIGHT_YELLOW}"
CYAN="${RESET};${FG_CYAN}"

BG_BLACK_YELLOW="${BG_BLACK};${FG_YELLOW}"
BG_BLACK_YELLOW_BOLD="${BG_BLACK};${FG_YELLOW};${BOLD}"
BG_BLACK_RED_BOLD="${BG_BLACK};${FG_RED};${BOLD}"
BG_RED_WHITE="${FG_WHITE};${BG_RED}"
BG_RED_BLACK="${FG_BLACK};${BG_RED}"
BG_YELLOW_BLACK="${FG_BLACK};${BG_BRIGHT_YELLOW}"
BG_GREEN_BLACK="${FG_BLACK};${BG_GREEN}"
BG_GREEN_BLUE="${FG_BLUE};${BG_GREEN}"
BG_BLUE_WHITE="${FG_WHITE};${BG_BLUE}"

# File type and special file colors
LSC_MISC="\
rs=${RESET}:\
di=${BG_YELLOW_BLACK}:\
ln=${BOLD_CYAN}:\
mh=${RESET}:\
pi=${BG_BLACK_YELLOW}:\
so=${BOLD_MAGENTA}:\
do=${BOLD_MAGENTA}:\
bd=${BG_BLACK_YELLOW_BOLD}:\
cd=${BG_BLACK_YELLOW_BOLD}:\
or=${BG_BLACK_RED_BOLD}:\
mi=${RESET}:\
su=${BG_RED_WHITE}:\
sg=${BG_YELLOW_BLACK}:\
ca=${BG_RED_BLACK}:\
tw=${BG_GREEN_BLACK}:\
ow=${BG_GREEN_BLUE}:\
st=${BG_BLUE_WHITE}:\
ex=${BOLD_GREEN}"

# Archive formats (bold red)
LSC_ARCHIVES="\
*.tar=${BOLD_RED}:\
*.tgz=${BOLD_RED}:\
*.arc=${BOLD_RED}:\
*.arj=${BOLD_RED}:\
*.taz=${BOLD_RED}:\
*.lha=${BOLD_RED}:\
*.lz4=${BOLD_RED}:\
*.lzh=${BOLD_RED}:\
*.lzma=${BOLD_RED}:\
*.tlz=${BOLD_RED}:\
*.txz=${BOLD_RED}:\
*.tzo=${BOLD_RED}:\
*.t7z=${BOLD_RED}:\
*.zip=${BOLD_RED}:\
*.z=${BOLD_RED}:\
*.dz=${BOLD_RED}:\
*.gz=${BOLD_RED}:\
*.lrz=${BOLD_RED}:\
*.lz=${BOLD_RED}:\
*.lzo=${BOLD_RED}:\
*.xz=${BOLD_RED}:\
*.zst=${BOLD_RED}:\
*.tzst=${BOLD_RED}:\
*.bz2=${BOLD_RED}:\
*.bz=${BOLD_RED}:\
*.tbz=${BOLD_RED}:\
*.tbz2=${BOLD_RED}:\
*.tz=${BOLD_RED}:\
*.deb=${BOLD_RED}:\
*.rpm=${BOLD_RED}:\
*.jar=${BOLD_RED}:\
*.war=${BOLD_RED}:\
*.ear=${BOLD_RED}:\
*.sar=${BOLD_RED}:\
*.rar=${BOLD_RED}:\
*.alz=${BOLD_RED}:\
*.ace=${BOLD_RED}:\
*.zoo=${BOLD_RED}:\
*.cpio=${BOLD_RED}:\
*.7z=${BOLD_RED}:\
*.rz=${BOLD_RED}:\
*.cab=${BOLD_RED}:\
*.wim=${BOLD_RED}:\
*.swm=${BOLD_RED}:\
*.dwm=${BOLD_RED}:\
*.esd=${BOLD_RED}"

# Image formats (bold bright magenta)
LSC_IMAGES="\
*.jpg=${BOLD_BRIGHT_MAGENTA}:\
*.jpeg=${BOLD_BRIGHT_MAGENTA}:\
*.mjpg=${BOLD_BRIGHT_MAGENTA}:\
*.mjpeg=${BOLD_BRIGHT_MAGENTA}:\
*.gif=${BOLD_BRIGHT_MAGENTA}:\
*.bmp=${BOLD_BRIGHT_MAGENTA}:\
*.pbm=${BOLD_BRIGHT_MAGENTA}:\
*.pgm=${BOLD_BRIGHT_MAGENTA}:\
*.ppm=${BOLD_BRIGHT_MAGENTA}:\
*.tga=${BOLD_BRIGHT_MAGENTA}:\
*.xbm=${BOLD_BRIGHT_MAGENTA}:\
*.xpm=${BOLD_BRIGHT_MAGENTA}:\
*.tif=${BOLD_BRIGHT_MAGENTA}:\
*.tiff=${BOLD_BRIGHT_MAGENTA}:\
*.png=${BOLD_BRIGHT_MAGENTA}:\
*.svg=${BOLD_BRIGHT_MAGENTA}:\
*.svgz=${BOLD_BRIGHT_MAGENTA}:\
*.mng=${BOLD_BRIGHT_MAGENTA}:\
*.pcx=${BOLD_BRIGHT_MAGENTA}"

# Video formats (mostly bold bright magenta, some bold magenta)
LSC_VIDEOS="\
*.mov=${BOLD_BRIGHT_MAGENTA}:\
*.mpg=${BOLD_BRIGHT_MAGENTA}:\
*.mpeg=${BOLD_BRIGHT_MAGENTA}:\
*.m2v=${BOLD_BRIGHT_MAGENTA}:\
*.mkv=${BOLD_BRIGHT_MAGENTA}:\
*.webm=${BOLD_BRIGHT_MAGENTA}:\
*.ogm=${BOLD_BRIGHT_MAGENTA}:\
*.mp4=${BOLD_BRIGHT_MAGENTA}:\
*.m4v=${BOLD_BRIGHT_MAGENTA}:\
*.mp4v=${BOLD_BRIGHT_MAGENTA}:\
*.vob=${BOLD_BRIGHT_MAGENTA}:\
*.qt=${BOLD_BRIGHT_MAGENTA}:\
*.nuv=${BOLD_BRIGHT_MAGENTA}:\
*.wmv=${BOLD_BRIGHT_MAGENTA}:\
*.asf=${BOLD_BRIGHT_MAGENTA}:\
*.rm=${BOLD_BRIGHT_MAGENTA}:\
*.rmvb=${BOLD_BRIGHT_MAGENTA}:\
*.flc=${BOLD_BRIGHT_MAGENTA}:\
*.avi=${BOLD_BRIGHT_MAGENTA}:\
*.fli=${BOLD_BRIGHT_MAGENTA}:\
*.flv=${BOLD_BRIGHT_MAGENTA}:\
*.gl=${BOLD_BRIGHT_MAGENTA}:\
*.dl=${BOLD_BRIGHT_MAGENTA}:\
*.xcf=${BOLD_BRIGHT_MAGENTA}:\
*.xwd=${BOLD_BRIGHT_MAGENTA}:\
*.yuv=${BOLD_BRIGHT_MAGENTA}:\
*.cgm=${BOLD_BRIGHT_MAGENTA}:\
*.emf=${BOLD_BRIGHT_MAGENTA}:\
*.ogv=${BOLD_MAGENTA}:\
*.ogx=${BOLD_MAGENTA}"

# Audio formats (normal cyan)
LSC_AUDIO="\
*.aac=${CYAN}:\
*.au=${CYAN}:\
*.flac=${CYAN}:\
*.m4a=${CYAN}:\
*.mid=${CYAN}:\
*.midi=${CYAN}:\
*.mka=${CYAN}:\
*.mp3=${CYAN}:\
*.mpc=${CYAN}:\
*.ogg=${CYAN}:\
*.ra=${CYAN}:\
*.wav=${CYAN}:\
*.oga=${CYAN}:\
*.opus=${CYAN}:\
*.spx=${CYAN}:\
*.xspf=${CYAN}"

export LS_COLORS="${LSC_MISC}:${LSC_ARCHIVES}:${LSC_IMAGES}:${LSC_VIDEOS}:${LSC_AUDIO}"
alias ls="ls --color=auto"
