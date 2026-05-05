#!/bin/bash

# set -euxo pipefail

alias g="git"
alias v="vim"

alias pip="python3 -m pip"
alias python="python3"

alias bmon="bmon -p enp4s0 -R 2.0 -o curses:fgchar='N' -o curses:bgchar=' ' -o curses:nchar='.'"

LESS_TERMCAP_mb=$(tput bold && tput setaf 2)                 # mb - begin bold mode                              - green
LESS_TERMCAP_md=$(tput bold && tput setaf 6)                 # md - begin double-bright mode                     - cyan
LESS_TERMCAP_me=$(tput sgr0)                                 # me - end mode (turn off all attributes)
LESS_TERMCAP_so=$(tput bold && tput setaf 3 && tput setab 4) # so - begin standout mode (reverse video)          - yellow on blue
LESS_TERMCAP_se=$(tput rmso && tput sgr0)                    # se - end standout mode
LESS_TERMCAP_us=$(tput smul && tput bold && tput setaf 7)    # us - begin underline mode                         - white and bold
LESS_TERMCAP_ue=$(tput rmul && tput sgr0)                    # ue - end underline mode
LESS_TERMCAP_mr=$(tput rev)                                  # mr - begin reverse mode
LESS_TERMCAP_mh=$(tput dim)                                  # mh - begin dim mode
LESS_TERMCAP_ZN=$(tput ssubm)                                # ZN - begin blinking mode
LESS_TERMCAP_ZV=$(tput rsubm)                                # ZV - end blinking mode
LESS_TERMCAP_ZO=$(tput ssupm)                                # ZO - begin bold mode (often used for bold colors)
LESS_TERMCAP_ZW=$(tput rsupm)                                # ZW - end bold mode (often used for bold colors)

export \
  LESS_TERMCAP_mb LESS_TERMCAP_md LESS_TERMCAP_me LESS_TERMCAP_so \
  LESS_TERMCAP_se LESS_TERMCAP_us LESS_TERMCAP_ue LESS_TERMCAP_mr \
  LESS_TERMCAP_mh LESS_TERMCAP_ZN LESS_TERMCAP_ZV LESS_TERMCAP_ZO \
  LESS_TERMCAP_ZW

export GROFF_NO_SGR=1             # For Konsole and Gnome-terminal
export LESS="--RAW-CONTROL-CHARS" # Allow ANSI colours in less

alias sort="LC_ALL=C sort" # Makes GNU sort _much_ faster
alias grep="grep --color"  # Enable grep colours
alias gpurge="git fetch origin --prune && git branch --merged | grep -v 'master\|main' | xargs git branch -d &> /dev/null || echo nothing to remove!"

alias dush="du -sh * | sort -h"
alias emacs="emacs -nw"

alias code="/usr/share/code/bin/code"

alias dark='gsettings set org.gnome.desktop.interface gtk-theme Adwaita-dark \
&& gsettings set org.gnome.desktop.interface color-scheme prefer-dark'

alias light='gsettings set org.gnome.desktop.interface gtk-theme Adwaita \
&& gsettings set org.gnome.desktop.interface color-scheme prefer-light'

function ppj-clipboard() {
  xclip -o -selection clipboard | jq | xclip -i -selection clipboard
}

_REGULAR=0 ; _BRIGHT=1 ; _DIM=2 ; _ITALIC=3; _UNDERSCORE=4 ; _BLINK=5 ; _REVERSE=7 ; _HIDDEN=8
_FG_BLACK=30   ; _FG_BRIGHT_BLACK=90   ; _BG_BLACK=40   ; _BG_BRIGHT_BLACK=100  ;
_FG_RED=31     ; _FG_BRIGHT_RED=91     ; _BG_RED=41     ; _BG_BRIGHT_RED=101    ;
_FG_GREEN=32   ; _FG_BRIGHT_GREEN=92   ; _BG_GREEN=42   ; _BG_BRIGHT_GREEN=102  ;
_FG_YELLOW=33  ; _FG_BRIGHT_YELLOW=93  ; _BG_YELLOW=43  ; _BG_BRIGHT_YELLOW=103 ;
_FG_BLUE=34    ; _FG_BRIGHT_BLUE=94    ; _BG_BLUE=44    ; _BG_BRIGHT_BLUE=104   ;
_FG_MAGENTA=35 ; _FG_BRIGHT_MAGENTA=95 ; _BG_MAGENTA=45 ; _BG_BRIGHT_MAGENTA=105 ;
_FG_CYAN=36    ; _FG_BRIGHT_CYAN=96    ; _BG_CYAN=46    ; _BG_BRIGHT_CYAN=106   ;
_FG_WHITE=37   ; _FG_BRIGHT_WHITE=97   ; _BG_WHITE=47   ; _BG_BRIGHT_WHITE=107  ;

JQ_NULL="$_UNDERSCORE;$_FG_WHITE"
JQ_TRUE="$_BRIGHT;$_FG_GREEN"
JQ_FALSE="$_BRIGHT;$_FG_RED"
JQ_NUMBERS="$_REGULAR;$_FG_CYAN"
JQ_STRINGS="$_REGULAR;$_FG_YELLOW"
JQ_ARRAYS="$_REGULAR;$_FG_GREEN"
JQ_OBJECTS="$_REGULAR;$_FG_RED"
JQ_OBJECT_KEYS="$_REGULAR;$_FG_WHITE"

export JQ_COLORS="${JQ_NULL}:${JQ_FALSE}:${JQ_TRUE}:${JQ_NUMBERS}:${JQ_STRINGS}:${JQ_ARRAYS}:${JQ_OBJECTS}:${JQ_OBJECT_KEYS}"

# File type and special file colors
LSC_MISC="\
rs=$_RESET:\
di=$_ITALIC;$_BG_BLACK;$_FG_YELLOW:\
ln=$_BOLD;$_FG_CYAN:\
mh=$_RESET:\
pi=$_BG_BLACK;$_FG_YELLOW:\
so=$_BOLD;$_FG_MAGENTA:\
do=$_BOLD;$_FG_MAGENTA:\
bd=$_BG_BLACK;$_FG_YELLOW;$_BOLD:\
cd=$_BG_BLACK;$_FG_YELLOW;$_BOLD:\
or=$_BG_BLACK;$_FG_RED;$_BOLD:\
mi=$_RESET:\
su=$_FG_WHITE;$_BG_RED:\
sg=$_FG_BLACK;$_BG_BRIGHT_YELLOW:\
ca=$_FG_BLACK;$_BG_RED:\
tw=$_FG_BLACK;$_BG_GREEN:\
ow=$_ITALIC;$_BG_BLACK;$_FG_GREEN:\
st=$_FG_WHITE;$_BG_BLUE:\
ex=$_RESET;$_ITALIC;$_BRIGHT;$_FG_RED:\
fi=$_FG_WHITE$_BOLD"

LSC_TEXT="\
*.txt=$_RESET;$_FG_WHITE;$_BOLD:\
*.log=$_RESET;$_ITALIC;$_DIM;$_FG_WHITE:\
*.csv=$_RESET;$_ITALIC;$_BRIGHT;$_FG_WHITE:\
*.json=$_RESET;$_ITALIC;$_BRIGHT;$_FG_WHITE:\
*.xml=$_RESET;$_BOLD;$_FG_GREEN:\
*.html=$_RESET;$_BOLD;$_FG_GREEN:\
*.md=$_RESET;$_ITALIC;$_BRIGHT;$_FG_BLUE:\
*.yaml=$_RESET;$_ITALIC;$_BRIGHT;$_FG_BLUE:\
*.yml=$_RESET;$_ITALIC;$_BRIGHT;$_FG_BLUE:\
*.toml=$_RESET;$_ITALIC;$_BRIGHT;$_FG_BLUE:\
*uv.lock=$_RESET;$_ITALIC;$_BRIGHT;$_FG_BLUE:\
*.py=$_RESET;$_ITALIC;$_BRIGHT;$_FG_RED"

# Archive formats (bold red)
LSC_ARCHIVES="\
*.tar=$_BOLD;$_FG_RED:\
*.tgz=$_BOLD;$_FG_RED:\
*.arc=$_BOLD;$_FG_RED:\
*.arj=$_BOLD;$_FG_RED:\
*.taz=$_BOLD;$_FG_RED:\
*.lha=$_BOLD;$_FG_RED:\
*.lz4=$_BOLD;$_FG_RED:\
*.lzh=$_BOLD;$_FG_RED:\
*.lzma=$_BOLD;$_FG_RED:\
*.tlz=$_BOLD;$_FG_RED:\
*.txz=$_BOLD;$_FG_RED:\
*.tzo=$_BOLD;$_FG_RED:\
*.t7z=$_BOLD;$_FG_RED:\
*.zip=$_BOLD;$_FG_RED:\
*.z=$_BOLD;$_FG_RED:\
*.dz=$_BOLD;$_FG_RED:\
*.gz=$_BOLD;$_FG_RED:\
*.lrz=$_BOLD;$_FG_RED:\
*.lz=$_BOLD;$_FG_RED:\
*.lzo=$_BOLD;$_FG_RED:\
*.xz=$_BOLD;$_FG_RED:\
*.zst=$_BOLD;$_FG_RED:\
*.tzst=$_BOLD;$_FG_RED:\
*.bz2=$_BOLD;$_FG_RED:\
*.bz=$_BOLD;$_FG_RED:\
*.tbz=$_BOLD;$_FG_RED:\
*.tbz2=$_BOLD;$_FG_RED:\
*.tz=$_BOLD;$_FG_RED:\
*.deb=$_BOLD;$_FG_RED:\
*.rpm=$_BOLD;$_FG_RED:\
*.jar=$_BOLD;$_FG_RED:\
*.war=$_BOLD;$_FG_RED:\
*.ear=$_BOLD;$_FG_RED:\
*.sar=$_BOLD;$_FG_RED:\
*.rar=$_BOLD;$_FG_RED:\
*.alz=$_BOLD;$_FG_RED:\
*.ace=$_BOLD;$_FG_RED:\
*.zoo=$_BOLD;$_FG_RED:\
*.cpio=$_BOLD;$_FG_RED:\
*.7z=$_BOLD;$_FG_RED:\
*.rz=$_BOLD;$_FG_RED:\
*.cab=$_BOLD;$_FG_RED:\
*.wim=$_BOLD;$_FG_RED:\
*.swm=$_BOLD;$_FG_RED:\
*.dwm=$_BOLD;$_FG_RED:\
*.esd=$_BOLD;$_FG_RED"

# Image formats (bold bright magenta)
LSC_IMAGES="\
*.jpg=$_FG_BRIGHT_MAGENTA:\
*.jpeg=$_FG_BRIGHT_MAGENTA:\
*.mjpg=$_FG_BRIGHT_MAGENTA:\
*.mjpeg=$_FG_BRIGHT_MAGENTA:\
*.gif=$_FG_BRIGHT_MAGENTA:\
*.bmp=$_FG_BRIGHT_MAGENTA:\
*.pbm=$_FG_BRIGHT_MAGENTA:\
*.pgm=$_FG_BRIGHT_MAGENTA:\
*.ppm=$_FG_BRIGHT_MAGENTA:\
*.tga=$_FG_BRIGHT_MAGENTA:\
*.xbm=$_FG_BRIGHT_MAGENTA:\
*.xpm=$_FG_BRIGHT_MAGENTA:\
*.tif=$_FG_BRIGHT_MAGENTA:\
*.tiff=$_FG_BRIGHT_MAGENTA:\
*.png=$_FG_BRIGHT_MAGENTA:\
*.svg=$_FG_BRIGHT_MAGENTA:\
*.svgz=$_FG_BRIGHT_MAGENTA:\
*.mng=$_FG_BRIGHT_MAGENTA:\
*.pcx=$_FG_BRIGHT_MAGENTA"

# Video formats (mostly bold bright magenta, some bold magenta)
LSC_VIDEOS="\
*.mov=$_BOLD;$_FG_BRIGHT_MAGENTA:\
*.mpg=$_BOLD;$_FG_BRIGHT_MAGENTA:\
*.mpeg=$_BOLD;$_FG_BRIGHT_MAGENTA:\
*.m2v=$_BOLD;$_FG_BRIGHT_MAGENTA:\
*.mkv=$_BOLD;$_FG_BRIGHT_MAGENTA:\
*.webm=$_BOLD;$_FG_BRIGHT_MAGENTA:\
*.ogm=$_BOLD;$_FG_BRIGHT_MAGENTA:\
*.mp4=$_BOLD;$_FG_BRIGHT_MAGENTA:\
*.m4v=$_BOLD;$_FG_BRIGHT_MAGENTA:\
*.mp4v=$_BOLD;$_FG_BRIGHT_MAGENTA:\
*.vob=$_BOLD;$_FG_BRIGHT_MAGENTA:\
*.qt=$_BOLD;$_FG_BRIGHT_MAGENTA:\
*.nuv=$_BOLD;$_FG_BRIGHT_MAGENTA:\
*.wmv=$_BOLD;$_FG_BRIGHT_MAGENTA:\
*.asf=$_BOLD;$_FG_BRIGHT_MAGENTA:\
*.rm=$_BOLD;$_FG_BRIGHT_MAGENTA:\
*.rmvb=$_BOLD;$_FG_BRIGHT_MAGENTA:\
*.flc=$_BOLD;$_FG_BRIGHT_MAGENTA:\
*.avi=$_BOLD;$_FG_BRIGHT_MAGENTA:\
*.fli=$_BOLD;$_FG_BRIGHT_MAGENTA:\
*.flv=$_BOLD;$_FG_BRIGHT_MAGENTA:\
*.gl=$_BOLD;$_FG_BRIGHT_MAGENTA:\
*.dl=$_BOLD;$_FG_BRIGHT_MAGENTA:\
*.xcf=$_BOLD;$_FG_BRIGHT_MAGENTA:\
*.xwd=$_BOLD;$_FG_BRIGHT_MAGENTA:\
*.yuv=$_BOLD;$_FG_BRIGHT_MAGENTA:\
*.cgm=$_BOLD;$_FG_BRIGHT_MAGENTA:\
*.emf=$_BOLD;$_FG_BRIGHT_MAGENTA:\
*.ogv=$_BOLD;$_FG_MAGENTA:\
*.ogx=$_BOLD;$_FG_MAGENTA"

# Audio formats (normal cyan)
LSC_AUDIO="\
*.aac=$_FG_CYAN:\
*.au=$_FG_CYAN:\
*.flac=$_FG_CYAN:\
*.m4a=$_FG_CYAN:\
*.mid=$_FG_CYAN:\
*.midi=$_FG_CYAN:\
*.mka=$_FG_CYAN:\
*.mp3=$_FG_CYAN:\
*.mpc=$_FG_CYAN:\
*.ogg=$_FG_CYAN:\
*.ra=$_FG_CYAN:\
*.wav=$_FG_CYAN:\
*.oga=$_FG_CYAN:\
*.opus=$_FG_CYAN:\
*.spx=$_FG_CYAN:\
*.xspf=$_FG_CYAN"

export LS_COLORS="${LSC_MISC}:${LSC_TEXT}:${LSC_ARCHIVES}:${LSC_IMAGES}:${LSC_VIDEOS}:${LSC_AUDIO}"
alias ls="ls --color=auto"
