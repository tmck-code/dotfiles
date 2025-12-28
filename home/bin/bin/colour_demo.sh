#!/bin/bash

echo -e "Default \e[39mDefault"
echo -e "Default \e[30mBlack"
echo -e "Default \e[31mRed"
echo -e "Default \e[32mGreen"
echo -e "Default \e[33mYellow"
echo -e "Default \e[34mBlue"
echo -e "Default \e[35mMagenta"
echo -e "Default \e[36mCyan"
echo -e "Default \e[37mLight gray"
echo -e "Default \e[90mDark gray"
echo -e "Default \e[91mLight red"
echo -e "Default \e[92mLight green"
echo -e "Default \e[93mLight yellow"
echo -e "Default \e[94mLight blue"
echo -e "Default \e[95mLight magenta"
echo -e "Default \e[96mLight cyan"
echo -e "Default \e[97mWhite"


function print_256_colours() {
  # From https://misc.flogisoft.com/bash/tip_colors_and_formatting
  local fgbg=$1

  echo "╭──────────────────────────────────────────────────────────────────────────╮"
  echo -n "│ "
  for color in {0..255} ; do
    # Display the color
    printf "\e[${fgbg};5;%sm  ${fgbg};5;%-3s  \e[0m" $color $color
    # Display 6 colors per lines
    if [ $((($color + 1) % 6)) == 4 ]; then
      if [ $color -eq 3 ] ; then
        echo -ne "                         │\n│ "
      elif [ $color -ne 255 ] ; then
        echo -ne " │\n│ "
      else
        echo -ne " │\n"
      fi
    fi
  done
  echo "╰──────────────────────────────────────────────────────────────────────────╯"
}

function print_8_16_colours() {
  # From https://misc.flogisoft.com/bash/tip_colors_and_formatting

  local reset="\e[0m"
  echo "╭───────────────────────────────────────────────╮"
  printf "│ 0;30m \e[0;30mBlack  ${reset}1;30m \e[1;30mbold 0;90m  \e[0;90mhigh intensity\e[0m │\n"
  printf "│ 0;31m \e[0;31mRed    ${reset}1;31m \e[1;31mbold 0;91m  \e[0;91mhigh intensity\e[0m │\n"
  printf "│ 0;32m \e[0;32mGreen  ${reset}1;32m \e[1;32mbold 0;92m  \e[0;92mhigh intensity\e[0m │\n"
  printf "│ 0;33m \e[0;33mYellow ${reset}1;33m \e[1;33mbold 0;93m  \e[0;93mhigh intensity\e[0m │\n"
  printf "│ 0;34m \e[0;34mBlue   ${reset}1;34m \e[1;34mbold 0;94m  \e[0;94mhigh intensity\e[0m │\n"
  printf "│ 0;35m \e[0;35mPurple ${reset}1;35m \e[1;35mbold 0;95m  \e[0;95mhigh intensity\e[0m │\n"
  printf "│ 0;36m \e[0;36mCyan   ${reset}1;36m \e[1;36mbold 0;96m  \e[0;96mhigh intensity\e[0m │\n"
  printf "│ 0;37m \e[0;37mWhite  ${reset}1;37m \e[1;37mbold 0;97m  \e[0;97mhigh intensity\e[0m │\n"

  printf "│ 0;40m \e[0;40mBlack  ${reset}1;40m \e[1;40mbold ${reset}0;100m \e[0;100mhigh intensity\e[0m │\n"
  printf "│ 0;41m \e[0;41mRed    ${reset}1;41m \e[1;41mbold ${reset}0;101m \e[0;101mhigh intensity\e[0m │\n"
  printf "│ 0;42m \e[0;42mGreen  ${reset}1;42m \e[1;42mbold ${reset}0;102m \e[0;102mhigh intensity\e[0m │\n"
  printf "│ 0;43m \e[0;43mYellow ${reset}1;43m \e[1;43mbold ${reset}0;103m \e[0;103mhigh intensity\e[0m │\n"
  printf "│ 0;44m \e[0;44mBlue   ${reset}1;44m \e[1;44mbold ${reset}0;104m \e[0;104mhigh intensity\e[0m │\n"
  printf "│ 0;45m \e[0;45mPurple ${reset}1;45m \e[1;45mbold ${reset}0;105m \e[0;105mhigh intensity\e[0m │\n"
  printf "│ 0;46m \e[0;46mCyan   ${reset}1;46m \e[1;46mbold ${reset}0;106m \e[0;106mhigh intensity\e[0m │\n"
  printf "│ 0;47m \e[0;47mWhite  ${reset}1;47m \e[1;47mbold ${reset}0;107m \e[0;107mhigh intensity\e[0m │\n"
  echo "╰───────────────────────────────────────────────╯"
}

echo "256 Colour Demo"
echo -e "\nForeground Colours:"
print_256_colours 38
echo -e "\nBackground Colours:"
print_256_colours 48

echo -e "\n8/16 Colour Demo"
print_8_16_colours 38
