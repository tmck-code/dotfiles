#!/bin/bash

alias g="git"
alias v="vim"

alias pip="python3 -m pip"
alias python="python3"

LS_COLORS_MISC="rs=0:di=02;93:ln=01;36:mh=00:pi=40;33:so=01;35:do=01;35:bd=40;33;01:cd=40;33;01:or=40;31;01:mi=00:su=37;41:sg=30;43:ca=30;41:tw=30;42:ow=34;42:st=37;44:ex=01;32"
LS_COLORS_ARCHIVES="*.tar=01;31:*.tgz=01;31:*.arc=01;31:*.arj=01;31:*.taz=01;31:*.lha=01;31:*.lz4=01;31:*.lzh=01;31:*.lzma=01;31:*.tlz=01;31:*.txz=01;31:*.tzo=01;31:*.t7z=01;31:*.zip=01;31:*.z=01;31:*.dz=01;31:*.gz=01;31:*.lrz=01;31:*.lz=01;31:*.lzo=01;31:*.xz=01;31:*.zst=01;31:*.tzst=01;31:*.bz2=01;31:*.bz=01;31:*.tbz=01;31:*.tbz2=01;31:*.tz=01;31:*.deb=01;31:*.rpm=01;31:*.jar=01;31:*.war=01;31:*.ear=01;31:*.sar=01;31:*.rar=01;31:*.alz=01;31:*.ace=01;31:*.zoo=01;31:*.cpio=01;31:*.7z=01;31:*.rz=01;31:*.cab=01;31:*.wim=01;31:*.swm=01;31:*.dwm=01;31:*.esd=01;31"
LS_COLORS_IMAGES="*.jpg=01;95:*.jpeg=01;95:*.mjpg=01;95:*.mjpeg=01;95:*.gif=01;95:*.bmp=01;95:*.pbm=01;95:*.pgm=01;95:*.ppm=01;95:*.tga=01;95:*.xbm=01;95:*.xpm=01;95:*.tif=01;95:*.tiff=01;95:*.png=01;95:*.svg=01;95:*.svgz=01;95:*.mng=01;95:*.pcx=01;95"
LS_COLORS_VIDEOS="*.mov=01;95:*.mpg=01;95:*.mpeg=01;95:*.m2v=01;95:*.mkv=01;95:*.webm=01;95:*.ogm=01;95:*.mp4=01;95:*.m4v=01;95:*.mp4v=01;95:*.vob=01;95:*.qt=01;95:*.nuv=01;95:*.wmv=01;95:*.asf=01;95:*.rm=01;95:*.rmvb=01;95:*.flc=01;95:*.avi=01;95:*.fli=01;95:*.flv=01;95:*.gl=01;95:*.dl=01;95:*.xcf=01;95:*.xwd=01;95:*.yuv=01;95:*.cgm=01;95:*.emf=01;95:*.ogv=01;35:*.ogx=01;35"
LS_COLORS_AUDIO="*.aac=00;36:*.au=00;36:*.flac=00;36:*.m4a=00;36:*.mid=00;36:*.midi=00;36:*.mka=00;36:*.mp3=00;36:*.mpc=00;36:*.ogg=00;36:*.ra=00;36:*.wav=00;36:*.oga=00;36:*.opus=00;36:*.spx=00;36:*.xspf=00;36"
export LS_COLORS="${LS_COLORS_MISC}:${LS_COLORS_ARCHIVES}:${LS_COLORS_IMAGES}:${LS_COLORS_VIDEOS}:${LS_COLORS_AUDIO}"
alias ls="ls --color=auto"

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
